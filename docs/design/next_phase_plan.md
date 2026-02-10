# Next Phase Plan (R-013)

最后更新：2026-02-10

## 1. 当前状态
- 已完成并验证：CEG / ARB / DMG + Merge Upper-Bound Prune。
- 已完成并验证：冲突语义增强（否定、条件、反事实 slot 提取）。
- 单元测试：31/31 通过。
- 已形成 3 套可复现实验：
  - 小样本消融：`outputs/ablation_metrics.json`
  - 100 样本 realistic 消融：`outputs/ablation_metrics_large.json`
  - 100 样本 stress 消融：`outputs/ablation_metrics_stress.json`

## 2. 本轮完成项（Phase-2）
1. 语义规则增强
- 新增模式：`NOT_EQUAL_PATTERN`、`NEGATED_KEY_VALUE_PATTERN`、条件/反事实作用域提取。
- 结果：冲突证据图可区分事实值与条件值（`cond:`）及反事实值（`cf:`）。

2. 测试补强
- 新增测试：`tests/test_conflict_semantics.py`
- 覆盖点：否定值提取、条件作用域隔离、反事实作用域提取。

3. 大样本实验
- `scripts/run_ablation.py` 已参数化：支持 `fragment-count`、阈值与数据集标签。
- 实验报告：`docs/eval/ablation_report_large_cn.md`、`docs/eval/ablation_report_stress_cn.md`。

## 3. 剩余高优先级工作
1. 性能工程（P1）
- 目标：降低大簇 O(k^2) 合并常数，探索 ANN/桶化候选筛选。
- 交付：可开关近似候选器 + 与 prune 联合对照实验。

2. 语义冲突精度（P1）
- 目标：补齐跨句指代、长句嵌套条件、否定词窗口误报。
- 交付：规则白名单/黑名单 + 误报集回归测试。

3. 申请前证据收口（P1）
- 目标：把“区别特征-技术效果-实验数据”固化为一套代理人可直接使用的证据包。
- 交付：统一表格 + 复现实验命令 + 图表截图索引。

## 4. 建议节奏
1. 2026-02-11 ~ 2026-02-12：性能工程原型（ANN/桶化）
2. 2026-02-13：语义精度回归与规则收口
3. 2026-02-14：专利证据包最终整理

## 5. 风险与缓解
- 风险：近似策略损害可解释性。
- 缓解：保留 exact 模式并强制输出对照指标。

- 风险：语义规则扩展带来误报。
- 缓解：每条规则绑定反例测试，进入 CI。

## 6. 非法律声明
本计划用于工程执行，不构成法律意见。正式申请文本需由专利代理人复核。
