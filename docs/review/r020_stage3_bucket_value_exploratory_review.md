# R-020 Stage 3 — `_bucket_value` 替代方案与探索策略深度评审

- **评审人**: Claude Opus (Reviewer)
- **评审对象**: Codex R-019 → R-020 工作（提交 aa478f5 及后续修复）
- **日期**: 2026-02-11
- **总体评级**: **B-**（较 R-019 的 B 降半级）

---

## 0. 评审范围

| 维度 | 内容 |
|------|------|
| 代码变更 | `_signed_projection` → `_bucket_value` + `_median` 替代；探索策略（exploratory neighbors）；`max_neighbors` 默认 48；严格测试恢复 |
| 测试 | 51/51 通过（已验证） |
| Benchmark | candidate_filter -5.7%/-10.2% 负加速；ann_prune quality_gate_pass=false |
| 文档 | FINAL_REPORT.md 已更新 |

---

## 1. 正面评价

### 1.1 P1-NEW（R-019）修复到位
- `max_neighbors` 默认值从 16 提升到 48
- 严格测试 `test_candidate_filter_keeps_merge_outcome_on_active_case` 恢复 `assertEqual`
- 合并结果在 active 场景完全等效（merges=29, cluster_count 一致）

### 1.2 测试与文档同步
- 51/51 通过，无 flaky test
- FINAL_REPORT.md 数据已刷新
- 证据包条件表达正确（`candidate_active_equal` 分支）

---

## 2. 严重问题

### P0-1: `_bucket_value` 签名退化 — P1-1 同类缺陷复现

**严重等级: P0（最高）**

**实测数据（240 条 HashEmbeddingProvider 嵌入，bucket_dims=10）：**

| 指标 | 实测值 | 理想值 |
|------|--------|--------|
| 唯一签名数 | 25/240 (10.4%) | ≥80% |
| 最大桶容量 | 96 (40%) | ≤ 5% |
| Hamming 权重分布 | {0: 96, 1: 112, 2: 28, 3: 4} | 均匀围绕 5 |
| Median 阈值 | 0.0000（全部样本） | 非零正值 |
| above_median 位数 | 0/10（96 个嵌入）| 5/10 |

**根因链条：**

```
HashEmbeddingProvider
  → 稀疏非负向量（256 维中大多数 = 0.0）
  → _bucket_value 仅采样 3 个维度 (idx_1, idx_2, idx_3)
  → 3 个随机维度极大概率全为 0.0
  → 10 个 bit 的 _bucket_value 全部 = 0.0
  → _median(10 个 0.0) = 0.0
  → 判定条件 "value > threshold" 全部为 false
  → 签名 = (0,0,0,0,0,0,0,0,0,0)
  → 96/240 嵌入落入同一个全零桶
```

**这与 R-011 发现的 P1-1（sign-bit 退化）是同一类根因**：对 HashEmbeddingProvider 的稀疏非负特性不具备鲁棒性。`_signed_projection` 至少使用 64 步随机投影跨越所有维度，能产生非零投影值。`_bucket_value` 仅采样 3 个维度（覆盖 11.33% 的维度空间），在稀疏向量上几乎必然退化。

**对系统的影响：**
- 桶划分完全失效 — 40% 的嵌入在同一个桶中
- 候选筛选的降耗效果全部依赖于**探索策略的暴力搜索**（见 P1-1）
- 若移除探索策略，候选筛选将产生大规模召回损失

### P1-1: 探索策略使候选筛选退化为 O(k²) 暴力搜索

**严重等级: P1（高）**

**代码位置**: [cluster.py:291-307](src/memory_cluster/cluster.py#L291-L307)

```python
all_ranked = sorted(
    [peer_id for peer_id in centroid_by_id.keys() if peer_id != cid],
    key=lambda peer_id: (
        -self._approx_cosine(centroid_by_id.get(cid) or [], centroid_by_id.get(peer_id) or []),
        peer_id,
    ),
)
exploratory = all_ranked[:explore_k]  # explore_k = max(4, 48) = 48
```

**问题**：对每个簇，计算与**所有其他簇**的 `_approx_cosine` 并排序，取 top-48。这是 O(k²) 的暴力最近邻搜索。

**实测影响**：
- Baseline (无候选筛选): 216.5 ms
- Candidate filter (含探索策略): 257.0 ms
- **净开销: +18.7%（负加速）**

**根本矛盾**：
1. 若桶划分有效（P0-1 修复后），探索策略不必要
2. 若桶划分无效（P0-1 未修复），探索策略使候选筛选比不用更慢
3. 当前实现 = "O(k²) 暴力搜索 + 桶划分开销 + 邻接图维护开销" > "不使用候选筛选"

增量刷新路径 `_compute_candidate_neighbors_for_cluster` ([cluster.py:569-592](src/memory_cluster/cluster.py#L569-L592)) 同样对 ALL clusters 全量扫描。

### P1-2: ANN quality_gate_pass=false（merges_applied 28 ≠ 29）

**严重等级: P1（高）**

**实测数据**（ann_hybrid_benchmark，merge_active_case）：

| 变体 | merges_applied | quality_gate_pass |
|------|---------------|-------------------|
| baseline_exact | 29 | — |
| prune_only | 29 | true |
| candidate_prune | 29 | true |
| **ann_prune** | **28** | **false** |
| hybrid_prune | 29 | true |

**根因**：ANN 签名同样退化（max_bucket=95-147/240），6 个 hash table 都无法区分大部分嵌入，导致某对真实可合并簇被遗漏。

**含义**：ANN 模块在当前实现下是**有损的**，不仅有负加速，还会丢失合并。

---

## 3. 中等问题

### P2-1: `_median` 量化在稀疏场景下退化

`_median` 的设计意图是"保证约 50% 的 bit 为 1"，但当大量 `_bucket_value` 值相同（全为 0.0）时，`value > threshold`（严格大于）导致所有相同值的 bit 都为 0。

实测 Hamming 权重分布 `{0: 96, 1: 112, 2: 28, 3: 4}` 远未达到期望的 5/10 均匀分布。

### P2-2: `_bucket_value` 维度覆盖严重不足

| 方案 | 每 bit 采样维度 | 信息源 |
|------|----------------|--------|
| `_signed_projection`（R-019） | 64 步（全维投影）| 全部 256 维 |
| `_bucket_value`（R-020） | 3 个固定索引 | 29/256 维 (11.33%) |

3 个维度的加权和（1.0/0.5/0.25）在统计上不等价于 SimHash 的随机超平面投影，对高维稀疏数据的区分力极度不足。

### P2-3: ANN 全场景负加速

| 场景 | ann_prune | hybrid_prune |
|------|-----------|--------------|
| sparse | +9.7% | -28.2% |
| active | **-9.7%** | **-52.8%** |

active 场景下 ann_prune 和 hybrid_prune 全部负加速，且 ann_prune 质量门失败。当前 ANN 模块在任何实用场景下都无正收益。

---

## 4. 低优先级问题

### P3-1: 探索策略 `_cap_neighbor_ids` 容量上限过宽
`merged = self._cap_neighbor_ids(ranked + exploratory, max(1, self.merge_candidate_max_neighbors * 6))`
- 容量上限 = 48 × 6 = 288，而总簇数仅 120 — 上限无实际约束意义

### P3-2: Hybrid OR 门控仍然是单调弱化
`candidate_filter OR ann` 严格比两者中任一方更宽松。实测 hybrid_prune -52.8% 的负加速印证了 OR 门控的固有缺陷。

---

## 5. 指标汇总

| 维度 | R-019 | R-020 | 变化 |
|------|-------|-------|------|
| 测试通过率 | 51/51 | 51/51 | = |
| 签名唯一率（候选） | ~33%¹ | **10.4%** | ↓↓ |
| active 候选筛选加速 | -10.2%² | -18.7%³ | ↓ |
| 召回损失 | 0（max_neighbors=48） | 0 | = |
| ANN 质量门（active） | false | false | = |
| P0 问题数 | 0 | **1** | ↑ |

¹ R-019 使用 `_signed_projection` 测得 2/6 unique（但有 P1-1 碰撞问题）
² Benchmark 报告数据
³ 本次独立实测

---

## 6. 根因总结与修复建议

### 6.1 核心矛盾
`_bucket_value` 是对 `_signed_projection` P2-NEW-3（索引碰撞）的过度简化修复。虽然避免了碰撞问题，但引入了更严重的退化问题（P0-1），并通过 O(k²) 探索策略（P1-1）掩盖了退化。

### 6.2 推荐修复路径

**P0-1 修复 — 三选一：**

**方案 A（推荐）: 恢复随机超平面投影，修复碰撞**
```python
def _lsh_projection(self, vector, *, seed):
    """SimHash: 随机超平面投影，对非负输入仍有效。"""
    dim = len(vector)
    rng_state = seed
    projection = 0.0
    mean_estimate = sum(vector) / dim if dim > 0 else 0.0
    for i in range(dim):
        # 中心化：减去均值使投影有正有负
        rng_state = (rng_state * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
        weight = ((rng_state >> 33) / (2**31)) - 1.0  # [-1, 1]
        projection += (vector[i] - mean_estimate) * weight
    return projection
```
关键改进：**中心化**（减去均值），使得即使全非负输入，投影值也有正有负，从而 `>= 0.0` 阈值有效。

**方案 B: MinHash 风格**
对 L2-归一化后的向量取 top-k 维度索引的 hash，适合稀疏非负场景。

**方案 C: 前缀余弦分桶**
用 `_approx_cosine` 的前缀子集做量化桶，复用已有基础设施。

**P1-1 修复：**
- 修复 P0-1 后，**移除探索策略**
- 若桶划分质量足够（unique signatures ≥ 60%），桶内+邻桶已足够覆盖真正邻居
- 移除后复杂度从 O(k²) 降回 O(k × bucket_size)

**P1-2 修复：**
- ANN 签名同样需要修复（与 P0-1 同源）
- 修复后重跑 benchmark，验证 quality_gate_pass=true

---

## 7. 对专利的影响

| 权利要求 | 影响 |
|----------|------|
| 18（候选筛选） | 当前实现实质为暴力搜索包装，与"签名桶候选筛选"的权利要求文本不匹配。修复 P0-1 后可恢复一致性 |
| 19（ANN 混合） | quality_gate_pass=false + 负加速，证据包 DF-06 的 `implemented_measured_not_default` 标注正确，但技术效果缺乏正面数据 |
| 20（语义精度回归） | 不受影响 |

---

## 8. 建议优先级排序

| 优先级 | 编号 | 任务 | 预估工作量 |
|--------|------|------|-----------|
| **P0** | P0-1 | 修复 `_bucket_value` 退化（推荐方案 A：中心化投影） | 半天 |
| **P1** | P1-1 | 移除探索策略（P0-1 修复后） | 1 小时 |
| **P1** | P1-2 | ANN 签名同步修复（与 P0-1 同源） | 2 小时 |
| P2 | P2-1 | `_median` 量化策略优化（P0-1 修复后自动缓解） | — |
| P2 | P2-2 | 维度覆盖增加（P0-1 修复后自动解决） | — |
| P2 | P2-3 | ANN 开销优化（修复签名后重新评估） | 待定 |
| P3 | P3-2 | Hybrid 门控 AND/OR 可配置 | 延后 |

---

## 9. 结论

R-020 采纳了 R-019 的核心建议（max_neighbors=48 + 严格测试恢复），这是积极的。但对 `_signed_projection` 的替换方案 `_bucket_value` 引入了**比原问题更严重的退化**（P0-1），并通过 O(k²) 探索策略掩盖了问题。

**当前候选筛选模块的实际行为**：对每个簇暴力计算全局 top-48 近邻 → 桶划分不提供增量价值 → 净开销 +18.7%。这使得该模块在所有场景下**严格劣于不使用候选筛选**。

**推荐下一步**：先修复 P0-1（中心化投影或等效 LSH），验证签名多样性 ≥ 60%，然后移除探索策略（P1-1），最后重跑全部 benchmark 验证正收益。

---

*评审结束。如有疑问请在 `.claude.md` 中追加讨论。*
