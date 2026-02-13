from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
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


def _run_case(
    *,
    fragments: list[MemoryFragment],
    pref: PreferenceConfig,
    similarity_threshold: float,
    merge_threshold: float,
    runs: int,
    warmup_runs: int,
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
    metrics = (last.metrics if last else {})
    return {
        "runs": len(durations_ms),
        "avg_ms": round(sum(durations_ms) / float(len(durations_ms)), 3),
        "p95_ms": round(ordered[p95_idx], 3),
        "metrics": metrics,
        "mixed_mode_clusters": _slot_mixing_count(last, "mode") if last is not None else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CEG/ARB/DMG ablation on external dataset")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--similarity-threshold", type=float, default=0.68)
    parser.add_argument("--merge-threshold", type=float, default=0.82)
    args = parser.parse_args()

    fragments = _load_fragments(Path(args.input))
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

    scenarios = [
        ("baseline", {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": False}),
        ("ceg", {"enable_conflict_graph": True, "enable_adaptive_budget": False, "enable_dual_merge_guard": False}),
        ("arb", {"enable_conflict_graph": False, "enable_adaptive_budget": True, "enable_dual_merge_guard": False}),
        ("dmg", {"enable_conflict_graph": False, "enable_adaptive_budget": False, "enable_dual_merge_guard": True}),
        ("full", {"enable_conflict_graph": True, "enable_adaptive_budget": True, "enable_dual_merge_guard": True}),
    ]

    rows: list[dict[str, Any]] = []
    for name, overrides in scenarios:
        pref = _scenario_pref(base_pref, overrides)
        result = _run_case(
            fragments=fragments,
            pref=pref,
            similarity_threshold=float(args.similarity_threshold),
            merge_threshold=float(args.merge_threshold),
            runs=args.runs,
            warmup_runs=args.warmup_runs,
        )
        rows.append({"scenario": name, **result})

    by_name = {row["scenario"]: row for row in rows}
    baseline = by_name.get("baseline", {})
    ceg = by_name.get("ceg", {})
    arb = by_name.get("arb", {})
    dmg = by_name.get("dmg", {})
    full = by_name.get("full", {})

    summary = {
        "ceg_conflict_priority_avg_gain": round(
            float(((ceg.get("metrics") or {}).get("conflict_priority_avg") or 0.0))
            - float(((baseline.get("metrics") or {}).get("conflict_priority_avg") or 0.0)),
            6,
        ),
        "arb_detail_budget_avg_gain": round(
            float(((arb.get("metrics") or {}).get("detail_budget_avg") or 0.0))
            - float(((baseline.get("metrics") or {}).get("detail_budget_avg") or 0.0)),
            6,
        ),
        "dmg_merge_block_gain": int((dmg.get("metrics") or {}).get("merges_blocked_by_guard") or 0)
        - int((baseline.get("metrics") or {}).get("merges_blocked_by_guard") or 0),
        "dmg_mixed_mode_clusters_reduction": int(baseline.get("mixed_mode_clusters") or 0)
        - int(dmg.get("mixed_mode_clusters") or 0),
        "full_merge_block_gain": int((full.get("metrics") or {}).get("merges_blocked_by_guard") or 0)
        - int((baseline.get("metrics") or {}).get("merges_blocked_by_guard") or 0),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(Path(args.input)),
        "fragment_count": len(fragments),
        "similarity_threshold": float(args.similarity_threshold),
        "merge_threshold": float(args.merge_threshold),
        "runs": int(args.runs),
        "scenarios": rows,
        "summary": summary,
        "source_distribution": dict(Counter(item.agent_id for item in fragments)),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        lines = [
            "# Core Ablation On Dataset",
            "",
            f"- generated_at: {payload.get('generated_at')}",
            f"- dataset: {payload.get('dataset')}",
            f"- fragment_count: {payload.get('fragment_count')}",
            f"- similarity_threshold: {payload.get('similarity_threshold')}",
            f"- merge_threshold: {payload.get('merge_threshold')}",
            f"- runs: {payload.get('runs')}",
            "",
            "## Scenario Summary",
        ]
        for row in rows:
            metrics = row.get("metrics") or {}
            lines.append(
                f"- {row.get('scenario')}: avg_ms={row.get('avg_ms')}, "
                f"cluster_count={metrics.get('cluster_count')}, "
                f"conflict_priority_avg={metrics.get('conflict_priority_avg')}, "
                f"detail_budget_avg={metrics.get('detail_budget_avg')}, "
                f"merges_blocked_by_guard={metrics.get('merges_blocked_by_guard')}, "
                f"mixed_mode_clusters={row.get('mixed_mode_clusters')}"
            )
        lines.extend(
            [
                "",
                "## Gains vs baseline",
                f"- ceg_conflict_priority_avg_gain: {summary.get('ceg_conflict_priority_avg_gain')}",
                f"- arb_detail_budget_avg_gain: {summary.get('arb_detail_budget_avg_gain')}",
                f"- dmg_merge_block_gain: {summary.get('dmg_merge_block_gain')}",
                f"- dmg_mixed_mode_clusters_reduction: {summary.get('dmg_mixed_mode_clusters_reduction')}",
                f"- full_merge_block_gain: {summary.get('full_merge_block_gain')}",
                "",
                "## Raw JSON",
                f"- {json.dumps(payload, ensure_ascii=False)}",
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
