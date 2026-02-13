from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_ablation import synthetic_fragments
from src.memory_cluster.models import PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


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


def _base_pref() -> PreferenceConfig:
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
            },
            "stale_after_hours": 72,
            "detail_budget": {"strong": 220, "weak": 150, "discardable": 90},
            "keep_conflicts": True,
            "enable_l2_clusters": False,
            "hard_keep_tags": ["global_task", "current_task"],
            "protected_path_prefixes": ["src/", "docs/patent_kit/"],
        }
    )


def _parse_counts(text: str) -> list[int]:
    output: list[int] = []
    for token in str(text).split(","):
        item = token.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            continue
        output.append(value)
    if not output:
        return [100, 500, 1000]
    return output


def _scenario_rows() -> list[tuple[str, dict[str, Any]]]:
    return [
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


def _run_scenario(
    *,
    pref: PreferenceConfig,
    fragments: list[Any],
    similarity_threshold: float,
    merge_threshold: float,
    runs: int,
) -> dict[str, Any]:
    elapsed_ms_rows: list[float] = []
    last_result: Any | None = None
    for _ in range(max(1, int(runs))):
        started = perf_counter()
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )
        elapsed_ms_rows.append((perf_counter() - started) * 1000.0)
        last_result = result

    assert last_result is not None
    metrics = last_result.metrics
    return {
        "runs": int(max(1, int(runs))),
        "avg_ms": round(sum(elapsed_ms_rows) / float(len(elapsed_ms_rows)), 3),
        "p95_ms": round(sorted(elapsed_ms_rows)[int((len(elapsed_ms_rows) - 1) * 0.95)], 3),
        "cluster_count": int(metrics.get("cluster_count") or 0),
        "conflict_count": int(metrics.get("conflict_count") or 0),
        "conflict_priority_avg": float(metrics.get("conflict_priority_avg") or 0.0),
        "detail_budget_avg": float(metrics.get("detail_budget_avg") or 0.0),
        "merges_blocked_by_guard": int(metrics.get("merges_blocked_by_guard") or 0),
        "mixed_mode_clusters": _slot_mixing_count(last_result, "mode"),
    }


def _summary_by_scale(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = rows.get("baseline") or {}
    ceg = rows.get("ceg") or {}
    arb = rows.get("arb") or {}
    dmg = rows.get("dmg") or {}
    full = rows.get("full") or {}

    baseline_ms = float(baseline.get("avg_ms") or 0.0)
    full_ms = float(full.get("avg_ms") or 0.0)
    runtime_delta_ratio = 0.0
    if baseline_ms > 0.0:
        runtime_delta_ratio = (full_ms - baseline_ms) / baseline_ms

    return {
        "ceg_conflict_priority_avg_gain": round(
            float(ceg.get("conflict_priority_avg") or 0.0) - float(baseline.get("conflict_priority_avg") or 0.0), 6
        ),
        "arb_detail_budget_avg_gain": round(
            float(arb.get("detail_budget_avg") or 0.0) - float(baseline.get("detail_budget_avg") or 0.0), 6
        ),
        "dmg_merge_block_gain": int(dmg.get("merges_blocked_by_guard") or 0)
        - int(baseline.get("merges_blocked_by_guard") or 0),
        "dmg_mixed_mode_clusters_reduction": int(baseline.get("mixed_mode_clusters") or 0)
        - int(dmg.get("mixed_mode_clusters") or 0),
        "full_conflict_priority_avg_gain": round(
            float(full.get("conflict_priority_avg") or 0.0) - float(baseline.get("conflict_priority_avg") or 0.0), 6
        ),
        "full_detail_budget_avg_gain": round(
            float(full.get("detail_budget_avg") or 0.0) - float(baseline.get("detail_budget_avg") or 0.0), 6
        ),
        "full_merge_block_gain": int(full.get("merges_blocked_by_guard") or 0)
        - int(baseline.get("merges_blocked_by_guard") or 0),
        "full_runtime_delta_ratio": round(runtime_delta_ratio, 6),
        "baseline_cluster_count": int(baseline.get("cluster_count") or 0),
        "full_cluster_count": int(full.get("cluster_count") or 0),
    }


def _resolve_thresholds(profile: str, sim: float | None, merge: float | None) -> tuple[float, float]:
    default_sim = 0.68
    default_merge = 0.82
    if profile == "stress":
        default_sim = 1.1
        default_merge = 0.05
    return float(default_sim if sim is None else sim), float(default_merge if merge is None else merge)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaling benchmark for CEG/ARB/DMG core modules")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--counts", default="100,500,1000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--profile", choices=["realistic", "stress"], default="realistic")
    parser.add_argument("--similarity-threshold", type=float, default=None)
    parser.add_argument("--merge-threshold", type=float, default=None)
    parser.add_argument("--dataset-label", default="synthetic_core_scaling_case")
    args = parser.parse_args()

    counts = _parse_counts(args.counts)
    similarity_threshold, merge_threshold = _resolve_thresholds(
        profile=str(args.profile),
        sim=args.similarity_threshold,
        merge=args.merge_threshold,
    )
    base_pref = _base_pref()

    scales: list[dict[str, Any]] = []
    for count in counts:
        fragments = synthetic_fragments(fragment_count=count)
        scenario_output: dict[str, dict[str, Any]] = {}
        for name, overrides in _scenario_rows():
            pref = _scenario_pref(base_pref, overrides)
            scenario_output[name] = _run_scenario(
                pref=pref,
                fragments=fragments,
                similarity_threshold=similarity_threshold,
                merge_threshold=merge_threshold,
                runs=args.runs,
            )
        scales.append(
            {
                "fragment_count": int(count),
                "scenarios": scenario_output,
                "summary": _summary_by_scale(scenario_output),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset_label),
        "profile": str(args.profile),
        "runs": int(max(1, int(args.runs))),
        "similarity_threshold": float(similarity_threshold),
        "merge_threshold": float(merge_threshold),
        "counts": counts,
        "scales": scales,
        "notes": {
            "focus": "core_claims_only",
            "candidate_filter_ann": "excluded_from_scaling_benchmark",
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Core Scaling Benchmark Report",
            "",
            f"- generated_at: {payload['generated_at']}",
            f"- dataset: {payload['dataset']}",
            f"- profile: {payload['profile']}",
            f"- runs_per_scenario: {payload['runs']}",
            f"- similarity_threshold: {payload['similarity_threshold']}",
            f"- merge_threshold: {payload['merge_threshold']}",
            f"- counts: {','.join(str(item) for item in counts)}",
            "",
            "## Per Scale Summary",
        ]
        for scale in scales:
            summary = scale.get("summary") or {}
            lines.extend(
                [
                    f"- N={scale.get('fragment_count')}: "
                    f"ceg_gain={summary.get('ceg_conflict_priority_avg_gain')}, "
                    f"arb_gain={summary.get('arb_detail_budget_avg_gain')}, "
                    f"dmg_block_gain={summary.get('dmg_merge_block_gain')}, "
                    f"dmg_mix_reduction={summary.get('dmg_mixed_mode_clusters_reduction')}, "
                    f"full_runtime_delta_ratio={summary.get('full_runtime_delta_ratio')}",
                ]
            )

        lines.extend(
            [
                "",
                "## Scenario Runtime (avg_ms)",
            ]
        )
        for scale in scales:
            row = scale.get("scenarios") or {}
            lines.extend(
                [
                    f"- N={scale.get('fragment_count')}: "
                    f"baseline={((row.get('baseline') or {}).get('avg_ms'))}, "
                    f"ceg={((row.get('ceg') or {}).get('avg_ms'))}, "
                    f"arb={((row.get('arb') or {}).get('avg_ms'))}, "
                    f"dmg={((row.get('dmg') or {}).get('avg_ms'))}, "
                    f"full={((row.get('full') or {}).get('avg_ms'))}",
                ]
            )

        lines.extend(
            [
                "",
                "## Notes",
                "- This benchmark focuses on CEG/ARB/DMG evidence only.",
                "- Candidate filter and ANN are excluded because they remain experimental.",
                "",
                "## Summary (Raw JSON)",
                f"- {json.dumps({'counts': counts, 'scales': scales}, ensure_ascii=False)}",
                "",
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
