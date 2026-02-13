from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import random
from pathlib import Path


AGENTS = ["planner_agent", "writer_agent", "verifier_agent", "ops_agent"]
TASKS = [
    "parser_refactor",
    "retrieval_latency",
    "memory_budget",
    "merge_guard_policy",
    "semantic_precision",
]
MODES = ["fast", "safe", "balanced", "strict"]
ALPHAS = ["0.2", "0.4", "0.6", "0.8"]
PATHS = [
    "src/memory_cluster/cluster.py",
    "src/memory_cluster/compress.py",
    "src/memory_cluster/pipeline.py",
    "tests/test_merge_candidate_filter.py",
    "docs/patent_kit/06_\u6743\u5229\u8981\u6c42\u4e66_\u8349\u6848.md",
]


def _pick_conflict_mode(mode: str, idx: int) -> str:
    for offset in (1, 2, 3):
        alt = MODES[(idx + offset) % len(MODES)]
        if alt != mode:
            return alt
    return MODES[(idx + 1) % len(MODES)]


def _build_pattern_payload(
    *,
    idx: int,
    task: str,
    mode: str,
    alpha: str,
    path: str,
    rng: random.Random,
    profile: str,
) -> tuple[str, str, dict[str, str]]:
    conflict_mode = _pick_conflict_mode(mode, idx)
    pattern = idx % 10

    if pattern == 0:
        return (
            f"For {task}, keep mode={mode} to reduce retries in this run.",
            "decision",
            {"category": "method", "scope": "current_task"},
        )

    if pattern == 1:
        return (
            f"\u5bf9\u4e8e {task}\uff0c\u4e0d\u662f mode={conflict_mode}\uff0c\u5efa\u8bae mode={mode}\uff0c\u5426\u5219\u9519\u8bef\u7387\u4e0a\u5347\u3002",
            "draft",
            {"category": "method", "lang": "zh"},
        )

    if pattern == 2:
        return (
            f"If latency spikes then alpha={alpha}; otherwise keep previous alpha.",
            "result",
            {"category": "evidence"},
        )

    if pattern == 3:
        return (
            f"\u5e76\u975e alpha={alpha} \u4e00\u5b9a\u6700\u4f18\uff0c\u53ea\u5728\u6761\u4ef6\u6ee1\u8db3\u65f6\u91c7\u7528\u3002",
            "result",
            {"category": "evidence", "lang": "zh"},
        )

    if pattern == 4:
        return (
            f"Tool log: replay_id={idx} file={path} status=ok duration={80 + (idx % 31)}ms",
            "log",
            {"category": "noise"},
        )

    if pattern == 5:
        return (
            f"Global policy: protect {path} and keep evidence for {task}.",
            "policy",
            {"category": "preference", "global_task": "1"},
        )

    if pattern == 6:
        return (
            f"Counterfactual: should have used mode={conflict_mode}, now enforce mode={mode}.",
            "draft",
            {"category": "method"},
        )

    if pattern == 7:
        deploy_flag = "rollback" if rng.random() < 0.5 else "hotfix"
        return (
            f"When deploy={deploy_flag}, do not set mode={mode} before verifier approval.",
            "draft",
            {"category": "method"},
        )

    if pattern == 8:
        return (
            f"If file_path={path} and task={task}, enable safeguard and keep alpha={alpha}.",
            "policy",
            {"category": "preference", "current_task": "1"},
        )

    if profile == "stress":
        return (
            f"Conflict replay: mode={mode}; later mode={conflict_mode}; finally not mode={conflict_mode}.",
            "draft",
            {"category": "method"},
        )
    return (
        f"Review note: task={task} mode={mode} alpha={alpha} file={path}.",
        "result",
        {"category": "evidence"},
    )


def _row(idx: int, ts: str, rng: random.Random, profile: str) -> dict[str, object]:
    task = TASKS[idx % len(TASKS)]
    mode = MODES[(idx * 3) % len(MODES)]
    alpha = ALPHAS[(idx * 5) % len(ALPHAS)]
    agent = AGENTS[idx % len(AGENTS)]
    path = PATHS[(idx * 7) % len(PATHS)]
    content, ftype, tags = _build_pattern_payload(
        idx=idx,
        task=task,
        mode=mode,
        alpha=alpha,
        path=path,
        rng=rng,
        profile=profile,
    )
    meta = {
        "slots": {"task": task, "mode": mode, "alpha": alpha},
        "file_path": path,
        "run_id": f"semi_real_{idx // 50:03d}",
        "profile": profile,
    }
    return {
        "id": f"sr{idx:06d}",
        "agent_id": agent,
        "timestamp": ts,
        "content": content,
        "type": ftype,
        "tags": tags,
        "meta": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate semi-real multi-agent memory fragments dataset")
    parser.add_argument("--output", required=True)
    parser.add_argument("--fragment-count", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=20260211)
    parser.add_argument("--profile", choices=["realistic", "stress"], default="realistic")
    args = parser.parse_args()

    count = max(100, int(args.fragment_count))
    rng = random.Random(int(args.seed))
    start = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for idx in range(count):
            ts = (start + timedelta(minutes=idx)).isoformat()
            payload = _row(idx=idx, ts=ts, rng=rng, profile=str(args.profile))
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(out_path),
                "fragment_count": count,
                "seed": int(args.seed),
                "profile": str(args.profile),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
