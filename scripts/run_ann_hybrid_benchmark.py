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


def synthetic_fragments(fragment_count: int, *, dataset_mode: str) -> list[MemoryFragment]:
    total = max(80, int(fragment_count))
    rows: list[MemoryFragment] = []
    if dataset_mode == "sparse":
        for idx in range(total):
            rows.append(
                MemoryFragment(
                    id=f"ahs{idx:04d}",
                    agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                    timestamp=f"2026-02-11T11:{idx % 60:02d}:00+00:00",
                    content=f"ann sparse token unique_{idx} variant_{idx * 19}",
                    type="log",
                    tags={"category": "noise"},
                    meta={"slots": {"k": str(idx)}},
                )
            )
        return rows

    for idx in range(total):
        mode = ("fast", "safe", "balanced", "strict")[idx % 4]
        alpha = ("0.2", "0.4", "0.6", "0.8")[(idx * 3) % 4]
        rows.append(
            MemoryFragment(
                id=f"aha{idx:04d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-11T12:{idx % 60:02d}:00+00:00",
                content=(
                    f"ann hybrid group_{idx % 12} mode {mode} alpha {alpha} "
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


def compare_to_baseline(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    base_avg = float(baseline.get("avg_ms") or 0.0)
    cand_avg = float(candidate.get("avg_ms") or 0.0)
    speedup = 0.0
    if base_avg > 0.0:
        speedup = (base_avg - cand_avg) / base_avg

    base_metrics = baseline.get("metrics") or {}
    cand_metrics = candidate.get("metrics") or {}
    base_attempts = int(base_metrics.get("merge_attempts") or 0)
    cand_attempts = int(cand_metrics.get("merge_attempts") or 0)
    attempt_reduction = 0.0
    if base_attempts > 0:
        attempt_reduction = (base_attempts - cand_attempts) / float(base_attempts)

    cluster_count_equal = int(cand_metrics.get("cluster_count") or 0) == int(base_metrics.get("cluster_count") or 0)
    merges_applied_equal = int(cand_metrics.get("merges_applied") or 0) == int(base_metrics.get("merges_applied") or 0)
    conflict_count_equal = int(cand_metrics.get("conflict_count") or 0) == int(base_metrics.get("conflict_count") or 0)
    quality_gate_pass = cluster_count_equal and merges_applied_equal and conflict_count_equal
    return {
        "avg_ms_delta": round(cand_avg - base_avg, 3),
        "avg_speedup_ratio": round(speedup, 6),
        "attempt_reduction_ratio": round(attempt_reduction, 6),
        "cluster_count_equal": cluster_count_equal,
        "merges_applied_equal": merges_applied_equal,
        "conflict_count_equal": conflict_count_equal,
        "quality_gate_pass": quality_gate_pass,
        "merge_activity_present": (int(base_metrics.get("merges_applied") or 0) > 0)
        or (int(cand_metrics.get("merges_applied") or 0) > 0),
        "candidate_skip_count": int(cand_metrics.get("merge_pairs_skipped_by_candidate_filter") or 0),
        "ann_skip_count": int(cand_metrics.get("merge_pairs_skipped_by_ann_candidates") or 0),
        "hybrid_skip_count": int(cand_metrics.get("merge_pairs_skipped_by_hybrid_candidates") or 0),
        "bound_pruned_count": int(cand_metrics.get("merge_pairs_pruned_by_bound") or 0),
    }


def build_variant_preferences(args: argparse.Namespace) -> dict[str, PreferenceConfig]:
    base = {
        "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
        "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
    }
    prune = {
        "enable_merge_upper_bound_prune": True,
        "merge_prune_dims": max(1, int(args.prune_dims)),
    }
    candidate = {
        "enable_merge_candidate_filter": True,
        "merge_candidate_bucket_dims": max(1, int(args.bucket_dims)),
        "merge_candidate_max_neighbors": max(1, int(args.candidate_max_neighbors)),
    }
    ann = {
        "enable_merge_ann_candidates": True,
        "merge_ann_num_tables": max(1, int(args.ann_num_tables)),
        "merge_ann_bits_per_table": max(1, int(args.ann_bits_per_table)),
        "merge_ann_probe_radius": max(0, min(1, int(args.ann_probe_radius))),
        "merge_ann_max_neighbors": max(1, int(args.ann_max_neighbors)),
        "merge_ann_score_dims": max(1, int(args.ann_score_dims)),
    }
    return {
        "baseline_exact": PreferenceConfig.from_dict({**base}),
        "prune_only": PreferenceConfig.from_dict({**base, **prune}),
        "candidate_prune": PreferenceConfig.from_dict({**base, **prune, **candidate}),
        "ann_prune": PreferenceConfig.from_dict({**base, **prune, **ann}),
        "hybrid_prune": PreferenceConfig.from_dict({**base, **prune, **candidate, **ann}),
    }


def run_scenario(
    *,
    name: str,
    fragments: list[MemoryFragment],
    variants: dict[str, PreferenceConfig],
    runs: int,
    warmup_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    variant_results: dict[str, dict[str, Any]] = {}
    for variant_name, pref in variants.items():
        variant_results[variant_name] = run_case(
            fragments=fragments,
            pref=pref,
            runs=runs,
            warmup_runs=warmup_runs,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )

    baseline = variant_results["baseline_exact"]
    comparisons: dict[str, dict[str, Any]] = {}
    for variant_name, result in variant_results.items():
        if variant_name == "baseline_exact":
            continue
        comparisons[variant_name] = compare_to_baseline(baseline, result)

    return {
        "name": name,
        "similarity_threshold": float(similarity_threshold),
        "merge_threshold": float(merge_threshold),
        "variants": variant_results,
        "comparisons_vs_baseline": comparisons,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# ANN Hybrid Benchmark",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- fragment_count: {payload.get('fragment_count')}",
        f"- prune_dims: {payload.get('prune_dims')}",
        f"- candidate_bucket_dims: {payload.get('bucket_dims')}",
        f"- candidate_max_neighbors: {payload.get('candidate_max_neighbors')}",
        f"- ann_num_tables: {payload.get('ann_num_tables')}",
        f"- ann_bits_per_table: {payload.get('ann_bits_per_table')}",
        f"- ann_probe_radius: {payload.get('ann_probe_radius')}",
        f"- ann_max_neighbors: {payload.get('ann_max_neighbors')}",
        f"- ann_score_dims: {payload.get('ann_score_dims')}",
        "",
    ]
    for scenario in payload.get("scenarios") or []:
        lines.append(f"## Scenario: {scenario.get('name')}")
        lines.append(f"- similarity_threshold: {scenario.get('similarity_threshold')}")
        lines.append(f"- merge_threshold: {scenario.get('merge_threshold')}")
        lines.append("")
        for variant, result in (scenario.get("variants") or {}).items():
            lines.extend(
                [
                    f"### Variant: {variant}",
                    f"- avg_ms: {result.get('avg_ms')}",
                    f"- merge_attempts: {(result.get('metrics') or {}).get('merge_attempts')}",
                    f"- merges_applied: {(result.get('metrics') or {}).get('merges_applied')}",
                    f"- merge_pairs_pruned_by_bound: {(result.get('metrics') or {}).get('merge_pairs_pruned_by_bound')}",
                    f"- merge_pairs_skipped_by_candidate_filter: {(result.get('metrics') or {}).get('merge_pairs_skipped_by_candidate_filter')}",
                    f"- merge_pairs_skipped_by_ann_candidates: {(result.get('metrics') or {}).get('merge_pairs_skipped_by_ann_candidates')}",
                    f"- merge_pairs_skipped_by_hybrid_candidates: {(result.get('metrics') or {}).get('merge_pairs_skipped_by_hybrid_candidates')}",
                    "",
                ]
            )
        lines.append("### Comparison vs baseline_exact")
        for variant, summary in (scenario.get("comparisons_vs_baseline") or {}).items():
            lines.extend(
                [
                    f"- {variant}: avg_speedup_ratio={summary.get('avg_speedup_ratio')}, "
                    f"attempt_reduction_ratio={summary.get('attempt_reduction_ratio')}, "
                    f"quality_gate_pass={summary.get('quality_gate_pass')}",
                ]
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark ANN hybrid merge candidate strategy")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--prune-dims", type=int, default=48)
    parser.add_argument("--bucket-dims", type=int, default=10)
    parser.add_argument("--candidate-max-neighbors", type=int, default=48)
    parser.add_argument("--ann-num-tables", type=int, default=6)
    parser.add_argument("--ann-bits-per-table", type=int, default=10)
    parser.add_argument("--ann-probe-radius", type=int, default=1)
    parser.add_argument("--ann-max-neighbors", type=int, default=48)
    parser.add_argument("--ann-score-dims", type=int, default=48)
    parser.add_argument("--sparse-similarity-threshold", type=float, default=2.0)
    parser.add_argument("--sparse-merge-threshold", type=float, default=0.95)
    parser.add_argument("--active-similarity-threshold", type=float, default=0.82)
    parser.add_argument("--active-merge-threshold", type=float, default=0.85)
    args = parser.parse_args()

    variants = build_variant_preferences(args)
    sparse_fragments = synthetic_fragments(args.fragment_count, dataset_mode="sparse")
    active_fragments = synthetic_fragments(args.fragment_count, dataset_mode="active")

    sparse = run_scenario(
        name="sparse_no_merge_case",
        fragments=sparse_fragments,
        variants=variants,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.sparse_similarity_threshold,
        merge_threshold=args.sparse_merge_threshold,
    )
    active = run_scenario(
        name="merge_active_case",
        fragments=active_fragments,
        variants=variants,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.active_similarity_threshold,
        merge_threshold=args.active_merge_threshold,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "synthetic_ann_hybrid_case",
        "fragment_count": int(args.fragment_count),
        "prune_dims": int(args.prune_dims),
        "bucket_dims": int(args.bucket_dims),
        "candidate_max_neighbors": int(args.candidate_max_neighbors),
        "ann_num_tables": int(args.ann_num_tables),
        "ann_bits_per_table": int(args.ann_bits_per_table),
        "ann_probe_radius": int(args.ann_probe_radius),
        "ann_max_neighbors": int(args.ann_max_neighbors),
        "ann_score_dims": int(args.ann_score_dims),
        "scenarios": [sparse, active],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
