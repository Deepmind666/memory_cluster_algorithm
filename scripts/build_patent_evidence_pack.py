from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing: {path.as_posix()}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # defensive parse guard
        return None, f"invalid-json: {path.as_posix()} ({exc})"
    if not isinstance(payload, dict):
        return None, f"invalid-root: {path.as_posix()} (expect object)"
    return payload, None


def _scenario_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if not name:
            continue
        output[name] = row
    return output


def _fmt_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _build_entries(
    *,
    ablation_small: dict[str, Any],
    ablation_large: dict[str, Any],
    ablation_stress: dict[str, Any],
    prune: dict[str, Any],
    candidate: dict[str, Any],
    ann: dict[str, Any],
    semantic: dict[str, Any],
) -> list[dict[str, Any]]:
    small_summary = ablation_small.get("summary") or {}
    large_summary = ablation_large.get("summary") or {}
    stress_summary = ablation_stress.get("summary") or {}
    prune_summary = prune.get("summary") or {}
    prune_sparse_summary = ((prune.get("secondary_sparse") or {}).get("summary") or {})
    prune_realistic_summary = ((prune.get("secondary_realistic") or {}).get("summary") or {})
    candidate_scenarios = _scenario_map(candidate.get("scenarios") or [])
    ann_scenarios = _scenario_map(ann.get("scenarios") or [])
    semantic_summary = semantic.get("summary") or {}

    candidate_sparse = (candidate_scenarios.get("sparse_no_merge_case") or {}).get("summary") or {}
    candidate_active = (candidate_scenarios.get("merge_active_case") or {}).get("summary") or {}
    candidate_active_equal = bool(candidate_active.get("cluster_count_equal")) and bool(
        candidate_active.get("merges_applied_equal")
    )

    ann_sparse = ((ann_scenarios.get("sparse_no_merge_case") or {}).get("comparisons_vs_baseline") or {}).get(
        "ann_prune"
    ) or {}
    ann_active = ((ann_scenarios.get("merge_active_case") or {}).get("comparisons_vs_baseline") or {}).get(
        "ann_prune"
    ) or {}
    hybrid_active = ((ann_scenarios.get("merge_active_case") or {}).get("comparisons_vs_baseline") or {}).get(
        "hybrid_prune"
    ) or {}

    entries: list[dict[str, Any]] = [
        {
            "feature_id": "DF-01",
            "feature_name": "冲突证据图 CEG",
            "claim_refs": ["权利要求14"],
            "technical_problem": "同槽位冲突值无法形成可计算证据链",
            "technical_mechanism": "冲突节点 + 切换边 + 主导值 + 优先级",
            "technical_effect": "冲突优先级可量化并可排序",
            "key_metrics": {
                "small_top1_conflict_priority_gain": (small_summary.get("ceg") or {}).get("top1_conflict_priority_gain"),
                "small_conflict_priority_avg_gain": (small_summary.get("ceg") or {}).get("conflict_priority_avg_gain"),
                "large_top1_conflict_priority_gain": (large_summary.get("ceg") or {}).get("top1_conflict_priority_gain"),
                "large_conflict_priority_avg_gain": (large_summary.get("ceg") or {}).get("conflict_priority_avg_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_large.json",
                "docs/eval/ablation_report_cn.md",
                "src/memory_cluster/compress.py",
            ],
            "status": "implemented_and_measured",
        },
        {
            "feature_id": "DF-02",
            "feature_name": "自适应预算 ARB",
            "claim_refs": ["权利要求15"],
            "technical_problem": "固定摘要预算在冲突高密度场景下证据保真不足",
            "technical_mechanism": "冲突密度 + 来源熵 + 时效衰减联合分配预算",
            "technical_effect": "关键簇预算与摘要信息量提升",
            "key_metrics": {
                "small_detail_budget_avg_gain": (small_summary.get("arb") or {}).get("detail_budget_avg_gain"),
                "small_avg_summary_chars_gain": (small_summary.get("arb") or {}).get("avg_summary_chars_gain"),
                "large_detail_budget_avg_gain": (large_summary.get("arb") or {}).get("detail_budget_avg_gain"),
                "large_avg_summary_chars_gain": (large_summary.get("arb") or {}).get("avg_summary_chars_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_large.json",
                "docs/eval/ablation_report_large_cn.md",
                "src/memory_cluster/preference.py",
            ],
            "status": "implemented_and_measured",
        },
        {
            "feature_id": "DF-03",
            "feature_name": "双通道合并门控 DMG",
            "claim_refs": ["权利要求16"],
            "technical_problem": "仅凭语义相似度会误合并冲突簇",
            "technical_mechanism": "语义阈值 + 冲突兼容阈值双通道联合门控",
            "technical_effect": "混合冲突簇减少，误合并可阻断",
            "key_metrics": {
                "small_mixed_mode_clusters_reduction": (small_summary.get("dmg") or {}).get("mixed_mode_clusters_reduction"),
                "small_merge_block_gain": (small_summary.get("dmg") or {}).get("merge_block_gain"),
                "stress_mixed_mode_clusters_reduction": (stress_summary.get("dmg") or {}).get(
                    "mixed_mode_clusters_reduction"
                ),
                "stress_merge_block_gain": (stress_summary.get("dmg") or {}).get("merge_block_gain"),
            },
            "evidence_files": [
                "outputs/ablation_metrics.json",
                "outputs/ablation_metrics_stress.json",
                "docs/eval/ablation_report_stress_cn.md",
                "src/memory_cluster/cluster.py",
            ],
            "status": "implemented_and_measured",
        },
        {
            "feature_id": "DF-04",
            "feature_name": "合并上界剪枝 Prune",
            "claim_refs": ["权利要求17"],
            "technical_problem": "簇合并 pair 全比较导致计算冗余",
            "technical_mechanism": "余弦上界估计，低于阈值直接剪枝",
            "technical_effect": "减少完整相似度计算并在稀疏场景提升速度",
            "key_metrics": {
                "primary_avg_speedup_ratio": prune_summary.get("avg_speedup_ratio"),
                "primary_optimized_pairs_pruned": prune_summary.get("optimized_pairs_pruned"),
                "sparse_avg_speedup_ratio": prune_sparse_summary.get("avg_speedup_ratio"),
                "sparse_optimized_pairs_pruned": prune_sparse_summary.get("optimized_pairs_pruned"),
                "realistic_avg_speedup_ratio": prune_realistic_summary.get("avg_speedup_ratio"),
                "cluster_count_equal_primary": prune_summary.get("cluster_count_equal"),
            },
            "evidence_files": [
                "outputs/prune_benchmark.json",
                "docs/eval/prune_benchmark_report.md",
                "src/memory_cluster/cluster.py",
            ],
            "status": "implemented_and_measured",
        },
        {
            "feature_id": "DF-05",
            "feature_name": "签名桶候选筛选 Candidate Filter",
            "claim_refs": ["权利要求18"],
            "technical_problem": "大规模候选对数量过大",
            "technical_mechanism": "按签名桶和邻桶限制候选邻接图",
            "technical_effect": (
                "显著减少 merge attempts，并在当前 active 基准保持结果一致"
                if candidate_active_equal
                else "显著减少 merge attempts；稀疏场景结果一致，active 场景存在可量化质量漂移"
            ),
            "key_metrics": {
                "sparse_attempt_reduction_ratio": candidate_sparse.get("attempt_reduction_ratio"),
                "sparse_avg_speedup_ratio": candidate_sparse.get("avg_speedup_ratio"),
                "active_attempt_reduction_ratio": candidate_active.get("attempt_reduction_ratio"),
                "active_avg_speedup_ratio": candidate_active.get("avg_speedup_ratio"),
                "active_cluster_count_equal": candidate_active.get("cluster_count_equal"),
                "active_merges_applied_equal": candidate_active.get("merges_applied_equal"),
            },
            "evidence_files": [
                "outputs/candidate_filter_benchmark.json",
                "docs/eval/candidate_filter_benchmark_report.md",
                "src/memory_cluster/cluster.py",
            ],
            "status": "implemented_and_measured",
        },
        {
            "feature_id": "DF-06",
            "feature_name": "ANN 多表近似候选与混合门控",
            "claim_refs": ["权利要求19"],
            "technical_problem": "进一步降低候选枚举复杂度常数",
            "technical_mechanism": "多表签名 + 邻域探针 + candidate/ann/hybrid 门控",
            "technical_effect": "在稀疏场景有加速，但 active 场景当前实现存在负加速",
            "key_metrics": {
                "sparse_ann_avg_speedup_ratio": ann_sparse.get("avg_speedup_ratio"),
                "sparse_ann_quality_gate_pass": ann_sparse.get("quality_gate_pass"),
                "active_ann_avg_speedup_ratio": ann_active.get("avg_speedup_ratio"),
                "active_ann_quality_gate_pass": ann_active.get("quality_gate_pass"),
                "active_hybrid_avg_speedup_ratio": hybrid_active.get("avg_speedup_ratio"),
                "active_hybrid_quality_gate_pass": hybrid_active.get("quality_gate_pass"),
            },
            "evidence_files": [
                "outputs/ann_hybrid_benchmark.json",
                "docs/eval/ann_hybrid_benchmark_report.md",
                "src/memory_cluster/cluster.py",
            ],
            "status": "implemented_measured_not_default",
        },
        {
            "feature_id": "DF-07",
            "feature_name": "冲突语义精度回归集",
            "claim_refs": ["权利要求20"],
            "technical_problem": "条件/否定/跨句指代造成冲突语义误提取",
            "technical_mechanism": "条件后件截断 + 双重否定窗口 + 槽位回指解析",
            "technical_effect": "语义抽取回归集零误报违规",
            "key_metrics": {
                "case_count": semantic_summary.get("case_count"),
                "case_pass_rate": semantic_summary.get("case_pass_rate"),
                "expected_hit_rate": semantic_summary.get("expected_hit_rate"),
                "forbidden_violations": semantic_summary.get("forbidden_violations"),
            },
            "evidence_files": [
                "outputs/semantic_regression_metrics.json",
                "docs/eval/semantic_regression_report.md",
                "src/memory_cluster/compress.py",
            ],
            "status": "implemented_and_measured",
        },
    ]
    return entries


def _write_markdown(
    *,
    path: Path,
    payload: dict[str, Any],
) -> None:
    lines = [
        "# 10 区别特征-技术效果-实验数据映射",
        "",
        f"- 生成时间: {payload.get('generated_at')}",
        f"- 数据集快照时间: {payload.get('data_snapshot_at')}",
        f"- 证据条目数: {len(payload.get('entries') or [])}",
        "",
        "## 一、总览",
        "",
        "| 特征ID | 区别特征 | 权利要求 | 关键效果指标 | 状态 |",
        "|---|---|---|---|---|",
    ]
    for row in payload.get("entries") or []:
        metric_preview = []
        for key, value in (row.get("key_metrics") or {}).items():
            metric_preview.append(f"{key}={_fmt_metric(value)}")
            if len(metric_preview) >= 2:
                break
        lines.append(
            f"| {row.get('feature_id')} | {row.get('feature_name')} | "
            f"{'/'.join(row.get('claim_refs') or [])} | "
            f"{'; '.join(metric_preview)} | {row.get('status')} |"
        )

    lines.extend(
        [
            "",
            "## 二、逐项映射",
            "",
        ]
    )
    for row in payload.get("entries") or []:
        lines.extend(
            [
                f"### {row.get('feature_id')} {row.get('feature_name')}",
                f"- 权利要求映射: {', '.join(row.get('claim_refs') or [])}",
                f"- 技术问题: {row.get('technical_problem')}",
                f"- 技术手段: {row.get('technical_mechanism')}",
                f"- 技术效果: {row.get('technical_effect')}",
                "- 指标证据:",
            ]
        )
        for key, value in (row.get("key_metrics") or {}).items():
            lines.append(f"  - {key}: {_fmt_metric(value)}")
        lines.append("- 证据文件:")
        for item in row.get("evidence_files") or []:
            lines.append(f"  - `{item}`")
        lines.append("")

    lines.extend(
        [
            "## 三、复现实验命令",
            "",
            "```powershell",
            "python scripts/run_ablation.py --output outputs/ablation_metrics.json --report docs/eval/ablation_report_cn.md",
            "python scripts/run_ablation.py --output outputs/ablation_metrics_large.json --report docs/eval/ablation_report_large_cn.md --fragment-count 100 --similarity-threshold 0.68 --merge-threshold 0.82 --dataset-label synthetic_conflict_memory_case_large",
            "python scripts/run_ablation.py --output outputs/ablation_metrics_stress.json --report docs/eval/ablation_report_stress_cn.md --fragment-count 100 --similarity-threshold 1.1 --merge-threshold 0.05 --dataset-label synthetic_conflict_memory_case_stress",
            "python scripts/run_prune_benchmark.py --output outputs/prune_benchmark.json --report docs/eval/prune_benchmark_report.md",
            "python scripts/run_candidate_filter_benchmark.py --output outputs/candidate_filter_benchmark.json --report docs/eval/candidate_filter_benchmark_report.md",
            "python scripts/run_ann_hybrid_benchmark.py --output outputs/ann_hybrid_benchmark.json --report docs/eval/ann_hybrid_benchmark_report.md",
            "python scripts/run_semantic_regression.py --output outputs/semantic_regression_metrics.json --report docs/eval/semantic_regression_report.md",
            "python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report docs/patent_kit/10_区别特征_技术效果_实验映射.md",
            "```",
            "",
            "## 四、工程决策快照",
            "",
            "- 当前默认推荐路径: `prune_only (exact merge)`。",
            "- Candidate Filter 状态: `implemented_and_measured`（稀疏场景收益明显，active 场景需按质量门槛调参）。",
            "- ANN 方案状态: `implemented_measured_not_default`（active 场景仍有负加速，后续继续调优）。",
            "- 说明: 本文档为技术证据索引，不构成法律意见。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build patent evidence pack from experiment outputs")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--report", required=True, help="Output markdown path")
    args = parser.parse_args()

    input_files = {
        "ablation_small": Path("outputs/ablation_metrics.json"),
        "ablation_large": Path("outputs/ablation_metrics_large.json"),
        "ablation_stress": Path("outputs/ablation_metrics_stress.json"),
        "prune": Path("outputs/prune_benchmark.json"),
        "candidate": Path("outputs/candidate_filter_benchmark.json"),
        "ann": Path("outputs/ann_hybrid_benchmark.json"),
        "semantic": Path("outputs/semantic_regression_metrics.json"),
    }

    loaded: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for key, path in input_files.items():
        payload, err = _load_json(path)
        if err:
            errors.append(err)
            continue
        loaded[key] = payload or {}

    if errors:
        raise SystemExit(";\n".join(errors))

    entries = _build_entries(
        ablation_small=loaded["ablation_small"],
        ablation_large=loaded["ablation_large"],
        ablation_stress=loaded["ablation_stress"],
        prune=loaded["prune"],
        candidate=loaded["candidate"],
        ann=loaded["ann"],
        semantic=loaded["semantic"],
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_snapshot_at": max(
            str(loaded[key].get("generated_at") or "") for key in ["ablation_small", "prune", "candidate", "ann", "semantic"]
        ),
        "entries": entries,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_markdown(path=Path(args.report), payload=payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
