# Review Checklist

版本：v2.2
最后更新：2026-02-13
更新人：Claude Opus 4.6（基于 R-011~R-026 八轮评审经验）

## 使用方法
- 使用时机：每次准备提交前（实现人自查）+ 每次评审时（评审人复查）。
- 规则：逐项勾选，不满足项必须给出修复计划或阻塞说明。
- P0 级条目未通过 → 退回重做；P1 级未通过 → 下一轮必须修复。
- CI 输出隔离（F 区）为 P1 强制门禁：任一条失败不得进入送审与发布。

---

## A. 代码正确性（P0 级）
- [ ] `python -m compileall -q src scripts tests` 无错误
- [ ] `python -m unittest discover -s tests -p "test_*.py"` 全部 PASS
- [ ] 新增功能有对应测试覆盖
- [ ] 无硬编码临时路径或调试代码残留
- [ ] 无 `tmp_*.py` 临时文件遗留

## B. Stage-2 门禁（P0 级）
- [ ] `run_stage2_guardrail.py` 输出 `passed=true`
- [ ] `blocker_failures=0`
- [ ] 门禁报告 (.md) 与 JSON 输出来自同一次运行（时间戳一致）
- [ ] 新增检查项有对应的 mock 测试路径

## C. 证据包完整性（P1 级）
- [ ] `build_patent_evidence_pack.py` 输出 `validation.passed=true`
- [ ] `missing_claim_refs=[]`
- [ ] `missing_evidence_files=[]`
- [ ] `missing_metrics=[]`
- [ ] DF-06 `technical_effect` 描述与最新验证结论一致

## D. 文档同步（P1 级）
- [ ] `FINAL_REPORT.md` 测试数 = 实际测试数
- [ ] `FINAL_REPORT.md` 包含本轮 R-delta 小节
- [ ] `next_phase_plan.md` 包含本轮 Plan Update
- [ ] `WORK_PROGRESS.md` 包含本轮 Entry（时间戳 + 自查结果）
- [ ] 新增命令已同步到 `README.md` 和 `COMMAND_CATALOG`
- [ ] 送审附件必须包含 `docs/review/review_closure_matrix.md`

## E. 参数一致性（P1 级）
- [ ] `cluster.py` 默认参数 = benchmark 脚本默认参数 = FINAL_REPORT 参数策略
- [ ] 门禁阈值（fallback: unique<0.18, bucket>0.90）在代码和文档中一致
- [ ] 不同脚本中的 `signature_radius`、`projection_steps`、`max_neighbors` 等无漂移

## F. 输出路径隔离（P1 级）
- [ ] `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json` 输出 `passed=true`
- [ ] `violation_count=0`
- [ ] CI bundle 不向 `outputs/` 根目录写入 benchmark JSON
- [ ] CI 报告写入 `outputs/ci_reports/`（非 `docs/eval/`）
- [ ] 全量 benchmark 输出未被 CI 轻量数据覆写
- [ ] `stage2-quality-gate.yml` 和 `stage2-nightly-trend.yml` 均包含 `Validate CI Output Isolation` 步骤

## G. 合规与风险（P2 级）
- [ ] 包含"非法律意见"声明
- [ ] 未出现"绝对新颖性/必然授权"表述
- [ ] ANN 在所有叙述中定位为"可选实施例"
- [ ] Candidate radius=3 在所有叙述中标注为"实验档"

## H. 工程可维护性（P2 级）
- [ ] 新增脚本有 `argparse` + `--help` 说明
- [ ] 新增函数有 type hints
- [ ] 模块间无循环导入
- [ ] README 可指导新同事 10 分钟内上手

## I. 提交格式（P3 级）
- [ ] 提交报告包含：已完成 / 自查结果 / 送审清单 / 下一步建议
- [ ] `WORK_PROGRESS.md` Entry 字段完整（Timestamp/Stage/Actions/Files/Checklist）
- [ ] 各文档 section 之间有空行分隔
- [ ] 若评审人直接修复问题，闭环矩阵状态应标注 `closed_by_reviewer`
