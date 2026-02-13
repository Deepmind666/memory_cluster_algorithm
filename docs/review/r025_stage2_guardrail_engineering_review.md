# R-025 Opus 评审：Stage-2 工程稳健性收口（门禁 + 细粒度测试 + 证据链升级）

- **评审人**: Claude Opus 4.6
- **时间戳**: 2026-02-12 20:45:00 +08:00
- **评审对象**: R-028 Codex（Stage-2 fail-fast 门禁 + embed/eval/store 细粒度测试 + 证据链同步）
- **前序评审**: R-024 Opus (A-)
- **总体评级**: **A-**

---

## 1. 评审范围

| 文件 | 变更类型 | 审查深度 |
|---|---|---|
| `scripts/run_stage2_guardrail.py` | **新增** | 逐行 |
| `tests/test_stage2_guardrail.py` | **新增** | 逐行 |
| `tests/test_embed_eval_unit.py` | **新增** | 逐行 |
| `tests/test_store_reliability.py` | **更新** | 逐行 |
| `scripts/build_patent_evidence_pack.py` | 更新 | 逐行（DF-06 + CMD 变更） |
| `outputs/stage2_guardrail.json` | 新增产出 | 交叉验证 |
| `docs/eval/stage2_guardrail_report.md` | 新增报告 | 全量 |
| `outputs/patent_evidence_pack.json` | 重建 | 关键字段验证 |
| `docs/FINAL_REPORT.md` | 更新 | 全量 |
| `docs/design/next_phase_plan.md` | 更新 | 全量 |

---

## 2. R-024 Opus 遗留问题处理状态

| ID | 描述 | 级别 | 本轮状态 |
|---|---|---|---|
| P2-1 | cluster-entry max_bucket=0.5106 偏高 | P2 | 未变（ANN 可选实施例，不处理） |
| P3-1 | DF-06 technical_effect "candidate 仍有有损风险" 描述滞后 | P3 | **未修** — 见下文 |
| P3-2 | ann_skip 运行间波动 | P3 | 未处理（观察性质） |
| P3-temp | 临时文件清理 | P3 | 未处理 |

---

## 3. 代码审查

### 3.1 `run_stage2_guardrail.py` — 门禁脚本（新增 253 行）

**架构设计**: 纯聚合层脚本，不运行任何 benchmark，仅读取已有 JSON 产出物并做 blocker/warning 分级判定。设计合理——关注点分离，门禁与实验互不耦合。

**9 项检查清单**:

| # | 检查名 | 严重性 | 目的 |
|---|---|---|---|
| 1 | candidate_default_quality_synthetic | blocker | r=4 synthetic 全量质量门 |
| 2 | candidate_default_quality_realistic | blocker | r=4 realistic 全量质量门 |
| 3 | candidate_default_quality_stress | blocker | r=4 stress 全量质量门 |
| 4 | candidate_default_n240_synthetic | blocker | r=4 synthetic N=240 专项 |
| 5 | candidate_fast_n240_known_loss | warning/blocker | r=3 已知有损（模式可切） |
| 6 | ann_runtime_signature_gate | blocker | ANN 运行时签名门 |
| 7 | ann_active_quality_ann_prune | blocker | ANN active 质量门 |
| 8 | ann_active_quality_hybrid_prune | blocker | hybrid active 质量门 |
| 9 | candidate_benchmark_active_quality | blocker | candidate benchmark 质量门 |

**关键设计亮点**:
- `allow_known_fast_loss` 参数：默认宽容（r=3 有损为 warning），`--strict-fast-profile` 可升级为 blocker。这是正确的已知限制管理方式。
- 退出码设计：passed → 0，任何 blocker failure → 2。可直接集成 CI。
- `_find_row()` 按 fragment_count 查找，`_active_ann_comparison()` 按 scenario name 查找，鲁棒地处理嵌套 JSON 结构。

**P3 观察**:
- 检查项 #4（`candidate_default_n240_synthetic`）与 #1（`candidate_default_quality_synthetic`）有部分冗余——如果 #1 的 `default_all_quality_gate_pass` 为 true，则 #4 必然为 true。但 #4 提供了更细粒度的诊断信息（指定 N=240），保留是合理的。

### 3.2 `test_stage2_guardrail.py` — 门禁测试（新增 83 行）

3 个测试覆盖核心路径：
1. `test_passes_with_known_fast_loss_allowed`: 默认宽容模式，r=3 有损被接受
2. `test_fails_when_default_quality_breaks`: r=4 质量门失败 → passed=false
3. `test_strict_mode_blocks_known_fast_loss`: 严格模式 r=3 有损 → blocker

**评价**: 测试用 mock payload 构造器（`_candidate_payload` / `_ann_payload`）设计清晰，覆盖了 happy/sad/strict 三路径。缺少的边界情况见下文。

### 3.3 `test_embed_eval_unit.py` — 嵌入/评估细粒度测试（新增 92 行）

5 个测试覆盖：
1. `test_tokenize_keeps_cjk_ascii_and_underscore`: CJK + ASCII + 下划线分词
2. `test_cosine_similarity_handles_zero_and_length_mismatch`: 零向量 + 长度不匹配
3. `test_hash_embedding_is_deterministic_and_l2_normalized`: 确定性 + L2 归一化
4. `test_compute_metrics_prefers_l1_clusters_for_summary_fields`: L1/L2 分层指标
5. `test_compute_metrics_falls_back_to_all_clusters_when_no_l1`: 无 L1 时回退

**评价**: 这些测试补齐了 `embed.py` 和 `eval.py` 长期缺失的单元测试，特别是 L1/L2 分层行为和边界条件。`cosine_similarity` 的零向量和长度不匹配测试是重要的防御性覆盖。

### 3.4 `test_store_reliability.py` — 存储可靠性测试（更新至 149 行）

8 个测试覆盖：
- 幂等追加（同 ID/同版本跳过、新版本允许、批内去重）
- 损坏行容错（非严格跳过、严格抛异常）
- UTF-8 BOM 兼容
- `load_latest_by_id_with_stats` 统计传播

**评价**: 这是一套有实际价值的存储层测试。幂等性测试（同版本跳过、版本升级、批内去重）覆盖了生产环境中最常见的数据完整性场景。BOM 兼容测试体现了对 Windows 环境的正确关注。

### 3.5 `build_patent_evidence_pack.py` — 证据包构建器更新

关键变更：
- 新增 `CMD_STAGE2_GUARDRAIL` 到 COMMAND_CATALOG（line 26）
- DF-06 `key_metrics` 新增 4 个 stage2_guardrail 字段（lines 319-324）
- DF-06 `evidence_files` 新增 `outputs/stage2_guardrail.json`（line 331）
- DF-06 `command_ids` 新增 `CMD_STAGE2_GUARDRAIL`（line 346）

**评价**: 集成完整，门禁结果已正确链接到证据包。

---

## 4. 独立验证结果

### 4.1 测试套件
- **68/68 通过** (4.101s)
- 较 R-026 增加 10 个测试（58→68）

### 4.2 门禁脚本独立运行

**默认模式**:
- `passed=true`, 9/9 checks OK
- `known_limitations.fast_profile_loss_at_synthetic_n240=true`
- 与 `outputs/stage2_guardrail.json` 产出一致

**严格模式** (`--strict-fast-profile`):
- `passed=false`, `blocker_failures=1`
- 失败项: `candidate_fast_n240_known_loss` (severity=blocker)
- 退出码: **2** ✓

### 4.3 证据包一致性
- `validation.passed=true`
- `missing_claim_refs=[]`
- `missing_evidence_files=[]`
- `missing_metrics=[]`
- DF-06 stage2_guardrail 字段: `passed=true`, `blocker_failures=0`

---

## 5. 本轮新发现

### P3-1 (承继，未修): DF-06 `technical_effect` 描述仍为 "candidate 仍有有损风险"

[build_patent_evidence_pack.py:288](scripts/build_patent_evidence_pack.py#L288):
```python
"technical_effect": "当前版本 active 场景存在负加速，且 candidate 仍有有损风险。",
```

R-025/R-023 已确认 candidate 默认档 (r=4) **零损失**。此描述对专利审查可能造成不必要的负面印象。建议改为：
> "Candidate 默认档 (r=4) 零损失保障；高性能实验档 (r=3) 存在轻微有损风险。ANN active 场景存在负加速。"

### P3-2 (新): 门禁缺少 Candidate 速度回归告警

当前 9 项检查全部聚焦**质量门**（cluster_count_equal / merges_applied_equal / signature_gate），没有速度相关检查。如果某次代码变更导致 Candidate 默认档速度从 -13% 恶化到 -50%，门禁不会报警。

建议新增：
```python
_check(
    name="candidate_default_speed_regression",
    passed=float(speedup) >= -0.30,  # 30% 负加速上限
    severity="warning",
    detail="Candidate default speed should not regress beyond -30%.",
)
```

### P3-3 (新): test_stage2_guardrail 缺少 `candidate_benchmark=None` 路径测试

`evaluate_guardrails` 接受 `candidate_benchmark=None`，`run_stage2_guardrail.py` 有 `--allow-missing-candidate-benchmark` 选项。但测试中所有 3 个用例都传入了非 None 的 `candidate_benchmark`。建议补一个 None 路径测试。

### P3-4 (观察): FINAL_REPORT.md 测试数仍写 58/58

[FINAL_REPORT.md:12](docs/FINAL_REPORT.md#L12) 写 `58/58 通过`，实际已是 68/68。这是因为 FINAL_REPORT 在 R-026 时写就，R-028 的新增测试未同步回该文档。

---

## 6. 文档一致性

| 文档 | 状态 | 备注 |
|---|---|---|
| FINAL_REPORT.md | ⚠️ 测试数滞后 | 写 58/58，实际 68/68 |
| next_phase_plan.md | ✓ | R-028 Plan Update 正确记录了门禁完成 |
| stage2_guardrail_report.md | ✓ | 与 JSON 一致 |
| patent_evidence_pack.json | ✓ | validation.passed=true |

---

## 7. 测试覆盖分析

| 测试文件 | 测试数 | 变更 | 覆盖质量 |
|---|---|---|---|
| test_stage2_guardrail.py | 3 | **新增** | 核心路径覆盖，缺 None 边界 |
| test_embed_eval_unit.py | 5 | **新增** | embed + eval 细粒度，好 |
| test_store_reliability.py | 8 | **更新** | store 幂等 + 容错，好 |
| 其余测试 | 52 | 未变 | — |
| **总计** | **68** | +10 | |

---

## 8. 总体评级：A-

### 评级理由

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | A | 门禁逻辑正确，默认/严格双模式验证通过 |
| 完整性 | A | 代码+测试+产出+证据包+文档全链条更新 |
| 工程价值 | A | fail-fast 门禁填补了关键 CI 缺口，细粒度测试覆盖长期盲区 |
| 文档同步 | B+ | FINAL_REPORT 测试数滞后，DF-06 描述仍有偏差 |
| 独创性 | B+ | 门禁设计合理但属于标准工程实践 |

**与前轮比较**: R-026 (A-) 是单点修复，R-028 范围更广（门禁+测试+证据链），工程价值更高。但同样有文档细节未完全同步，维持 A-。

### 评审轨迹
B → B- → B+ → A- → A → A- → **A-** （七轮评审，高位稳定）

---

## 9. 下一步建议

### P1: FINAL_REPORT 测试数同步
- 将 `58/58` 更新为 `68/68`
- 同步记录门禁脚本到自查命令列表

### P2: DF-06 `technical_effect` 修正
- 体现 "candidate 默认零损失" 这一已确认结论

### P2: 门禁速度回归告警
- 新增 Candidate/ANN 速度退化 warning 检查
- 阈值建议: Candidate default ≥ -30%, ANN active ≥ -50%

### P2: ANN 冻结决策
- 仍无正加速证据，建议正式冻结为"仅可选实施例"
- 在 next_phase_plan 中标记 "ANN 性能优化投入停止"

### P3: 补充测试
- test_stage2_guardrail: `candidate_benchmark=None` 路径
- test_stage2_guardrail: ANN runtime signature gate failure 路径

### P3: 临时文件清理
- `tmp_r022_verify.py`, `tmp_r023_verify.py`, `tmp_r023_ann_check.py`, `tmp_r024_verify.py`

---

## 附录：独立验证记录

| 验证项 | 结果 |
|---|---|
| 测试套件 68/68 | PASS (4.101s) |
| 门禁默认模式 | passed=true, 9/9 |
| 门禁严格模式 | passed=false, exit=2, blocker=candidate_fast_n240_known_loss |
| 证据包 validation | passed=true, missing=[] |
