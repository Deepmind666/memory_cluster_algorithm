# GPT-5.3 Codex Agent 主任务说明书（专利交底 + 工程执行）

最后更新：2026-02-09  
适用环境：Windows（优先）/ Linux（兼容）

## 1. 任务定位
你是 Codex Agent，目标不是“写一篇空泛说明”，而是输出一套**可执行、可审计、可交接**的方案，用于支撑以下主题：

> 基于 GPU/CPU 运行态反馈的代码生成优化闭环（生成 -> 执行 -> 监测 -> 分析 -> 优化 -> 再生成）

你必须同时完成：
- 技术交底书草案（中文、结构化、可用于后续专利文本整理）。
- 自动化执行说明（命令、脚本、日志产物、错误处理）。
- 风险评估（尤其是现有论文/专利重叠风险）。

## 2. 非功能强制要求
- 全流程记录：每个关键步骤必须写入 `WORK_PROGRESS.md`，包含时间戳、动作、文件清单、评审清单。
- 结论可追踪：每个“关键判断”必须附来源链接。
- 禁止伪造实验：示例数据必须可复现实跑，禁止编造性能数字。
- 先正确再优化：先保证可运行，再进入性能迭代。
- 输出分层：给零代码用户可直接复制粘贴的命令与模板。

## 3. 法律与合规边界（必须遵守）
- 不宣称“绝对新颖性”或“必然授权”。
- 使用“初步检索显示”“存在重叠风险”“需代理人复核”等谨慎措辞。
- 对已有公开技术，必须做对比并明确差异化定位。
- 该文档仅用于技术与流程准备，不是法律意见。

## 4. 截止 2026-02-09 的先行技术基线（初步）

### 4.1 论文与技术工作
1. PerfCodeGen（arXiv:2412.03578）
- 关键词：execution feedback、代码性能优化。
- 对本方案的启发：执行反馈有效，但多以运行结果驱动，硬件多指标联动深度仍可扩展。
- 来源：https://arxiv.org/abs/2412.03578

2. POLO（IJCAI 2025）
- 关键词：项目级代码性能优化、多代理。
- 对本方案的启发：项目级优化可行，但实现复杂，单机闭环可继续精简落地。
- 来源：https://www.ijcai.org/proceedings/2025/814

3. ECO（OpenReview）
- 关键词：performance-aware prompting。
- 对本方案的启发：提示词层可驱动性能改善，但应与本地硬件观测闭环结合。
- 来源：https://openreview.net/forum?id=KhwOuB0fs9

4. EffiLearner（OpenReview）
- 关键词：强化学习 + 测试时优化。
- 对本方案的启发：反馈驱动优化趋势明确，需强调你方案中的“硬件信号粒度”与“单机可执行性”。
- 来源：https://openreview.net/forum?id=R5L1TD1Z58

5. SWE-Perf（OpenReview）
- 关键词：性能缺陷修复基准。
- 对本方案的启发：可作为后续评估基准来源，避免只做主观性能叙述。
- 来源：https://openreview.net/forum?id=KxFaKvtBiG

### 4.2 专利风险基线（初步）
1. US11941378B1（2024-03-26 授权）
- 标题涉及“利用生产洞察改进生成式 AI 模型”。
- 风险点：运行数据反哺生成逻辑的框架思想存在重叠。
- 来源：https://patents.google.com/patent/US11941378B1/en

2. US20250130778A1（2025-04-17 公布）
- 标题涉及“基于性能分析改进代码生成”。
- 风险点：性能分析驱动代码优化，与本任务主题接近。
- 来源：https://patents.google.com/patent/US20250130778A1/en

3. CN119917107A（2025-05-06 公布）
- 标题涉及“大模型自动化代码审查与修复”。
- 风险点：虽然聚焦审查修复，但同属 AI 代码闭环流程，应评估权利要求边界。
- 来源：https://patents.google.com/patent/CN119917107A/en

4. US11941373B2（2024-03-26 授权）
- 标题涉及“代码质量评估的强化学习优化”。
- 风险点：反馈驱动生成策略与 RL 调优思路有相邻区域。
- 来源：https://patents.google.com/patent/US11941373B2

5. US20250165890A1（2025-05-22 公布）
- 标题涉及“机器学习辅助开发环境性能优化”。
- 风险点：IDE/开发流程级性能建议与本任务存在应用场景邻近。
- 来源：https://patents.google.com/patent/US20250165890A1/en

## 5. 差异化定位建议（写作策略）
为降低碰撞风险，交底书应强调以下组合，而非单点口号：
- 强调“单机高性能设备场景（非集群）”。
- 强调“多维硬件信号协同”（CPU 占用、GPU 显存、功耗/温度、I/O 等）。
- 强调“闭环中的自动策略生成机制”（反馈解释器 -> 策略选择器 -> 代码再生成）。
- 强调“可审计证据链”（日志、配置、版本、基线对照）。
- 强调“先正确性门禁，再性能门禁”的双门控流程。

## 6. Codex Agent 执行流程（硬约束）
1. 初始化
- 读取任务文档、确认目录结构、写入进展日志首条记录。

2. 环境探测
- 检查 Python、GPU 监测工具、系统权限。
- 产出环境快照 `env_snapshot.json`。

3. 基线代码生成
- 先产出功能正确版本。
- 运行单元测试或最小可执行验证。

4. 监测与采样
- 采集 CPU/GPU/内存/耗时指标。
- 产出 `perf_raw.json` 与终端摘要。

5. 反馈解释
- 依据阈值识别瓶颈类型。
- 产出 `feedback_report.md`。

6. 优化再生成
- 仅改动瓶颈相关代码，保留可读性。
- 每轮必须记录“改动点-依据-结果”。

7. 收敛判定
- 达到目标阈值或 2 轮连续提升 < 5% 即停止。
- 产出最终版本与对照表。

8. 文档汇总
- 生成技术交底稿、流程图、参考文献与风险说明。

## 7. 输出文件规范（建议）
- `outputs/env_snapshot.json`
- `outputs/perf_raw.json`
- `outputs/perf_summary.md`
- `outputs/feedback_report.md`
- `outputs/optimization_rounds.json`
- `outputs/final_disclosure.md`
- `outputs/figures/flowchart.svg`

## 8. 质量门禁（提交前必须逐项通过）
- 功能正确性：优化前后输出一致或误差可解释。
- 性能证据：有原始数据、有统计方法、有可复现命令。
- 可读性：关键逻辑有注释，文档结构分明。
- 追踪性：每条关键结论可追溯到日志或来源。
- 风险控制：包含专利重叠风险段落与非法律声明。

## 9. 可直接复用的主提示词模板
将下方模板交给 Codex Agent：

```text
你是 Codex Agent。请在当前仓库执行“运行态反馈驱动代码优化闭环”任务，严格遵守：
1) 先功能正确，后性能优化；
2) 每个关键步骤写入 WORK_PROGRESS.md（时间戳+动作+文件+评审清单）；
3) 产出 outputs/ 下的结构化证据文件；
4) 不伪造实验数据，必须实测；
5) 在最终文档中加入先行技术对比与碰撞风险说明，禁止宣称绝对新颖性。

任务目标：
- 生成并优化一份可运行代码；
- 采集并分析 CPU/GPU 运行态数据；
- 完成“技术交底书草案 + 流程图 + 参考文献列表”；
- 给出后续需专利代理人复核的风险清单。

输出要求：
- 中文为主，结构化 Markdown；
- 所有关键结论带来源链接；
- 给出复现实验命令；
- 最终提供变更文件清单和下一步建议。
```

## 10. 最终交付检查清单
- [ ] 文档结构完整（背景、问题、方案、实施例、对比、风险、结论）。
- [ ] 有可运行示例与真实性能日志。
- [ ] 有流程图并在文档引用。
- [ ] 有先行技术引用与日期说明。
- [ ] 有“非法律意见”声明。
- [ ] `WORK_PROGRESS.md` 记录完整且时间连续。

---

## 附录 A：参考链接
- PerfCodeGen: https://arxiv.org/abs/2412.03578
- POLO (IJCAI 2025): https://www.ijcai.org/proceedings/2025/814
- ECO (OpenReview): https://openreview.net/forum?id=KhwOuB0fs9
- EffiLearner (OpenReview): https://openreview.net/forum?id=R5L1TD1Z58
- SWE-Perf (OpenReview): https://openreview.net/forum?id=KxFaKvtBiG
- US11941378B1: https://patents.google.com/patent/US11941378B1/en
- US20250130778A1: https://patents.google.com/patent/US20250130778A1/en
- CN119917107A: https://patents.google.com/patent/CN119917107A/en
- US11941373B2: https://patents.google.com/patent/US11941373B2
- US20250165890A1: https://patents.google.com/patent/US20250165890A1/en

> 注：以上为截至 2026-02-09 的初步检索基线，不替代专利法律检索与侵权分析。
