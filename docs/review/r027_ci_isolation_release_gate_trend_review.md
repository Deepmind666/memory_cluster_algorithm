# R-027 Opus 评审：R-031~R-035 CI 隔离 + 发版门禁 + 夜间趋势 + 策略强化

- **评审人**: Claude Opus 4.6
- **时间戳**: 2026-02-13 13:10:00 +08:00
- **评审对象**: R-031 Codex（夜间趋势管线）+ R-032 Codex（发版门禁）+ R-033 Codex（CI 输出路径隔离修复）+ R-034 Codex（CI 隔离策略自动守卫）+ R-035 Codex（评审清单门禁升级 v2.1）
- **前序评审**: R-026 Opus (A-)
- **总体评级**: **A**

---

## 1. 评审范围

本次评审覆盖 R-031 至 R-035 共 5 个连续提交轮次。这是 R-026 Opus 以来的第一次 Opus 评审。

| 文件 | 变更类型 | 来源轮次 | 审查深度 |
|---|---|---|---|
| `scripts/update_guardrail_trend.py` | **新增** | R-031 | 逐行 |
| `tests/test_guardrail_trend_unit.py` | **新增** | R-031 | 逐行 |
| `.github/workflows/stage2-nightly-trend.yml` | **新增** | R-031 | 逐行 |
| `scripts/check_stage2_gate_for_sha.py` | **新增** | R-032 | 逐行 |
| `tests/test_check_stage2_gate_for_sha_unit.py` | **新增** | R-032 | 逐行 |
| `.github/workflows/release-with-stage2-gate.yml` | **新增** | R-032 | 逐行 |
| `scripts/run_ci_guardrail_bundle.py` | **重构** | R-033 | 逐行 |
| `tests/test_ci_guardrail_bundle_unit.py` | **更新** | R-033 | 逐行 |
| `.github/workflows/stage2-quality-gate.yml` | **更新** | R-033/R-034 | 逐行 |
| `scripts/check_ci_output_isolation.py` | **新增** | R-034 | 逐行 |
| `tests/test_ci_output_isolation_unit.py` | **新增** | R-034 | 逐行 |
| `docs/REVIEW_CHECKLIST.md` | **更新** v2.0→v2.1 | R-035 | 全量 |
| `docs/FINAL_REPORT.md` | **更新** | R-031~R-035 | 全量 |
| `docs/design/next_phase_plan.md` | **更新** | R-031~R-035 | 全量 |
| `WORK_PROGRESS.md` | **更新** | R-031~R-035 | 尾部 |
| `README.md` | **更新** | R-031~R-034 | 全量 |

---

## 2. R-026 Opus 遗留问题处理状态

| ID | 描述 | 级别 | 本轮状态 |
|---|---|---|---|
| P1-1 | CI Bundle 覆写全量 Benchmark 输出 | P1 | **已修** (R-033) — `_build_bundle_commands()` 重构，全部 CI JSON 输出到 `outputs/ci_outputs/` |
| P2-1 | 报告/JSON 时间戳不一致 | P2 | **已修** — P1-1 修复后自动解决。独立验证 JSON 与报告 `generated_at` 完全一致 |
| P2-2 | CI Bundle 集成测试 | P2 | **部分** — 新增路径隔离断言 (R-033) + 策略守卫 (R-034)；无 dry-run/mock 集成测试 |
| P3-1 | speed check 路径断言完善 | P3 | **未处理** — 不影响功能 |
| P3-2 | next_phase_plan 格式修复 | P3 | **未处理** — next_phase_plan 各 section 之间仍缺少空行（部分） |

**P1 全部关闭。P2 基本处理。P3 自行判断。**

---

## 3. 代码审查

### 3.1 `scripts/run_ci_guardrail_bundle.py` — 输出路径隔离重构 (R-033)

**关键变更**: 新增 `_build_bundle_commands()` 函数（line 75-205），将 6 条命令的构建逻辑从 `main()` 中提取出来，接受 `ci_outputs` 和 `ci_reports` 参数。

**设计亮点**:
- 路径全部由 `ci_outputs / "xxx.json"` 生成，从根源杜绝覆写
- `_build_bundle_commands()` 是纯函数（无副作用），可供 `check_ci_output_isolation.py` 直接复用作静态分析
- `main()` 中 `stage2_guardrail_path = ci_outputs / "stage2_guardrail.json"` (line 250) 与命令构建中的路径一致

**评价**: 这是正确的修复方案。命令构建与执行分离，使静态验证成为可能。**A**

### 3.2 `scripts/check_ci_output_isolation.py` — 策略自动守卫 (R-034, 152 行)

**核心设计**:
- `validate_bundle_commands()`: 从 `_build_bundle_commands()` 获取命令列表，检查所有 `--output` 类参数是否指向 `outputs/ci_outputs/`
- `validate_workflow_text()`: 用正则扫描 workflow 文本，检查是否包含禁止路径 + 必需路径
- `_FORBIDDEN_ROOT_JSON_PATHS`: 明确列出 6 个禁写根路径
- `_REQUIRED_WORKFLOW_PATHS`: 按 workflow 列出必须存在的 CI 路径引用
- `main()`: 综合两类检查，输出 JSON + 退出码

**设计亮点**:
- **复用 `_build_bundle_commands()`** (line 101) — 与 CI bundle 脚本共享同一个命令构建逻辑，不是 hardcode 的重复检查
- **双层防护**: 既检查命令参数（运行时路径），又检查 workflow 文本（声明式路径）
- **扩展性好**: 新增 workflow 或禁止路径只需修改字典

**改进观察**:
- `_extract_output_paths` (line 57) 的 `str(command[next_idx]).replace("\\", "/")` — 对 Windows 路径做了归一化处理，合理
- workflow 正则 `r"outputs/[A-Za-z0-9_./-]+\.json"` (line 79) — 能匹配常规 JSON 路径，但如果路径中有空格或特殊字符会漏匹配。当前项目路径命名均为 ASCII，可接受

**评价**: 超出预期。从被动修复（R-033）升级为主动防护（R-034），体现了 defense-in-depth 理念。**A+**

### 3.3 `scripts/check_stage2_gate_for_sha.py` — 发版前门禁检查 (R-032, 158 行)

**核心功能**: 查询 GitHub API，验证目标 SHA 在指定时间窗口内有成功的 `stage2-quality-gate` 运行。

**实现质量**:
- `_iso_to_utc()`: 处理 `Z` 后缀 + `fromisoformat()` + naive→aware 转换 — 防御性充分
- `select_successful_run()`: SHA 过滤 → conclusion=success → 按时间排序 → 年龄检查 — 逻辑清晰
- `evaluate_gate()`: 封装选择逻辑，返回结构化结果 (passed/reason/selected_run)
- `_build_runs_url()`: 正确使用 `urllib.parse.quote` 编码 workflow 文件名和 SHA
- `_request_json()`: 标准 GitHub API 请求，使用 Bearer token + API 版本头

**安全观察**:
- Token 从环境变量读取，不接受命令行参数 — 正确的安全实践
- `urllib.request.urlopen(req, timeout=20)` — 有超时保护
- `nosec B310` 注释说明已知安全风险 — 可接受

**评价**: 功能完整，逻辑正确，安全意识到位。**A**

### 3.4 `scripts/update_guardrail_trend.py` — 趋势追踪 (R-031, 127 行)

**设计**:
- `build_trend_record()`: 从 guardrail payload 中提取 summary + known_limitations + failed_check_names
- `update_trend_payload()`: 追加记录 → 保留窗口裁剪 → 计算聚合指标（pass_rate, blocker_failure_rate, speed 均值等）
- `_avg_nonnull()`: 安全的 None 值过滤均值计算

**评价**: 简洁实用。趋势数据结构设计合理，便于可视化和告警。**A-**

### 3.5 Workflow 文件

#### `.github/workflows/stage2-nightly-trend.yml` (R-031, 67 行)
- 触发: `cron 0 2 * * *` + 手动
- 步骤: checkout → python → deps → **isolation check** → compile → tests → CI bundle (runs=3) → update trend → upload
- **亮点**: nightly 使用 `runs=3, warmup=1`（比 CI 的 `runs=1` 更稳定），正确的策略分层

#### `.github/workflows/release-with-stage2-gate.yml` (R-032, 124 行)
- 触发: `workflow_dispatch` 仅手动
- 参数: tag_name (必填), target_sha, release_title, prerelease, generate_notes
- 步骤: checkout(depth=0) → python → resolve SHA → verify gate → upload artifact → create tag → create release
- **亮点**: tag 重复检测（local + remote）、`set -euo pipefail` 安全模式、`permissions` 最小权限

#### `.github/workflows/stage2-quality-gate.yml` (更新)
- 新增: `Validate CI Output Isolation` 步骤在 compile/tests 之前
- Artifact 列表: 新增 `output_isolation_check.json`
- 所有 artifact 路径已切换至 `outputs/ci_outputs/` + `outputs/ci_reports/`

**评价**: 三个 workflow 形成完整的 CI/CD 安全链：PR 门禁 → 夜间趋势 → 发版关卡。**A**

### 3.6 测试文件

| 测试文件 | 测试数 | 变更 | 覆盖质量 |
|---|---|---|---|
| `test_guardrail_trend_unit.py` | 3 | **新增** (R-031) | 记录提取 + 保留窗口 + roundtrip |
| `test_check_stage2_gate_for_sha_unit.py` | 5 | **新增** (R-032) | ISO 解析 + 选择最新 + 过期失败 + 通过 + URL 编码 |
| `test_ci_guardrail_bundle_unit.py` | 3 | **+1** (R-033) | 路径隔离断言（全量命令验证） |
| `test_ci_output_isolation_unit.py` | 4 | **新增** (R-034) | bundle 通过/失败 + workflow 通过/失败 |
| 其余 | 69 | 未变 | — |
| **总计** | **84** | **+13** (从 71) | |

**评价**: 测试覆盖充分，正反用例兼备。特别值得肯定的是 `test_build_bundle_commands_isolates_ci_outputs` (R-033) 对全部 6 条命令的输出路径进行了逐一验证。

---

## 4. 独立验证结果

### 4.1 测试套件
- **84/84 通过** (5.451s)
- 较 R-026 Opus (71/71) 增加 13 个测试

### 4.2 编译检查
- `python -m compileall -q src scripts tests` — 无错误

### 4.3 CI 输出隔离验证
- `check_ci_output_isolation.py`: **passed=true, violation_count=0**
- 检查范围: `stage2-quality-gate.yml` + `stage2-nightly-trend.yml`

### 4.4 门禁独立验证
- `passed=true`, 12/12 checks (11 pass + 1 warning fail)
- `blocker_failures=0`, `warning_failures=1`
- Warning: `ann_active_positive_speed_target_warn` (ANN 仍无正加速)
- `candidate_active_speed=0.046391` (轻微正加速)
- `ann_active_speed=-0.09661` (仍为负)
- **`stage2_guardrail.json` 与 `stage2_guardrail_report.md` generated_at 时间戳完全一致** ← R-026 P2-1 已修复

### 4.5 证据包一致性
- `validation.passed=true`
- `missing_claim_refs=[]`
- `missing_evidence_files=[]`
- `missing_metrics=[]`

### 4.6 临时文件
- 无 `tmp_*.py` 文件残留

---

## 5. 本轮新发现

### P2-1 (NEW): FINAL_REPORT R-delta 排列顺序错误

`docs/FINAL_REPORT.md` 中 R-031~R-035 的排列顺序为：

```
R-031 → R-034 → R-035 → R-033 → R-032
```

正确顺序应为：

```
R-031 → R-032 → R-033 → R-034 → R-035
```

`next_phase_plan.md` 中的 Plan Update 排列顺序是正确的。WORK_PROGRESS 中的条目时间戳也是正确的（R-031 11:44 → R-032 12:05 → R-033 12:28 → R-034 12:38 → R-035 12:56）。

**影响**: 阅读 FINAL_REPORT 历史记录时造成混乱，但不影响技术正确性。

### P2-2 (NEW): FINAL_REPORT R-031 Delta 测试计数不一致

R-031 Delta 声称 "Current total tests: `84/84`"，但交叉验证表明：
- WORK_PROGRESS R-031 Entry: `74/74`
- next_phase_plan R-031 Plan Update: "Test baseline now `74/74`"

实际测试计数演变：
| 轮次 | 新增测试 | 累计 |
|---|---|---|
| R-030b | — | 71 |
| R-031 | +3 (trend unit) | **74** |
| R-032 | +5 (gate sha unit) | **79** |
| R-033 | +1 (bundle path isolation) | **80** |
| R-034 | +4 (isolation unit) | **84** |
| R-035 | 0 | **84** |

R-031 Delta 中的 `84/84` 是被后续轮次的编辑覆写或误写。FINAL_REPORT §2 当前显示 `84/84` 是正确的（全局最新值）。

**建议**: R-031 Delta 应修正为 `74/74`，或标注其为全局最新值而非 R-031 时点值。

### P3-1 (Observation): .claude.md 清单版本引用滞后

Line 42 引用 `(v2.0)` 但 `docs/REVIEW_CHECKLIST.md` 已升级至 `v2.1` (R-035)。

### P3-2 (Observation): R-032 WORK_PROGRESS 缺少全量测试计数

R-032 Entry (line 2148) 的 unittest 验证只写了 "PASS"，未标注具体测试数。其他所有 Entry 均标注了 `XX/XX` 计数。

### P3-3 (Self-Note): codex_execution_prompt.md §5 快照滞后

`docs/design/codex_execution_prompt.md` §5 仍显示 "测试: 74/74"。该文件由 Opus 评审人维护（非 Codex 职责），将在本轮评审后自行更新。

---

## 6. 文档一致性

| 文档 | 状态 | 备注 |
|---|---|---|
| FINAL_REPORT §2 测试数 | ✓ 84/84 | 与实际一致 |
| FINAL_REPORT R-delta 顺序 | ⚠️ 乱序 | 见 P2-1 |
| FINAL_REPORT R-031 Delta 测试数 | ⚠️ 84≠74 | 见 P2-2 |
| next_phase_plan R-031~R-035 | ✓ | 顺序正确，测试数正确 |
| WORK_PROGRESS R-031~R-035 | ✓ | 时间戳正确，内容完整 |
| stage2_guardrail JSON/报告 | ✓ | 同一次运行，时间戳一致 |
| patent_evidence_pack.json | ✓ | validation.passed=true |
| .claude.md 清单版本 | ⚠️ v2.0→v2.1 | 见 P3-1 |
| README.md | ✓ | CI 命令与输出路径已更新 |
| REVIEW_CHECKLIST v2.1 | ✓ | F 区隔离条款完整 |

---

## 7. 专利证据链完整性评估

### 7.1 核心主张（CEG / ARB / DMG / 语义精度）

| 主张 | 证据状态 | 说明 |
|---|---|---|
| DF-01 CEG | ✓ 证据充分 | 6 项 benchmark 输出均在 `outputs/` 根目录（全量数据） |
| DF-02 ARB | ✓ 证据充分 | 同上 |
| DF-03 DMG | ✓ 证据充分 | 同上 |
| DF-04 语义精度 | ✓ 证据充分 | `semantic_regression_metrics.json` 8/8 case pass |

### 7.2 可选主张（Prune / Candidate / ANN）

| 主张 | 证据状态 | 说明 |
|---|---|---|
| DF-05 Prune | ✓ 可选实施例 | `prune_benchmark.json` 有数据支撑 |
| DF-06 Candidate/ANN | ✓ 可选实验 | DF-06 叙述准确反映零损失 + 实验风险 |

### 7.3 门禁/证据链安全

- **CI/全量数据隔离**: ✓ 自动策略守卫已就位 (`check_ci_output_isolation.py`)
- **证据包始终从 `outputs/` 根目录读取**: ✓ `build_patent_evidence_pack.py` 未被修改，路径不变
- **门禁 JSON/报告同步**: ✓ `generated_at` 时间戳一致
- **锁定决策未被违反**: ✓ 无参数漂移、无 ANN 提升、无 Candidate 默认变更

**结论**: 专利证据链完整性在本轮得到显著加强。CI 输出隔离从文档规范升级为自动化执行，消除了 R-026 Opus 发现的数据覆写风险。

---

## 8. 总体评级：A

### 评级理由

| 维度 | 评分 | 说明 |
|---|---|---|
| P1 修复质量 | A+ | CI 隔离不仅修复，还增加了自动策略守卫——defense-in-depth |
| 正确性 | A+ | 84/84 测试通过，全部门禁绿灯，零 blocker |
| 工程价值 | A | 三管齐下：发版门禁 + 夜间趋势 + CI 策略守卫——CI/CD 安全链完整 |
| 测试覆盖 | A | +13 新测试，正反用例兼备，路径隔离回归保护 |
| 文档同步 | B+ | FINAL_REPORT R-delta 顺序与测试数有误，.claude.md 版本引用滞后 |
| 风险控制 | A+ | 自动化策略守卫在 CI 流水线最前方执行——最有效的 shift-left 实践 |

**与前轮比较**: R-026 Opus (A-) → R-027 Opus (**A**)。本轮不仅完成了 P1 修复，还超出预期地建立了三层防护体系：代码修复 (R-033) → 自动守卫 (R-034) → 流程绑定 (R-035)。这是自 R-023 Opus (A) 以来的最高评级。

### 评审轨迹
B → B- → B+ → A- → A → A- → A- → A- → **A** （九轮评审，重回高点）

---

## 9. 下一步建议

### P2: FINAL_REPORT R-delta 整理
- 将 R-031~R-035 排列为正确的时间顺序
- 修正 R-031 Delta 中的测试计数为 `74/74`（或明确标注为全局最新值）
- 考虑为 R-032 Delta 补充测试计数（`79/79`）

### P3: .claude.md 版本引用更新
- Line 42: `(v2.0)` → `(v2.1)`

### P3: 可选 — CI Bundle 集成测试
- 当前仅有单元级测试（数据生成 + 命令构建 + 路径隔离）
- 可选增加一个 dry-run 模式或 mock 集成测试，验证 6 步流水线的完整串联

### P3: 观察 — ANN 速度趋势
- 本轮 `candidate_active_speed=0.046391` 维持轻微正加速
- 建议在 1-2 周夜间趋势数据积累后，评估是否调整 speed warning floor（从 -0.20 收紧）

### Opus 自行更新
- `docs/design/codex_execution_prompt.md` §5 快照: 测试数 74→84

---

## 附录：独立验证记录

| 验证项 | 结果 |
|---|---|
| 测试套件 84/84 | PASS (5.451s) |
| 编译检查 | PASS |
| CI 输出隔离 | passed=true, violation_count=0 |
| 门禁默认模式 | passed=true, 12 checks, warning=1 |
| 证据包 validation | passed=true, missing=[] |
| JSON/报告时间戳一致性 | ✓ (2026-02-13T05:05:26) |
| 临时文件 | 无残留 |
| 参数漂移检查 | 无漂移 |

### 测试数演变确认

| 轮次 | 新增测试文件/方法 | 累计 |
|---|---|---|
| R-026 Opus 基线 | — | 71 |
| R-031 | test_guardrail_trend_unit (+3) | 74 |
| R-032 | test_check_stage2_gate_for_sha_unit (+5) | 79 |
| R-033 | test_ci_guardrail_bundle_unit (+1 method) | 80 |
| R-034 | test_ci_output_isolation_unit (+4) | 84 |
| R-035 | 无新增 | 84 |
