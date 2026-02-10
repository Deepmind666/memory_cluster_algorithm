# Next Phase Plan (R-017)

最后更新：2026-02-11

## 1. 当前状态
- 已完成并验证：CEG / ARB / DMG + Merge Upper-Bound Prune。
- 已完成并验证：Merge Candidate Filter（候选筛选降耗，默认关闭）。
- 已完成并验证：语义精度回归（条件边界、否定窗口、跨句指代）。
- 已完成并验证：ANN Hybrid Candidates（多表近似候选，默认关闭）。
- 单元测试：47/47 通过。
- 已形成 7 套可复现实验：
  - 小样本消融：`outputs/ablation_metrics.json`
  - 100 样本 realistic 消融：`outputs/ablation_metrics_large.json`
  - 100 样本 stress 消融：`outputs/ablation_metrics_stress.json`
  - prune 对照：`outputs/prune_benchmark.json`
  - candidate filter 对照：`outputs/candidate_filter_benchmark.json`
  - semantic regression：`outputs/semantic_regression_metrics.json`
  - ann hybrid 对照：`outputs/ann_hybrid_benchmark.json`

## 2. 本轮完成项（Phase-5 性能工程第二阶段）
1. ANN 候选门控实现（`src/memory_cluster/cluster.py`）
- 新增 ANN 近似候选开关与参数：
  - `enable_merge_ann_candidates`
  - `merge_ann_num_tables`
  - `merge_ann_bits_per_table`
  - `merge_ann_probe_radius`
  - `merge_ann_max_neighbors`
  - `merge_ann_score_dims`
- 支持三种门控模式：
  - candidate only
  - ann only
  - hybrid（candidate ∪ ann）
- 新增可审计指标：
  - `merge_pairs_skipped_by_ann_candidates`
  - `merge_pairs_skipped_by_hybrid_candidates`

2. 工程接入
- `PreferenceConfig`、`pipeline.py`、`cli.py` 全链路接入 ANN 参数。
- CLI 新增参数：`--enable-merge-ann-candidates` 与 `--merge-ann-*`。

3. 测试与证据
- 新增测试：`tests/test_merge_ann_candidates.py`（3 条）。
- 新增 benchmark：`scripts/run_ann_hybrid_benchmark.py`。
- 新增报告：`docs/eval/ann_hybrid_benchmark_report.md`。
- 质量门槛（cluster/merge/conflict 一致性）在实验中全部通过。

## 3. 第二阶段结论
1. sparse_no_merge 场景
- `candidate_prune` 最优：`avg_speedup_ratio=37.8138%`
- `ann_prune` 有收益：`11.3727%`
- `hybrid_prune` 有收益：`10.1826%`

2. merge_active 场景
- `candidate_prune` 最优：`16.0152%`
- `ann_prune` 与 `hybrid_prune` 均出现负加速（分别 `-16.0874%`、`-17.9044%`）

3. 决策
- ANN 门控保留为实验特性，默认关闭。
- 当前生产推荐路径：`candidate_filter + prune`。

## 4. 剩余高优先级工作
1. 专利证据收口（P1）
- 目标：形成“区别特征-技术效果-实验数据”统一证据包，支持代理人直接复核。
- 交付：统一索引表、复现实验命令、图表截图索引、指标对应权利要求映射。

2. ANN 降开销优化（P2）
- 目标：降低 ANN 构建和探针开销，使 active 场景不再负加速。
- 交付：轻量索引实现、参数网格搜索结果、收益区间图。

3. 语义长句扩展（P2）
- 目标：覆盖多重嵌套条件与跨句链式指代（>=3 句）。
- 交付：误报集扩容 + 对抗样例回归脚本。

## 5. 建议节奏
1. 2026-02-11：证据包索引结构与专利映射模板落地
2. 2026-02-12：ANN 参数网格与轻量索引试验
3. 2026-02-13：专利文本对齐与提交前自查

## 6. 风险与缓解
- 风险：ANN 在活跃合并场景引入额外开销。
- 缓解：默认关闭 ANN；启用时必须通过质量门槛并对比 baseline speedup。

- 风险：规则与性能策略增多导致可解释性下降。
- 缓解：每个开关必须对应指标字段与对照实验报告。

## 7. 非法律声明
本计划用于工程执行，不构成法律意见。正式申请文本需由专利代理人复核。
