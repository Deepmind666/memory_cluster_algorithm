# FINAL REPORT

最后更新：2026-02-10

## 1. 当前完成状态
- [x] 多 Agent 记忆碎片采集与 JSONL 持久化
- [x] 本地零依赖语义向量化（HashEmbeddingProvider）
- [x] 增量聚类与簇合并
- [x] 簇内去重、冲突显式标记、严格冲突分裂
- [x] 偏好策略（类别/来源/时效/预算）
- [x] L2 层次主题簇（可开关）
- [x] 检索分页与排序增强（level filter + offset）
- [x] CEG（冲突证据图）
- [x] ARB（自适应保留预算）
- [x] DMG（双通道合并门控）
- [x] Merge Upper-Bound Prune（安全上界剪枝）
- [x] Merge Candidate Filter（候选筛选降耗，默认关闭）
- [x] ANN Hybrid Candidates（多表近似候选，默认关闭）
- [x] 消融实验脚本与报告（baseline/ceg/arb/dmg/full）
- [x] 存储可靠性增强（ingest 幂等 + JSONL 容错加载）
- [x] 冲突语义增强（否定/条件/反事实 slot 抽取）
- [x] 语义精度回归（条件后件隔离 + 双重否定窗口 + 跨句指代回指）

## 2. 核心命令
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state_full.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85 --strict-conflict-split --enable-conflict-graph --enable-adaptive-budget --enable-dual-merge-guard --enable-merge-upper-bound-prune --merge-prune-dims 48 --enable-merge-candidate-filter --merge-candidate-bucket-dims 10 --merge-candidate-max-neighbors 16 --enable-l2-clusters --l2-min-children 2
python -m src.memory_cluster.cli query --state outputs/cluster_state_full.json --query "冲突 alpha" --top-k 3 --cluster-level all --expand
python scripts/run_benchmark.py --input data/examples/multi_agent_memory_fragments.jsonl --preferences data/examples/preference_profile.json --output outputs/benchmark_latest.json --runs 5
python scripts/run_ablation.py --output outputs/ablation_metrics.json --report docs/eval/ablation_report_cn.md
python scripts/run_ablation.py --output outputs/ablation_metrics_large.json --report docs/eval/ablation_report_large_cn.md --fragment-count 100 --similarity-threshold 0.68 --merge-threshold 0.82 --dataset-label synthetic_conflict_memory_case_large
python scripts/run_ablation.py --output outputs/ablation_metrics_stress.json --report docs/eval/ablation_report_stress_cn.md --fragment-count 100 --similarity-threshold 1.1 --merge-threshold 0.05 --dataset-label synthetic_conflict_memory_case_stress
python scripts/run_prune_benchmark.py --output outputs/prune_benchmark.json --report docs/eval/prune_benchmark_report.md
python scripts/run_candidate_filter_benchmark.py --output outputs/candidate_filter_benchmark.json --report docs/eval/candidate_filter_benchmark_report.md
python scripts/run_ann_hybrid_benchmark.py --output outputs/ann_hybrid_benchmark.json --report docs/eval/ann_hybrid_benchmark_report.md
python scripts/run_semantic_regression.py --output outputs/semantic_regression_metrics.json --report docs/eval/semantic_regression_report.md
python -m unittest discover -s tests -p "test_*.py" -v
```

## 3. 最新实测结果
### 3.1 单元测试
- 命令：`python -m unittest discover -s tests -p "test_*.py" -v`
- 结果：47/47 通过

### 3.2 Benchmark（默认偏好配置，runs=5）
- `avg_ms`: 2.503
- `p95_ms`: 2.719
- `fragment_count`: 12
- `cluster_count`: 10
- `compression_ratio`: 1.299694
- `merge_attempts`: 45
- `merge_pairs_pruned_by_bound`: 0（默认关闭）

### 3.3 消融实验（synthetic_conflict_memory_case）
来源：`outputs/ablation_metrics.json`

- CEG 对 baseline：
  - `top1_conflict_priority_gain = +8.8`
  - `conflict_priority_avg_gain = +8.8`

- ARB 对 baseline：
  - `detail_budget_avg_gain = +68.0`
  - `avg_summary_chars_gain = +209.0`

- DMG 对 baseline：
  - `mixed_mode_clusters_reduction = 1`
  - `merge_block_gain = +4`
  - `cluster_count_delta = +2`

- FULL 对 baseline：
  - `mixed_mode_clusters_reduction_vs_baseline = 1`
  - `detail_budget_avg_gain_vs_baseline = +29.333`
  - `merge_block_gain_vs_baseline = +4`

### 3.4 Merge Upper-Bound Prune 对照实验（synthetic_merge_prune_case）
来源：`outputs/prune_benchmark.json`

- Primary（merge_active_case）设定：`fragment_count=100`, `similarity_threshold=0.82`, `merge_threshold=0.85`
- Primary 结果：
  - baseline（prune off）`avg_ms=19.84`
  - optimized（prune on）`avg_ms=22.565`
  - `avg_speedup_ratio=-13.7349%`（该场景 `merge_pairs_pruned_by_bound=0`，存在剪枝开销）
  - `cluster_count_equal=true`
  - `merge_activity_present=true`（非空洞对比）

- Secondary（realistic_068_082_case）设定：`similarity_threshold=0.68`, `merge_threshold=0.82`
  - `avg_speedup_ratio=7.3310%`
  - `merge_activity_present=false`（该场景不进入 merge 阶段）

- Secondary（sparse_no_merge_case）设定：`similarity_threshold=2.0`, `merge_threshold=0.95`
  - `avg_speedup_ratio=13.7943%`
  - `merge_pairs_pruned_by_bound=2519`
  - `cluster_count_equal=true`

### 3.5 第二阶段大样本消融（100 fragments）
来源：`outputs/ablation_metrics_large.json`, `outputs/ablation_metrics_stress.json`

- realistic 配置（`0.68/0.82`）：
  - baseline `cluster_count=10`, `mixed_mode_clusters=2`, `conflict_count=4`
  - CEG 增益：`top1_conflict_priority_gain=+5.8`, `conflict_priority_avg_gain=+2.29`
  - ARB 增益：`detail_budget_avg_gain=+38.2`, `avg_summary_chars_gain=+64.4`
  - DMG：`merge_block_gain=0`（该参数区间未触发门控）

- stress 配置（`1.1/0.05`）：
  - baseline `cluster_count=1`, `mixed_mode_clusters=1`
  - DMG 增益：`mixed_mode_clusters_reduction=1`, `merge_block_gain=+120`, `cluster_count_delta=+3`
  - full 相对 baseline：`detail_budget_avg_gain_vs_baseline=+21.25`

### 3.6 Merge Candidate Filter 对照实验（synthetic_candidate_filter_case）
来源：`outputs/candidate_filter_benchmark.json`

- 参数：`bucket_dims=10`, `max_neighbors=16`（可开关，默认关闭）

- sparse_no_merge_case（`2.0/0.95`）：
  - `avg_speedup_ratio=42.6363%`
  - `attempt_reduction_ratio=75.0140%`
  - `cluster_count_equal=true`

- merge_active_case（`0.82/0.85`）：
  - `avg_speedup_ratio=19.8265%`
  - `attempt_reduction_ratio=44.4496%`
  - `cluster_count_equal=true`
  - `merges_applied` 与 baseline 一致（21）

### 3.7 语义精度回归（semantic_precision_regression_v1）
来源：`outputs/semantic_regression_metrics.json`

- 覆盖样例：8 条（条件边界、英文否定、双重否定 flag、英文/中文跨句指代、条件作用域指代、反事实否定、条件 flag 隔离）
- `case_pass_rate=1.0`（8/8）
- `expected_hit_rate=1.0`（17/17 目标对命中）
- `forbidden_violations=0`（6/6 误报约束零触发）

### 3.8 ANN Hybrid 对照实验（synthetic_ann_hybrid_case）
来源：`outputs/ann_hybrid_benchmark.json`

- 参数：`prune_dims=48`, `bucket_dims=10`, `candidate_max_neighbors=24`, `ann_num_tables=6`, `ann_bits_per_table=10`, `ann_probe_radius=1`, `ann_max_neighbors=48`
- 质量门槛：所有变体均满足 `cluster_count_equal=true`、`merges_applied_equal=true`、`conflict_count_equal=true`

- sparse_no_merge_case（`2.0/0.95`）：
  - `prune_only`: `avg_speedup_ratio=19.7754%`
  - `candidate_prune`: `avg_speedup_ratio=37.8138%`（本场景最佳）
  - `ann_prune`: `avg_speedup_ratio=11.3727%`
  - `hybrid_prune`: `avg_speedup_ratio=10.1826%`

- merge_active_case（`0.82/0.85`）：
  - `candidate_prune`: `avg_speedup_ratio=16.0152%`（本场景最佳）
  - `prune_only`: `avg_speedup_ratio=-2.3038%`
  - `ann_prune`: `avg_speedup_ratio=-16.0874%`
  - `hybrid_prune`: `avg_speedup_ratio=-17.9044%`

- 结论：ANN 候选在当前实现与参数下未稳定优于 candidate filter，因此保持默认关闭，后续以参数调优和更轻量索引结构继续优化。

## 4. 交付资产
- 代码：`src/memory_cluster/`
- 测试：`tests/`（当前 47 条）
- 数据：`data/examples/`
- 实验脚本：`scripts/run_benchmark.py`, `scripts/run_ablation.py`, `scripts/run_prune_benchmark.py`, `scripts/run_candidate_filter_benchmark.py`, `scripts/run_ann_hybrid_benchmark.py`, `scripts/run_semantic_regression.py`
- 实验报告：`docs/eval/ablation_report_cn.md`, `docs/eval/ablation_report_large_cn.md`, `docs/eval/ablation_report_stress_cn.md`, `docs/eval/prune_benchmark_report.md`, `docs/eval/candidate_filter_benchmark_report.md`, `docs/eval/ann_hybrid_benchmark_report.md`, `docs/eval/semantic_regression_report.md`
- 规格：`docs/design/algorithm_spec.md`, `docs/design/algorithm_spec_detailed.md`
- 快申计划：`docs/design/cn_fast_track_patent_plan.md`
- 专利草案：`docs/patent_kit/`
- 进展日志：`WORK_PROGRESS.md`

## 5. 当前主要风险
1. 大规模性能风险：当前通过上界剪枝与候选筛选降低常见场景成本，但最坏复杂度仍为 O(k^2)，ANN 方案在 active 场景尚未达到稳定正收益。
2. 冲突语义风险：已补齐跨句指代和否定窗口误报回归，但长句多重嵌套条件仍需持续扩展测试集。
3. 指标解释风险：DMG 会改变簇结构，需按业务目标解释“冲突减少 vs 合并减少”的取舍。

## 6. 非法律声明
本报告仅用于工程实现与专利草案准备，不构成法律意见。正式申请前应由专利代理人进行完整检索与法律审查。
