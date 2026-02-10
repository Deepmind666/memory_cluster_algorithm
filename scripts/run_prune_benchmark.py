from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def synthetic_fragments(fragment_count: int) -> list[MemoryFragment]:
    total = max(40, int(fragment_count))
    modes = ["fast", "safe", "balanced", "strict"]
    alphas = ["0.2", "0.4", "0.6", "0.8"]
    rows: list[MemoryFragment] = []
    for idx in range(total):
        mode = modes[idx % len(modes)]
        alpha = alphas[(idx * 3) % len(alphas)]
        group = idx % 10
        category = "method" if idx % 3 != 0 else "evidence"
        agent = "planner_agent" if idx % 2 == 0 else "writer_agent"
        minute = idx % 60
        hour = 10 + (idx // 60)
        rows.append(
            MemoryFragment(
                id=f"pb{idx:04d}",
                agent_id=agent,
                timestamp=f"2026-02-09T{hour:02d}:{minute:02d}:00+00:00",
                content=(
                    f"pipeline group_{group} mode {mode} alpha {alpha} "
                    f"strategy variant_{idx} for benchmark window"
                ),
                type="draft" if category == "method" else "result",
                tags={"category": category},
                meta={"slots": {"mode": mode, "alpha": alpha, "group": str(group)}},
            )
        )
    return rows


def run_case(
    fragments: list[MemoryFragment],
    pref: PreferenceConfig,
    runs: int,
    warmup_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    for _ in range(max(0, int(warmup_runs))):
        build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )

    durations_ms: list[float] = []
    last = None
    for _ in range(max(1, int(runs))):
        start = time.perf_counter()
        last = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )
        durations_ms.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(durations_ms)
    p95_idx = int(round((len(ordered) - 1) * 0.95))
    return {
        "runs": len(durations_ms),
        "avg_ms": round(sum(durations_ms) / len(durations_ms), 3),
        "p95_ms": round(ordered[p95_idx], 3),
        "metrics": (last.metrics if last else {}),
    }


def summarize_pair(baseline: dict[str, Any], pruned: dict[str, Any]) -> dict[str, Any]:
    baseline_avg = float(baseline.get("avg_ms") or 0.0)
    pruned_avg = float(pruned.get("avg_ms") or 0.0)
    speedup = 0.0
    if baseline_avg > 0:
        speedup = (baseline_avg - pruned_avg) / baseline_avg

    baseline_metrics = baseline.get("metrics") or {}
    pruned_metrics = pruned.get("metrics") or {}
    baseline_merges = int(baseline_metrics.get("merges_applied") or 0)
    pruned_merges = int(pruned_metrics.get("merges_applied") or 0)
    return {
        "avg_ms_delta": round(pruned_avg - baseline_avg, 3),
        "avg_speedup_ratio": round(speedup, 6),
        "baseline_merge_attempts": int(baseline_metrics.get("merge_attempts") or 0),
        "optimized_merge_attempts": int(pruned_metrics.get("merge_attempts") or 0),
        "baseline_merges_applied": baseline_merges,
        "optimized_merges_applied": pruned_merges,
        "optimized_pairs_pruned": int(pruned_metrics.get("merge_pairs_pruned_by_bound") or 0),
        "cluster_count_equal": int(baseline_metrics.get("cluster_count") or 0)
        == int(pruned_metrics.get("cluster_count") or 0),
        "merge_activity_present": (baseline_merges > 0) or (pruned_merges > 0),
    }


def run_scenario(
    *,
    name: str,
    fragments: list[MemoryFragment],
    base_pref: PreferenceConfig,
    optimized_pref: PreferenceConfig,
    runs: int,
    warmup_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    baseline = run_case(
        fragments=fragments,
        pref=base_pref,
        runs=runs,
        warmup_runs=warmup_runs,
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
    )
    pruned = run_case(
        fragments=fragments,
        pref=optimized_pref,
        runs=runs,
        warmup_runs=warmup_runs,
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
    )
    return {
        "name": name,
        "similarity_threshold": float(similarity_threshold),
        "merge_threshold": float(merge_threshold),
        "baseline_no_prune": baseline,
        "optimized_prune": pruned,
        "summary": summarize_pair(baseline, pruned),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark merge upper-bound prune on/off")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=100)
    parser.add_argument("--runs", type=int, default=12)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--similarity-threshold", type=float, default=0.82)
    parser.add_argument("--merge-threshold", type=float, default=0.85)
    parser.add_argument("--realistic-similarity-threshold", type=float, default=0.68)
    parser.add_argument("--realistic-merge-threshold", type=float, default=0.82)
    parser.add_argument("--skip-realistic-scenario", action="store_true")
    parser.add_argument("--sparse-similarity-threshold", type=float, default=2.0)
    parser.add_argument("--sparse-merge-threshold", type=float, default=0.95)
    parser.add_argument("--skip-sparse-scenario", action="store_true")
    args = parser.parse_args()

    fragments = synthetic_fragments(args.fragment_count)
    base = PreferenceConfig.from_dict(
        {
            "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
            "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
            "enable_merge_upper_bound_prune": False,
            "merge_prune_dims": 48,
        }
    )
    optimized = PreferenceConfig.from_dict(
        {
            **base.to_dict(),
            "enable_merge_upper_bound_prune": True,
            "merge_prune_dims": 48,
        }
    )
    primary = run_scenario(
        name="merge_active_case",
        fragments=fragments,
        base_pref=base,
        optimized_pref=optimized,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.similarity_threshold,
        merge_threshold=args.merge_threshold,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "synthetic_merge_prune_case",
        "fragment_count": len(fragments),
        "similarity_threshold": float(primary["similarity_threshold"]),
        "merge_threshold": float(primary["merge_threshold"]),
        "baseline_no_prune": primary["baseline_no_prune"],
        "optimized_prune": primary["optimized_prune"],
        "summary": primary["summary"],
        "primary_scenario": primary,
    }
    if not args.skip_realistic_scenario:
        payload["secondary_realistic"] = run_scenario(
            name="realistic_068_082_case",
            fragments=fragments,
            base_pref=base,
            optimized_pref=optimized,
            runs=args.runs,
            warmup_runs=args.warmup_runs,
            similarity_threshold=args.realistic_similarity_threshold,
            merge_threshold=args.realistic_merge_threshold,
        )
    if not args.skip_sparse_scenario:
        payload["secondary_sparse"] = run_scenario(
            name="sparse_no_merge_case",
            fragments=fragments,
            base_pref=base,
            optimized_pref=optimized,
            runs=args.runs,
            warmup_runs=args.warmup_runs,
            similarity_threshold=args.sparse_similarity_threshold,
            merge_threshold=args.sparse_merge_threshold,
        )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        primary_case = payload.get("primary_scenario") or {}
        primary_baseline = primary_case.get("baseline_no_prune") or {}
        primary_optimized = primary_case.get("optimized_prune") or {}
        primary_summary = primary_case.get("summary") or {}
        report_lines = [
            "# Merge Upper-Bound Prune Benchmark",
            "",
            f"- generated_at: {payload.get('generated_at')}",
            f"- fragment_count: {payload['fragment_count']}",
            f"- primary_similarity_threshold: {payload['similarity_threshold']}",
            f"- primary_merge_threshold: {payload['merge_threshold']}",
            "",
            "## Primary Scenario: merge_active_case",
            "### Baseline (prune off)",
            f"- avg_ms: {primary_baseline.get('avg_ms')}",
            f"- p95_ms: {primary_baseline.get('p95_ms')}",
            f"- merge_attempts: {(primary_baseline.get('metrics') or {}).get('merge_attempts')}",
            f"- merges_applied: {(primary_baseline.get('metrics') or {}).get('merges_applied')}",
            "",
            "### Optimized (prune on)",
            f"- avg_ms: {primary_optimized.get('avg_ms')}",
            f"- p95_ms: {primary_optimized.get('p95_ms')}",
            f"- merge_attempts: {(primary_optimized.get('metrics') or {}).get('merge_attempts')}",
            f"- merges_applied: {(primary_optimized.get('metrics') or {}).get('merges_applied')}",
            f"- merge_pairs_pruned_by_bound: {(primary_optimized.get('metrics') or {}).get('merge_pairs_pruned_by_bound')}",
            "",
            "### Summary",
            f"- avg_ms_delta: {primary_summary.get('avg_ms_delta')}",
            f"- avg_speedup_ratio: {primary_summary.get('avg_speedup_ratio')}",
            f"- cluster_count_equal: {primary_summary.get('cluster_count_equal')}",
            f"- merge_activity_present: {primary_summary.get('merge_activity_present')}",
        ]
        realistic = payload.get("secondary_realistic")
        if isinstance(realistic, dict):
            realistic_baseline = realistic.get("baseline_no_prune") or {}
            realistic_optimized = realistic.get("optimized_prune") or {}
            realistic_summary = realistic.get("summary") or {}
            report_lines.extend(
                [
                    "",
                    "## Secondary Scenario: realistic_068_082_case",
                    f"- similarity_threshold: {realistic.get('similarity_threshold')}",
                    f"- merge_threshold: {realistic.get('merge_threshold')}",
                    "### Baseline (prune off)",
                    f"- avg_ms: {realistic_baseline.get('avg_ms')}",
                    f"- merge_attempts: {(realistic_baseline.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(realistic_baseline.get('metrics') or {}).get('merges_applied')}",
                    "### Optimized (prune on)",
                    f"- avg_ms: {realistic_optimized.get('avg_ms')}",
                    f"- merge_attempts: {(realistic_optimized.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(realistic_optimized.get('metrics') or {}).get('merges_applied')}",
                    f"- merge_pairs_pruned_by_bound: {(realistic_optimized.get('metrics') or {}).get('merge_pairs_pruned_by_bound')}",
                    "### Summary",
                    f"- avg_ms_delta: {realistic_summary.get('avg_ms_delta')}",
                    f"- avg_speedup_ratio: {realistic_summary.get('avg_speedup_ratio')}",
                    f"- cluster_count_equal: {realistic_summary.get('cluster_count_equal')}",
                    f"- merge_activity_present: {realistic_summary.get('merge_activity_present')}",
                ]
            )
        sparse = payload.get("secondary_sparse")
        if isinstance(sparse, dict):
            sparse_baseline = sparse.get("baseline_no_prune") or {}
            sparse_optimized = sparse.get("optimized_prune") or {}
            sparse_summary = sparse.get("summary") or {}
            report_lines.extend(
                [
                    "",
                    "## Secondary Scenario: sparse_no_merge_case",
                    f"- similarity_threshold: {sparse.get('similarity_threshold')}",
                    f"- merge_threshold: {sparse.get('merge_threshold')}",
                    "### Baseline (prune off)",
                    f"- avg_ms: {sparse_baseline.get('avg_ms')}",
                    f"- merge_attempts: {(sparse_baseline.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(sparse_baseline.get('metrics') or {}).get('merges_applied')}",
                    "### Optimized (prune on)",
                    f"- avg_ms: {sparse_optimized.get('avg_ms')}",
                    f"- merge_attempts: {(sparse_optimized.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(sparse_optimized.get('metrics') or {}).get('merges_applied')}",
                    f"- merge_pairs_pruned_by_bound: {(sparse_optimized.get('metrics') or {}).get('merge_pairs_pruned_by_bound')}",
                    "### Summary",
                    f"- avg_ms_delta: {sparse_summary.get('avg_ms_delta')}",
                    f"- avg_speedup_ratio: {sparse_summary.get('avg_speedup_ratio')}",
                    f"- cluster_count_equal: {sparse_summary.get('cluster_count_equal')}",
                    f"- merge_activity_present: {sparse_summary.get('merge_activity_present')}",
                ]
            )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
