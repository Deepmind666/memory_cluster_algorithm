from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import subprocess
import sys
import time
from typing import Sequence


def _run(cmd: Sequence[str]) -> None:
    print(f"[ci-guardrail] run: {' '.join(cmd)}", flush=True)
    started = time.perf_counter()
    subprocess.run(cmd, check=True)
    elapsed = time.perf_counter() - started
    print(f"[ci-guardrail] done ({elapsed:.2f}s): {' '.join(cmd)}", flush=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_semi_real_dataset(path: Path, *, fragment_count: int, seed: int, profile: str) -> None:
    agents = ["planner_agent", "writer_agent", "verifier_agent", "ops_agent"]
    tasks = ["parser_refactor", "retrieval_latency", "memory_budget", "merge_guard_policy", "semantic_precision"]
    modes = ["fast", "safe", "balanced", "strict"]
    alphas = ["0.2", "0.4", "0.6", "0.8"]
    rng = random.Random(int(seed))
    start = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for idx in range(max(80, int(fragment_count))):
            task = tasks[idx % len(tasks)]
            mode = modes[(idx * 3) % len(modes)]
            alpha = alphas[(idx * 5) % len(alphas)]
            alt_mode = modes[(idx * 3 + 1) % len(modes)]
            ts = (start + timedelta(minutes=idx)).isoformat()
            text_mode = (
                f"for {task}, keep mode={mode}, alpha={alpha}, run={idx}"
                if profile == "realistic"
                else f"conflict replay: mode={mode}; then mode={alt_mode}; not mode={alt_mode}; run={idx}"
            )
            if idx % 5 == 0:
                content = f"policy path=src/memory_cluster/cluster.py {text_mode}"
                ftype = "policy"
                tags = {"category": "preference"}
            elif idx % 3 == 0:
                content = f"result {text_mode}"
                ftype = "result"
                tags = {"category": "evidence"}
            else:
                content = f"draft {text_mode}"
                ftype = "draft"
                tags = {"category": "method"}
            row = {
                "id": f"ci_sr_{profile}_{idx:05d}",
                "agent_id": agents[idx % len(agents)],
                "timestamp": ts,
                "content": content,
                "type": ftype,
                "tags": tags,
                "meta": {
                    "slots": {"task": task, "mode": mode, "alpha": alpha},
                    "profile": profile,
                    "seed": int(seed),
                },
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight stage-2 guardrail bundle for CI")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter path")
    parser.add_argument("--seed", type=int, default=20260213)
    parser.add_argument("--dataset-size", type=int, default=240)
    parser.add_argument("--benchmark-fragment-count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--warmup-runs", type=int, default=0)
    args = parser.parse_args()

    py = str(args.python)
    size = max(120, int(args.dataset_size))
    frag_count = max(80, int(args.benchmark_fragment_count))
    runs = max(1, int(args.runs))
    warmups = max(0, int(args.warmup_runs))

    outputs = Path("outputs")
    outputs.mkdir(parents=True, exist_ok=True)
    ci_reports = outputs / "ci_reports"
    ci_reports.mkdir(parents=True, exist_ok=True)

    realistic_dataset = outputs / f"ci_semi_real_{size}_realistic.jsonl"
    stress_dataset = outputs / f"ci_semi_real_{size}_stress.jsonl"
    _write_semi_real_dataset(realistic_dataset, fragment_count=size, seed=int(args.seed), profile="realistic")
    _write_semi_real_dataset(stress_dataset, fragment_count=size, seed=int(args.seed), profile="stress")

    _run(
        [
            py,
            "scripts/run_candidate_filter_benchmark.py",
            "--output",
            "outputs/candidate_filter_benchmark.json",
            "--report",
            (ci_reports / "candidate_filter_benchmark_report.md").as_posix(),
            "--fragment-count",
            str(frag_count),
            "--runs",
            str(runs),
            "--warmup-runs",
            str(warmups),
        ]
    )
    _run(
        [
            py,
            "scripts/run_candidate_profile_validation.py",
            "--dataset-label",
            "synthetic_active_ci",
            "--output",
            "outputs/candidate_profile_validation_synthetic_active.json",
            "--report",
            (ci_reports / "candidate_profile_validation_synthetic_active_report.md").as_posix(),
            "--sizes",
            str(size),
            "--runs",
            str(runs),
            "--warmup-runs",
            str(warmups),
            "--similarity-threshold",
            "0.82",
            "--merge-threshold",
            "0.85",
        ]
    )
    _run(
        [
            py,
            "scripts/run_candidate_profile_validation.py",
            "--dataset-input",
            realistic_dataset.as_posix(),
            "--dataset-label",
            "semi_real_realistic_ci",
            "--output",
            "outputs/candidate_profile_validation_realistic.json",
            "--report",
            (ci_reports / "candidate_profile_validation_realistic_report.md").as_posix(),
            "--sizes",
            str(size),
            "--runs",
            str(runs),
            "--warmup-runs",
            str(warmups),
            "--similarity-threshold",
            "0.68",
            "--merge-threshold",
            "0.82",
        ]
    )
    _run(
        [
            py,
            "scripts/run_candidate_profile_validation.py",
            "--dataset-input",
            stress_dataset.as_posix(),
            "--dataset-label",
            "semi_real_stress_ci",
            "--output",
            "outputs/candidate_profile_validation_stress.json",
            "--report",
            (ci_reports / "candidate_profile_validation_stress_report.md").as_posix(),
            "--sizes",
            str(size),
            "--runs",
            str(runs),
            "--warmup-runs",
            str(warmups),
            "--similarity-threshold",
            "1.1",
            "--merge-threshold",
            "0.05",
        ]
    )
    _run(
        [
            py,
            "scripts/run_ann_hybrid_benchmark.py",
            "--output",
            "outputs/ann_hybrid_benchmark.json",
            "--report",
            (ci_reports / "ann_hybrid_benchmark_report.md").as_posix(),
            "--fragment-count",
            str(frag_count),
            "--runs",
            str(runs),
            "--warmup-runs",
            str(warmups),
        ]
    )
    _run(
        [
            py,
            "scripts/run_stage2_guardrail.py",
            "--output",
            "outputs/stage2_guardrail.json",
            "--report",
            (ci_reports / "stage2_guardrail_report.md").as_posix(),
        ]
    )

    result = _read_json(Path("outputs/stage2_guardrail.json"))
    passed = bool((result.get("summary") or {}).get("passed"))
    blockers = int((result.get("summary") or {}).get("blocker_failures") or 0)
    warnings = int((result.get("summary") or {}).get("warning_failures") or 0)
    print(
        json.dumps(
            {
                "status": "ok" if passed else "failed",
                "stage2_guardrail_passed": passed,
                "blocker_failures": blockers,
                "warning_failures": warnings,
                "guardrail_file": "outputs/stage2_guardrail.json",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
