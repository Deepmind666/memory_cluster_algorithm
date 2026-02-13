# R-026 Opus 评审：R-029 速度门禁 + R-030/R-030b CI 集成

- **评审人**: Claude Opus 4.6
- **时间戳**: 2026-02-13 11:30:00 +08:00
- **评审对象**: R-029 Codex（速度回归告警 + None 路径测试 + DF-06 修正 + ANN 冻结 + 临时清理） + R-030/R-030b Codex（CI 集成 + 自包含 bundle）
- **前序评审**: R-025 Opus (A-)
- **总体评级**: **A-**

---

## 1. 评审范围

本次评审覆盖 R-029 + R-030 + R-030b 三个连续提交。用户仅提交了 R-029 工作报告，但代码库已包含 R-030/R-030b 变更，一并评审。

| 文件 | 变更类型 | 来源轮次 | 审查深度 |
|---|---|---|---|
| `scripts/run_stage2_guardrail.py` | **更新** | R-029 | 逐行 |
| `tests/test_stage2_guardrail.py` | **更新** | R-029 | 逐行 |
| `scripts/build_patent_evidence_pack.py` | **更新** | R-029 | 关键字段 |
| `docs/FINAL_REPORT.md` | **更新** | R-029/R-030/R-030b | 全量 |
| `docs/design/next_phase_plan.md` | **更新** | R-029/R-030/R-030b | 全量 |
| `.github/workflows/stage2-quality-gate.yml` | **新增** | R-030 | 逐行 |
| `scripts/run_ci_guardrail_bundle.py` | **新增** | R-030/R-030b | 逐行 |
| `tests/test_ci_guardrail_bundle_unit.py` | **新增** | R-030b | 逐行 |
| `outputs/stage2_guardrail.json` | 重跑 | R-030b | 交叉验证 |
| `docs/eval/stage2_guardrail_report.md` | 未重跑 | — | 交叉验证 |
| 临时文件 `tmp_r02*.py` | **已删除** | R-029 | 确认 |

---

## 2. R-025 Opus 遗留问题处理状态

| ID | 描述 | 级别 | 本轮状态 |
|---|---|---|---|
| P1 | FINAL_REPORT 测试数 58→68 同步 | P1 | **已修** → 71/71（含 R-030b 新增） |
| P2-1 | DF-06 technical_effect 描述滞后 | P2 | **已修** — "默认零损失 + 实验档风险披露" |
| P2-2 | 门禁速度回归告警 | P2 | **已修** — 新增 3 项 speed checks |
| P2-3 | ANN 冻结决策 | P2 | **已修** — 写入 FINAL_REPORT + next_phase_plan |
| P3-1 | test_stage2_guardrail candidate_benchmark=None | P3 | **已修** — test_supports_missing_candidate_benchmark_payload |
| P3-2 | 临时文件清理 | P3 | **已修** — 全部删除 |

**全部 6 项遗留已处理，达标率 100%。**

---

## 3. 代码审查

### 3.1 `run_stage2_guardrail.py` — 速度回归告警（更新 253→316 行）

**新增内容**:
1. 函数签名新增 `candidate_active_speed_warn_floor` / `ann_active_speed_warn_floor` 参数（默认 -0.20）
2. 新增 `_active_candidate_summary()` 辅助函数（line 40-45），提取 candidate benchmark 的 active scenario summary
3. 三项新增检查:
   - `ann_active_speed_regression_warn` (line 146-156): ANN active 速度不低于 floor
   - `ann_active_positive_speed_target_warn` (line 157-163): ANN active 速度目标为正（aspirational）
   - `candidate_active_speed_regression_warn` (line 177-187): Candidate active 速度不低于 floor

4. CLI 新增 `--candidate-active-speed-warn-floor` / `--ann-active-speed-warn-floor` 参数

**设计亮点**:
- ANN speed 检查**无条件执行**（总是有 ann_hybrid 数据）
- Candidate speed 检查**在 `if candidate_benchmark is not None` 块内**（正确处理 None 路径）
- 所有 speed checks 均为 `severity="warning"`，不阻断发布 — 这是正确的定位：质量是底线（blocker），速度是观测（warning）
- `ann_active_positive_speed_target_warn` 作为方向性指标，目前始终 `passed=false` — 合理的 aspirational check

**known_limitations 扩展**:
- 新增 `candidate_active_speed` 和 `ann_active_speed` 字段（line 205-206），记录实际值供趋势分析

### 3.2 `test_stage2_guardrail.py` — None 路径（更新 83→97 行）

新增 `test_supports_missing_candidate_benchmark_payload` (line 81-92):
- candidate_benchmark=None + allow_known_fast_loss=True
- 验证 `passed=true`
- 验证 `candidate_benchmark_active_quality` 不在 check_names 中
- 验证 `candidate_active_speed_regression_warn` 不在 check_names 中（隐式验证，因 None 分支跳过了整个 candidate_benchmark 块）

**评价**: 覆盖正确。但该测试未验证 speed warning 计数的变化（None 路径比完整路径少 1 个 speed warning check），这是一个可改进的断言。

### 3.3 `build_patent_evidence_pack.py` — DF-06 叙述修正

Line 288 变更:
```
旧: "当前版本 active 场景存在负加速，且 candidate 仍有有损风险。"
新: "默认 Candidate 档位已验证零损失；active 场景总体仍偏负加速，实验档 candidate/ANN 仍需风险披露。"
```

**评价**: 准确反映了 R-023~R-025 的验证结论。措辞平衡——既强调默认档的零损失保障，又保持了对实验档的风险披露。

新增 guardrail 速度指标到 DF-06 key_metrics (lines 325-329):
- `stage2_guardrail_ann_active_not_positive_speedup`
- `stage2_guardrail_candidate_active_speed`
- `stage2_guardrail_ann_active_speed`

### 3.4 `.github/workflows/stage2-quality-gate.yml` — CI 工作流（新增 60 行）

**架构**:
- 触发条件: PR / push main / 手动触发 — 完整覆盖
- Python 3.11 + pip install requirements.txt
- 四步流水线: compile check → unit tests → guardrail bundle → artifact upload

**关键设计**:
- `timeout-minutes: 30` — 充足的 CI 时间预算
- `if: always()` on artifact upload — 即使失败也保留诊断数据
- CI 轻量参数: `--dataset-size 240 --benchmark-fragment-count 120 --runs 1 --warmup-runs 0`

### 3.5 `run_ci_guardrail_bundle.py` — CI 自包含 Bundle（新增 236 行）

**核心流程**:
1. 内部生成 semi-real 数据集（`_write_semi_real_dataset`）— 自包含，不依赖外部大数据集
2. 依次运行 5 个 benchmark + 1 个 guardrail
3. 读取 guardrail 结果并返回退出码

**`_write_semi_real_dataset` 设计** (line 26-72):
- 4 agents × 5 tasks × 4 modes × 4 alphas 的组合空间
- profile="realistic" 生成正常文本，profile="stress" 生成冲突重放模式
- `max(80, fragment_count)` 确保最低样本量
- 确定性随机（`Random(seed)`）

**CI bundle 测试** (`test_ci_guardrail_bundle_unit.py`, 36 行):
- `test_write_semi_real_dataset_generates_valid_jsonl`: 验证 JSONL 格式 + 行数 + 字段完整性
- `test_write_semi_real_dataset_enforces_minimum_count`: 验证最低 80 行保障

---

## 4. 独立验证结果

### 4.1 测试套件
- **71/71 通过** (4.573s)
- 较 R-028 增加 3 个测试（68→71）:
  - test_stage2_guardrail: +1 (None 路径)
  - test_ci_guardrail_bundle_unit: +2 (数据生成)

### 4.2 门禁独立验证

**默认模式**:
- `passed=true`, 12/12 checks (11 pass + 1 warning fail)
- `blocker_failures=0`, `warning_failures=1`
- Warning: `ann_active_positive_speed_target_warn` (ANN 仍无正加速)
- `candidate_active_speed=0.046391` (轻微正加速!)
- `ann_active_speed=-0.09661` (仍为负)

**严格模式** (`--strict-fast-profile`):
- `passed=false`, exit=2
- `blocker_failures=1`: `candidate_fast_n240_known_loss`

### 4.3 证据包一致性
- `validation.passed=true`
- `missing_claim_refs=[]`
- `missing_evidence_files=[]`
- `missing_metrics=[]`

### 4.4 编译检查
- `python -m compileall -q src scripts tests` — 无错误

---

## 5. 本轮新发现

### P1-1 (NEW, 重要): CI Bundle 覆写全量 Benchmark 输出

`run_ci_guardrail_bundle.py` 将 CI 轻量级数据写入与全量 benchmark 相同的输出路径:
- `outputs/candidate_filter_benchmark.json`
- `outputs/candidate_profile_validation_synthetic_active.json`
- `outputs/candidate_profile_validation_realistic.json`
- `outputs/candidate_profile_validation_stress.json`
- `outputs/ann_hybrid_benchmark.json`
- `outputs/stage2_guardrail.json`

**风险**: 本地运行 CI bundle 后，全量 benchmark 数据被 CI 轻量数据覆写。后续重建 evidence pack 将基于 N=120/240, runs=1 的数据，而非完整验证数据 (N=240~5000, runs=2~10)。

**当前实际影响**: `stage2_guardrail.json` 已被覆写——其 `generated_at` (02:50:20) 晚于 `stage2_guardrail_report.md` (02:47:40)，且两者数值不一致:
- 报告: `candidate_active_speed=-0.018025`, `ann_active_speed=-0.168449`
- JSON: `candidate_active_speed=0.046391`, `ann_active_speed=-0.09661`

**建议修复**:
```python
# 方案 A: CI bundle 使用独立输出命名空间
outputs_dir = outputs / "ci_outputs"
# 方案 B: CI bundle 运行后自动恢复原始文件
# 方案 C: CI guardrail 仅读取 ci_outputs 子目录
```

### P2-1 (NEW): 报告/JSON 时间戳不一致

直接后果是 P1-1。`docs/eval/stage2_guardrail_report.md` 基于全量数据生成（02:47:40），`outputs/stage2_guardrail.json` 被 CI bundle 覆写为轻量数据（02:50:20）。两者描述的不是同一次运行。

### P3-1 (Observation): FINAL_REPORT 编码问题

FINAL_REPORT.md 在 raw 模式下中文内容显示为 mojibake（UTF-8 BOM 相关）。这是预存问题，非本轮引入。

### P3-2 (Observation): next_phase_plan.md 格式

Line 84-85 之间缺少空行分隔 R-028 和 R-029 section header。

### P3-3 (Observation): _active_candidate_summary 防御性包装

`run_stage2_guardrail.py` line 44: `return dict(scenario.get("summary") or {})` 中 `dict()` 是冗余包装（`.get()` 已返回 dict）。不影响正确性。

---

## 6. 文档一致性

| 文档 | 状态 | 备注 |
|---|---|---|
| FINAL_REPORT.md | ✓ 测试数已更新 | 71/71 ✓, R-029/R-030 Delta ✓ |
| next_phase_plan.md | ✓ | R-029/R-030/R-030b Plan Updates ✓ |
| stage2_guardrail_report.md | ⚠️ 与 JSON 不同步 | 报告=全量数据, JSON=CI 数据 |
| stage2_guardrail.json | ⚠️ 被 CI 覆写 | 见 P1-1 |
| patent_evidence_pack.json | ✓ | validation.passed=true |

---

## 7. 测试覆盖分析

| 测试文件 | 测试数 | 变更 | 覆盖质量 |
|---|---|---|---|
| test_stage2_guardrail.py | 4 | **+1** (None 路径) | 好，缺 speed check 计数断言 |
| test_ci_guardrail_bundle_unit.py | 2 | **新增** | 数据生成基本覆盖 |
| test_embed_eval_unit.py | 5 | 未变 | — |
| test_store_reliability.py | 8 | 未变 | — |
| 其余测试 | 52 | 未变 | — |
| **总计** | **71** | +3 | |

---

## 8. 总体评级：A-

### 评级理由

| 维度 | 评分 | 说明 |
|---|---|---|
| 遗留修复 | A+ | 6/6 R-025 Opus 遗留全部处理，达标率 100% |
| 正确性 | A | 速度门禁逻辑正确，CI 流水线可用 |
| 工程价值 | A | CI 集成填补了发布流水线的关键缺口 |
| 风险控制 | B | CI 输出覆写全量数据是隐蔽但高影响的缺陷 |
| 文档同步 | B+ | 报告/JSON 不一致是 P1-1 的直接后果 |
| 测试覆盖 | A- | CI bundle 有单测，但 speed check 路径缺少计数断言 |

**与前轮比较**: R-025 Opus (A-) 时 6 项遗留待处理，本轮全部解决且额外完成了 CI 集成。工程价值高于上轮。但 P1-1 (CI 覆写) 是新引入的风险，平衡后维持 A-。

### 评审轨迹
B → B- → B+ → A- → A → A- → A- → **A-** （八轮评审，高位稳定）

---

## 9. 下一步建议

### P1: CI Bundle 输出路径隔离（优先修复）
- CI bundle 的所有 benchmark 输出应写入 `outputs/ci_outputs/` 或使用 `ci_` 前缀
- Guardrail 在 CI 模式下应从 CI 输出目录读取
- 这能同时解决 P1-1 和 P2-1

### P2: CI Bundle 集成测试
- 当前仅有数据生成的单元测试
- 建议增加一个 dry-run / mock 模式的集成测试，验证 bundle 完整流程

### P3: speed check 路径断言完善
- `test_supports_missing_candidate_benchmark_payload` 应额外断言 `check_count` 少于完整路径

### P3: 文档微调
- next_phase_plan.md 各 section 之间增加空行
- 考虑修复 FINAL_REPORT.md 的编码问题

---

## 附录：独立验证记录

| 验证项 | 结果 |
|---|---|
| 测试套件 71/71 | PASS (4.573s) |
| 编译检查 | PASS |
| 门禁默认模式 | passed=true, 12 checks, warning=1 |
| 门禁严格模式 | passed=false, exit=2, blocker=fast_n240 |
| 证据包 validation | passed=true, missing=[] |
| 临时文件清理 | 确认 tmp_r02*.py 已全部删除 |

### Candidate 速度正向信号
本轮 `candidate_active_speed=0.046391` — Candidate 默认档在 active 场景首次出现轻微正加速。这是一个积极信号，但由于 CI bundle 覆写了全量数据，需要用全量 benchmark 独立确认后方可作为正式结论。
