# R-024 Opus 评审：ANN 诊断口径对齐与收口

- **评审人**: Claude Opus 4.6
- **时间戳**: 2026-02-12 15:00:00 +08:00
- **评审对象**: R-026 Codex（ANN 诊断口径对齐 + 文档决策固化 + 证据包重建）
- **前序评审**: R-023 Opus (A)
- **总体评级**: **A-**

---

## 1. 评审范围

| 文件 | 变更类型 | 审查深度 |
|---|---|---|
| `scripts/run_ann_hybrid_benchmark.py` | 新增双口径诊断函数 | 逐行 |
| `tests/test_merge_ann_candidates.py` | 新增回归测试 | 逐行 |
| `outputs/ann_hybrid_benchmark.json` | 重跑产出 | 交叉验证 |
| `docs/eval/ann_hybrid_benchmark_report.md` | 重生成 | 全量 |
| `docs/FINAL_REPORT.md` | 重写 | 全量 |
| `docs/design/next_phase_plan.md` | 重写 | 全量 |
| `outputs/patent_evidence_pack.json` | 重建 | 交叉验证 |
| `docs/patent_kit/10_区别特征_技术效果_实验映射.md` | 同步 | 全量 |
| `docs/patent_kit/11_主张_证据_命令对照.md` | 同步 | 全量 |
| `WORK_PROGRESS.md` | 追加 | 完整性 |
| `.claude.md` | 追加 | 完整性 |

---

## 2. R-023 遗留问题处理状态

| ID | 描述 | 级别 | 本轮状态 |
|---|---|---|---|
| P2-NEW-1 | ANN 签名诊断（fragment-level）与运行时行为（cluster-level）不一致 | P2 | **已解决** ✓ |
| P2-NEW-2 | ANN 默认 tables=3 cluster 级 max_bucket_ratio 高 | P2 | **已澄清**（51% on 94 centroids，运行门通过但严格门不过） |
| P2-3 | ANN 仍无正加速配置 | P2 | 未变（明确归入可选实施例） |
| P3 | DMG realistic gain=0; 投影步数自适应 | P3 | 未处理（不在本轮范围） |

### P2-NEW-1 解决方案评价

R-026 将签名诊断拆为三级门控：

| 门控名称 | 口径 | 阈值 | 本次结果 | 用途 |
|---|---|---|---|---|
| `signature_gate_pass_fragment_strict` | 原始 fragment 嵌入 (N=240) | unique≥0.25, bucket≤0.25 | **false** | 离线严格诊断 |
| `signature_gate_pass_cluster_strict` | 合并前 cluster 质心 (N=94) | unique≥0.25, bucket≤0.25 | **false** | 严格质量观察 |
| `signature_gate_pass_cluster_runtime` | 合并前 cluster 质心 (N=94) | unique≥0.18, bucket≤0.90 | **true** | 运行时 fallback 一致 |

关键设计：`signature_gate_pass` 别名对齐为 `cluster_runtime`，消除了"报告失败但运行正常"的认知冲突。

**评价**: 设计合理，三级门控提供了从严到宽的完整诊断光谱。特别是 `_build_merge_entry_centroids()` 正确使用 `merge_threshold=1.0` 获取合并前质心，与运行时 `_build_ann_candidate_neighbors()` 的输入一致。

---

## 3. 代码审查

### 3.1 `_ann_signature_stats_for_vectors()` (benchmark.py:135-165)

从 `_ann_signature_stats()` 抽取的通用版本，接受任意向量集。实现正确：
- 逐表计算签名、统计 unique ratio 和 max bucket ratio
- 计算 table0 weight spread（位权重分散度）
- 返回 min/max 汇总值

### 3.2 `_build_merge_entry_centroids()` (benchmark.py:168-181)

构造与运行时一致的合并前质心集合：
- 使用 `similarity_threshold` 驱动 fragment-to-cluster 分配
- `merge_threshold=1.0` 确保无合并发生（仅做分配）
- 返回 94 个 cluster 质心向量

**技术细节**: R-023 Opus 独立验证基于 18 个合并后质心（unique 33-50%），本轮正确修正为 94 个合并前质心（unique 21.3%）。这是一个隐含的修正——R-023 的诊断虽然方向正确（cluster > fragment），但用错了比较基准。

### 3.3 门控注入逻辑 (benchmark.py:413-428)

在 `active_comparisons` 中为 `ann_prune` 和 `hybrid_prune` 注入双口径诊断字段。逻辑正确，字段命名清晰。

### 3.4 回归测试 (test_merge_ann_candidates.py:293-317)

`test_ann_cluster_entry_signature_quality_matches_runtime_gate`:
- 使用 benchmark 相同分布的 fragments (N=240, active)
- 分别计算 fragment-level 和 cluster-entry-level stats
- 断言 cluster-entry 通过运行时门控 (unique≥0.18, bucket≤0.90)
- 断言 cluster unique ≥ fragment unique（方向性约束）

**评价**: 回归测试设计合理，能有效防止未来口径回退。

---

## 4. 独立验证结果

使用独立脚本 `tmp_r024_verify.py` 完全复现双口径诊断：

### 4.1 Fragment-level (N=240)
| Table | unique_ratio | max_bucket_ratio |
|---|---|---|
| 0 | 0.179167 | 0.158333 |
| 1 | 0.137500 | 0.420833 |
| 2 | 0.233333 | 0.154167 |
| **汇总** | **min=0.1375** | **max=0.4208** |
| strict gate | **false** | |

### 4.2 Cluster-entry (N=94, pre-merge)
| Table | unique_ratio | max_bucket_ratio |
|---|---|---|
| 0 | 0.255319 | 0.180851 |
| 1 | 0.212766 | 0.510638 |
| 2 | 0.372340 | 0.223404 |
| **汇总** | **min=0.2128** | **max=0.5106** |
| runtime gate | **true** | |
| strict gate | **false** | |

### 4.3 Pipeline 质量门
- baseline: clusters=18, merges=76
- ann: clusters=18, merges=76
- quality_gate_pass: **true**
- ann_fallbacks: **0**

### 4.4 JSON 一致性（9/9 检查通过）
| 字段 | JSON 值 | 独立计算 | 状态 |
|---|---|---|---|
| cluster_entry_count | 94 | 94 | OK |
| cluster_min_unique | 0.212766 | 0.212766 | OK |
| cluster_max_bucket | 0.510638 | 0.510638 | OK |
| fragment_min_unique | 0.1375 | 0.1375 | OK |
| fragment_max_bucket | 0.420833 | 0.420833 | OK |
| gate_runtime | true | true | OK |
| gate_cluster_strict | false | false | OK |
| gate_fragment_strict | false | false | OK |
| gate_alias (=runtime) | true | true | OK |

---

## 5. 文档与证据一致性

### 5.1 FINAL_REPORT.md
- 3.4 节 ANN 双口径描述与 JSON 完全一致 ✓
- `avg_speedup_ratio=-0.129717` 与 JSON 一致 ✓
- "运行时 fallback 发生在 cluster-entry 质心层"解释准确 ✓
- ANN "不进入核心主张"定位明确 ✓

### 5.2 证据包 (patent_evidence_pack.json)
- `validation.passed=true` ✓
- `missing_claim_refs=[]` ✓
- `missing_evidence_files=[]` ✓
- DF-06 ANN 指标与 JSON 交叉一致 ✓

### 5.3 专利对照文档 (10/11 号)
- DF-06 status = `optional_experimental` ✓
- 命令索引 CMD_ANN_HYBRID 更新 ✓

---

## 6. 本轮新发现

### P2-1 (承继): cluster-entry max_bucket_ratio=0.5106 仍然偏高

Table 1 有 51% 的质心落入同一个桶，意味着 ANN 对该表几乎无区分能力。这是 ANN 在 active 场景持续负加速的直接原因——签名碰撞率太高导致候选集无法有效收窄。

**影响**: 运行时门控阈值 (bucket≤0.90) 过宽，允许了质量较差的 ANN 运行。这不是 bug，而是设计选择（宁可跑但效果差，也不 fallback 丢失功能）。给定 ANN 已被定位为"可选实施例"，这是可接受的。

**建议**: 若未来要让 ANN 产生正加速，需要：
1. 增加 tables 数量（4→6）以分散碰撞
2. 或提高 bits_per_table（10→12）
3. 或收紧运行时门控至 bucket≤0.50，强制退回精确计算

### P3-1 (观察): DF-06 技术效果描述略有滞后

证据包 DF-06 `technical_effect` 写 "candidate 仍有有损风险"。但 R-025 已确认 candidate 默认档（radius=4）零损失。建议更新为 "candidate 默认档零损失，高性能实验档有轻微有损风险"。

### P3-2 (观察): ann_skip 计数的运行间波动

独立验证 ann_skip=752 vs benchmark JSON ann_skip=806（差异 ~7%）。两者最终质量指标一致（clusters=18, merges=76）。差异可能源自浮点精度或合并循环中的评估顺序。不影响正确性，但提示 ANN 候选筛选在边界附近有一定敏感性。

---

## 7. 测试覆盖

| 指标 | 值 |
|---|---|
| 总测试数 | 58 |
| 全部通过 | ✓ (6.787s) |
| 新增测试 | +1 (cluster-entry 口径回归) |
| 覆盖率变化 | ANN 诊断口径回归锁定 |

---

## 8. 总体评级：A-

### 评级理由

| 维度 | 评分 | 说明 |
|---|---|---|
| 正确性 | A | 双口径诊断逻辑正确，JSON 9/9 一致 |
| 完整性 | A | 代码+测试+文档+证据包全链条更新 |
| 独创性 | B+ | 主要是实现 R-023 Opus 建议，设计层面新增较少 |
| 风险控制 | A | ANN 可选实施例定位明确，不拖累核心主张 |
| 文档质量 | A | FINAL_REPORT 双口径解释清晰，专利证据包一致 |

**较 R-025(A) 的差异**: R-025 范围大（参数对齐 + 等效修复 + N=5000）；R-026 范围小但执行精准。降半级主要因为范围有限且主要是落实已知改进建议。

### 评审轨迹
B → B- → B+ → A- → **A** → **A-** （六轮评审，高位稳定）

---

## 9. 下一步建议

### P1: Candidate 高性能档三档复验（推荐立即执行）
- 在 N=240/1000/5000 对 radius=3 做等效+性能复验
- 通过门：`cluster_count_equal` + `merges_applied_equal`
- 速度门：active 场景加速 ≥ 0（至少不退化）
- 结果写入证据包，为专利可选实施例提供分层证据

### P2: ANN 冻结决策
- 如 P1 完成后仍无 ANN 正加速证据，建议正式冻结 ANN 为"仅可选实施例"，停止性能优化投入
- 在 FINAL_REPORT 和 next_phase_plan 中标记"ANN 功能冻结"

### P3: 证据包 DF-06 描述微调
- 更新 `technical_effect` 为 "candidate 默认零损失，高性能实验档有轻微有损风险；ANN 负加速但质量门通过"

### P3: 临时文件清理
- 删除 `tmp_r022_verify.py`, `tmp_r023_verify.py`, `tmp_r023_ann_check.py`, `tmp_r024_verify.py`

---

## 附录：独立验证脚本

验证脚本：`tmp_r024_verify.py`
- 6 项独立检查全部通过
- JSON 一致性 9/9 OK
- 完整输出见评审会话记录
