from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


COMMAND_CATALOG: dict[str, str] = {
    "CMD_ABLATION_SMALL": "python scripts/run_ablation.py --output outputs/ablation_metrics.json --report docs/eval/ablation_report_cn.md",
    "CMD_ABLATION_LARGE": "python scripts/run_ablation.py --output outputs/ablation_metrics_large.json --report docs/eval/ablation_report_large_cn.md --fragment-count 100 --similarity-threshold 0.68 --merge-threshold 0.82 --dataset-label synthetic_conflict_memory_case_large",
    "CMD_ABLATION_STRESS": "python scripts/run_ablation.py --output outputs/ablation_metrics_stress.json --report docs/eval/ablation_report_stress_cn.md --fragment-count 100 --similarity-threshold 1.1 --merge-threshold 0.05 --dataset-label synthetic_conflict_memory_case_stress",
    "CMD_CORE_SCALING_REALISTIC": "python scripts/run_core_scaling_benchmark.py --output outputs/core_scaling_realistic.json --report docs/eval/core_scaling_realistic_report.md --counts 100,500,1000,2000,5000 --runs 5 --profile realistic --dataset-label synthetic_core_scaling_case_realistic_v2",
    "CMD_CORE_SCALING_STRESS": "python scripts/run_core_scaling_benchmark.py --output outputs/core_scaling_stress.json --report docs/eval/core_scaling_stress_report.md --counts 500,1000 --runs 4 --profile stress",
    "CMD_GEN_SEMI_REAL_REALISTIC": "python scripts/generate_semi_real_dataset.py --output data/examples/semi_real_memory_fragments_5000_realistic.jsonl --fragment-count 5000 --profile realistic --seed 20260211",
    "CMD_GEN_SEMI_REAL_STRESS": "python scripts/generate_semi_real_dataset.py --output data/examples/semi_real_memory_fragments_5000_stress.jsonl --fragment-count 5000 --profile stress --seed 20260211",
    "CMD_ABLATION_SEMI_REAL_REALISTIC": "python scripts/run_core_ablation_on_dataset.py --input data/examples/semi_real_memory_fragments_5000_realistic.jsonl --output outputs/core_ablation_semi_real_5000_realistic.json --report docs/eval/core_ablation_semi_real_5000_realistic_report.md --runs 5 --warmup-runs 1 --similarity-threshold 0.68 --merge-threshold 0.82",
    "CMD_ABLATION_SEMI_REAL_STRESS": "python scripts/run_core_ablation_on_dataset.py --input data/examples/semi_real_memory_fragments_5000_stress.jsonl --output outputs/core_ablation_semi_real_5000_stress_runs2.json --report docs/eval/core_ablation_semi_real_5000_stress_runs2_report.md --runs 2 --warmup-runs 0 --similarity-threshold 1.1 --merge-threshold 0.05",
    "CMD_CORE_STABILITY_REALISTIC": "python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_2000_realistic.jsonl --output outputs/core_claim_stability_semi_real_2000_realistic.json --report docs/eval/core_claim_stability_semi_real_2000_realistic_report.md --runs 12 --warmup-runs 2 --similarity-threshold 0.68 --merge-threshold 0.82",
    "CMD_CORE_STABILITY_STRESS": "python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_2000_stress.jsonl --output outputs/core_claim_stability_semi_real_2000_stress.json --report docs/eval/core_claim_stability_semi_real_2000_stress_report.md --runs 4 --warmup-runs 1 --similarity-threshold 1.1 --merge-threshold 0.05",
    "CMD_CORE_STABILITY_REALISTIC_5000": "python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_5000_realistic.jsonl --output outputs/core_claim_stability_semi_real_5000_realistic.json --report docs/eval/core_claim_stability_semi_real_5000_realistic_report.md --runs 6 --warmup-runs 1 --similarity-threshold 0.68 --merge-threshold 0.82 --checkpoint outputs/core_claim_stability_semi_real_5000_realistic_checkpoint.json",
    "CMD_CORE_STABILITY_STRESS_5000_BATCH1": "python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_5000_stress.jsonl --output outputs/core_claim_stability_semi_real_5000_stress.json --report docs/eval/core_claim_stability_semi_real_5000_stress_report.md --runs 3 --max-new-runs 1 --warmup-runs 0 --similarity-threshold 1.1 --merge-threshold 0.05 --checkpoint outputs/core_claim_stability_semi_real_5000_stress_checkpoint.json",
    "CMD_CORE_STABILITY_STRESS_5000_RESUME": "python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_5000_stress.jsonl --output outputs/core_claim_stability_semi_real_5000_stress.json --report docs/eval/core_claim_stability_semi_real_5000_stress_report.md --runs 3 --max-new-runs 2 --warmup-runs 0 --similarity-threshold 1.1 --merge-threshold 0.05 --checkpoint outputs/core_claim_stability_semi_real_5000_stress_checkpoint.json --resume",
    "CMD_PRUNE": "python scripts/run_prune_benchmark.py --output outputs/prune_benchmark.json --report docs/eval/prune_benchmark_report.md",
    "CMD_CANDIDATE": "python scripts/run_candidate_filter_benchmark.py --output outputs/candidate_filter_benchmark.json --report docs/eval/candidate_filter_benchmark_report.md --fragment-count 240 --runs 10 --warmup-runs 2",
    "CMD_CANDIDATE_PROFILE_SYNTH": "python scripts/run_candidate_profile_validation.py --dataset-label synthetic_active --output outputs/candidate_profile_validation_synthetic_active.json --report docs/eval/candidate_profile_validation_synthetic_active_report.md --sizes 240,1000,5000 --runs 2 --warmup-runs 1 --similarity-threshold 0.82 --merge-threshold 0.85",
    "CMD_CANDIDATE_PROFILE_REALISTIC": "python scripts/run_candidate_profile_validation.py --dataset-input data/examples/semi_real_memory_fragments_5000_realistic.jsonl --dataset-label semi_real_realistic --output outputs/candidate_profile_validation_realistic.json --report docs/eval/candidate_profile_validation_realistic_report.md --sizes 240,1000,5000 --runs 2 --warmup-runs 1 --similarity-threshold 0.68 --merge-threshold 0.82",
    "CMD_CANDIDATE_PROFILE_STRESS": "python scripts/run_candidate_profile_validation.py --dataset-input data/examples/semi_real_memory_fragments_5000_stress.jsonl --dataset-label semi_real_stress --output outputs/candidate_profile_validation_stress.json --report docs/eval/candidate_profile_validation_stress_report.md --sizes 240,1000,5000 --runs 1 --warmup-runs 0 --similarity-threshold 1.1 --merge-threshold 0.05",
    "CMD_STAGE2_GUARDRAIL": "python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md",
    "CMD_ANN_HYBRID": "python scripts/run_ann_hybrid_benchmark.py --output outputs/ann_hybrid_benchmark.json --report docs/eval/ann_hybrid_benchmark_report.md --fragment-count 240 --runs 10 --warmup-runs 2",
    "CMD_SEMANTIC": "python scripts/run_semantic_regression.py --output outputs/semantic_regression_metrics.json --report docs/eval/semantic_regression_report.md",
    "CMD_STAGE3_SWEEP": "python scripts/run_stage3_param_sweep.py --output outputs/stage3_param_sweep.json --report docs/eval/stage3_param_sweep_report.md --fragment-count 120 --runs 3 --warmup-runs 1",
}


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path.as_posix()}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"invalid-json: {path.as_posix()} ({exc})"
    if not isinstance(payload, dict):
        return None, f"invalid-root: {path.as_posix()} (expect object)"
    return payload, None


def _scenario_by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if name:
            out[name] = row
    return out


def _scale_summary_by_count(payload: dict[str, Any], count: int) -> dict[str, Any]:
    for row in payload.get("scales") or []:
        if not isinstance(row, dict):
            continue
        if int(row.get("fragment_count") or 0) == int(count):
            return dict(row.get("summary") or {})
    return {}


def _pick(summary: dict[str, Any], key: str) -> Any:
    return summary.get(key)


def _fmt_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _claim_refs_to_text(refs: list[int]) -> str:
    return "/".join(f"权利要求{item}" for item in refs)


def _extract_claim_numbers(claims_markdown: str) -> set[int]:
    pattern = re.compile(r"^###\s*权利要求(\d+)", re.MULTILINE)
    return {int(match.group(1)) for match in pattern.finditer(claims_markdown)}


def _build_entries(
    *,
    ablation_small: dict[str, Any],
    ablation_large: dict[str, Any],
    ablation_stress: dict[str, Any],
    core_scaling_realistic: dict[str, Any],
    core_scaling_stress: dict[str, Any],
    semi_real_realistic: dict[str, Any],
    semi_real_stress: dict[str, Any],
    prune: dict[str, Any],
    candidate: dict[str, Any],
    candidate_profile_synthetic: dict[str, Any],
    candidate_profile_realistic: dict[str, Any],
    candidate_profile_stress: dict[str, Any],
    stage2_guardrail: dict[str, Any],
    ann_hybrid: dict[str, Any],
    semantic: dict[str, Any],
) -> list[dict[str, Any]]:
    small_summary = dict(ablation_small.get("summary") or {})
    large_summary = dict(ablation_large.get("summary") or {})
    stress_summary = dict(ablation_stress.get("summary") or {})

    realistic_1000 = _scale_summary_by_count(core_scaling_realistic, 1000)
    stress_1000 = _scale_summary_by_count(core_scaling_stress, 1000)
    stress_500 = _scale_summary_by_count(core_scaling_stress, 500)
    semi_real_realistic_summary = dict(semi_real_realistic.get("summary") or {})
    semi_real_stress_summary = dict(semi_real_stress.get("summary") or {})

    semantic_summary = dict(semantic.get("summary") or {})

    prune_summary = dict(prune.get("summary") or {})
    prune_secondary_sparse = dict((prune.get("secondary_sparse") or {}).get("summary") or {})
    prune_secondary_realistic = dict((prune.get("secondary_realistic") or {}).get("summary") or {})

    candidate_rows = _scenario_by_name(list(candidate.get("scenarios") or []))
    candidate_sparse = dict((candidate_rows.get("sparse_no_merge_case") or {}).get("summary") or {})
    candidate_active = dict((candidate_rows.get("merge_active_case") or {}).get("summary") or {})
    candidate_profile_synthetic_summary = dict(candidate_profile_synthetic.get("summary") or {})
    candidate_profile_realistic_summary = dict(candidate_profile_realistic.get("summary") or {})
    candidate_profile_stress_summary = dict(candidate_profile_stress.get("summary") or {})
    stage2_guardrail_summary = dict(stage2_guardrail.get("summary") or {})
    stage2_guardrail_known = dict(stage2_guardrail.get("known_limitations") or {})

    ann_rows = _scenario_by_name(list(ann_hybrid.get("scenarios") or []))
    ann_sparse_comp = dict((ann_rows.get("sparse_no_merge_case") or {}).get("comparisons_vs_baseline") or {})
    ann_active_comp = dict((ann_rows.get("merge_active_case") or {}).get("comparisons_vs_baseline") or {})
    ann_sparse = dict(ann_sparse_comp.get("ann_prune") or {})
    ann_active = dict(ann_active_comp.get("ann_prune") or {})
    ann_candidate_active = dict(ann_active_comp.get("candidate_prune") or {})
    ann_hybrid_active = dict(ann_active_comp.get("hybrid_prune") or {})

    entries: list[dict[str, Any]] = [
        {
            "feature_id": "DF-01",
            "feature_name": "冲突证据图 CEG",
            "claim_refs": [1, 4, 5],
            "is_core_claim": True,
            "technical_problem": "同槽位多值冲突缺少可量化证据链与优先级排序。",
            "technical_mechanism": "构建冲突值节点、值切换边、证据计数，计算主导值与冲突优先级。",
            "technical_effect": "冲突优先级可计算、可审计、可排序。",
            "key_metrics": {
                "small_conflict_priority_avg_gain": _pick(dict(small_summary.get("ceg") or {}), "conflict_priority_avg_gain"),
                "large_conflict_priority_avg_gain": _pick(dict(large_summary.get("ceg") or {}), "conflict_priority_avg_gain"),
                "scaling_realistic_n1000_gain": _pick(realistic_1000, "ceg_conflict_priority_avg_gain"),
                "scaling_stress_n1000_gain": _pick(stress_1000, "ceg_conflict_priority_avg_gain"),
                "semi_real_realistic_n5000_gain": _pick(semi_real_realistic_summary, "ceg_conflict_priority_avg_gain"),
                "semi_real_stress_n5000_gain": _pick(semi_real_stress_summary, "ceg_conflict_priority_avg_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_large.json",
                "outputs/core_scaling_realistic.json",
                "outputs/core_scaling_stress.json",
                "outputs/core_ablation_semi_real_5000_realistic.json",
                "outputs/core_ablation_semi_real_5000_stress_runs2.json",
                "outputs/core_claim_stability_semi_real_5000_realistic.json",
                "outputs/core_claim_stability_semi_real_5000_stress.json",
                "src/memory_cluster/compress.py",
            ],
            "command_ids": [
                "CMD_ABLATION_SMALL",
                "CMD_ABLATION_LARGE",
                "CMD_CORE_SCALING_REALISTIC",
                "CMD_CORE_SCALING_STRESS",
                "CMD_ABLATION_SEMI_REAL_REALISTIC",
                "CMD_ABLATION_SEMI_REAL_STRESS",
                "CMD_CORE_STABILITY_REALISTIC_5000",
                "CMD_CORE_STABILITY_STRESS_5000_BATCH1",
                "CMD_CORE_STABILITY_STRESS_5000_RESUME",
            ],
            "status": "core_claim_ready",
        },
        {
            "feature_id": "DF-02",
            "feature_name": "自适应保留预算 ARB",
            "claim_refs": [1, 6, 7],
            "is_core_claim": True,
            "technical_problem": "固定预算在冲突密集区域无法保留足够证据。",
            "technical_mechanism": "按冲突密度、来源熵、时效衰减三因子联合分配并限幅预算。",
            "technical_effect": "关键簇预算与信息保真度提升。",
            "key_metrics": {
                "small_detail_budget_avg_gain": _pick(dict(small_summary.get("arb") or {}), "detail_budget_avg_gain"),
                "large_detail_budget_avg_gain": _pick(dict(large_summary.get("arb") or {}), "detail_budget_avg_gain"),
                "scaling_realistic_n1000_gain": _pick(realistic_1000, "arb_detail_budget_avg_gain"),
                "scaling_stress_n1000_gain": _pick(stress_1000, "arb_detail_budget_avg_gain"),
                "semi_real_realistic_n5000_gain": _pick(semi_real_realistic_summary, "arb_detail_budget_avg_gain"),
                "semi_real_stress_n5000_gain": _pick(semi_real_stress_summary, "arb_detail_budget_avg_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_large.json",
                "outputs/core_scaling_realistic.json",
                "outputs/core_scaling_stress.json",
                "outputs/core_ablation_semi_real_5000_realistic.json",
                "outputs/core_ablation_semi_real_5000_stress_runs2.json",
                "outputs/core_claim_stability_semi_real_5000_realistic.json",
                "outputs/core_claim_stability_semi_real_5000_stress.json",
                "src/memory_cluster/preference.py",
            ],
            "command_ids": [
                "CMD_ABLATION_SMALL",
                "CMD_ABLATION_LARGE",
                "CMD_CORE_SCALING_REALISTIC",
                "CMD_CORE_SCALING_STRESS",
                "CMD_ABLATION_SEMI_REAL_REALISTIC",
                "CMD_ABLATION_SEMI_REAL_STRESS",
                "CMD_CORE_STABILITY_REALISTIC_5000",
                "CMD_CORE_STABILITY_STRESS_5000_BATCH1",
                "CMD_CORE_STABILITY_STRESS_5000_RESUME",
            ],
            "status": "core_claim_ready",
        },
        {
            "feature_id": "DF-03",
            "feature_name": "双通道合并门控 DMG",
            "claim_refs": [1, 8, 9],
            "is_core_claim": True,
            "technical_problem": "仅按语义相似度会误合并冲突碎片。",
            "technical_mechanism": "语义相似阈值与冲突兼容阈值联合门控，冲突不兼容直接阻断。",
            "technical_effect": "显著降低冲突混簇，阻断高风险合并。",
            "key_metrics": {
                "small_merge_block_gain": _pick(dict(small_summary.get("dmg") or {}), "merge_block_gain"),
                "stress_merge_block_gain": _pick(dict(stress_summary.get("dmg") or {}), "merge_block_gain"),
                "scaling_stress_n500_block_gain": _pick(stress_500, "dmg_merge_block_gain"),
                "scaling_stress_n1000_block_gain": _pick(stress_1000, "dmg_merge_block_gain"),
                "semi_real_stress_n5000_block_gain": _pick(semi_real_stress_summary, "dmg_merge_block_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_stress.json",
                "outputs/core_scaling_stress.json",
                "outputs/core_ablation_semi_real_5000_stress_runs2.json",
                "outputs/core_claim_stability_semi_real_5000_stress.json",
                "src/memory_cluster/cluster.py",
            ],
            "command_ids": [
                "CMD_ABLATION_SMALL",
                "CMD_ABLATION_STRESS",
                "CMD_CORE_SCALING_STRESS",
                "CMD_ABLATION_SEMI_REAL_STRESS",
                "CMD_CORE_STABILITY_STRESS_5000_BATCH1",
                "CMD_CORE_STABILITY_STRESS_5000_RESUME",
            ],
            "status": "core_claim_ready",
        },
        {
            "feature_id": "DF-04",
            "feature_name": "冲突语义精度抽取",
            "claim_refs": [1, 10, 11],
            "is_core_claim": True,
            "technical_problem": "条件句、否定、反事实与跨句指代引起误报漏报。",
            "technical_mechanism": "作用域隔离 + 否定窗口 + 中英双语回指联合解析。",
            "technical_effect": "语义回归集保持零违规约束。",
            "key_metrics": {
                "case_count": _pick(semantic_summary, "case_count"),
                "case_pass_rate": _pick(semantic_summary, "case_pass_rate"),
                "expected_hit_rate": _pick(semantic_summary, "expected_hit_rate"),
                "forbidden_violations": _pick(semantic_summary, "forbidden_violations"),
            },
            "evidence_files": [
                "outputs/semantic_regression_metrics.json",
                "docs/eval/semantic_regression_report.md",
                "src/memory_cluster/compress.py",
            ],
            "command_ids": ["CMD_SEMANTIC"],
            "status": "core_claim_ready",
        },
        {
            "feature_id": "DF-05",
            "feature_name": "合并上界剪枝 Prune",
            "claim_refs": [12],
            "is_core_claim": False,
            "technical_problem": "簇对全比较带来计算开销膨胀。",
            "technical_mechanism": "利用余弦上界估计，低于阈值时跳过精确相似度计算。",
            "technical_effect": "稀疏场景可提速，active 场景收益不稳定。",
            "key_metrics": {
                "primary_avg_speedup_ratio": _pick(prune_summary, "avg_speedup_ratio"),
                "sparse_avg_speedup_ratio": _pick(prune_secondary_sparse, "avg_speedup_ratio"),
                "sparse_optimized_pairs_pruned": _pick(prune_secondary_sparse, "optimized_pairs_pruned"),
                "realistic_avg_speedup_ratio": _pick(prune_secondary_realistic, "avg_speedup_ratio"),
            },
            "evidence_files": [
                "outputs/prune_benchmark.json",
                "docs/eval/prune_benchmark_report.md",
                "src/memory_cluster/cluster.py",
            ],
            "command_ids": ["CMD_PRUNE"],
            "status": "optional_impl_only",
            "risk_note": "不作为核心授权叙事，仅建议作为可选实施例。",
        },
        {
            "feature_id": "DF-06",
            "feature_name": "候选筛选/ANN 加速路径",
            "claim_refs": [13, 14],
            "is_core_claim": False,
            "technical_problem": "进一步减少候选簇对比较数量。",
            "technical_mechanism": "候选签名桶与 ANN 多表近似候选联合门控。",
            "technical_effect": "默认 Candidate 档位已验证零损失；active 场景总体仍偏负加速，实验档 candidate/ANN 仍需风险披露。",
            "key_metrics": {
                "candidate_sparse_avg_speedup_ratio": _pick(candidate_sparse, "avg_speedup_ratio"),
                "candidate_active_avg_speedup_ratio": _pick(candidate_active, "avg_speedup_ratio"),
                "candidate_active_quality_gate_pass": bool(_pick(candidate_active, "cluster_count_equal"))
                and bool(_pick(candidate_active, "merges_applied_equal")),
                "candidate_active_merges_applied_equal": _pick(candidate_active, "merges_applied_equal"),
                "ann_sparse_avg_speedup_ratio": _pick(ann_sparse, "avg_speedup_ratio"),
                "ann_active_avg_speedup_ratio": _pick(ann_active, "avg_speedup_ratio"),
                "ann_active_quality_gate_pass": _pick(ann_active, "quality_gate_pass"),
                "ann_candidate_active_quality_gate_pass": _pick(ann_candidate_active, "quality_gate_pass"),
                "hybrid_active_avg_speedup_ratio": _pick(ann_hybrid_active, "avg_speedup_ratio"),
                "hybrid_active_quality_gate_pass": _pick(ann_hybrid_active, "quality_gate_pass"),
                "profile_synth_default_all_quality_gate_pass": _pick(
                    candidate_profile_synthetic_summary, "default_all_quality_gate_pass"
                ),
                "profile_synth_fast_all_quality_gate_pass": _pick(
                    candidate_profile_synthetic_summary, "fast_all_quality_gate_pass"
                ),
                "profile_synth_fast_min_speedup_ratio": _pick(
                    candidate_profile_synthetic_summary, "fast_min_speedup_ratio"
                ),
                "profile_realistic_fast_min_speedup_ratio": _pick(
                    candidate_profile_realistic_summary, "fast_min_speedup_ratio"
                ),
                "profile_stress_fast_min_speedup_ratio": _pick(
                    candidate_profile_stress_summary, "fast_min_speedup_ratio"
                ),
                "profile_synth_recommendation": _pick(candidate_profile_synthetic_summary, "recommendation"),
                "profile_realistic_recommendation": _pick(candidate_profile_realistic_summary, "recommendation"),
                "profile_stress_recommendation": _pick(candidate_profile_stress_summary, "recommendation"),
                "stage2_guardrail_passed": _pick(stage2_guardrail_summary, "passed"),
                "stage2_guardrail_blocker_failures": _pick(stage2_guardrail_summary, "blocker_failures"),
                "stage2_guardrail_warning_failures": _pick(stage2_guardrail_summary, "warning_failures"),
                "stage2_guardrail_fast_profile_loss_known": _pick(
                    stage2_guardrail_known, "fast_profile_loss_at_synthetic_n240"
                ),
                "stage2_guardrail_ann_active_not_positive_speedup": _pick(
                    stage2_guardrail_known, "ann_active_not_positive_speedup"
                ),
                "stage2_guardrail_candidate_active_speed": _pick(stage2_guardrail_known, "candidate_active_speed"),
                "stage2_guardrail_ann_active_speed": _pick(stage2_guardrail_known, "ann_active_speed"),
            },
            "evidence_files": [
                "outputs/candidate_filter_benchmark.json",
                "outputs/candidate_profile_validation_synthetic_active.json",
                "outputs/candidate_profile_validation_realistic.json",
                "outputs/candidate_profile_validation_stress.json",
                "outputs/stage2_guardrail.json",
                "outputs/ann_hybrid_benchmark.json",
                "outputs/stage3_param_sweep.json",
                "docs/eval/candidate_filter_benchmark_report.md",
                "docs/eval/candidate_profile_validation_summary.md",
                "docs/eval/stage2_guardrail_report.md",
                "docs/eval/ann_hybrid_benchmark_report.md",
                "docs/eval/stage3_param_sweep_report.md",
                "src/memory_cluster/cluster.py",
            ],
            "command_ids": [
                "CMD_CANDIDATE",
                "CMD_CANDIDATE_PROFILE_SYNTH",
                "CMD_CANDIDATE_PROFILE_REALISTIC",
                "CMD_CANDIDATE_PROFILE_STRESS",
                "CMD_STAGE2_GUARDRAIL",
                "CMD_ANN_HYBRID",
                "CMD_STAGE3_SWEEP",
            ],
            "status": "optional_experimental",
            "risk_note": "建议保留代码实现，但不作为核心独立主张。",
        },
    ]
    return entries


def _collect_validation(
    *,
    entries: list[dict[str, Any]],
    claims_file: Path,
) -> dict[str, Any]:
    claim_text = claims_file.read_text(encoding="utf-8")
    claim_numbers = _extract_claim_numbers(claim_text)

    referenced_claims = sorted({int(item) for row in entries for item in row.get("claim_refs") or []})
    missing_claim_refs = [f"权利要求{num}" for num in referenced_claims if num not in claim_numbers]

    missing_evidence_files: list[str] = []
    missing_metrics: list[str] = []
    for row in entries:
        fid = str(row.get("feature_id") or "")
        for file_path in row.get("evidence_files") or []:
            if not Path(file_path).exists():
                missing_evidence_files.append(f"{fid}:{file_path}")
        for metric_key, metric_value in (row.get("key_metrics") or {}).items():
            if metric_value is None:
                missing_metrics.append(f"{fid}:{metric_key}")

    return {
        "claim_numbers_in_06": sorted(claim_numbers),
        "referenced_claim_numbers": referenced_claims,
        "missing_claim_refs": missing_claim_refs,
        "missing_evidence_files": missing_evidence_files,
        "missing_metrics": missing_metrics,
        "passed": not (missing_claim_refs or missing_evidence_files or missing_metrics),
    }


def _write_mapping_markdown(path: Path, payload: dict[str, Any]) -> None:
    entries = payload.get("entries") or []
    core = [row for row in entries if bool(row.get("is_core_claim"))]
    optional = [row for row in entries if not bool(row.get("is_core_claim"))]

    lines: list[str] = [
        "# 10 区别特征-技术效果-实验数据映射",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- data_snapshot_at: {payload.get('data_snapshot_at')}",
        f"- evidence_items: {len(entries)}",
        f"- validation_passed: {payload.get('validation', {}).get('passed')}",
        "",
        "## 1. 总览",
        "",
        "| 特征ID | 区别特征 | 权利要求 | 核心主张 | 状态 |",
        "|---|---|---|---|---|",
    ]

    for row in entries:
        lines.append(
            f"| {row.get('feature_id')} | {row.get('feature_name')} | {_claim_refs_to_text(list(row.get('claim_refs') or []))} | "
            + ("是" if bool(row.get("is_core_claim")) else "否")
            + f" | {row.get('status')} |"
        )

    def _append_entry(row: dict[str, Any], is_core: bool) -> None:
        lines.extend(
            [
                f"### {row.get('feature_id')} {row.get('feature_name')}",
                f"- 权利要求映射: {_claim_refs_to_text(list(row.get('claim_refs') or []))}",
                f"- 技术问题: {row.get('technical_problem')}",
                f"- 技术手段: {row.get('technical_mechanism')}",
                f"- {'技术效果' if is_core else '当前结论'}: {row.get('technical_effect')}",
                "- 指标证据:",
            ]
        )
        for key, value in (row.get("key_metrics") or {}).items():
            lines.append(f"  - {key}: {_fmt_metric(value)}")
        lines.append("- 证据文件:")
        for file_path in row.get("evidence_files") or []:
            lines.append(f"  - `{file_path}`")
        lines.append("- 可复现命令ID:")
        for command_id in row.get("command_ids") or []:
            lines.append(f"  - `{command_id}`")
        if row.get("risk_note"):
            lines.append(f"- 风险说明: {row.get('risk_note')}")
        lines.append("")

    lines.extend(["", "## 2. 核心主张（建议重点保护）", ""])
    for row in core:
        _append_entry(row, is_core=True)

    lines.extend(["## 3. 可选实施例（不建议作为核心独立主张）", ""])
    for row in optional:
        _append_entry(row, is_core=False)

    lines.extend(["## 4. 命令索引", ""])
    for command_id, command in COMMAND_CATALOG.items():
        lines.append(f"- `{command_id}`: `{command}`")

    validation = payload.get("validation") or {}
    lines.extend(["", "## 5. 一致性校验", ""])
    lines.append(f"- claim_numbers_in_06: {validation.get('claim_numbers_in_06')}")
    lines.append(f"- referenced_claim_numbers: {validation.get('referenced_claim_numbers')}")
    lines.append(f"- missing_claim_refs: {validation.get('missing_claim_refs')}")
    lines.append(f"- missing_evidence_files: {validation.get('missing_evidence_files')}")
    lines.append(f"- missing_metrics: {validation.get('missing_metrics')}")
    lines.append(f"- passed: {validation.get('passed')}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_claim_index_markdown(path: Path, payload: dict[str, Any]) -> None:
    entries = payload.get("entries") or []
    claim_to_features: dict[int, list[dict[str, Any]]] = {}
    for row in entries:
        for claim_num in row.get("claim_refs") or []:
            key = int(claim_num)
            claim_to_features.setdefault(key, []).append(row)

    lines: list[str] = [
        "# 11 主张-证据ID-命令对照",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        "",
        "## 1. 一页总表",
        "",
        "| 权利要求 | 证据ID | 主张类型 | 关键指标摘要 | 关键证据文件 | 命令ID |",
        "|---|---|---|---|---|---|",
    ]

    for claim_num in sorted(claim_to_features.keys()):
        rows = claim_to_features.get(claim_num) or []
        for row in rows:
            metrics = row.get("key_metrics") or {}
            metric_items = list(metrics.items())[:3]
            metric_text = "; ".join(f"{k}={_fmt_metric(v)}" for k, v in metric_items)
            evidence = (row.get("evidence_files") or ["-"])[0]
            command_ids = ",".join(row.get("command_ids") or [])
            claim_text = f"权利要求{claim_num}"
            kind = "核心" if bool(row.get("is_core_claim")) else "可选"
            lines.append(
                f"| {claim_text} | {row.get('feature_id')} | {kind} | {metric_text} | `{evidence}` | `{command_ids}` |"
            )

    lines.extend(["", "## 2. 评审快速答复模板", ""])
    lines.append("- 证据定位：先按权利要求号找到对应 DF，再看该 DF 的 `key_metrics` 与 `evidence_files`。")
    lines.append("- 复现方式：按命令ID到 `10_区别特征_技术效果_实验映射.md` 的命令索引执行。")
    lines.append("- 风险披露：DF-05/DF-06 属于可选实施例，不作为核心独立主张。")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _data_snapshot(loaded: dict[str, dict[str, Any]]) -> str:
    stamps: list[str] = []
    for payload in loaded.values():
        value = str(payload.get("generated_at") or "")
        if value:
            stamps.append(value)
    if not stamps:
        return ""
    return max(stamps)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build patent evidence pack from benchmark outputs")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--report", required=True, help="Output markdown report path")
    parser.add_argument(
        "--index-report",
        default="docs/patent_kit/11_主张_证据_命令对照.md",
        help="Output claim-evidence-command index markdown path",
    )
    parser.add_argument(
        "--claims-file",
        default="docs/patent_kit/06_权利要求书_草案.md",
        help="Claims markdown file for alignment checks",
    )
    args = parser.parse_args()

    input_files = {
        "ablation_small": Path("outputs/ablation_metrics.json"),
        "ablation_large": Path("outputs/ablation_metrics_large.json"),
        "ablation_stress": Path("outputs/ablation_metrics_stress.json"),
        "core_scaling_realistic": Path("outputs/core_scaling_realistic.json"),
        "core_scaling_stress": Path("outputs/core_scaling_stress.json"),
        "semi_real_realistic": Path("outputs/core_ablation_semi_real_5000_realistic.json"),
        "semi_real_stress": Path("outputs/core_ablation_semi_real_5000_stress_runs2.json"),
        "prune": Path("outputs/prune_benchmark.json"),
        "candidate": Path("outputs/candidate_filter_benchmark.json"),
        "candidate_profile_synthetic": Path("outputs/candidate_profile_validation_synthetic_active.json"),
        "candidate_profile_realistic": Path("outputs/candidate_profile_validation_realistic.json"),
        "candidate_profile_stress": Path("outputs/candidate_profile_validation_stress.json"),
        "stage2_guardrail": Path("outputs/stage2_guardrail.json"),
        "ann_hybrid": Path("outputs/ann_hybrid_benchmark.json"),
        "semantic": Path("outputs/semantic_regression_metrics.json"),
    }

    loaded: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for key, path in input_files.items():
        payload, error = _load_json(path)
        if error:
            errors.append(error)
            continue
        loaded[key] = payload or {}

    claims_file = Path(args.claims_file)
    if not claims_file.exists():
        errors.append(f"missing: {claims_file.as_posix()}")

    if errors:
        raise SystemExit(";\n".join(errors))

    entries = _build_entries(
        ablation_small=loaded["ablation_small"],
        ablation_large=loaded["ablation_large"],
        ablation_stress=loaded["ablation_stress"],
        core_scaling_realistic=loaded["core_scaling_realistic"],
        core_scaling_stress=loaded["core_scaling_stress"],
        semi_real_realistic=loaded["semi_real_realistic"],
        semi_real_stress=loaded["semi_real_stress"],
        prune=loaded["prune"],
        candidate=loaded["candidate"],
        candidate_profile_synthetic=loaded["candidate_profile_synthetic"],
        candidate_profile_realistic=loaded["candidate_profile_realistic"],
        candidate_profile_stress=loaded["candidate_profile_stress"],
        stage2_guardrail=loaded["stage2_guardrail"],
        ann_hybrid=loaded["ann_hybrid"],
        semantic=loaded["semantic"],
    )

    validation = _collect_validation(entries=entries, claims_file=claims_file)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_snapshot_at": _data_snapshot(loaded),
        "entries": entries,
        "command_catalog": COMMAND_CATALOG,
        "validation": validation,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_mapping_markdown(Path(args.report), payload)
    _write_claim_index_markdown(Path(args.index_report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
