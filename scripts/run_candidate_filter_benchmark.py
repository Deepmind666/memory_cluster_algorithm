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
    total = max(60, int(fragment_count))
    rows: list[MemoryFragment] = []
    for idx in range(total):
        mode = ("fast", "safe", "balanced", "strict")[idx % 4]
        alpha = ("0.2", "0.4", "0.6", "0.8")[(idx * 3) % 4]
        rows.append(
            MemoryFragment(
                id=f"cfb{idx:04d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-10T13:{idx % 60:02d}:00+00:00",
                content=(
                    f"memory candidate group_{idx % 12} mode {mode} alpha {alpha} "
                    f"variant_{idx} replay token_{idx * 11}"
                ),
                type="draft" if idx % 3 else "result",
                tags={"category": "method" if idx % 3 else "evidence"},
                meta={"slots": {"mode": mode, "alpha": alpha, "group": str(idx % 12)}},
            )
        )
    return rows


def run_case(
    *,
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


def summarize_pair(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    base_avg = float(baseline.get("avg_ms") or 0.0)
    opt_avg = float(optimized.get("avg_ms") or 0.0)
    speedup = 0.0
    if base_avg > 0:
        speedup = (base_avg - opt_avg) / base_avg

    base_metrics = baseline.get("metrics") or {}
    opt_metrics = optimized.get("metrics") or {}
    base_attempts = int(base_metrics.get("merge_attempts") or 0)
    opt_attempts = int(opt_metrics.get("merge_attempts") or 0)
    attempt_reduction = 0.0
    if base_attempts > 0:
        attempt_reduction = (base_attempts - opt_attempts) / float(base_attempts)
    return {
        "avg_ms_delta": round(opt_avg - base_avg, 3),
        "avg_speedup_ratio": round(speedup, 6),
        "attempt_reduction_ratio": round(attempt_reduction, 6),
        "baseline_merge_attempts": base_attempts,
        "optimized_merge_attempts": opt_attempts,
        "baseline_merges_applied": int(base_metrics.get("merges_applied") or 0),
        "optimized_merges_applied": int(opt_metrics.get("merges_applied") or 0),
        "merges_applied_equal": int(base_metrics.get("merges_applied") or 0)
        == int(opt_metrics.get("merges_applied") or 0),
        "optimized_pairs_skipped_by_candidate_filter": int(
            opt_metrics.get("merge_pairs_skipped_by_candidate_filter") or 0
        ),
        "cluster_count_equal": int(base_metrics.get("cluster_count") or 0) == int(opt_metrics.get("cluster_count") or 0),
        "merge_activity_present": (int(base_metrics.get("merges_applied") or 0) > 0)
        or (int(opt_metrics.get("merges_applied") or 0) > 0),
    }


def run_scenario(
    *,
    name: str,
    fragments: list[MemoryFragment],
    baseline_pref: PreferenceConfig,
    optimized_pref: PreferenceConfig,
    runs: int,
    warmup_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    baseline = run_case(
        fragments=fragments,
        pref=baseline_pref,
        runs=runs,
        warmup_runs=warmup_runs,
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
    )
    optimized = run_case(
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
        "baseline_no_filter": baseline,
        "optimized_candidate_filter": optimized,
        "summary": summarize_pair(baseline, optimized),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark merge candidate filter on/off")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--bucket-dims", type=int, default=10)
    parser.add_argument("--max-neighbors", type=int, default=48)
    parser.add_argument("--sparse-similarity-threshold", type=float, default=2.0)
    parser.add_argument("--sparse-merge-threshold", type=float, default=0.95)
    parser.add_argument("--active-similarity-threshold", type=float, default=0.82)
    parser.add_argument("--active-merge-threshold", type=float, default=0.85)
    args = parser.parse_args()

    fragments = synthetic_fragments(args.fragment_count)
    baseline_pref = PreferenceConfig.from_dict(
        {
            "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
            "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
            "enable_merge_candidate_filter": False,
        }
    )
    optimized_pref = PreferenceConfig.from_dict(
        {
            **baseline_pref.to_dict(),
            "enable_merge_candidate_filter": True,
            "merge_candidate_bucket_dims": max(1, int(args.bucket_dims)),
            "merge_candidate_max_neighbors": max(1, int(args.max_neighbors)),
        }
    )

    sparse = run_scenario(
        name="sparse_no_merge_case",
        fragments=fragments,
        baseline_pref=baseline_pref,
        optimized_pref=optimized_pref,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.sparse_similarity_threshold,
        merge_threshold=args.sparse_merge_threshold,
    )
    active = run_scenario(
        name="merge_active_case",
        fragments=fragments,
        baseline_pref=baseline_pref,
        optimized_pref=optimized_pref,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.active_similarity_threshold,
        merge_threshold=args.active_merge_threshold,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "synthetic_candidate_filter_case",
        "fragment_count": len(fragments),
        "bucket_dims": max(1, int(args.bucket_dims)),
        "max_neighbors": max(1, int(args.max_neighbors)),
        "scenarios": [sparse, active],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        lines = [
            "# Merge Candidate Filter Benchmark",
            "",
            f"- generated_at: {payload.get('generated_at')}",
            f"- fragment_count: {payload.get('fragment_count')}",
            f"- bucket_dims: {payload.get('bucket_dims')}",
            f"- max_neighbors: {payload.get('max_neighbors')}",
            "",
        ]
        for scenario in payload.get("scenarios") or []:
            baseline = scenario.get("baseline_no_filter") or {}
            optimized = scenario.get("optimized_candidate_filter") or {}
            summary = scenario.get("summary") or {}
            lines.extend(
                [
                    f"## Scenario: {scenario.get('name')}",
                    f"- similarity_threshold: {scenario.get('similarity_threshold')}",
                    f"- merge_threshold: {scenario.get('merge_threshold')}",
                    "### Baseline (filter off)",
                    f"- avg_ms: {baseline.get('avg_ms')}",
                    f"- merge_attempts: {(baseline.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(baseline.get('metrics') or {}).get('merges_applied')}",
                    "### Optimized (filter on)",
                    f"- avg_ms: {optimized.get('avg_ms')}",
                    f"- merge_attempts: {(optimized.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(optimized.get('metrics') or {}).get('merges_applied')}",
                    f"- merge_pairs_skipped_by_candidate_filter: {(optimized.get('metrics') or {}).get('merge_pairs_skipped_by_candidate_filter')}",
                    "### Summary",
                    f"- avg_ms_delta: {summary.get('avg_ms_delta')}",
                    f"- avg_speedup_ratio: {summary.get('avg_speedup_ratio')}",
                    f"- attempt_reduction_ratio: {summary.get('attempt_reduction_ratio')}",
                    f"- cluster_count_equal: {summary.get('cluster_count_equal')}",
                    f"- merges_applied_equal: {summary.get('merges_applied_equal')}",
                    f"- merge_activity_present: {summary.get('merge_activity_present')}",
                    "",
                ]
            )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
