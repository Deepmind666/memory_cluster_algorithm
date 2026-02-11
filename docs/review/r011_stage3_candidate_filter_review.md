# R-011 Stage 3 深度评估：Merge Candidate Filter

- 评审人：Claude Opus 4.6
- 评审日期：2026-02-10
- 评审对象：Stage 3 性能工程原型（commit 6d0ed35）
- 被评审代码基线：38/38 tests, compileall pass

---

## 1. 评审范围

| 变更文件 | 类别 | 新增/修改 |
|---|---|---|
| `src/memory_cluster/cluster.py` | 核心算法 | +82 行（候选筛选方法） |
| `src/memory_cluster/models.py` | 数据模型 | +6 行（3 个配置字段） |
| `src/memory_cluster/pipeline.py` | 管道接入 | +3 行（参数穿透） |
| `src/memory_cluster/cli.py` | CLI 接入 | +9 行（3 个开关参数） |
| `tests/test_merge_candidate_filter.py` | 单元测试 | 新增（134 行，3 条用例） |
| `scripts/run_candidate_filter_benchmark.py` | 性能脚本 | 新增（259 行） |
| `docs/eval/candidate_filter_benchmark_report.md` | 性能报告 | 新增（45 行） |
| `docs/FINAL_REPORT.md` | 总报告 | 更新（+Section 3.6） |
| `docs/design/next_phase_plan.md` | 规划文档 | 更新 |

总变更量：~788 行插入，12 文件。

---

## 2. 架构评审

### 2.1 候选筛选机制概述

```
centroid → _candidate_signature(前N维符号量化)
         → 桶映射(signature → bucket)
         → 同桶 + 邻接桶(Hamming=1)邻居收集
         → max_neighbors 上限截断
         → 对称化(A→B ⇒ B→A)
         → 候选邻居图
```

merge_clusters_with_lookup 在外循环(while merged)中每轮重建候选图，内循环中对非候选 pair 跳过(skip + 计数)。

### 2.2 设计优点

1. **默认关闭** — `enable_merge_candidate_filter=False`，零侵入生产路径。
2. **审计指标** — `merge_pairs_skipped_by_candidate_filter` 提供筛选效果的可观测性。
3. **三层贯通** — models → pipeline → cli 配置穿透完整，参数验证 `max(1, ...)` 到位。
4. **对称化保证** — 邻居图双向对称，避免方向性遗漏。
5. **与 Upper-Bound Prune 正交组合** — 候选筛选先截断 pair 集，再对通过的 pair 做 bound 剪枝，两级过滤。

### 2.3 设计风险

签名函数基于 **符号位量化**（`v >= 0.0 → 1, v < 0.0 → 0`），假设嵌入维度值围绕 0 分布。该假设在 learned embedding（word2vec / BERT）中成立，但在 HashEmbeddingProvider 中 **完全失效**（详见 §3 P1-1）。

---

## 3. 问题发现

### P1-1：签名函数与 HashEmbeddingProvider 不兼容（严重设计缺陷）

**现象**：对 benchmark 的 120 个合成 fragment 生成 embedding 后计算签名，全部得到 `(1, 1, 1, 1, 1, 1, 1, 1, 1, 1)`，桶化机制完全退化为单桶。

**根因**：

```python
# cluster.py:253
def _candidate_signature(self, vector: list[float]) -> tuple[int, ...]:
    return tuple(1 if float(vector[idx]) >= 0.0 else 0 for idx in range(dim))
```

`HashEmbeddingProvider.embed()` 的工作方式：
1. 每个 token 通过 `blake2b → hash % dim` 映射到一个维度
2. 对应维度 +1.0（词袋累加）
3. L2 归一化

结果：所有维度值 ≥ 0.0（非零维度为正值，零维度为 0.0）。

由于 `0.0 >= 0.0 == True`，签名的每一位恒为 1。

**实测验证**：

```
100个随机文本，前10维 |v|<0.05 的比例: 988/1000 = 98.80%
120个fragment签名: 全部为 (1,1,1,1,1,1,1,1,1,1)
不同签名数: 1
```

**后果**：
- 所有簇落入同一个桶，邻接桶逻辑完全空转
- 筛选效果 **仅来自** `max_neighbors` 上限截断（等价于随机邻居采样）
- benchmark 报告的 75.0% attempt reduction 和 42.6% speedup 是真实的，但原因是随机截断而非空间局部性
- `cluster_count_equal=true` 在当前测试数据上成立，但在真合并对超过 max_neighbors 时将产生 **假阴性**

**修复建议**（择一）：

| 方案 | 描述 | 复杂度 |
|---|---|---|
| A. SimHash 随机超平面 | 用 k 个随机向量做内积符号量化 | 中 |
| B. 维度中位数量化 | 各维度用所有簇的中位数做阈值 | 低 |
| C. 随机投影 LSH | 标准 LSH 多表多桶 | 高（即 ANN 方向） |

**注**：观察到代码库已开始 ANN 候选模块（`enable_merge_ann_candidates` 等参数已入 cli/pipeline），如果 ANN 模块使用随机投影，建议将 candidate filter 标记为 deprecated 或文档注明仅适用于 signed embedding provider。

---

### P2-1：对称化后邻居上限无约束

**现象**：`_build_candidate_neighbors` 在对称化前限制每簇 ≤ max_neighbors，但对称化阶段（lines 244-246）无上限检查。

**实测**：
```python
# max_neighbors=2, 8个簇全在同一桶
c0 -> 7个邻居 (配置上限=2)
c1 -> 7个邻居
c2~c7 -> 各2个邻居
```

Hub 簇（被多个簇选为邻居）的邻居数可远超配置值。

**影响**：不影响正确性（更多邻居 = 更多检查 = 更保守），但降低筛选效率。对于大量簇落入同一桶的场景（如 P1-1 所述），hub 膨胀尤其严重。

**修复建议**：对称化后对每个簇执行二次截断，或改用对称 k-NN 图构建策略。

---

### P2-2：邻居图每轮合并迭代全量重建

**位置**：`cluster.py:94` `_build_candidate_neighbors(active)` 在 `while merged:` 循环内。

**影响**：每轮合并后重建整个签名桶和邻居图。对多轮合并场景（active case 中 merges_applied=21），增加常数开销。

**缓解**：当前默认关闭，且实测 active 场景仍有 19.8% 加速，说明桶构建开销远小于节省的相似度计算。但随簇数增大，重建成本会上升。

**修复建议**：引入增量维护——合并后仅更新 base 簇的签名和邻接关系，移除被吞并簇的条目。

---

### P2-3：benchmark 报告 summary 缺少 merges_applied 一致性校验

**位置**：`run_candidate_filter_benchmark.py:81-107` `summarize_pair()`

**现象**：计算了 `cluster_count_equal` 和 `merge_activity_present`，但未输出 `merges_applied_equal`。

**影响**：`cluster_count_equal=true` 是必要非充分条件——簇数相同不代表合并路径一致。`merges_applied` 是验证筛选无损性的更直接指标。

**修复建议**：在 summary 中增加：
```python
"merges_applied_equal": int(base_merges) == int(opt_merges),
"merges_applied_baseline": int(base_merges),
"merges_applied_optimized": int(opt_merges),
```

---

### P3-1：仅 2 个 benchmark 场景

缺少高合并率场景（如 `similarity_threshold=0.5, merge_threshold=0.7`），无法验证大量合并时筛选的稳定性。

### P3-2：测试数据无中文覆盖

`_sparse_fragments` 和 `_active_fragments` 均为英文。中文 token 的哈希分布可能不同，建议增加中文数据用例。

### P3-3：无运行时召回损失自动诊断

当候选筛选导致 merge 结果不同时，管道内无 warning/metric 输出。建议在 `build_cluster_result` 中增加可选的 `--verify-candidate-filter` 模式（同时运行 filtered/unfiltered，对比并输出差异）。

---

## 4. 测试评审

### 4.1 现有测试（3 条）

| 用例 | 覆盖点 | 评价 |
|---|---|---|
| `test_candidate_filter_reduces_attempts_on_sparse_case` | 稀疏场景筛选有效 + cluster_count 一致 | 充分 |
| `test_candidate_filter_disabled_reports_zero_skips` | 关闭时零跳过 | 充分 |
| `test_candidate_filter_keeps_merge_outcome_on_active_case` | 活跃场景 cluster_count + merges_applied 一致 | 充分 |

### 4.2 测试缺口

| 缺失场景 | 优先级 |
|---|---|
| 签名实际分桶效果验证（当前全退化为单桶无从测起） | P1 |
| max_neighbors=1 极端截断场景 | P2 |
| 单簇 / 空簇输入的边界行为 | P3 |
| 中文内容 fragment 候选筛选 | P3 |

---

## 5. 性能证据评审

### 5.1 benchmark 结果

| 场景 | attempt_reduction | avg_speedup | cluster_count_equal |
|---|---|---|---|
| sparse (2.0/0.95) | 75.0% | 42.6% | true |
| merge_active (0.82/0.85) | 44.4% | 19.8% | true |

### 5.2 结果解读（基于 P1-1 发现）

上述加速 **实质来源**：

- 120 个簇全部落入同一桶，每簇仅选前 16 个同桶邻居
- 等价于 **随机邻居截断**（非 LSH 空间局部性）
- sparse 场景：120 簇 × 119/2 = 7140 pair → 截断至 ≈1784 pair（75% 减少）
- 加速是真实的，但不具备数据分布鲁棒性

如果未来替换为 learned embedding（值有正有负），签名桶化将开始发挥真正作用。

---

## 6. 工程质量评审

### 6.1 代码风格

- 方法命名清晰：`_candidate_signature`, `_adjacent_signatures`, `_build_candidate_neighbors`
- 数据结构选型合理：`dict[str, set[str]]` 邻居图，`dict[tuple[int,...], list[str]]` 桶映射
- 无循环依赖，无全局状态污染
- `snapshot_stats()` 审计指标输出完整

### 6.2 参数防御

- `max(1, int(...))` 在 models/cli/cluster 三层一致
- `bucket_dims=0` 和 `max_neighbors=0` 均被 clamp 至 ≥1
- 空簇列表 (`len(clusters) < 2`) 短路返回空 dict

### 6.3 文档与报告

- `next_phase_plan.md` 准确反映当前状态
- `FINAL_REPORT.md` Section 3.6 数据与 JSON 一致
- benchmark 报告格式清晰，可复现命令已记录

---

## 7. 综合评级

| 维度 | 评级 | 说明 |
|---|---|---|
| 架构设计 | B | 默认关闭 + 审计指标 + 正交组合 优秀；但签名函数选型失误 |
| 正确性 | B- | 当前测试场景下结果正确，但签名退化意味着理论召回无保证 |
| 工程质量 | A- | 三层贯通、参数防御、测试覆盖均到位 |
| 性能证据 | B+ | 加速数据真实可复现，但加速机制非设计预期（随机截断 ≠ LSH） |
| 文档完整性 | A- | 规划、报告、命令均更新 |

**综合评级：B+**

与 R-010b（A-）相比下降半档，主要因签名函数与当前 embedding provider 不兼容的设计缺陷。该缺陷不影响运行安全性（默认关闭），但影响技术方案的 **专利叙事完整性**——如果候选筛选作为专利权利要求的一部分，需要证明桶化机制确实利用了空间局部性，而非随机截断。

---

## 8. 行动建议

### 必须修复（阻塞专利叙事）

| # | 项目 | 优先级 | 建议 |
|---|---|---|---|
| 1 | 签名函数替换为 SimHash 或中位数量化 | P1 | 确保桶化对 HashEmbeddingProvider 有效 |
| 2 | benchmark 增加 merges_applied_equal 指标 | P2 | 强化无损证据 |

### 建议改进

| # | 项目 | 优先级 |
|---|---|---|
| 3 | 对称化后二次截断 | P2 |
| 4 | 邻居图增量维护 | P2 |
| 5 | 增加高合并率 benchmark 场景 | P3 |
| 6 | 增加中文测试数据 | P3 |
| 7 | 可选 verify 模式（filtered vs unfiltered 对比） | P3 |

### 关于 ANN 模块

观察到代码库已新增 `enable_merge_ann_candidates` 等参数。如 ANN 模块使用随机投影（random hyperplane LSH），则可自然解决 P1-1 问题。建议：
- 如 ANN 模块已覆盖候选筛选功能，将 candidate filter 标记为 deprecated
- 如两者共存，明确文档说明各自适用场景

---

## 9. Stage 3 进展判定

| 判定项 | 结论 |
|---|---|
| 38/38 测试通过 | 通过 |
| 性能加速可复现 | 通过（但加速机制需修正） |
| 代码质量 | 通过 |
| 签名函数适配性 | **未通过** — 需修复后重验 |
| 是否阻塞下一步 | **不阻塞**（候选筛选默认关闭，ANN 方向可并行推进） |

**结论**：Stage 3 候选筛选原型的 **工程骨架合格**，但核心签名函数存在与 HashEmbeddingProvider 不兼容的设计缺陷（P1-1），需要在合入专利证据包前修复。当前可继续推进语义精度回归和 ANN 混合策略，P1-1 修复应纳入性能工程第二阶段闭环。

---

## 10. 附录：手动验证脚本输出

### A. 签名退化验证
```
120 个fragment，不同签名数: 1
  (1, 1, 1, 1, 1, 1, 1, 1, 1, 1): 120 个簇
→ 桶化机制完全失效
```

### B. 近零维度分布
```
100个随机文本，前10维 |v|<0.05 的比例: 988/1000 = 98.80%
```

### C. 对称化膨胀
```
max_neighbors=2, 8个簇全在同一桶:
  c0 -> 7个邻居 (配置=2)
  c1 -> 7个邻居
→ 对称化后实际上限远超配置值
```

### D. 召回风险极端场景
```
v1=[+0.001]*10 + [1.0]*246
v2=[-0.001]*10 + [1.0]*246
余弦相似度: 1.000000, Hamming距离: 10
→ 候选筛选会漏掉 cosine≈1.0 的合法合并对
```

---

*本评审由 Claude Opus 4.6 生成，仅用于工程改进，不构成法律意见。*
