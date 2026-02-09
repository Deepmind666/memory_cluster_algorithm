from __future__ import annotations

import argparse
import json
import sys
import time
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark merge upper-bound prune on/off")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=100)
    parser.add_argument("--runs", type=int, default=12)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--similarity-threshold", type=float, default=2.0)
    parser.add_argument("--merge-threshold", type=float, default=0.95)
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

    baseline = run_case(
        fragments=fragments,
        pref=base,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.similarity_threshold,
        merge_threshold=args.merge_threshold,
    )
    pruned = run_case(
        fragments=fragments,
        pref=optimized,
        runs=args.runs,
        warmup_runs=args.warmup_runs,
        similarity_threshold=args.similarity_threshold,
        merge_threshold=args.merge_threshold,
    )

    baseline_avg = float(baseline.get("avg_ms") or 0.0)
    pruned_avg = float(pruned.get("avg_ms") or 0.0)
    speedup = 0.0
    if baseline_avg > 0:
        speedup = (baseline_avg - pruned_avg) / baseline_avg

    payload = {
        "dataset": "synthetic_merge_prune_case",
        "fragment_count": len(fragments),
        "similarity_threshold": float(args.similarity_threshold),
        "merge_threshold": float(args.merge_threshold),
        "baseline_no_prune": baseline,
        "optimized_prune": pruned,
        "summary": {
            "avg_ms_delta": round(pruned_avg - baseline_avg, 3),
            "avg_speedup_ratio": round(speedup, 6),
            "baseline_merge_attempts": int((baseline.get("metrics") or {}).get("merge_attempts") or 0),
            "optimized_merge_attempts": int((pruned.get("metrics") or {}).get("merge_attempts") or 0),
            "optimized_pairs_pruned": int((pruned.get("metrics") or {}).get("merge_pairs_pruned_by_bound") or 0),
            "cluster_count_equal": int((baseline.get("metrics") or {}).get("cluster_count") or 0)
            == int((pruned.get("metrics") or {}).get("cluster_count") or 0),
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        report_lines = [
            "# Merge Upper-Bound Prune Benchmark",
            "",
            f"- fragment_count: {payload['fragment_count']}",
            f"- similarity_threshold: {payload['similarity_threshold']}",
            f"- merge_threshold: {payload['merge_threshold']}",
            "",
            "## Baseline (prune off)",
            f"- avg_ms: {baseline.get('avg_ms')}",
            f"- p95_ms: {baseline.get('p95_ms')}",
            f"- merge_attempts: {(baseline.get('metrics') or {}).get('merge_attempts')}",
            "",
            "## Optimized (prune on)",
            f"- avg_ms: {pruned.get('avg_ms')}",
            f"- p95_ms: {pruned.get('p95_ms')}",
            f"- merge_attempts: {(pruned.get('metrics') or {}).get('merge_attempts')}",
            f"- merge_pairs_pruned_by_bound: {(pruned.get('metrics') or {}).get('merge_pairs_pruned_by_bound')}",
            "",
            "## Summary",
            f"- avg_ms_delta: {payload['summary']['avg_ms_delta']}",
            f"- avg_speedup_ratio: {payload['summary']['avg_speedup_ratio']}",
            f"- cluster_count_equal: {payload['summary']['cluster_count_equal']}",
        ]
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
