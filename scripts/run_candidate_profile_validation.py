from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_candidate_filter_benchmark import run_case, summarize_pair, synthetic_fragments
from src.memory_cluster.models import MemoryFragment, PreferenceConfig


def _parse_int_list(text: str) -> list[int]:
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
        raise ValueError("sizes cannot be empty")
    return output


def _load_fragments(path: Path) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(MemoryFragment.from_dict(json.loads(line)))
    rows.sort(key=lambda item: item.timestamp)
    return rows


def _base_pref() -> PreferenceConfig:
    return PreferenceConfig.from_dict(
        {
            "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
            "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
            "enable_merge_candidate_filter": False,
        }
    )


def _candidate_pref(
    *,
    base: PreferenceConfig,
    bucket_dims: int,
    max_neighbors: int,
    projection_steps: int,
    signature_radius: int,
) -> PreferenceConfig:
    payload = base.to_dict()
    payload.update(
        {
            "enable_merge_candidate_filter": True,
            "merge_candidate_bucket_dims": max(1, int(bucket_dims)),
            "merge_candidate_max_neighbors": max(1, int(max_neighbors)),
            "merge_candidate_projection_steps": max(1, int(projection_steps)),
            "merge_candidate_signature_radius": max(0, int(signature_radius)),
        }
    )
    return PreferenceConfig.from_dict(payload)


def _quality_gate(summary: dict[str, Any]) -> bool:
    return bool(summary.get("cluster_count_equal")) and bool(summary.get("merges_applied_equal"))


def _run_profile_comparison(
    *,
    fragments: list[MemoryFragment],
    sizes: list[int],
    runs: int,
    warmup_runs: int,
    similarity_threshold: float,
    merge_threshold: float,
    bucket_dims: int,
    max_neighbors: int,
    projection_steps: int,
    default_radius: int,
    fast_radius: int,
) -> dict[str, Any]:
    if not fragments:
        raise ValueError("no fragments provided")

    max_size = max(sizes)
    if len(fragments) < max_size:
        raise ValueError(f"fragment count too small: need {max_size}, got {len(fragments)}")

    base = _base_pref()
    default_pref = _candidate_pref(
        base=base,
        bucket_dims=bucket_dims,
        max_neighbors=max_neighbors,
        projection_steps=projection_steps,
        signature_radius=default_radius,
    )
    fast_pref = _candidate_pref(
        base=base,
        bucket_dims=bucket_dims,
        max_neighbors=max_neighbors,
        projection_steps=projection_steps,
        signature_radius=fast_radius,
    )

    rows: list[dict[str, Any]] = []
    for size in sorted(sizes):
        subset = fragments[:size]
        baseline = run_case(
            fragments=subset,
            pref=base,
            runs=runs,
            warmup_runs=warmup_runs,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )
        default_case = run_case(
            fragments=subset,
            pref=default_pref,
            runs=runs,
            warmup_runs=warmup_runs,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )
        fast_case = run_case(
            fragments=subset,
            pref=fast_pref,
            runs=runs,
            warmup_runs=warmup_runs,
            similarity_threshold=similarity_threshold,
            merge_threshold=merge_threshold,
        )
        default_summary = summarize_pair(baseline, default_case)
        fast_summary = summarize_pair(baseline, fast_case)
        rows.append(
            {
                "fragment_count": int(size),
                "baseline": baseline,
                "default_profile": {
                    "params": {
                        "bucket_dims": int(bucket_dims),
                        "max_neighbors": int(max_neighbors),
                        "projection_steps": int(projection_steps),
                        "signature_radius": int(default_radius),
                    },
                    "case": default_case,
                    "summary": default_summary,
                    "quality_gate_pass": _quality_gate(default_summary),
                },
                "fast_profile": {
                    "params": {
                        "bucket_dims": int(bucket_dims),
                        "max_neighbors": int(max_neighbors),
                        "projection_steps": int(projection_steps),
                        "signature_radius": int(fast_radius),
                    },
                    "case": fast_case,
                    "summary": fast_summary,
                    "quality_gate_pass": _quality_gate(fast_summary),
                },
            }
        )

    default_all_pass = all(bool((row.get("default_profile") or {}).get("quality_gate_pass")) for row in rows)
    fast_all_pass = all(bool((row.get("fast_profile") or {}).get("quality_gate_pass")) for row in rows)
    fast_min_speedup = min(
        float(((row.get("fast_profile") or {}).get("summary") or {}).get("avg_speedup_ratio") or 0.0)
        for row in rows
    )
    fast_any_positive = any(
        float((((row.get("fast_profile") or {}).get("summary") or {}).get("avg_speedup_ratio") or 0.0) > 0.0) for row in rows
    )
    recommendation = "keep_default_radius4"
    if fast_all_pass and fast_min_speedup >= -0.05 and fast_any_positive:
        recommendation = "fast_profile_can_be_promoted_after_more_runs"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sizes": sorted(sizes),
        "runs": int(runs),
        "warmup_runs": int(warmup_runs),
        "similarity_threshold": float(similarity_threshold),
        "merge_threshold": float(merge_threshold),
        "rows": rows,
        "summary": {
            "default_all_quality_gate_pass": bool(default_all_pass),
            "fast_all_quality_gate_pass": bool(fast_all_pass),
            "fast_min_speedup_ratio": round(float(fast_min_speedup), 6),
            "fast_any_positive_speedup": bool(fast_any_positive),
            "recommendation": recommendation,
        },
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Candidate Profile Validation",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- dataset_label: {payload.get('dataset_label')}",
        f"- source: {payload.get('source')}",
        f"- runs: {payload.get('runs')}",
        f"- warmup_runs: {payload.get('warmup_runs')}",
        f"- sizes: {payload.get('sizes')}",
        f"- similarity_threshold: {payload.get('similarity_threshold')}",
        f"- merge_threshold: {payload.get('merge_threshold')}",
        "",
        "## Per Size",
    ]
    for row in payload.get("rows") or []:
        default_summary = ((row.get("default_profile") or {}).get("summary") or {})
        fast_summary = ((row.get("fast_profile") or {}).get("summary") or {})
        lines.extend(
            [
                f"### N={row.get('fragment_count')}",
                f"- default(r=4): speedup={default_summary.get('avg_speedup_ratio')}, "
                f"quality_gate={((row.get('default_profile') or {}).get('quality_gate_pass'))}, "
                f"merges_equal={default_summary.get('merges_applied_equal')}",
                f"- fast(r=3): speedup={fast_summary.get('avg_speedup_ratio')}, "
                f"quality_gate={((row.get('fast_profile') or {}).get('quality_gate_pass'))}, "
                f"merges_equal={fast_summary.get('merges_applied_equal')}",
                "",
            ]
        )

    summary = payload.get("summary") or {}
    lines.extend(
        [
            "## Summary",
            f"- default_all_quality_gate_pass: {summary.get('default_all_quality_gate_pass')}",
            f"- fast_all_quality_gate_pass: {summary.get('fast_all_quality_gate_pass')}",
            f"- fast_min_speedup_ratio: {summary.get('fast_min_speedup_ratio')}",
            f"- fast_any_positive_speedup: {summary.get('fast_any_positive_speedup')}",
            f"- recommendation: {summary.get('recommendation')}",
            "",
            "## Raw JSON",
            f"- {json.dumps(payload, ensure_ascii=False)}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate default vs fast profile across scales")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--dataset-input", required=False)
    parser.add_argument("--dataset-label", default="synthetic")
    parser.add_argument("--sizes", default="240,1000,5000")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--similarity-threshold", type=float, default=0.82)
    parser.add_argument("--merge-threshold", type=float, default=0.85)
    parser.add_argument("--bucket-dims", type=int, default=10)
    parser.add_argument("--max-neighbors", type=int, default=48)
    parser.add_argument("--projection-steps", type=int, default=32)
    parser.add_argument("--default-radius", type=int, default=4)
    parser.add_argument("--fast-radius", type=int, default=3)
    args = parser.parse_args()

    sizes = _parse_int_list(args.sizes)
    max_size = max(sizes)
    if args.dataset_input:
        source = Path(args.dataset_input)
        fragments = _load_fragments(source)
    else:
        source = Path("synthetic_candidate_filter_case")
        fragments = synthetic_fragments(max_size)

    payload = _run_profile_comparison(
        fragments=fragments,
        sizes=sizes,
        runs=max(1, int(args.runs)),
        warmup_runs=max(0, int(args.warmup_runs)),
        similarity_threshold=float(args.similarity_threshold),
        merge_threshold=float(args.merge_threshold),
        bucket_dims=max(1, int(args.bucket_dims)),
        max_neighbors=max(1, int(args.max_neighbors)),
        projection_steps=max(1, int(args.projection_steps)),
        default_radius=max(0, int(args.default_radius)),
        fast_radius=max(0, int(args.fast_radius)),
    )
    payload["dataset_label"] = str(args.dataset_label)
    payload["source"] = source.as_posix()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        _write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
