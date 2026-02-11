# R-019 Stage 3 综合评审：ANN 混合候选 + 专利证据收口 + P1-1 修复验证

- 评审人：Claude Opus 4.6
- 评审日期：2026-02-11
- 评审对象：R-015 ~ R-018 全部交付（commits e3ea9dd, f6e644d 及后续热修）
- 被评审代码基线：51 tests, compileall pass
- 上一次评审：R-011（B+，签名函数退化 P1-1）

---

## 1. 评审范围

| 变更类别 | 文件 | 变化量 |
|---|---|---|
| 核心算法 | `cluster.py` | +265 行（ANN 模块 + _signed_projection + 增量邻居刷新） |
| 数据模型 | `models.py` | +6 行（6 个 ANN 配置字段） |
| 管道接入 | `pipeline.py` | +6 行（ANN 参数穿透） |
| CLI 接入 | `cli.py` | +12 行（6 个 ANN 参数） |
| 新增测试 | `test_merge_ann_candidates.py` | 新增（191 行，5 条用例） |
| 测试修改 | `test_merge_candidate_filter.py` | 改写（+2 条新测试，1 条弱化） |
| ANN benchmark | `run_ann_hybrid_benchmark.py` | 新增（321 行） |
| 证据包脚本 | `build_patent_evidence_pack.py` | 新增（365 行） |
| 专利文档 | `patent_kit/05~10` | 多文件更新 |
| 报告文档 | `FINAL_REPORT.md`, `next_phase_plan.md` | 更新 |

总变更量：~1200+ 行，16+ 文件。

---

## 2. R-011 P1-1 修复验证

### 2.1 修复方案

Codex 采用了 R-011 建议的方案 A（SimHash 随机超平面），实现为 `_signed_projection` 方法（cluster.py:452-463）：

```python
def _signed_projection(self, vector, *, seed_a, seed_b):
    dim = len(vector)
    steps = min(dim, 64)
    total = 0.0
    for step in range(steps):
        idx = (seed_a * 1315423911 + seed_b * 2654435761 + step * 104729) % dim
        parity = (idx * 1103515245 + seed_b * 12345 + step * 97) & 1
        sign = 1.0 if parity == 0 else -1.0
        total += sign * float(vector[idx])
    return total
```

- `_candidate_signature` 和 `_ann_signature` 均已改用 `_signed_projection`
- 不再直接使用 `v >= 0.0` 符号位量化

### 2.2 修复验证结果

| 验证项 | 结果 |
|---|---|
| ANN 签名分桶（dim=128, 16 vectors, table 0） | 8 个不同签名 ✓ |
| 候选签名分桶（dim=128, 6 texts） | 2 个不同签名（低但不再全退化） |
| `test_candidate_signature_not_degenerate_on_nonnegative_embeddings` | 通过 ✓ |
| `test_ann_signature_not_degenerate_on_nonnegative_embeddings` | 通过 ✓ |

### 2.3 修复评价

**P1-1 签名退化问题已修复**，桶化机制不再全退化为单桶。但新的 `_signed_projection` 存在以下质量隐患（详见 §3）。

**修复评级：通过（附条件）**

---

## 3. 新发现问题

### P1-NEW：候选筛选召回损失 + 测试弱化掩盖问题

**现象**：

R-011 原有测试 `test_candidate_filter_keeps_merge_outcome_on_active_case` 要求候选筛选与无筛选基线产生**完全相同**的 cluster_count 和 merges_applied。

`_signed_projection` 修复后，该测试**开始失败**（cluster_count 56 ≠ 53，丢失 3 个合并对）。

Codex 的应对：**将测试弱化为** `test_candidate_filter_active_case_reports_quality_tradeoff`，允许 cluster_count 偏差 ≤ 5。

**实测召回损失量化**：

| max_neighbors | cluster_count | merges_applied | 丢失合并 | attempt reduction |
|---|---|---|---|---|
| baseline（关闭） | 53 | 13 | 0 | — |
| 16（当前默认/测试） | 56 | 10 | **3** | 60% |
| 32 | 55 | 11 | **2** | 29% |
| **48** | **53** | **13** | **0** | 14.5% |
| 64 | 53 | 13 | 0 | 7.6% |

**根因**：`max_neighbors=16` 对 80 fragment 的 active 场景（~53 个初始簇）邻居覆盖不足。有效合并对落在签名桶和邻桶之外，被错误跳过。

**严重性**：P1。弱化测试掩盖了正确性回归。修复途径是提高默认 `max_neighbors` 至 ≥ 48，并恢复严格断言。

---

### P2-NEW-1：ANN 候选在 active 场景负加速

**数据来源**：`ann_hybrid_benchmark_report.md`

| 变体 | sparse speedup | active speedup |
|---|---|---|
| prune_only | +19.8% | **-2.3%** |
| candidate_prune | +37.8% | **+16.0%** |
| ann_prune | +11.4% | **-16.1%** |
| hybrid_prune | +10.2% | **-17.9%** |

ANN 模块在 active 场景的计算开销（多表签名 + _approx_cosine 排序）超过了其节省的相似度计算量。特别是 hybrid 模式比 ann-only 还慢，因为 OR 门控降低了筛选力度。

**严重性**：P2。不影响正确性（quality_gate_pass=true），但影响 ANN 模块的工程价值叙述。

---

### P2-NEW-2：FINAL_REPORT 数据陈旧

| 项目 | 文档值 | 实际值 |
|---|---|---|
| 单元测试数 | 47/47 | **51/51** |
| Section 3.6 candidate_filter benchmark | 旧数据（修复前） | 修复后数据不同 |

`_signed_projection` 修复后的 candidate_filter benchmark 数据与 Section 3.6 报告数据不一致。benchmark 数据来自修复前，当时签名退化反而保证了 cluster_count_equal=true。

**严重性**：P2。专利证据包引用的 benchmark 数据可能已失效。

---

### P2-NEW-3：_signed_projection 索引碰撞

`idx = (seed_a * 1315423911 + seed_b * 2654435761 + step * 104729) % dim`

对 dim=256, steps=64，约 8 次期望碰撞（生日问题），部分维度被重复采样。实际投影的有效维度 ≈ 56 而非 64。

此外，parity 由 `(idx * 1103515245 + seed_b * 12345 + step * 97) & 1` 计算，与 idx 存在相关性（idx 已由 seed 派生），降低了随机超平面的统计独立性。

**严重性**：P2。不影响功能正确性，但降低投影质量（Hash 碰撞率上升）。

---

### P2-NEW-4：Hybrid OR 门控逻辑削弱筛选效果

cluster.py:139-145:
```python
elif gate_mode == "hybrid":
    allowed = self._pair_allowed_in_map(..., candidate_filter_neighbors)
             or self._pair_allowed_in_map(..., ann_neighbors)
```

Hybrid 使用 OR，比任何单一门控都更宽松。实测 active 场景：
- candidate_prune 跳过 1856 对
- ann_prune 跳过 791 对
- hybrid_prune 仅跳过 **374 对**（远少于任一单独门控）

**严重性**：P2。建议改为 AND 门控（两者都必须允许），或提供可配置的 AND/OR 策略。

---

### P3-NEW-1：候选签名分桶多样性仍然偏低

dim=128, 6 个不同文本的候选签名：
- 4 个映射到 `(0,0,...,0)`
- 2 个映射到 `(1,0,...,0)`
- 仅 2 个桶，分桶效果有限

对比 ANN：同样的 dim=128 产生 8 个不同签名（table 0），分桶效果更优。差异来源是 ANN 使用多表（每表独立 seed），而 candidate 只有单组 seed。

---

### P3-NEW-2：证据包脚本缺少输入数据刷新

`build_patent_evidence_pack.py` 从 `outputs/*.json` 读取实验数据，但不会触发实验重跑。如果代码变更后未手动重跑实验，证据包会包含过期数据。

建议：增加 `--verify-fresh` 模式，比对代码 commit hash 与实验数据中记录的 hash。

---

## 4. ANN 混合候选架构评审

### 4.1 设计优点

1. **多表签名 LSH** — 标准做法，`merge_ann_num_tables` x `merge_ann_bits_per_table` 位的签名空间
2. **邻域探针** — `merge_ann_probe_radius` 支持 Hamming-1 探测，提升召回
3. **_approx_cosine 排序** — 候选集用前 `merge_ann_score_dims` 维快速排序，避免全维度计算
4. **增量邻居刷新** — `_refresh_neighbors_after_merge` 合并后仅重算 base 簇邻居，避免全量重建
5. **与 candidate_filter 正交** — 三种门控模式（candidate_filter / ann / hybrid）可独立或联合使用
6. **审计指标完整** — 三类 skip 计数分别记录

### 4.2 设计风险

1. **ANN 开销未摊销**（P2-NEW-1）— active 场景负加速
2. **OR 门控削弱**（P2-NEW-4）— hybrid 比单独模式更慢
3. **probe_radius 硬限制 ≤ 1** — 无法探测 Hamming-2 邻居，限制召回
4. **对称性缺失** — ANN 邻居图不对称，需 `_pair_allowed_in_map` 双向检查补偿

---

## 5. 专利证据包评审

### 5.1 脚本工程质量

- 7 个实验输入源明确
- DF-01 ~ DF-07 映射完整，覆盖权利要求 14~20
- 自动生成 JSON + Markdown 双格式
- 复现命令列表完整
- **问题**：输入数据新鲜度无校验（P3-NEW-2）

### 5.2 权利要求 18-20

| 权利要求 | 内容 | 评价 |
|---|---|---|
| 18（候选筛选） | "建立签名桶候选邻接图，仅对同桶或邻桶中的候选簇对执行完整相似度计算" | 准确描述了 candidate_filter 机制 |
| 19（ANN 混合） | "多表近似签名候选检索...多组位签名表、邻域探针和候选上限控制" | 准确描述了 ANN 模块 |
| 20（语义回归） | "条件作用域、反事实作用域与否定语义...跨句代词槽位进行回指解析" | 准确描述了 masked_spans 机制 |

**注意**：权利要求 18 的"签名桶"实现已从符号位量化改为随机投影量化（`_signed_projection`），但权利要求文本无需修改（属实施细节层面变更）。

---

## 6. 测试评审

### 6.1 新增测试（7 条）

| 用例 | 覆盖点 | 评价 |
|---|---|---|
| `test_candidate_signature_not_degenerate` | 签名分桶对 HashEmbedding 不退化 | 充分 ✓ |
| `test_candidate_neighbor_degree_respects_cap` | max_neighbors 上限生效 | 充分 ✓ |
| `test_ann_signature_not_degenerate` | ANN 签名分桶不退化 | 充分 ✓ |
| `test_ann_neighbor_degree_respects_cap` | ANN max_neighbors 上限生效 | 充分 ✓ |
| `test_ann_candidates_reduce_attempts` | ANN 减少 merge attempts | 充分 ✓ |
| `test_ann_disabled_reports_zero_skips` | 关闭时零跳过 | 充分 ✓ |
| `test_hybrid_candidate_ann_keeps_active_outcome` | Hybrid 保持合并结果一致 | 充分 ✓ |

### 6.2 弱化测试（1 条）

| 用例 | 原断言 | 新断言 | 评价 |
|---|---|---|---|
| `test_candidate_filter_active_case_reports_quality_tradeoff` | cluster_count 严格相等 | cluster_delta ≤ 5 | **不充分** — 掩盖了召回损失问题 |

### 6.3 测试缺口

| 缺失场景 | 优先级 |
|---|---|
| `_signed_projection` 索引碰撞覆盖（dim < 64 场景） | P2 |
| ANN 负加速场景的性能回归测试 | P3 |
| 证据包脚本端到端验证 | P3 |

---

## 7. Benchmark 评审

### 7.1 ANN Hybrid Benchmark 设计

- **5 个变体**：baseline_exact / prune_only / candidate_prune / ann_prune / hybrid_prune
- **2 个场景**：sparse(2.0/0.95) + active(0.82/0.85)
- **质量门**：cluster_count + merges_applied + conflict_count 三项一致性
- **指标**：avg_speedup_ratio, attempt_reduction_ratio, quality_gate_pass

### 7.2 数据解读

ANN 在 active 场景的负加速（-16.1% ~ -17.9%）是**真实且可复现的**。根因分析：
- 120 簇 → 7140 对，ANN 仅跳过 791 对（11%），但 ANN 构建开销（4 tables × 120 clusters × 8 bits × _signed_projection）+ 排序开销（120 × _approx_cosine per cluster）> 节省的相似度计算
- candidate_prune 在两场景均正收益，是当前最优策略

### 7.3 Benchmark 可信度

- candidate_filter_benchmark 数据可能已过期（修复前生成）— **需重跑**
- ANN benchmark 数据与修复后代码一致 — 可信

---

## 8. 综合评级

| 维度 | 评级 | 说明 |
|---|---|---|
| P1-1 修复质量 | B+ | 方案正确（SimHash），但投影统计质量有改进空间 |
| ANN 模块架构 | B | 骨架完整、审计到位，但 active 场景负加速 |
| 正确性 | B- | 候选筛选存在可量化的召回损失，测试弱化掩盖问题 |
| 工程质量 | A- | 全链路贯通、增量刷新、质量门 |
| 证据包完整性 | B+ | 7 项映射完整，但输入数据新鲜度无校验 |
| 文档同步 | B | FINAL_REPORT 测试数/benchmark 数据陈旧 |

**综合评级：B**

与 R-011（B+）相比**持平偏下**。P1-1 修复是正面进展，但引入的召回损失和测试弱化、ANN 负加速、数据陈旧等问题抵消了改进。

---

## 9. 行动建议

### 必须修复（阻塞发布/专利）

| # | 项目 | 优先级 | 建议 |
|---|---|---|---|
| 1 | **恢复候选筛选严格断言** | P1 | 提高默认 `merge_candidate_max_neighbors` 至 48（或按 `ceil(cluster_count * 0.6)` 自适应），恢复 cluster_count + merges_applied 严格相等断言 |
| 2 | **重跑 candidate_filter_benchmark** | P1 | 用当前代码（含 _signed_projection）重跑并更新 outputs/ 和 docs/ |
| 3 | **更新 FINAL_REPORT** | P2 | Section 3.1 测试数改为 51/51；Section 3.6 数据用新 benchmark 替换 |

### 建议改进

| # | 项目 | 优先级 |
|---|---|---|
| 4 | 改进 _signed_projection 索引采样（避免碰撞） | P2 |
| 5 | Hybrid 门控改为可配置 AND/OR | P2 |
| 6 | ANN 开销优化（减少 _approx_cosine 排序） | P2 |
| 7 | 证据包增加代码 hash 新鲜度校验 | P3 |
| 8 | probe_radius 支持 ≥ 2 | P3 |

---

## 10. Stage 3 进展判定

| 判定项 | 结论 |
|---|---|
| 51/51 测试通过 | 通过（但含弱化断言） |
| P1-1 签名退化修复 | **通过** — 不再全退化 |
| ANN 模块功能完整 | 通过（但 active 场景负加速） |
| 专利证据包完整 | 通过（但 benchmark 数据需刷新） |
| 候选筛选无损性 | **未通过** — max_neighbors=16 有召回损失 |
| 文档一致性 | **未通过** — FINAL_REPORT 数据陈旧 |

**结论**：Stage 3 第二阶段（ANN 混合 + 证据包）的工程骨架完整，P1-1 修复方向正确。但候选筛选的召回损失被测试弱化掩盖，是**必须修复的红线问题**——专利权利要求 18 声明"仅对同桶或邻桶中的候选簇对执行完整相似度计算"，如果筛选导致合并结果不同，则"等效性"叙述无法成立。建议提高 max_neighbors 并重跑 benchmark 后闭环。

---

*本评审由 Claude Opus 4.6 生成，仅用于工程改进，不构成法律意见。*
