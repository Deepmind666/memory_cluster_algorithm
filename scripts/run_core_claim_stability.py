from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def compute_distribution_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "ci95": 0.0,
            "p05": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "positive_rate": 0.0,
        }
    ordered = sorted(float(item) for item in values)
    n = len(ordered)
    avg = float(mean(ordered))
    if n <= 1:
        std = 0.0
    else:
        variance = sum((item - avg) ** 2 for item in ordered) / float(n - 1)
        std = math.sqrt(max(0.0, variance))
    ci95 = 1.96 * std / math.sqrt(float(n)) if n > 1 else 0.0

    def pct(position: float) -> float:
        if not ordered:
            return 0.0
        idx = int(round((len(ordered) - 1) * position))
        return float(ordered[idx])

    positive = sum(1 for item in ordered if item > 0.0)
    return {
        "count": float(n),
        "mean": round(avg, 6),
        "std": round(std, 6),
        "ci95": round(ci95, 6),
        "p05": round(pct(0.05), 6),
        "p50": round(pct(0.50), 6),
        "p95": round(pct(0.95), 6),
        "positive_rate": round(float(positive) / float(n), 6),
    }


def _load_fragments(path: Path) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            rows.append(MemoryFragment.from_dict(payload))
    rows.sort(key=lambda item: item.timestamp)
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


def _base_preference() -> PreferenceConfig:
    return PreferenceConfig.from_dict(
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
                "ops_agent": 1.2,
            },
            "stale_after_hours": 72,
            "detail_budget": {"strong": 220, "weak": 150, "discardable": 90},
            "keep_conflicts": True,
            "enable_l2_clusters": False,
            "hard_keep_tags": ["global_task", "current_task"],
            "protected_path_prefixes": ["src/", "docs/patent_kit/"],
        }
    )


def _scenario_config() -> list[tuple[str, dict[str, Any]]]:
    return [
        ("baseline", {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": False}),
        ("ceg", {"enable_conflict_graph": True, "enable_adaptive_budget": False, "enable_dual_merge_guard": False}),
        ("arb", {"enable_conflict_graph": False, "enable_adaptive_budget": True, "enable_dual_merge_guard": False}),
        ("dmg", {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": True}),
        ("full", {"enable_conflict_graph": True, "enable_adaptive_budget": True, "enable_dual_merge_guard": True}),
    ]


def _run_single_scenario(
    *,
    fragments: list[MemoryFragment],
    preference: PreferenceConfig,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, float]:
    started = time.perf_counter()
    result = build_cluster_result(
        fragments=fragments,
        preference_config=preference,
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    metrics = result.metrics
    return {
        "elapsed_ms": float(elapsed_ms),
        "cluster_count": float(metrics.get("cluster_count") or 0),
        "conflict_priority_avg": float(metrics.get("conflict_priority_avg") or 0.0),
        "detail_budget_avg": float(metrics.get("detail_budget_avg") or 0.0),
        "merges_blocked_by_guard": float(metrics.get("merges_blocked_by_guard") or 0),
        "mixed_mode_clusters": float(_slot_mixing_count(result, "mode")),
    }


def _build_run_records(
    *,
    fragments: list[MemoryFragment],
    runs: int,
    similarity_threshold: float,
    merge_threshold: float,
    warmup_runs: int,
) -> tuple[list[dict[str, dict[str, float]]], dict[str, dict[str, Any]]]:
    base = _base_preference()
    scenario_rows = _scenario_config()

    for _ in range(max(0, int(warmup_runs))):
        for _name, overrides in scenario_rows:
            pref = _scenario_pref(base, overrides)
            _run_single_scenario(
                fragments=fragments,
                preference=pref,
                similarity_threshold=similarity_threshold,
                merge_threshold=merge_threshold,
            )

    per_run: list[dict[str, dict[str, float]]] = []
    for index in range(max(1, int(runs))):
        run_data: dict[str, dict[str, float]] = {}
        for name, overrides in scenario_rows:
            pref = _scenario_pref(base, overrides)
            run_data[name] = _run_single_scenario(
                fragments=fragments,
                preference=pref,
                similarity_threshold=similarity_threshold,
                merge_threshold=merge_threshold,
            )
        run_data["meta"] = {"run_index": float(index)}
        per_run.append(run_data)

    scenario_stats: dict[str, dict[str, Any]] = {}
    for name, _overrides in scenario_rows:
        elapsed = [row[name]["elapsed_ms"] for row in per_run]
        conflict = [row[name]["conflict_priority_avg"] for row in per_run]
        detail = [row[name]["detail_budget_avg"] for row in per_run]
        blocked = [row[name]["merges_blocked_by_guard"] for row in per_run]
        mixed = [row[name]["mixed_mode_clusters"] for row in per_run]
        cluster_count = [row[name]["cluster_count"] for row in per_run]
        scenario_stats[name] = {
            "elapsed_ms": compute_distribution_stats(elapsed),
            "conflict_priority_avg": compute_distribution_stats(conflict),
            "detail_budget_avg": compute_distribution_stats(detail),
            "merges_blocked_by_guard": compute_distribution_stats(blocked),
            "mixed_mode_clusters": compute_distribution_stats(mixed),
            "cluster_count": compute_distribution_stats(cluster_count),
        }
    return per_run, scenario_stats


def _gain_series(per_run: list[dict[str, dict[str, float]]], metric_key: str, lhs: str, rhs: str) -> list[float]:
    output: list[float] = []
    for row in per_run:
        left = float((row.get(lhs) or {}).get(metric_key) or 0.0)
        right = float((row.get(rhs) or {}).get(metric_key) or 0.0)
        output.append(left - right)
    return output


def _build_summary(*, per_run: list[dict[str, dict[str, float]]], scenario_stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ceg_gain = _gain_series(per_run, "conflict_priority_avg", "ceg", "baseline")
    arb_gain = _gain_series(per_run, "detail_budget_avg", "arb", "baseline")
    dmg_block_gain = _gain_series(per_run, "merges_blocked_by_guard", "dmg", "baseline")
    dmg_mix_reduction = _gain_series(per_run, "mixed_mode_clusters", "baseline", "dmg")
    full_block_gain = _gain_series(per_run, "merges_blocked_by_guard", "full", "baseline")
    runtime_delta = _gain_series(per_run, "elapsed_ms", "full", "baseline")

    return {
        "ceg_conflict_priority_gain": compute_distribution_stats(ceg_gain),
        "arb_detail_budget_gain": compute_distribution_stats(arb_gain),
        "dmg_merge_block_gain": compute_distribution_stats(dmg_block_gain),
        "dmg_mixed_mode_reduction": compute_distribution_stats(dmg_mix_reduction),
        "full_merge_block_gain": compute_distribution_stats(full_block_gain),
        "full_runtime_delta_ms": compute_distribution_stats(runtime_delta),
        "stability_gate": {
            "ceg_ci95_lower_gt_0": (
                float(compute_distribution_stats(ceg_gain).get("mean") or 0.0)
                - float(compute_distribution_stats(ceg_gain).get("ci95") or 0.0)
            )
            > 0.0,
            "arb_ci95_lower_gt_0": (
                float(compute_distribution_stats(arb_gain).get("mean") or 0.0)
                - float(compute_distribution_stats(arb_gain).get("ci95") or 0.0)
            )
            > 0.0,
            "dmg_ci95_lower_gt_0": (
                float(compute_distribution_stats(dmg_block_gain).get("mean") or 0.0)
                - float(compute_distribution_stats(dmg_block_gain).get("ci95") or 0.0)
            )
            > 0.0,
            "full_runtime_ci95_upper_lt_0": (
                float(compute_distribution_stats(runtime_delta).get("mean") or 0.0)
                + float(compute_distribution_stats(runtime_delta).get("ci95") or 0.0)
            )
            < 0.0,
        },
        "scenario_stats": scenario_stats,
    }


def _build_report_text(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    gates = dict(summary.get("stability_gate") or {})

    def _line(metric_name: str, label: str) -> str:
        row = dict(summary.get(metric_name) or {})
        return (
            f"- {label}: mean={row.get('mean')}, ci95={row.get('ci95')}, "
            f"p50={row.get('p50')}, positive_rate={row.get('positive_rate')}"
        )

    lines = [
        "# Core Claim Stability Report",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- dataset: {payload.get('dataset')}",
        f"- fragment_count: {payload.get('fragment_count')}",
        f"- runs: {payload.get('runs')}",
        f"- warmup_runs: {payload.get('warmup_runs')}",
        f"- similarity_threshold: {payload.get('similarity_threshold')}",
        f"- merge_threshold: {payload.get('merge_threshold')}",
        "",
        "## Gain Distribution",
        _line("ceg_conflict_priority_gain", "CEG conflict-priority gain"),
        _line("arb_detail_budget_gain", "ARB detail-budget gain"),
        _line("dmg_merge_block_gain", "DMG merge-block gain"),
        _line("dmg_mixed_mode_reduction", "DMG mixed-mode reduction"),
        _line("full_merge_block_gain", "FULL merge-block gain"),
        _line("full_runtime_delta_ms", "FULL runtime delta (ms)"),
        "",
        "## Stability Gate",
        f"- ceg_ci95_lower_gt_0: {gates.get('ceg_ci95_lower_gt_0')}",
        f"- arb_ci95_lower_gt_0: {gates.get('arb_ci95_lower_gt_0')}",
        f"- dmg_ci95_lower_gt_0: {gates.get('dmg_ci95_lower_gt_0')}",
        f"- full_runtime_ci95_upper_lt_0: {gates.get('full_runtime_ci95_upper_lt_0')}",
        "",
        "## Raw JSON",
        f"- {json.dumps(payload, ensure_ascii=False)}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repeated CEG/ARB/DMG stability benchmark with CI95 statistics.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--dataset-label", default="")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--similarity-threshold", type=float, default=0.68)
    parser.add_argument("--merge-threshold", type=float, default=0.82)
    args = parser.parse_args()

    fragments = _load_fragments(Path(args.input))
    run_records, scenario_stats = _build_run_records(
        fragments=fragments,
        runs=int(args.runs),
        similarity_threshold=float(args.similarity_threshold),
        merge_threshold=float(args.merge_threshold),
        warmup_runs=int(args.warmup_runs),
    )
    summary = _build_summary(per_run=run_records, scenario_stats=scenario_stats)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset_label or str(Path(args.input)),
        "input_path": str(Path(args.input)),
        "fragment_count": len(fragments),
        "runs": int(args.runs),
        "warmup_runs": int(args.warmup_runs),
        "similarity_threshold": float(args.similarity_threshold),
        "merge_threshold": float(args.merge_threshold),
        "summary": summary,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_build_report_text(payload), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
