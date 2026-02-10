# Claude4.6 Strict Review Checklist (R-010)

更新时间：2026-02-10  
基线提交：`f7b2d93`  
评审目标：对“专利算法实现 + 工程可复现性 + 风险点”进行严格复核，输出可用于下一轮开发和专利材料收口的结论。

---

## 0. 评审输入清单

- 代码目录：`src/memory_cluster/`
- 测试目录：`tests/`
- 实验脚本：`scripts/run_ablation.py`, `scripts/run_prune_benchmark.py`, `scripts/run_benchmark.py`
- 状态报告：`docs/FINAL_REPORT.md`
- 计划文档：`docs/design/next_phase_plan.md`
- 专利文档：`docs/patent_kit/`
- 进展日志：`WORK_PROGRESS.md`
- 交接规范：`.claude.md`

---

## 1. 一票否决项（P0 Gate）

以下任一项失败，评审结论必须标记为 P0，不得直接进入专利材料定稿阶段。

- [ ] `python -m unittest discover -s tests -p "test_*.py" -v` 全部通过（当前应为 28/28）。
- [ ] `python -m compileall src tests scripts` 无语法错误。
- [ ] `scripts/run_ablation.py` 可运行，输出 `outputs/ablation_metrics.json`。
- [ ] `scripts/run_prune_benchmark.py` 可运行，输出 `outputs/prune_benchmark.json`。
- [ ] `build -> query` 端到端 CLI 流程可运行，无崩溃。
- [ ] 核心指标文件存在并可读：`outputs/benchmark_latest.json`, `outputs/ablation_metrics.json`, `outputs/prune_benchmark.json`。

---

## 2. 算法完成度核查（按创新点）

### 2.1 CEG（Conflict Evidence Graph）

- [ ] `ConflictRecord` 字段包含 `priority`, `dominant_value`, `transition_count`：`src/memory_cluster/models.py`
- [ ] `compress.py` 存在 `_build_conflict_graph(...)` 且在 `compress(...)` 中接入。
- [ ] 冲突节点、切换边、优先级计算逻辑与文档描述一致。
- [ ] `tests/test_conflict_graph_and_budget.py` 覆盖 CEG 关键断言。
- [ ] 检索侧可返回冲突优先级：`src/memory_cluster/retrieve.py`

### 2.2 ARB（Adaptive Retention Budget）

- [ ] `PreferenceConfig` 含 ARB 参数（冲突权重、熵权重、时效惩罚、scale 上下界）。
- [ ] `cluster_budget(...)` 公式实现与配置参数一致：`src/memory_cluster/preference.py`
- [ ] `compress(...)` 使用 `cluster_budget(...)` 而非固定预算。
- [ ] `tests/test_conflict_graph_and_budget.py` 覆盖预算提升/下降的对比断言。
- [ ] 报告中的 ARB 指标增益可复现：`docs/eval/ablation_report_cn.md`

### 2.3 DMG（Dual Merge Guard）

- [ ] `cluster.py` 含 `_extract_slots`, `_slot_profile`, `_conflict_compatibility`。
- [ ] 合并前同时检查语义阈值和冲突兼容阈值。
- [ ] `merges_blocked_by_guard` 指标在 metrics 中可见。
- [ ] `tests/test_dual_merge_guard.py` 覆盖“混合模式簇被阻断”行为。

### 2.4 Merge Upper-Bound Prune（新增性能优化）

- [ ] `cluster.py` 合并循环中存在“上界判定后跳过完整余弦”。
- [ ] `merge_pairs_pruned_by_bound` 指标可观测。
- [ ] 默认策略为关闭，需显式开启（配置和 CLI 一致）。
- [ ] `tests/test_merge_upper_bound_prune.py` 覆盖“结果一致性 + 剪枝触发”。
- [ ] `scripts/run_prune_benchmark.py` 结果显示开启后存在可解释收益，且 `cluster_count_equal=true`。

---

## 3. 模块级代码审查清单（逐文件）

### 3.1 `src/memory_cluster/models.py`

- [ ] dataclass 字段默认值合理，无可变默认值陷阱。
- [ ] `from_dict/to_dict` 前后兼容（新增字段缺失时不崩溃）。
- [ ] `PreferenceConfig` 的新字段默认值与 CLI 行为一致。
- [ ] 类型转换安全（float/int/bool/list）无隐式异常。

### 3.2 `src/memory_cluster/embed.py`

- [ ] 向量生成确定性（同输入同输出）。
- [ ] L2 归一化正确，零向量处理安全。
- [ ] `cosine_similarity` 边界安全（空向量、长度不一致）。

### 3.3 `src/memory_cluster/cluster.py`

- [ ] `assign()` 不会遗漏兼容簇，阈值分支正确。
- [ ] `merge_clusters_with_lookup()` 在 guard 开关关闭时不改变既有行为。
- [ ] 上界剪枝数学上“只跳过必不可能达阈值”的 pair，不引入误剪。
- [ ] 合并后 `centroid/source_distribution/version/last_updated` 更新完整。
- [ ] 统计字段单调合理：`merge_attempts`, `merges_applied`, `merges_blocked_by_guard`, `merge_pairs_pruned_by_bound`。

### 3.4 `src/memory_cluster/compress.py`

- [ ] 语义去重不误删关键冲突证据。
- [ ] slot 提取规则对中英文、flag、meta slots 一致。
- [ ] 冲突记录保留 evidence，不静默覆盖。
- [ ] summary 构建预算控制正确，超长截断可预期。
- [ ] `strict_conflict_split` 行为在冲突场景可解释。

### 3.5 `src/memory_cluster/preference.py`

- [ ] 保护规则命中后不再被 source/staleness 降级覆盖。
- [ ] `source_promote/demote` 阈值逻辑可审计。
- [ ] `_normalized_entropy` 数学实现正确（范围 [0,1]）。
- [ ] `cluster_budget` scale clamp 生效。
- [ ] reasons 记录完整，可追踪决策链。

### 3.6 `src/memory_cluster/pipeline.py`

- [ ] 处理顺序合理：assign -> merge -> decide -> compress -> split -> l2 -> metrics。
- [ ] 配置开关全部透传到对应模块（DMG、CEG、ARB、prune、L2）。
- [ ] metrics 汇总不丢字段。

### 3.7 `src/memory_cluster/retrieve.py`

- [ ] 排序分数组合可解释：semantic + keyword + strength + freshness + conflict bonus。
- [ ] `offset/top_k/cluster_level` 行为正确。
- [ ] `expand=True` 时 backrefs 展开与状态一致。

### 3.8 `src/memory_cluster/eval.py`

- [ ] 压缩率、冲突率、簇规模等指标公式正确。
- [ ] L1/L2 口径一致，不混算。
- [ ] 除零保护完整。

### 3.9 `src/memory_cluster/store.py`

- [ ] JSONL 读写稳定，load_latest_by_id 去重逻辑正确。
- [ ] 版本字段语义清晰。
- [ ] 明确并发写入限制是否已文档化。

### 3.10 `src/memory_cluster/cli.py`

- [ ] 参数到配置映射完整：CEG/ARB/DMG/prune/protected 等。
- [ ] 默认行为与 `PreferenceConfig` 默认值一致。
- [ ] 错误输出为结构化 JSON，便于自动化调用。

### 3.11 `scripts/*.py`

- [ ] `run_ablation.py` 场景定义与 summary 计算逻辑正确。
- [ ] `run_prune_benchmark.py` 对照组/实验组可重复运行。
- [ ] benchmark 脚本输出字段可被报告引用。

---

## 4. 测试充分性审查

### 4.1 已覆盖项（应核实）

- [ ] 基本聚类。
- [ ] 冲突标记。
- [ ] CEG/ARB。
- [ ] DMG。
- [ ] 保护偏好。
- [ ] L2 层级。
- [ ] 检索排序与分页。
- [ ] store roundtrip。
- [ ] 上界剪枝一致性与触发。

### 4.2 建议补充项（若缺失，记为 P2/P3）

- [ ] `embed.py` 独立单测（长度不一致、零向量、纯中文/纯英文）。
- [ ] `eval.py` 指标函数的构造性单测。
- [ ] `compress.py` 对复杂否定句、条件句、反事实句的冲突识别单测。
- [ ] `store.py` 异常输入单测（损坏 JSON 行、空字段）。
- [ ] 大规模样本（>=200 fragments）回归测试。

---

## 5. 性能与可复现性审查

- [ ] `run_benchmark.py` 与 `run_prune_benchmark.py` 至少各跑一次并留存 JSON。
- [ ] 记录运行参数（阈值、runs、warmup、fragment_count）。
- [ ] 结果分析包含“收益场景”和“无收益/负收益场景”解释。
- [ ] 不把偶发单次结果当作结论，至少使用多轮平均值。
- [ ] 报告结论与 JSON 原始数据一致。

---

## 6. 专利一致性审查（中国申请导向）

- [ ] 每个创新点都能映射“技术问题 -> 技术手段 -> 技术效果”。
- [ ] 权利要求与代码能力一致，不夸大未实现特性。
- [ ] `docs/patent_kit/06_权利要求书_草案.md` 与当前实现同步（含 14-16）。
- [ ] `docs/patent_kit/05_具体实施方式.md` 含量化实验支撑。
- [ ] `docs/patent_kit/08_对比文件与绕开说明.md` 有结构化三联表（最接近现有技术/区别特征/技术效果）。
- [ ] 明确 trade-off：DMG+ARB 可能提升可解释性但不一定降低 summary 长度。

---

## 7. 安全与工程风险审查

- [ ] 仓库中无凭证泄漏（token/password/key）。
- [ ] 输入文件解析具备最小防护（格式错误不导致静默坏数据）。
- [ ] 路径参数不会导致误写关键文件。
- [ ] Windows 编码（GBK 控制台）影响是否已文档化。
- [ ] `.claude.md` 与 `WORK_PROGRESS.md` 记录完整、可交接。

---

## 8. 评审输出模板（交付给负责人）

请 Claude4.6 按以下结构输出，避免“只有结论没有证据”。

1. **Findings（按严重级别排序）**
- P0:
- P1:
- P2:
- P3:

2. **Evidence（每条问题给文件与行号）**
- `path:line` + 现象 + 风险 + 复现方法

3. **Pass/Fail Gates**
- 单测 gate:
- 编译 gate:
- 实验 gate:
- 文档一致性 gate:

4. **Fix Recommendations**
- 必改（本轮必须合并）:
- 可延后（下一阶段）:

5. **Residual Risks**
- 尚未解决的技术风险与专利风险。

---

## 9. 当前任务进度快照（供评审参考）

- 算法主线完成度：高（CEG/ARB/DMG/L2/Prune 已实现并有测试）。
- 代码稳定性：高（当前 28/28 单测通过）。
- 实验证据：中高（已有 ablation 与 prune benchmark，可复现）。
- 待继续推进：复杂冲突语义、超大规模性能、专利证据链收口。
