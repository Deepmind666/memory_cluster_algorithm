# Next Phase Plan (R-016)

最后更新：2026-02-11

## 1. 当前状态
- 已完成并验证：CEG / ARB / DMG + Merge Upper-Bound Prune。
- 已完成并验证：Merge Candidate Filter（候选筛选降耗，默认关闭）。
- 已完成并验证：语义精度回归（条件边界、否定窗口、跨句指代）。
- 单元测试：44/44 通过。
- 已形成 6 套可复现实验：
  - 小样本消融：`outputs/ablation_metrics.json`
  - 100 样本 realistic 消融：`outputs/ablation_metrics_large.json`
  - 100 样本 stress 消融：`outputs/ablation_metrics_stress.json`
  - prune 对照：`outputs/prune_benchmark.json`
  - candidate filter 对照：`outputs/candidate_filter_benchmark.json`
  - semantic regression：`outputs/semantic_regression_metrics.json`

## 2. 本轮完成项（Phase-4 语义精度回归）
1. 规则增强（`src/memory_cluster/compress.py`）
- 条件后件隔离：`if/如果 ... then/则/那么 ...` 仅前件进入 `cond:*`。
- 英文否定补齐：支持 `not key=value`。
- 双重否定窗口：`do not disable cache` 不再产出 `flag:false`。
- 跨句槽位回指：`it/this/that/它/其/该参数` 回指前一显式槽位。

2. 回归测试（`tests/test_semantic_precision_regression.py`）
- 新增 6 条单测，覆盖：条件边界、英文否定、双重否定、英文/中文跨句指代、条件作用域指代。
- 全量测试回归通过：44/44。

3. 证据脚本与报告
- 新增脚本：`scripts/run_semantic_regression.py`。
- 新增报告：`docs/eval/semantic_regression_report.md`。
- 核心结果：`case_pass_rate=1.0`，`expected_hit_rate=1.0`，`forbidden_violations=0`。

## 3. 剩余高优先级工作
1. 性能工程第二阶段（P1）
- 目标：在 candidate filter + prune 基础上引入 ANN 混合候选，继续降低大规模复杂度常数。
- 交付：ANN on/off + prune on/off + candidate filter on/off 三方对照，附质量守恒门槛。

2. 专利证据收口（P1）
- 目标：形成“区别特征-技术效果-实验数据”统一证据包，支持代理人直接复核。
- 交付：统一索引表、复现实验命令、图表截图索引、指标对应权利要求映射。

3. 语义长句扩展（P2）
- 目标：覆盖多重嵌套条件与跨句链式指代（>=3 句）。
- 交付：误报集扩容 + 对抗样例回归脚本。

## 4. 建议节奏
1. 2026-02-11：ANN 混合候选原型 + 指标埋点
2. 2026-02-12：三方对照实验与质量门槛校验
3. 2026-02-13：专利证据包收口与文本对齐

## 5. 风险与缓解
- 风险：ANN 近似检索引入召回损失。
- 缓解：默认关闭 ANN；开启时强制输出 `cluster_count_equal`、`merges_applied`、`conflict_count` 差异。

- 风险：语义规则持续扩展导致局部误报。
- 缓解：每条新增规则绑定正例+反例测试，纳入 CI。

## 6. 非法律声明
本计划用于工程执行，不构成法律意见。正式申请文本需由专利代理人复核。
