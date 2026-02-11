# Next Phase Plan (R-018)

最后更新：2026-02-11

## 1. 当前状态
- 已完成并验证：CEG / ARB / DMG / Prune / Candidate Filter / ANN Hybrid / 语义精度回归。
- 已完成并验证：专利证据包自动收口（区别特征-技术效果-实验数据统一映射）。
- 单元测试：47/47 通过。
- 已形成 8 套可复现实验/证据产物：
  - `outputs/ablation_metrics.json`
  - `outputs/ablation_metrics_large.json`
  - `outputs/ablation_metrics_stress.json`
  - `outputs/prune_benchmark.json`
  - `outputs/candidate_filter_benchmark.json`
  - `outputs/ann_hybrid_benchmark.json`
  - `outputs/semantic_regression_metrics.json`
  - `outputs/patent_evidence_pack.json`

## 2. 本轮完成项（Phase-6 专利证据收口）
1. 证据包脚本（`scripts/build_patent_evidence_pack.py`）
- 自动汇总 ablation/prune/candidate/ann/semantic 输出。
- 统一生成：
  - `outputs/patent_evidence_pack.json`
  - `docs/patent_kit/10_区别特征_技术效果_实验映射.md`

2. 权利要求与对比文档对齐
- `docs/patent_kit/06_权利要求书_草案.md` 新增从属项：
  - 权利要求18（候选筛选）
  - 权利要求19（ANN 混合候选）
  - 权利要求20（冲突语义精度回归）
- `docs/patent_kit/08_对比文件与绕开说明.md` 增补 R-017 差异化条目。
- `docs/patent_kit/05_具体实施方式.md` 增补实施例五/六量化结果。

3. 交付目录更新
- `docs/patent_kit/00_技术交底书_总览.md` 增加第 10 号文档索引。

## 3. 当前工程决策
1. 默认推荐路径
- `candidate_filter + prune`

2. ANN 状态
- `implemented_measured_not_default`
- 原因：active merge 场景当前仍有负加速，需进一步优化索引与参数。

## 4. 剩余高优先级工作
1. ANN 开销优化（P1）
- 目标：active 场景转正收益。
- 交付：轻量索引实现 + 网格参数扫描 + 收益区间图。

2. 专利文本增强（P1）
- 目标：将证据包映射到完整独权/从权论证链，降低审查答复成本。
- 交付：权利要求逐条“问题-手段-效果-证据ID”附录。

3. 长句语义回归扩展（P2）
- 目标：覆盖多重嵌套条件、链式回指、否定冲突组合。
- 交付：新增对抗样例集（>=30）与自动回归脚本。

## 5. 建议节奏
1. 2026-02-11：ANN 参数网格与轻量索引原型
2. 2026-02-12：权利要求逐条证据附录
3. 2026-02-13：提交前总复核（代码+实验+专利文本一致性）

## 6. 风险与缓解
- 风险：性能优化与证据一致性冲突。
- 缓解：每次优化后强制重跑 benchmark + evidence pack 生成脚本。

- 风险：专利文本与实测数据脱节。
- 缓解：仅允许从 `outputs/patent_evidence_pack.json` 引用指标，不手工抄写。

## 7. 非法律声明
本计划用于工程执行，不构成法律意见。正式申请文本需由专利代理人复核。
