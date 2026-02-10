from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.memory_cluster.embed import HashEmbeddingProvider
from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result
from src.memory_cluster.retrieve import MemoryRetriever


def _base_fragments() -> list[MemoryFragment]:
    return [
        MemoryFragment(
            id="ab01",
            agent_id="planner_agent",
            timestamp="2026-02-09T09:00:00+00:00",
            content="Parser strategy mode fast for throughput in current task.",
            type="decision",
            tags={"category": "method", "scope": "current_task"},
            meta={"slots": {"mode": "fast"}, "file_path": "src/parser/strategy.py"},
        ),
        MemoryFragment(
            id="ab02",
            agent_id="writer_agent",
            timestamp="2026-02-09T09:01:00+00:00",
            content="Parser strategy mode safe for reliability in current task.",
            type="draft",
            tags={"category": "method", "scope": "current_task"},
            meta={"slots": {"mode": "safe"}, "file_path": "src/parser/strategy.py"},
        ),
        MemoryFragment(
            id="ab03",
            agent_id="planner_agent",
            timestamp="2026-02-09T09:02:00+00:00",
            content="Parser strategy mode fast keeps speed under load.",
            type="draft",
            tags={"category": "method"},
            meta={"slots": {"mode": "fast"}},
        ),
        MemoryFragment(
            id="ab04",
            agent_id="writer_agent",
            timestamp="2026-02-09T09:03:00+00:00",
            content="Parser strategy mode safe keeps correctness under load.",
            type="draft",
            tags={"category": "method"},
            meta={"slots": {"mode": "safe"}},
        ),
        MemoryFragment(
            id="ab05",
            agent_id="verifier_agent",
            timestamp="2026-02-09T09:05:00+00:00",
            content="Experiment alpha=0.7 gives better quick score.",
            type="result",
            tags={"category": "evidence"},
            meta={"slots": {"alpha": "0.7"}},
        ),
        MemoryFragment(
            id="ab06",
            agent_id="verifier_agent",
            timestamp="2026-02-09T09:06:00+00:00",
            content="Experiment alpha=0.2 gives better stable score.",
            type="result",
            tags={"category": "evidence"},
            meta={"slots": {"alpha": "0.2"}},
        ),
        MemoryFragment(
            id="ab07",
            agent_id="verifier_agent",
            timestamp="2026-02-09T09:07:00+00:00",
            content="Experiment alpha=0.7 observed again in replay.",
            type="result",
            tags={"category": "evidence"},
            meta={"slots": {"alpha": "0.7"}},
        ),
        MemoryFragment(
            id="ab08",
            agent_id="writer_agent",
            timestamp="2026-02-01T09:00:00+00:00",
            content="Old noisy log line for parser benchmark.",
            type="log",
            tags={"category": "noise"},
            meta={"file_path": "logs/old_run.log"},
        ),
        MemoryFragment(
            id="ab09",
            agent_id="planner_agent",
            timestamp="2026-02-09T09:10:00+00:00",
            content="Global task: preserve patent-kit evidence and conflict chain.",
            type="policy",
            tags={"category": "preference", "global_task": "1"},
            meta={"file_path": "docs/patent_kit/05_具体实施方式.md"},
        ),
    ]


def synthetic_fragments(fragment_count: int = 9) -> list[MemoryFragment]:
    base = _base_fragments()
    target = max(1, int(fragment_count))
    if target <= len(base):
        return base[:target]

    rows = list(base)
    start = datetime(2026, 2, 9, 9, 11, tzinfo=timezone.utc)
    mode_values = ["fast", "safe", "balanced"]
    alpha_values = ["0.7", "0.2", "0.4"]
    agents = ["planner_agent", "writer_agent", "verifier_agent"]

    for idx in range(len(base) + 1, target + 1):
        offset = idx - len(base) - 1
        ts = (start + timedelta(minutes=offset)).isoformat()
        mode = mode_values[offset % len(mode_values)]
        alpha = alpha_values[(offset * 2) % len(alpha_values)]
        agent_id = agents[offset % len(agents)]
        cid = f"ab{idx:04d}"

        if offset % 6 == 0:
            rows.append(
                MemoryFragment(
                    id=cid,
                    agent_id=agent_id,
                    timestamp=ts,
                    content=f"如果 mode={mode} 则提升吞吐，但本应 mode=safe 保持稳定。",
                    type="draft",
                    tags={"category": "method"},
                    meta={"slots": {"mode": mode}},
                )
            )
            continue

        if offset % 6 == 1:
            rows.append(
                MemoryFragment(
                    id=cid,
                    agent_id=agent_id,
                    timestamp=ts,
                    content=f"alpha != {alpha} is risky for this replay window.",
                    type="result",
                    tags={"category": "evidence"},
                    meta={"slots": {"alpha": alpha}},
                )
            )
            continue

        if offset % 6 == 2:
            rows.append(
                MemoryFragment(
                    id=cid,
                    agent_id=agent_id,
                    timestamp=ts,
                    content=f"Parser strategy mode {mode} with alpha={alpha} for mixed traffic.",
                    type="draft",
                    tags={"category": "method"},
                    meta={"slots": {"mode": mode, "alpha": alpha}},
                )
            )
            continue

        if offset % 6 == 3:
            rows.append(
                MemoryFragment(
                    id=cid,
                    agent_id=agent_id,
                    timestamp=ts,
                    content=f"Old noisy log line {idx} for parser benchmark replay.",
                    type="log",
                    tags={"category": "noise"},
                    meta={"file_path": f"logs/run_{idx}.log"},
                )
            )
            continue

        if offset % 6 == 4:
            rows.append(
                MemoryFragment(
                    id=cid,
                    agent_id=agent_id,
                    timestamp=ts,
                    content=f"Counterfactual: should have alpha={alpha} if latency spikes.",
                    type="result",
                    tags={"category": "evidence"},
                    meta={"slots": {"alpha": alpha}},
                )
            )
            continue

        rows.append(
            MemoryFragment(
                id=cid,
                agent_id=agent_id,
                timestamp=ts,
                content=f"Global task checkpoint {idx}: preserve conflict chain and key evidence.",
                type="policy",
                tags={"category": "preference", "global_task": "1"},
                meta={"file_path": "docs/patent_kit/05_具体实施方式.md"},
            )
        )

    return rows


def _slot_mixing_count(result: Any, slot_name: str) -> int:
    by_id = {item.id: item for item in result.fragments}
    count = 0
    for cluster in result.clusters:
        if int(cluster.level) != 1:
            continue
        values: set[str] = set()
        for fid in cluster.fragment_ids:
            fragment = by_id.get(fid)
            if fragment is None:
                continue
            slots = fragment.meta.get("slots")
            if isinstance(slots, dict) and slot_name in slots:
                values.add(str(slots.get(slot_name)))
        if len(values) > 1:
            count += 1
    return count


def _scenario_pref(base: PreferenceConfig, overrides: dict[str, Any]) -> PreferenceConfig:
    payload = base.to_dict()
    payload.update(overrides)
    return PreferenceConfig.from_dict(payload)


def run_scenario(
    name: str,
    pref: PreferenceConfig,
    fragments: list[MemoryFragment],
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    result = build_cluster_result(
        fragments=fragments,
        preference_config=pref,
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
    )
    retriever = MemoryRetriever(HashEmbeddingProvider(dim=256))
    state = result.to_dict()
    query = retriever.query(state=state, query_text="conflict alpha mode", top_k=1, cluster_level="all", expand=False)
    top = query[0] if query else {}

    l1_clusters = [cluster for cluster in result.clusters if int(cluster.level) == 1]
    avg_summary_chars = (
        sum(len(cluster.summary or "") for cluster in l1_clusters) / float(len(l1_clusters)) if l1_clusters else 0.0
    )

    output = {
        "scenario": name,
        "metrics": result.metrics,
        "mixed_mode_clusters": _slot_mixing_count(result, "mode"),
        "top1_conflict_count": int(top.get("conflict_count") or 0),
        "top1_conflict_priority": float(top.get("conflict_priority") or 0.0),
        "avg_summary_chars_l1": round(avg_summary_chars, 3),
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ablation study for CEG/ARB/DMG")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=9)
    parser.add_argument("--similarity-threshold", type=float, default=1.1)
    parser.add_argument("--merge-threshold", type=float, default=0.05)
    parser.add_argument("--dataset-label", default="synthetic_conflict_memory_case")
    args = parser.parse_args()

    base_pref = PreferenceConfig.from_dict(
        {
            "category_strength": {
                "method": "strong",
                "evidence": "strong",
                "preference": "strong",
                "noise": "discardable",
            },
            "source_weight": {
                "planner_agent": 1.1,
                "writer_agent": 1.0,
                "verifier_agent": 1.6,
            },
            "stale_after_hours": 72,
            "detail_budget": {"strong": 220, "weak": 150, "discardable": 90},
            "keep_conflicts": True,
            "enable_l2_clusters": False,
            "hard_keep_tags": ["global_task", "current_task"],
            "protected_path_prefixes": ["src/", "docs/patent_kit/"],
        }
    )

    fragments = synthetic_fragments(fragment_count=args.fragment_count)
    scenarios = [
        (
            "baseline",
            {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": False},
        ),
        (
            "ceg",
            {"enable_conflict_graph": True, "enable_adaptive_budget": False, "enable_dual_merge_guard": False},
        ),
        (
            "arb",
            {"enable_conflict_graph": False, "enable_adaptive_budget": True, "enable_dual_merge_guard": False},
        ),
        (
            "dmg",
            {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": True},
        ),
        (
            "full",
            {"enable_conflict_graph": True, "enable_adaptive_budget": True, "enable_dual_merge_guard": True},
        ),
    ]

    rows: list[dict[str, Any]] = []
    for name, overrides in scenarios:
        pref = _scenario_pref(base_pref, overrides)
        rows.append(
            run_scenario(
                name=name,
                pref=pref,
                fragments=fragments,
                similarity_threshold=float(args.similarity_threshold),
                merge_threshold=float(args.merge_threshold),
            )
        )

    by_name = {row["scenario"]: row for row in rows}
    baseline = by_name.get("baseline", {})
    ceg = by_name.get("ceg", {})
    arb = by_name.get("arb", {})
    dmg = by_name.get("dmg", {})
    full = by_name.get("full", {})
    summary = {
        "ceg": {
            "top1_conflict_priority_gain": round(
                float(ceg.get("top1_conflict_priority") or 0.0)
                - float(baseline.get("top1_conflict_priority") or 0.0),
                6,
            ),
            "conflict_priority_avg_gain": round(
                float(((ceg.get("metrics") or {}).get("conflict_priority_avg") or 0.0))
                - float(((baseline.get("metrics") or {}).get("conflict_priority_avg") or 0.0)),
                6,
            ),
        },
        "arb": {
            "detail_budget_avg_gain": round(
                float(((arb.get("metrics") or {}).get("detail_budget_avg") or 0.0))
                - float(((baseline.get("metrics") or {}).get("detail_budget_avg") or 0.0)),
                6,
            ),
            "avg_summary_chars_gain": round(
                float(arb.get("avg_summary_chars_l1") or 0.0) - float(baseline.get("avg_summary_chars_l1") or 0.0),
                6,
            ),
        },
        "dmg": {
            "mixed_mode_clusters_reduction": int(baseline.get("mixed_mode_clusters") or 0)
            - int(dmg.get("mixed_mode_clusters") or 0),
            "merge_block_gain": int((dmg.get("metrics") or {}).get("merges_blocked_by_guard") or 0)
            - int((baseline.get("metrics") or {}).get("merges_blocked_by_guard") or 0),
            "cluster_count_delta": int((dmg.get("metrics") or {}).get("cluster_count") or 0)
            - int((baseline.get("metrics") or {}).get("cluster_count") or 0),
        },
        "full": {
            "mixed_mode_clusters_reduction_vs_baseline": int(baseline.get("mixed_mode_clusters") or 0)
            - int(full.get("mixed_mode_clusters") or 0),
            "detail_budget_avg_gain_vs_baseline": round(
                float(((full.get("metrics") or {}).get("detail_budget_avg") or 0.0))
                - float(((baseline.get("metrics") or {}).get("detail_budget_avg") or 0.0)),
                6,
            ),
            "merge_block_gain_vs_baseline": int((full.get("metrics") or {}).get("merges_blocked_by_guard") or 0)
            - int((baseline.get("metrics") or {}).get("merges_blocked_by_guard") or 0),
        },
        "sanity_checks": {
            "baseline_cluster_count": int((baseline.get("metrics") or {}).get("cluster_count") or 0),
            "full_cluster_count": int((full.get("metrics") or {}).get("cluster_count") or 0),
            "baseline_conflict_count": int((baseline.get("metrics") or {}).get("conflict_count") or 0),
            "full_conflict_count": int((full.get("metrics") or {}).get("conflict_count") or 0),
        },
        "mixed_mode_clusters_reduction": (
            int(baseline.get("mixed_mode_clusters") or 0) - int(full.get("mixed_mode_clusters") or 0)
        ),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset_label),
        "fragment_count": len(fragments),
        "similarity_threshold": float(args.similarity_threshold),
        "merge_threshold": float(args.merge_threshold),
        "scenarios": rows,
        "summary": summary,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Ablation Report (CN Fast-Track)",
            "",
            f"- generated_at: {payload.get('generated_at')}",
            f"- dataset: {payload.get('dataset')}",
            f"- fragment_count: {payload.get('fragment_count')}",
            f"- similarity_threshold: {payload.get('similarity_threshold')}",
            f"- merge_threshold: {payload.get('merge_threshold')}",
            "",
            "## Scenarios",
        ]
        for row in rows:
            metrics = row.get("metrics") or {}
            lines.extend(
                [
                    f"- {row['scenario']}: cluster_count={metrics.get('cluster_count')}, "
                    f"mixed_mode_clusters={row.get('mixed_mode_clusters')}, "
                    f"conflict_priority_avg={metrics.get('conflict_priority_avg')}, "
                    f"detail_budget_avg={metrics.get('detail_budget_avg')}, "
                    f"merges_blocked_by_guard={metrics.get('merges_blocked_by_guard')}",
                ]
            )
        lines.extend(
            [
                "",
                "## Summary",
                f"- ceg_top1_conflict_priority_gain: {(summary.get('ceg') or {}).get('top1_conflict_priority_gain')}",
                f"- ceg_conflict_priority_avg_gain: {(summary.get('ceg') or {}).get('conflict_priority_avg_gain')}",
                f"- arb_detail_budget_avg_gain: {(summary.get('arb') or {}).get('detail_budget_avg_gain')}",
                f"- arb_avg_summary_chars_gain: {(summary.get('arb') or {}).get('avg_summary_chars_gain')}",
                f"- dmg_mixed_mode_clusters_reduction: {(summary.get('dmg') or {}).get('mixed_mode_clusters_reduction')}",
                f"- dmg_merge_block_gain: {(summary.get('dmg') or {}).get('merge_block_gain')}",
                f"- dmg_cluster_count_delta: {(summary.get('dmg') or {}).get('cluster_count_delta')}",
                f"- full_mixed_mode_clusters_reduction_vs_baseline: {(summary.get('full') or {}).get('mixed_mode_clusters_reduction_vs_baseline')}",
                f"- full_detail_budget_avg_gain_vs_baseline: {(summary.get('full') or {}).get('detail_budget_avg_gain_vs_baseline')}",
                f"- full_merge_block_gain_vs_baseline: {(summary.get('full') or {}).get('merge_block_gain_vs_baseline')}",
                f"- sanity_baseline_cluster_count: {(summary.get('sanity_checks') or {}).get('baseline_cluster_count')}",
                f"- sanity_full_cluster_count: {(summary.get('sanity_checks') or {}).get('full_cluster_count')}",
                f"- sanity_baseline_conflict_count: {(summary.get('sanity_checks') or {}).get('baseline_conflict_count')}",
                f"- sanity_full_conflict_count: {(summary.get('sanity_checks') or {}).get('full_conflict_count')}",
                f"- mixed_mode_clusters_reduction: {summary.get('mixed_mode_clusters_reduction')}",
                "",
                "## Summary (Raw JSON)",
                f"- {json.dumps(summary, ensure_ascii=False)}",
                "",
            ]
        )
        report_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
