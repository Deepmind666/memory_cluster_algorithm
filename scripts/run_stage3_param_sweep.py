from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_ann_hybrid_benchmark import compare_to_baseline, run_case as run_ann_case, synthetic_fragments as ann_fragments
from scripts.run_candidate_filter_benchmark import (
    run_case as run_candidate_case,
    summarize_pair,
    synthetic_fragments as candidate_fragments,
)
from src.memory_cluster.cluster import IncrementalClusterer
from src.memory_cluster.embed import HashEmbeddingProvider
from src.memory_cluster.models import PreferenceConfig


def _parse_int_list(text: str) -> list[int]:
    out: list[int] = []
    for token in str(text).split(","):
        item = token.strip()
        if not item:
            continue
        out.append(int(item))
    if not out:
        raise ValueError("empty integer list")
    return out


def _candidate_signature_stats(
    *,
    fragments: list[Any],
    bucket_dims: int,
    max_neighbors: int,
    projection_steps: int,
    signature_radius: int,
) -> dict[str, float]:
    provider = HashEmbeddingProvider(dim=256)
    clusterer = IncrementalClusterer(
        enable_merge_candidate_filter=True,
        merge_candidate_bucket_dims=max(1, int(bucket_dims)),
        merge_candidate_max_neighbors=max(1, int(max_neighbors)),
        merge_candidate_projection_steps=max(1, int(projection_steps)),
        merge_candidate_signature_radius=max(0, int(signature_radius)),
    )
    vectors = [provider.embed(item.content) for item in fragments]
    counts = Counter(clusterer._candidate_signature(vec) for vec in vectors)
    total = max(1, len(vectors))
    return {
        "unique_ratio": round(len(counts) / float(total), 6),
        "max_bucket_ratio": round(max(counts.values()) / float(total), 6),
    }


def _ann_signature_stats(
    *,
    fragments: list[Any],
    ann_num_tables: int,
    ann_bits: int,
    ann_projection_steps: int,
) -> dict[str, float]:
    provider = HashEmbeddingProvider(dim=256)
    clusterer = IncrementalClusterer(
        enable_merge_ann_candidates=True,
        merge_ann_num_tables=max(1, int(ann_num_tables)),
        merge_ann_bits_per_table=max(1, int(ann_bits)),
        merge_ann_projection_steps=max(1, int(ann_projection_steps)),
    )
    vectors = [provider.embed(item.content) for item in fragments]
    signatures = [clusterer._ann_signature(vec, 0) for vec in vectors]
    counts = Counter(signatures)
    total = max(1, len(vectors))
    weights = [bin(value).count("1") for value in signatures]
    return {
        "unique_ratio": round(len(counts) / float(total), 6),
        "max_bucket_ratio": round(max(counts.values()) / float(total), 6),
        "weight_spread": int(max(weights) - min(weights)) if weights else 0,
    }


def _run_candidate_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    fragments = candidate_fragments(args.fragment_count)
    baseline_pref = PreferenceConfig.from_dict(
        {
            "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
            "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
            "enable_merge_candidate_filter": False,
        }
    )

    rows: list[dict[str, Any]] = []
    for projection_steps in _parse_int_list(args.candidate_projection_steps):
        for signature_radius in _parse_int_list(args.candidate_signature_radius):
            for max_neighbors in _parse_int_list(args.candidate_max_neighbors):
                pref = PreferenceConfig.from_dict(
                    {
                        **baseline_pref.to_dict(),
                        "enable_merge_candidate_filter": True,
                        "merge_candidate_bucket_dims": int(args.candidate_bucket_dims),
                        "merge_candidate_max_neighbors": int(max_neighbors),
                        "merge_candidate_projection_steps": int(projection_steps),
                        "merge_candidate_signature_radius": int(signature_radius),
                    }
                )
                sparse_base = run_candidate_case(
                    fragments=fragments,
                    pref=baseline_pref,
                    runs=args.runs,
                    warmup_runs=args.warmup_runs,
                    similarity_threshold=args.sparse_similarity_threshold,
                    merge_threshold=args.sparse_merge_threshold,
                )
                sparse_opt = run_candidate_case(
                    fragments=fragments,
                    pref=pref,
                    runs=args.runs,
                    warmup_runs=args.warmup_runs,
                    similarity_threshold=args.sparse_similarity_threshold,
                    merge_threshold=args.sparse_merge_threshold,
                )
                active_base = run_candidate_case(
                    fragments=fragments,
                    pref=baseline_pref,
                    runs=args.runs,
                    warmup_runs=args.warmup_runs,
                    similarity_threshold=args.active_similarity_threshold,
                    merge_threshold=args.active_merge_threshold,
                )
                active_opt = run_candidate_case(
                    fragments=fragments,
                    pref=pref,
                    runs=args.runs,
                    warmup_runs=args.warmup_runs,
                    similarity_threshold=args.active_similarity_threshold,
                    merge_threshold=args.active_merge_threshold,
                )
                sparse_summary = summarize_pair(sparse_base, sparse_opt)
                active_summary = summarize_pair(active_base, active_opt)
                signature_stats = _candidate_signature_stats(
                    fragments=fragments,
                    bucket_dims=int(args.candidate_bucket_dims),
                    max_neighbors=int(max_neighbors),
                    projection_steps=int(projection_steps),
                    signature_radius=int(signature_radius),
                )
                quality_gate = bool(active_summary.get("cluster_count_equal")) and bool(
                    active_summary.get("merges_applied_equal")
                )
                signature_gate = (float(signature_stats.get("unique_ratio") or 0.0) >= 0.20) and (
                    float(signature_stats.get("max_bucket_ratio") or 1.0) <= 0.25
                )
                rows.append(
                    {
                        "params": {
                            "bucket_dims": int(args.candidate_bucket_dims),
                            "max_neighbors": int(max_neighbors),
                            "projection_steps": int(projection_steps),
                            "signature_radius": int(signature_radius),
                        },
                        "sparse": sparse_summary,
                        "active": active_summary,
                        "signature": signature_stats,
                        "quality_gate_pass": quality_gate,
                        "signature_gate_pass": signature_gate,
                        "all_gates_pass": quality_gate and signature_gate,
                    }
                )
    rows.sort(
        key=lambda item: (
            not bool(item.get("all_gates_pass")),
            -float(((item.get("active") or {}).get("avg_speedup_ratio") or -999.0)),
            -float(((item.get("sparse") or {}).get("avg_speedup_ratio") or -999.0)),
        )
    )
    return rows


def _run_ann_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    sparse_frags = ann_fragments(args.fragment_count, dataset_mode="sparse")
    active_frags = ann_fragments(args.fragment_count, dataset_mode="active")
    base_pref = PreferenceConfig.from_dict(
        {
            "category_strength": {"method": "strong", "evidence": "strong", "noise": "discardable"},
            "detail_budget": {"strong": 220, "weak": 140, "discardable": 80},
            "enable_merge_upper_bound_prune": True,
            "merge_prune_dims": int(args.prune_dims),
        }
    )

    rows: list[dict[str, Any]] = []
    for ann_steps in _parse_int_list(args.ann_projection_steps):
        for ann_tables in _parse_int_list(args.ann_num_tables):
            for ann_bits in _parse_int_list(args.ann_bits_per_table):
                for ann_probe in _parse_int_list(args.ann_probe_radius):
                    for ann_neighbors in _parse_int_list(args.ann_max_neighbors):
                        ann_pref = PreferenceConfig.from_dict(
                            {
                                **base_pref.to_dict(),
                                "enable_merge_ann_candidates": True,
                                "merge_ann_num_tables": int(ann_tables),
                                "merge_ann_bits_per_table": int(ann_bits),
                                "merge_ann_probe_radius": int(ann_probe),
                                "merge_ann_max_neighbors": int(ann_neighbors),
                                "merge_ann_score_dims": int(args.ann_score_dims),
                                "merge_ann_projection_steps": int(ann_steps),
                            }
                        )
                        sparse_base = run_ann_case(
                            fragments=sparse_frags,
                            pref=base_pref,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            similarity_threshold=args.sparse_similarity_threshold,
                            merge_threshold=args.sparse_merge_threshold,
                        )
                        sparse_ann = run_ann_case(
                            fragments=sparse_frags,
                            pref=ann_pref,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            similarity_threshold=args.sparse_similarity_threshold,
                            merge_threshold=args.sparse_merge_threshold,
                        )
                        active_base = run_ann_case(
                            fragments=active_frags,
                            pref=base_pref,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            similarity_threshold=args.active_similarity_threshold,
                            merge_threshold=args.active_merge_threshold,
                        )
                        active_ann = run_ann_case(
                            fragments=active_frags,
                            pref=ann_pref,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            similarity_threshold=args.active_similarity_threshold,
                            merge_threshold=args.active_merge_threshold,
                        )
                        sparse_summary = compare_to_baseline(sparse_base, sparse_ann)
                        active_summary = compare_to_baseline(active_base, active_ann)
                        signature_stats = _ann_signature_stats(
                            fragments=active_frags,
                            ann_num_tables=int(ann_tables),
                            ann_bits=int(ann_bits),
                            ann_projection_steps=int(ann_steps),
                        )
                        signature_gate = (
                            float(signature_stats.get("unique_ratio") or 0.0) >= 0.25
                            and float(signature_stats.get("max_bucket_ratio") or 1.0) <= 0.25
                            and int(signature_stats.get("weight_spread") or 0) > 2
                        )
                        quality_gate = bool(active_summary.get("quality_gate_pass"))
                        rows.append(
                            {
                                "params": {
                                    "ann_projection_steps": int(ann_steps),
                                    "ann_num_tables": int(ann_tables),
                                    "ann_bits_per_table": int(ann_bits),
                                    "ann_probe_radius": int(ann_probe),
                                    "ann_max_neighbors": int(ann_neighbors),
                                    "ann_score_dims": int(args.ann_score_dims),
                                },
                                "sparse": sparse_summary,
                                "active": active_summary,
                                "signature": signature_stats,
                                "quality_gate_pass": quality_gate,
                                "signature_gate_pass": signature_gate,
                                "all_gates_pass": quality_gate and signature_gate,
                            }
                        )

    rows.sort(
        key=lambda item: (
            not bool(item.get("all_gates_pass")),
            -float(((item.get("active") or {}).get("avg_speedup_ratio") or -999.0)),
            -float(((item.get("sparse") or {}).get("avg_speedup_ratio") or -999.0)),
        )
    )
    return rows


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    cand_rows = payload.get("candidate_grid") or []
    ann_rows = payload.get("ann_grid") or []
    lines = [
        "# Stage3 Parameter Sweep Report",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- fragment_count: {payload.get('fragment_count')}",
        f"- runs: {payload.get('runs')}",
        "",
        "## Candidate Top-10",
    ]
    for idx, row in enumerate(cand_rows[:10], start=1):
        lines.append(
            f"- [{idx}] params={row.get('params')} "
            f"active_speedup={((row.get('active') or {}).get('avg_speedup_ratio'))} "
            f"active_equal={((row.get('active') or {}).get('merges_applied_equal'))} "
            f"signature={row.get('signature')} gates={row.get('all_gates_pass')}"
        )
    lines.extend(["", "## ANN Top-10"])
    for idx, row in enumerate(ann_rows[:10], start=1):
        lines.append(
            f"- [{idx}] params={row.get('params')} "
            f"active_speedup={((row.get('active') or {}).get('avg_speedup_ratio'))} "
            f"quality={row.get('quality_gate_pass')} "
            f"signature={row.get('signature')} gates={row.get('all_gates_pass')}"
        )
    lines.extend(
        [
            "",
            "## Recommendation Snapshot",
            f"- candidate_best: {(cand_rows[0].get('params') if cand_rows else {})}",
            f"- ann_best: {(ann_rows[0].get('params') if ann_rows else {})}",
            "",
            "## Raw JSON",
            f"- {json.dumps(payload, ensure_ascii=False)}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage3 candidate/ANN parameter sweep")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=False)
    parser.add_argument("--fragment-count", type=int, default=120)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--prune-dims", type=int, default=48)
    parser.add_argument("--sparse-similarity-threshold", type=float, default=2.0)
    parser.add_argument("--sparse-merge-threshold", type=float, default=0.95)
    parser.add_argument("--active-similarity-threshold", type=float, default=0.82)
    parser.add_argument("--active-merge-threshold", type=float, default=0.85)
    parser.add_argument("--candidate-bucket-dims", type=int, default=10)
    parser.add_argument("--candidate-projection-steps", default="16,24,32,48")
    parser.add_argument("--candidate-signature-radius", default="2,3,4")
    parser.add_argument("--candidate-max-neighbors", default="48,64")
    parser.add_argument("--ann-projection-steps", default="12,16,24,32")
    parser.add_argument("--ann-num-tables", default="3,4,6")
    parser.add_argument("--ann-bits-per-table", default="8,10")
    parser.add_argument("--ann-probe-radius", default="0,1")
    parser.add_argument("--ann-max-neighbors", default="24,32,48")
    parser.add_argument("--ann-score-dims", type=int, default=48)
    args = parser.parse_args()

    candidate_rows = _run_candidate_grid(args)
    ann_rows = _run_ann_grid(args)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fragment_count": int(args.fragment_count),
        "runs": int(args.runs),
        "candidate_grid": candidate_rows,
        "ann_grid": ann_rows,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        _write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
