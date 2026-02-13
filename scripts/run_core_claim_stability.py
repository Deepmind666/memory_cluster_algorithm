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


def determine_new_runs(*, target_runs: int, existing_runs: int, max_new_runs: int) -> int:
    remaining = max(0, int(target_runs) - int(existing_runs))
    if remaining <= 0:
        return 0
    if int(max_new_runs) <= 0:
        return remaining
    return min(remaining, int(max_new_runs))


def compute_activation_metrics(per_run: list[dict[str, dict[str, float]]]) -> dict[str, float | bool]:
    total = max(1, len(per_run))
    dmg_guard_active = 0
    dmg_mix_reduction = 0
    baseline_mixed_presence = 0
    for row in per_run:
        baseline = row.get("baseline") or {}
        dmg = row.get("dmg") or {}
        baseline_blocked = float(baseline.get("merges_blocked_by_guard") or 0.0)
        dmg_blocked = float(dmg.get("merges_blocked_by_guard") or 0.0)
        baseline_mixed = float(baseline.get("mixed_mode_clusters") or 0.0)
        dmg_mixed = float(dmg.get("mixed_mode_clusters") or 0.0)
        if dmg_blocked > baseline_blocked:
            dmg_guard_active += 1
        if baseline_mixed > dmg_mixed:
            dmg_mix_reduction += 1
        if baseline_mixed > 0.0:
            baseline_mixed_presence += 1
    dmg_guard_activation_rate = float(dmg_guard_active) / float(total)
    dmg_mixed_mode_reduction_rate = float(dmg_mix_reduction) / float(total)
    baseline_mixed_mode_presence_rate = float(baseline_mixed_presence) / float(total)
    return {
        "runs": float(len(per_run)),
        "dmg_guard_activation_rate": round(dmg_guard_activation_rate, 6),
        "dmg_mixed_mode_reduction_rate": round(dmg_mixed_mode_reduction_rate, 6),
        "baseline_mixed_mode_presence_rate": round(baseline_mixed_mode_presence_rate, 6),
        "dmg_effective_profile": (dmg_guard_activation_rate > 0.0) or (dmg_mixed_mode_reduction_rate > 0.0),
    }


def _checkpoint_signature(
    *,
    input_path: Path,
    similarity_threshold: float,
    merge_threshold: float,
) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "similarity_threshold": float(similarity_threshold),
        "merge_threshold": float(merge_threshold),
    }


def _load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("checkpoint root must be object")
    return payload


def _save_checkpoint(
    *,
    path: Path,
    signature: dict[str, Any],
    run_records: list[dict[str, dict[str, float]]],
    target_runs: int,
    warmup_runs: int,
) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "signature": signature,
        "target_runs": int(target_runs),
        "warmup_runs": int(warmup_runs),
        "runs_completed": len(run_records),
        "run_records": run_records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
    target_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
    warmup_runs: int,
    existing_records: list[dict[str, dict[str, float]]] | None = None,
    max_new_runs: int = 0,
    checkpoint_path: Path | None = None,
    checkpoint_signature: dict[str, Any] | None = None,
) -> tuple[list[dict[str, dict[str, float]]], dict[str, dict[str, Any]], int]:
    base = _base_preference()
    scenario_rows = _scenario_config()
    per_run: list[dict[str, dict[str, float]]] = list(existing_records or [])

    if not per_run:
        for _ in range(max(0, int(warmup_runs))):
            for _name, overrides in scenario_rows:
                pref = _scenario_pref(base, overrides)
                _run_single_scenario(
                    fragments=fragments,
                    preference=pref,
                    similarity_threshold=similarity_threshold,
                    merge_threshold=merge_threshold,
                )

    planned_new_runs = determine_new_runs(
        target_runs=int(target_runs),
        existing_runs=len(per_run),
        max_new_runs=int(max_new_runs),
    )
    start_index = len(per_run)
    for index in range(start_index, start_index + planned_new_runs):
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
        if checkpoint_path is not None:
            _save_checkpoint(
                path=checkpoint_path,
                signature=dict(checkpoint_signature or {}),
                run_records=per_run,
                target_runs=int(target_runs),
                warmup_runs=int(warmup_runs),
            )

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
    return per_run, scenario_stats, planned_new_runs


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
    ceg_stats = compute_distribution_stats(ceg_gain)
    arb_stats = compute_distribution_stats(arb_gain)
    dmg_stats = compute_distribution_stats(dmg_block_gain)
    dmg_mix_stats = compute_distribution_stats(dmg_mix_reduction)
    full_block_stats = compute_distribution_stats(full_block_gain)
    runtime_stats = compute_distribution_stats(runtime_delta)
    activation = compute_activation_metrics(per_run)

    return {
        "ceg_conflict_priority_gain": ceg_stats,
        "arb_detail_budget_gain": arb_stats,
        "dmg_merge_block_gain": dmg_stats,
        "dmg_mixed_mode_reduction": dmg_mix_stats,
        "full_merge_block_gain": full_block_stats,
        "full_runtime_delta_ms": runtime_stats,
        "activation": activation,
        "stability_gate": {
            "ceg_ci95_lower_gt_0": (float(ceg_stats.get("mean") or 0.0) - float(ceg_stats.get("ci95") or 0.0)) > 0.0,
            "arb_ci95_lower_gt_0": (float(arb_stats.get("mean") or 0.0) - float(arb_stats.get("ci95") or 0.0)) > 0.0,
            "dmg_ci95_lower_gt_0": (float(dmg_stats.get("mean") or 0.0) - float(dmg_stats.get("ci95") or 0.0)) > 0.0,
            "full_runtime_ci95_upper_lt_0": (
                float(runtime_stats.get("mean") or 0.0) + float(runtime_stats.get("ci95") or 0.0)
            )
            < 0.0,
        },
        "scenario_stats": scenario_stats,
    }


def _build_report_text(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    gates = dict(summary.get("stability_gate") or {})
    activation = dict(summary.get("activation") or {})

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
        f"- runs_target: {payload.get('runs')}",
        f"- runs_completed: {payload.get('runs_completed')}",
        f"- is_complete: {payload.get('is_complete')}",
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
        "## DMG Activation",
        f"- dmg_guard_activation_rate: {activation.get('dmg_guard_activation_rate')}",
        f"- dmg_mixed_mode_reduction_rate: {activation.get('dmg_mixed_mode_reduction_rate')}",
        f"- baseline_mixed_mode_presence_rate: {activation.get('baseline_mixed_mode_presence_rate')}",
        f"- dmg_effective_profile: {activation.get('dmg_effective_profile')}",
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
    parser.add_argument("--max-new-runs", type=int, default=0)
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--similarity-threshold", type=float, default=0.68)
    parser.add_argument("--merge-threshold", type=float, default=0.82)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    target_runs = max(1, int(args.runs))
    max_new_runs = int(args.max_new_runs)
    if max_new_runs < 0:
        raise ValueError("--max-new-runs must be >= 0")

    signature = _checkpoint_signature(
        input_path=input_path,
        similarity_threshold=float(args.similarity_threshold),
        merge_threshold=float(args.merge_threshold),
    )
    checkpoint_path = Path(args.checkpoint) if str(args.checkpoint).strip() else None
    existing_records: list[dict[str, dict[str, float]]] = []
    if checkpoint_path is not None:
        checkpoint_payload = _load_checkpoint(checkpoint_path)
        if checkpoint_payload is not None and args.resume:
            stored_signature = dict(checkpoint_payload.get("signature") or {})
            if stored_signature != signature:
                raise ValueError("checkpoint signature mismatch with current input/thresholds")
            existing = checkpoint_payload.get("run_records") or []
            if isinstance(existing, list):
                existing_records = [row for row in existing if isinstance(row, dict)]
        elif checkpoint_payload is None and args.resume:
            print(f"resume requested but checkpoint missing: {checkpoint_path.as_posix()}")

    fragments = _load_fragments(input_path)
    run_records, scenario_stats, _new_runs = _build_run_records(
        fragments=fragments,
        target_runs=target_runs,
        similarity_threshold=float(args.similarity_threshold),
        merge_threshold=float(args.merge_threshold),
        warmup_runs=int(args.warmup_runs),
        existing_records=existing_records,
        max_new_runs=max_new_runs,
        checkpoint_path=checkpoint_path,
        checkpoint_signature=signature,
    )
    runs_completed = len(run_records)
    is_complete = runs_completed >= target_runs
    summary = _build_summary(per_run=run_records, scenario_stats=scenario_stats)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset_label or str(input_path),
        "input_path": str(input_path),
        "fragment_count": len(fragments),
        "runs": int(target_runs),
        "runs_completed": int(runs_completed),
        "is_complete": bool(is_complete),
        "max_new_runs": int(max_new_runs),
        "resumed_from_checkpoint": bool(args.resume and bool(existing_records)),
        "warmup_runs": int(args.warmup_runs),
        "similarity_threshold": float(args.similarity_threshold),
        "merge_threshold": float(args.merge_threshold),
        "summary": summary,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if checkpoint_path is not None:
        _save_checkpoint(
            path=checkpoint_path,
            signature=signature,
            run_records=run_records,
            target_runs=target_runs,
            warmup_runs=int(args.warmup_runs),
        )

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_build_report_text(payload), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
