# CLAUDE.md — 项目级 AI 协作规范

> 本文件对所有 AI Agent（Codex 实现 / Opus 评审）生效。违反 P0/P1 级规则的交付将被退回。

## 1. 项目概要

- **名称**: memory_cluster_algorithm
- **定位**: 多 Agent 语义记忆碎片聚类压缩原型 + 中国发明专利草案
- **语言**: Python 3.10+，零外部依赖（仅 stdlib）
- **核心模块**: models → embed → cluster → compress → preference → store → retrieve → eval → pipeline → cli
- **Stage 3 扩展**: candidate filter, ANN candidates, semantic regression, stage-2 guardrail

## 2. 角色分工

| 角色 | 负责人 | 职责 |
|---|---|---|
| 实现 (Codex) | GPT-5.3 Codex | 代码、测试、文档落地、benchmark 运行、自查 |
| 评审 (Opus) | Claude Opus 4.6 | 逐行审查、独立复现、问题分级 (P0-P3)、改进建议 |
| 裁决 | 用户 | 冲突以"可运行实测结果 + 用户最新目标"为准 |

## 3. 强制规则（P0 级）

### 3.1 输出路径隔离

CI / 轻量级运行 **禁止覆写** 全量 benchmark 输出。

```
全量输出:  outputs/*.json, docs/eval/*.md
CI 输出:   outputs/ci_outputs/*.json, outputs/ci_reports/*.md
趋势输出:  outputs/stage2_guardrail_trend.json
```

**违反后果**: 证据包会引用 CI 轻量数据而非全量验证数据，直接影响专利证据链完整性。

### 3.2 测试数同步

每次新增/删除测试后，**同一个提交** 内必须同步更新以下文件中的测试计数：
- `docs/FINAL_REPORT.md` 第 2 节（自查结果）
- `WORK_PROGRESS.md` 当前 Entry

**验证方法**: `python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -1` 的数字必须与文档一致。

### 3.3 报告/JSON 时间戳一致性

同一个门禁/benchmark 的 `.json` 输出和 `.md` 报告必须来自**同一次运行**。禁止仅重跑 JSON 而不重生成报告，或反之。

### 3.4 参数一致性

以下参数必须在所有引用位置保持一致：
- `signature_radius`: 默认=4, 实验=3
- `projection_steps`: 默认=32
- `max_neighbors`: 默认=48
- `num_tables`: 默认=3, `bits_per_table`: 默认=10
- Fallback 阈值: `unique_ratio < 0.18`, `max_bucket_ratio > 0.90`

修改任何默认参数前必须更新: `cluster.py` 默认值 → benchmark 脚本默认值 → FINAL_REPORT 参数策略节。

## 4. 自查协议（每轮提交前必须执行）

```bash
# 1. 编译检查
python -m compileall -q src scripts tests

# 2. 全量测试
python -m unittest discover -s tests -p "test_*.py"

# 3. Stage-2 门禁（使用全量数据，非 CI 轻量数据）
python scripts/run_stage2_guardrail.py \
  --output outputs/stage2_guardrail.json \
  --report docs/eval/stage2_guardrail_report.md

# 4. 证据包重建
python scripts/build_patent_evidence_pack.py \
  --output outputs/patent_evidence_pack.json \
  --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"

# 5. 验证通过条件
#   - 测试: 全部 PASS
#   - 门禁: passed=true, blocker_failures=0
#   - 证据包: validation.passed=true, missing_*=[]
```

## 5. 提交报告模板

每轮提交必须包含以下信息（缺项将被退回）：

```
本轮已完成
- [变更描述 1]
- [变更描述 2]
- ...

自查结果
- python -m unittest: XX/XX PASS
- python -m compileall: PASS
- run_stage2_guardrail: passed=true/false, blocker=N, warning=N
- build_patent_evidence_pack: validation.passed=true/false

送审文件清单
- [file1.py]
- [file2.md]
- ...

下一步建议
- [建议 1]
```

## 6. 文档同步规则

| 事件 | 必须同步的文档 |
|---|---|
| 新增/删除测试 | FINAL_REPORT §2, WORK_PROGRESS |
| 修改默认参数 | FINAL_REPORT §4, cluster.py, benchmark 脚本 |
| 新增 benchmark 命令 | COMMAND_CATALOG (evidence pack), README §快速运行 |
| 新增 CI workflow | README §进展与质量门禁, next_phase_plan |
| DF-06 叙述变更 | evidence pack technical_effect, FINAL_REPORT §3.3/3.4 |
| 门禁检查项变更 | stage2_guardrail_report.md, FINAL_REPORT R-delta |

## 7. 已确定的技术决策（不可回退除非用户授权）

| 决策 | 状态 | 确定轮次 |
|---|---|---|
| Candidate 默认 radius=4 零损失优先 | **锁定** | R-023 Opus |
| Candidate radius=3 仅实验档 | **锁定** | R-023 Opus |
| ANN 冻结为可选实施例 | **锁定** | R-026 Opus |
| 核心主张: CEG/ARB/DMG/语义精度 | **锁定** | R-022 Opus |
| 可选主张: Prune/Candidate/ANN | **锁定** | R-022 Opus |
| 诊断口径=运行时口径 (cluster-entry) | **锁定** | R-024 Opus |

## 8. 临时文件管理

- 评审验证临时文件命名: `tmp_rXXX_*.py`
- 每轮评审结束后由评审人清理
- 实现人的临时脚本在自查通过后**必须删除**，不得提交

## 9. 评审问题分级

| 级别 | 含义 | 处理要求 |
|---|---|---|
| P0 | 阻塞 — 阻止提交 | 必须在本轮修复 |
| P1 | 严重 — 功能/数据完整性风险 | 必须在下一轮修复 |
| P2 | 中等 — 工程质量/文档 | 应在 2 轮内修复 |
| P3 | 轻微 — 观察/建议 | 自行判断是否修复 |
