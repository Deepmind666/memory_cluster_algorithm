# R-023 Opus 深度评审：Candidate 等效 + N=5000 半真实 + 参数漂移修复

**评审人**: Claude Opus 4.6
**时间戳**: 2026-02-11 20:30:00 +08:00
**评审基线**: R-022 Opus (A-) 后的 Codex R-025 执行轮次
**代码基线**: 57/57 tests pass

---

## 总体评级：A

**这是项目迄今最强的单轮交付。** R-022 Opus 提出的两个 P1 问题全部以高质量方式关闭，实验证据链从 N=2000 扩展至 N=5000，候选筛选从"有损"提升至"默认等效"，文档对风险的披露诚实到位。

---

## 1. R-022 Opus P1 问题闭环

### P1-NEW-1：参数漂移 → **已修复 ✓**

**发现**：`cluster.py` 构造器 `merge_ann_num_tables=4` vs `models.py` 默认 `=3`；`merge_ann_max_neighbors=32` vs `=48`。

**修复验证**：逐字段对比 `PreferenceConfig()` 默认值与 `IncrementalClusterer()` 默认值，全部 10 个相关参数完全一致：

| 参数 | models.py | cluster.py | 状态 |
|------|-----------|------------|------|
| merge_ann_num_tables | 3 | 3 | OK |
| merge_ann_max_neighbors | 48 | 48 | OK |
| merge_ann_bits_per_table | 10 | 10 | OK |
| merge_ann_probe_radius | 1 | 1 | OK |
| merge_ann_projection_steps | 32 | 32 | OK |
| merge_ann_score_dims | 32 | 32 | OK |
| merge_candidate_bucket_dims | 10 | 10 | OK |
| merge_candidate_max_neighbors | 48 | 48 | OK |
| merge_candidate_projection_steps | 32 | 32 | OK |
| merge_candidate_signature_radius | 4 | 4 | OK |

### P1-NEW-2：Candidate active 有损 (77→76) → **已修复 ✓**

**原问题**：默认 radius=3 导致 merges 77→76，1.3% 召回损失。

**修复策略**：将默认 `merge_candidate_signature_radius` 从 3 提升至 4（质量优先档），以 Hamming 半径=4 覆盖更多候选邻居。

**独立验证**（tmp_r023_verify.py）：
```
Baseline: clusters=18, merges=77, conflicts=4
Filtered: clusters=18, merges=77, conflicts=4
cluster_count_equal: True
merges_applied_equal: True
skipped_by_filter: 637
fallbacks: 0
```
候选签名质量：unique_ratio=0.2667, max_bucket_ratio=0.1042 — 远超质量门。

---

## 2. 实验证据增强

### 2.1 N=5000 半真实数据集

| 场景 | CEG gain | ARB gain | DMG block gain |
|------|----------|----------|----------------|
| realistic (N=5000) | +181.1 | +76.8 | 0 |
| stress (N=5000) | +1748.8 | +2.0 | +30746 |

**评价**：相比 R-022 Opus 评审时的 N=2000 (CEG +76.1/+698.8)，N=5000 规模下效果进一步放大。stress 场景 DMG +30746 是迄今最大的 DMG 增益数据，对专利证据链有极强补充价值。

### 2.2 Stage3 参数扫描

| 类型 | 全门通过数 | 最佳 active speedup |
|------|-----------|-------------------|
| Candidate | 8 / 24 | **+1.8%** (steps=32, radius=3, neighbors=48) |
| ANN | 6 / 288 | -11.4% (仍为负) |

**评价**：
- **Candidate 首次出现全门通过+正加速配置**，这是重要的工程里程碑。虽然 +1.8% 绝对值小，但证明候选筛选在特定参数下不仅零损失，还有正收益。
- 默认发布档（radius=4）优先保证等效性（-13.5% 轻度负加速），这是合理的工程决策。
- ANN 6 组通过全门但仍为负加速，继续维持"可选实施例"合理。

### 2.3 Candidate Benchmark

```
active: merges_applied_equal=true, cluster_count_equal=true
       avg_speedup_ratio=-0.135157
sparse: avg_speedup_ratio=+0.173857
```

**评价**：active 等效性从 R-022 时的 false (77→76) 修复为 true (77=77)。签名质量门通过。

---

## 3. 新发现的问题

### P2-NEW-1（中）：ANN 签名诊断与运行时行为不一致

**现象**：
- Benchmark 报告 ANN 默认配置 (tables=3) `signature_gate_pass=false`，min_table_unique_ratio=0.1375（原始 fragment 嵌入上计算）
- 但运行时 `merge_ann_candidate_fallbacks=0`（不触发 fallback），ANN 正常执行并跳过 752 个 pair

**根因**：Benchmark 的签名诊断在 **240 条原始 fragment 嵌入** 上计算，而运行时 fallback 检查在 **18 个聚类质心** 上计算。聚类质心经过均值聚合后更加分散，签名质量显著提升：

| 维度 | 原始 fragments (N=240) | 聚类质心 (N=18) |
|------|----------------------|----------------|
| Table 0 unique_ratio | 0.1792 | 0.3889 |
| Table 1 unique_ratio | 0.1375 | 0.3333 |
| Table 2 unique_ratio | 0.2333 | 0.5000 |
| min unique_ratio | 0.1375 (< 0.18) | 0.3333 (> 0.18) |

**影响**：
- 不影响正确性（ANN 在聚类质心上工作良好，quality_gate_pass=true）
- 但造成 Benchmark 诊断（false）与运行时行为（正常执行）的认知不一致
- 建议：在 benchmark 报告中增加 "cluster-level signature quality" 补充诊断，或在文档中解释两者差异

### P2-NEW-2（低）：ANN 默认配置实际上处于"边缘状态"

ANN 默认 tables=3 在聚类质心上的 max_bucket_ratio 高达 61.1%（Table 1），意味着超过一半的聚类落在同一个桶中。虽然未触发 fallback（阈值 90%），但桶分布不均衡会导致：
- 某些聚类的 ANN 邻居几乎覆盖所有其他聚类 → 失去筛选效果
- 另一些聚类可能缺少应有的邻居 → 潜在召回损失

---

## 4. 代码审查要点

### 4.1 cluster.py — 无新增逻辑变更
本轮 cluster.py 的核心变更仅为构造器默认参数对齐（tables 4→3, max_neighbors 32→48），无算法逻辑变更。代码审查确认：
- `_projection_score`：xorshift64* 内循环无变动
- `_build_candidate_state` / `_build_ann_state`：fallback 逻辑无变动
- `_refresh_neighbors_after_merge`：增量刷新逻辑无变动
- `_hamming_neighbor_signatures`：泛化 Hamming 邻域无变动

### 4.2 Benchmark 脚本增强
- `run_candidate_filter_benchmark.py`：新增 `_candidate_signature_stats()` 输出签名质量诊断
- `run_ann_hybrid_benchmark.py`：新增 `_ann_signature_stats()` 输出多表签名质量诊断
- 两者均在 benchmark JSON 输出中附加 `signature_*` 字段 — **合理且有价值**

### 4.3 测试增强
- `test_merge_candidate_filter.py`：`test_candidate_filter_default_keeps_benchmark_active_outcome` 使用 benchmark 同源数据 + 默认参数 — 直接验证发布配置的等效性
- `test_merge_ann_candidates.py`：`test_ann_default_keeps_benchmark_active_outcome` 同理
- 两个新测试回应了 R-021 P1-3（质量门覆盖缺口），设计合理

### 4.4 FINAL_REPORT.md — 清晰诚实
- 明确区分"默认质量优先档"（等效但负加速）和"非默认档可能有损"
- ANN 坦诚 signature_gate_pass=false，不进入核心主张
- N=5000 stress 数据显著增强核心证据链

---

## 5. 综合评审矩阵

| 维度 | R-022 Opus (A-) | 本轮 | 变化 |
|------|-----------------|------|------|
| 参数漂移 | P1-NEW-1 (cluster vs models) | **修复 ✓** | ↑ |
| Candidate 召回 | 77→76 有损 | **77=77 等效 ✓** | ↑↑ |
| Candidate 正加速 | 无 | **+1.8% (radius=3 组合)** | ↑ |
| ANN 正加速 | 无 | 无 (最佳 -11.4%) | → |
| 半真实数据规模 | N=2000 | **N=5000** | ↑ |
| CEG 最大增益 | +698.8 | **+1748.8** | ↑ |
| DMG 最大增益 | +12373 | **+30746** | ↑ |
| Benchmark 诊断 | 无签名质量输出 | **签名质量门输出** | ↑ |
| 测试覆盖 | 57/57 | 57/57（含 benchmark 对齐） | → |
| 文档诚实度 | 好 | **优秀** | ↑ |

---

## 6. 下一步建议

### 优先级 P1（推荐在专利提交前完成）

1. **ANN 签名诊断对齐**：在 benchmark 中增加 cluster-level signature quality 诊断，消除"签名门 false 但运行正常"的认知矛盾。或在文档中明确解释 fragment-level vs cluster-level 的差异。

2. **ANN 默认配置决策**：当前 tables=3 在 fragment 级别 signature_gate=false，在 cluster 级别 max_bucket_ratio=61%。建议：
   - 方案 A：默认 tables=4（sweep 显示 4 表有更好签名质量），接受 N=3 → N=4 的开销增加
   - 方案 B：维持 tables=3 但在文档中明确标注"默认 ANN 仅作为轻量级候选缩减，签名质量不满足严格门"

### 优先级 P2（可选改进）

3. **Candidate radius=3 正加速配置推广**：Stage3 扫描发现 8 组全门通过配置，其中 radius=3 有正加速。建议提供"双档推荐"文档：默认安全档 (radius=4) 和高性能档 (radius=3, steps=32, neighbors=48)。

4. **核心实验增强**：
   - DMG realistic 场景仍然 gain=0，可尝试设计更激进的 realistic 半真实数据模板来触发 DMG
   - 考虑 N=10000 规模测试（如 stress 成本可控）

### 优先级 P3（长期）

5. 投影步数自适应（根据输入向量稀疏度动态调整）
6. 半真实数据集领域扩展（医疗/法律/金融领域模板）

---

## Self-Check SC-R023-Opus

1. 57/57 测试全部通过：**确认**
2. cluster.py 全量审查（含构造器参数对齐验证）：**确认**
3. 独立参数漂移验证（10 字段逐一比对）：**确认**
4. 独立 Candidate 等效性验证（merges 77=77）：**确认**
5. ANN fallback 行为深度调查（fragment vs cluster centroid）：**确认**
6. 实验数据交叉验证（5 组 benchmark/experiment）：**确认**
7. FINAL_REPORT 与 JSON 数据一致性：**确认**
8. 验证脚本写入 `tmp_r023_verify.py` + `tmp_r023_ann_check.py`：**确认**
