# Next Phase Plan (R-015)

最后更新：2026-02-10

## 1. 当前状态
- 已完成并验证：CEG / ARB / DMG + Merge Upper-Bound Prune。
- 已完成并验证：冲突语义增强（否定、条件、反事实 slot 提取）。
- 已完成并验证：Merge Candidate Filter（候选筛选降耗，默认关闭）。
- 单元测试：38/38 通过。
- 已形成 5 套可复现实验：
  - 小样本消融：`outputs/ablation_metrics.json`
  - 100 样本 realistic 消融：`outputs/ablation_metrics_large.json`
  - 100 样本 stress 消融：`outputs/ablation_metrics_stress.json`
  - prune 对照：`outputs/prune_benchmark.json`
  - candidate filter 对照：`outputs/candidate_filter_benchmark.json`

## 2. 本轮完成项（Phase-3 性能原型）
1. 候选筛选机制（可开关）
- 新增配置：`enable_merge_candidate_filter`、`merge_candidate_bucket_dims`、`merge_candidate_max_neighbors`。
- 合并阶段新增签名桶候选图，仅对候选 pair 计算相似度。
- 新增审计指标：`merge_pairs_skipped_by_candidate_filter`。

2. 工程接入与测试
- CLI 增加开关参数：`--enable-merge-candidate-filter` 等。
- 新增测试：`tests/test_merge_candidate_filter.py`。
- 全量测试回归通过：38/38。

3. 性能证据
- 新增脚本：`scripts/run_candidate_filter_benchmark.py`。
- 新增报告：`docs/eval/candidate_filter_benchmark_report.md`。
- 关键结果（bucket=10, neighbors=16）：
  - sparse 场景：`attempt_reduction_ratio=75.0140%`，`avg_speedup_ratio=42.6363%`
  - merge-active 场景：`attempt_reduction_ratio=44.4496%`，`avg_speedup_ratio=19.8265%`
  - 两场景 `cluster_count_equal=true`

## 3. 剩余高优先级工作
1. 语义冲突精度（P1）
- 目标：补齐跨句指代、长句嵌套条件、否定词窗口误报。
- 交付：规则白名单/黑名单 + 误报集回归测试。

2. 性能工程第二阶段（P1）
- 目标：在候选筛选基础上继续降低大规模复杂度常数，并探索 ANN 混合策略。
- 交付：候选筛选 + prune + ANN 的三方对照实验（含质量守恒门槛）。

3. 申请前证据收口（P1）
- 目标：把“区别特征-技术效果-实验数据”固化为代理人可直接使用的证据包。
- 交付：统一表格 + 复现实验命令 + 图表截图索引。

## 4. 建议节奏
1. 2026-02-11：语义精度回归（跨句与嵌套条件）
2. 2026-02-12：性能第二阶段原型（ANN 混合）
3. 2026-02-13：证据包收口与专利文本对齐

## 5. 风险与缓解
- 风险：近似候选策略引入召回损失。
- 缓解：默认关闭候选筛选；开启时强制输出 `cluster_count_equal` 与差异指标。

- 风险：语义规则扩展带来误报。
- 缓解：每条新规则绑定反例测试，进入 CI。

## 6. 非法律声明
本计划用于工程执行，不构成法律意见。正式申请文本需由专利代理人复核。
