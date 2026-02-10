# Self Audit & Patent Potential (R-010)

更新时间：2026-02-10 10:27:47 +08:00  
审计基线：`main`（最新已推送到 `origin/main` 的主线能力 + 本轮自查补充）  
定位：代码漏洞/风险自查 + 中国发明专利授权潜力自评（非法律意见）

---

## 1. 本轮自查执行记录

已执行检查：

- `python -m unittest discover -s tests -p "test_*.py" -q` -> 23/23 通过
- 凭证扫描（关键字）：`ghp_`, `token`, `password`, `secret`, `private key`
- 高风险 API 扫描：`eval/exec/os.system/pickle.loads/yaml.load`
- 核心模块人工复核：
  - `src/memory_cluster/cluster.py`
  - `src/memory_cluster/compress.py`
  - `src/memory_cluster/preference.py`
  - `src/memory_cluster/retrieve.py`
  - `src/memory_cluster/store.py`
  - `src/memory_cluster/cli.py`
- 专利材料复核：
  - `docs/patent_kit/05_具体实施方式.md`
  - `docs/patent_kit/08_对比文件与绕开说明.md`
  - `docs/patent_kit/09_授权潜力评估与下一步建议.md`

---

## 2. 发现与分级（自查结论）

### P0（阻塞）: 0 项

- 未发现直接导致远程代码执行、凭证泄漏、数据破坏的高危漏洞。

### P1（高优先级）: 3 项

1. JSONL 容错不足导致服务级失败风险  
- 位置：`src/memory_cluster/store.py`, `src/memory_cluster/cli.py`  
- 现象：遇到损坏 JSON 行会抛异常中断流程。  
- 风险：在真实流水线中，单行坏数据导致整批失败（可用性风险）。  
- 建议：加入“严格模式/容错模式”开关与错误计数输出。

2. 并发写入缺少锁机制  
- 位置：`src/memory_cluster/store.py`  
- 现象：append-only 写入未做进程级锁。  
- 风险：多进程并发 ingest 可能产生行交错、数据损坏。  
- 建议：引入文件锁（Windows + POSIX 兼容）或单写入进程策略。

3. 中国专利评估文档过时  
- 位置：`docs/patent_kit/09_授权潜力评估与下一步建议.md`  
- 现象：最后更新停留在 2026-02-09，未纳入 CEG/ARB/DMG/Prune 最新进展。  
- 风险：专利路线判断滞后，影响申报优先级。  
- 建议：更新“当前公开内容风险 + 未公开增量方案”的双路径评估。

### P2（中优先级）: 4 项

1. 指标/效果声明与场景耦合较强  
- 位置：`docs/FINAL_REPORT.md`, `docs/eval/*.md`  
- 现象：部分收益依赖特定阈值和数据分布。  
- 建议：增加“收益边界条件”章节，避免过度外推。

2. 冲突语义仍偏规则驱动  
- 位置：`src/memory_cluster/compress.py`  
- 现象：否定、条件句、反事实复杂语义覆盖有限。  
- 建议：扩展规则 + 反例单测，提升稳健性。

3. `_parse_iso` 在多模块重复  
- 位置：`src/memory_cluster/preference.py`, `src/memory_cluster/retrieve.py`  
- 现象：重复实现，异常处理策略不同。  
- 建议：抽到共享 util，统一语义。

4. store 全量加载内存  
- 位置：`src/memory_cluster/store.py`  
- 现象：大文件时内存压力升高。  
- 建议：提供流式读取或分块处理接口。

### P3（低优先级）: 2 项

1. `KEY_VALUE_PATTERN` 可能误匹配 URL 片段  
- 位置：`src/memory_cluster/compress.py`  

2. Windows 控制台编码提示仍可完善  
- 位置：CLI 输出路径与运行文档  

---

## 3. 本轮已修复项（自查闭环）

已确认并补齐：

- 中文冲突关键词权重可用性校验（新增单测）  
  - 测试：`tests/test_retrieve_ordering.py` 新增 `test_chinese_conflict_query_uses_conflict_priority_bonus`  
  - 结果：中文“冲突”查询可正确触发冲突优先级加分。

---

## 4. 中国发明专利授权潜力（技术视角自评）

## 4.1 评分（非法律意见）

- 技术实现完整度：8.8/10  
- 差异化工程特征强度（CEG+ARB+DMG+Prune 组合）：7.2/10  
- 可复现实验证据强度：7.0/10  
- 法域新颖性安全性（针对“已公开版本”）：3.0/10  

综合判断（中国，当前公开版本直接申请）：**中低潜力**。

## 4.2 关键原因

正向：

- 方案不是空泛算法，已落到具体结构/流程/指标；
- 有可运行代码、测试、实验报告，工程证据链较完整。

负向：

- GitHub 公开时间较早，当前公开方案在中国法域新颖性压力较大；
- 创造性仍需靠“区别特征 + 量化效果”进一步稳固，不宜仅靠功能叙事。

## 4.3 可行策略（务实）

1. 不建议直接以“当前已公开方案”作为唯一申请包。  
2. 建议以“未公开改进包”作为核心申请对象：  
- 复杂冲突语义判别增强；  
- 合并阶段近似索引 + 可解释性约束；  
- L1/L2 路由策略量化收益。  
3. 用三联表固定证据链：最接近现有技术 -> 区别特征 -> 技术效果（含数字）。

---

## 5. 为下一轮“Claude 对比评审”准备

已准备对比模板：

- `docs/review/claude_review_diff_template.md`

对比方法：

1. 逐条对齐 P0-P3。  
2. 对每条分歧写“我方证据 vs Claude证据”。  
3. 最终产出“接受 / 暂缓 / 拒绝”三分类处置单并绑定提交计划。

---

## 6. 结论

- 当前核心算法研发处于“可评审、可复现、可继续增强”的稳态。  
- 下一阶段优先级：
1. 容错与并发写入风险收敛（工程可靠性）  
2. 冲突语义增强（技术效果增强）  
3. 专利证据链更新（法律表达一致性）
