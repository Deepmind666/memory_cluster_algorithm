# R-022 — 半真实数据集、参数扫描与 Stage3 稳健性深度评审

- **评审人**: Claude Opus (Reviewer)
- **评审对象**: Codex R-023 全量工作（R-021 Opus 后续改进）
- **日期**: 2026-02-11
- **总体评级**: **A-**（较 R-021 Opus 的 B+ 上升半级）

---

## 0. 评审范围

| 维度 | 内容 |
|------|------|
| 代码变更 | `_projection_score` xorshift64* 内联优化；Candidate/ANN 签名退化 fallback 防线；ANN 签名缓存复用；`_hamming_neighbor_signatures` 泛化（取代 `_adjacent_signatures` + `_two_hop_signatures`）；参数默认值调整（steps=32, radius=3→4, tables=6→3→4） |
| 新增脚本 | `generate_semi_real_dataset.py`（10 模式半真实数据生成）；`run_core_ablation_on_dataset.py`（外部数据集消融）；`run_stage3_param_sweep.py`（Candidate/ANN 网格搜索） |
| 新增实验 | 半真实数据 2000 条 × realistic/stress 消融；240 条 benchmark 重跑（+warmup+多轮）；参数扫描（Candidate 16 配置 × ANN 288 配置） |
| 测试 | 57/57 通过（+4，含 2 个 benchmark 对齐测试 + 2 个 fallback 测试）|
| 文档 | FINAL_REPORT.md 重写；WORK_PROGRESS.md / .claude.md 同步 |

---

## 1. 正面评价

### 1.1 R-021 三个 P1 全部实质性解决

**P1-1（候选签名退化）→ 已修复**

| 指标 | R-021 (steps=16) | R-023 (steps=32) | 改善 |
|------|-----------------|------------------|------|
| 唯一率（benchmark 文本） | 10.8% | **24.6%** | +127% |
| 最大桶占比 | 35.4% | **10.4%** | -71% |
| Hamming 权重重心 | ~7 (偏极端) | ~4 (均匀) | ✓ |
| 质量门通过情况 | 仅 test 文本通过 | **benchmark + test 均通过** | ✓ |

steps=32 覆盖 12.5% 维度，是 steps=16 (6.25%) 的两倍。xorshift64* 内联优化使签名计算仅增加 1.51× 开销（而非预期的 2.0×）。

**P1-2（ANN 性能灾难）→ 大幅缓解**

| 配置 | 运算量/签名 | Active 加速率 |
|------|------------|-------------|
| R-021: 6表×10bit×48步 | 2880 ops | **-677%** |
| R-023: 4表×10bit×32步 | 1280 ops | **-24.9%** |

改善幅度 **27 倍**。虽然仍为负加速，但已从"性能灾难"降级为"中等开销"。

**P1-3（质量门测试覆盖缺口）→ 已修复**

新增两个 benchmark 对齐测试：
- `test_candidate_filter_default_keeps_benchmark_active_outcome`：导入 `benchmark_candidate_fragments(240)`，在 0.82/0.85 参数下用 `assertEqual` 验证 merges_applied 完全一致
- `test_ann_default_keeps_benchmark_active_outcome`：导入 `benchmark_ann_fragments(240)`，同样 `assertEqual` 验证

**这直接消除了 R-021 指出的"测试文本 vs benchmark 文本分布不同导致虚假通过"的根因。**

### 1.2 半真实数据集 — 专利核心证据质的飞跃

`generate_semi_real_dataset.py` 生成 10 种模式的记忆碎片：

| 模式 | 内容类型 | 语言 | 冲突模式 |
|------|---------|------|---------|
| 0 | 决策记录 | EN | 直接冲突 |
| 1 | 建议（否定+推荐） | **ZH** | 否定另一模式 |
| 2 | 条件句 | EN | 条件触发 |
| 3 | 不确定（"并非一定最优"） | **ZH** | 语义否定 |
| 4 | 工具日志 | EN | — (noise) |
| 5 | 全局策略 | EN | — (policy) |
| 6 | 反事实 | EN | should have / enforce |
| 7 | 条件否定 | EN | when X, do not Y |
| 8 | 条件策略 | EN | if file_path and task |
| 9 (stress) | 冲突重放 | EN | 三连冲突 |

**覆盖了冲突语义精度（条件/否定/反事实/中文）的核心场景，与权利要求 10-11 直接对应。**

半真实数据消融结果（N=2000）：

| 模块 | Realistic | Stress |
|------|-----------|--------|
| CEG | **+76.1** | **+698.8** |
| ARB | **+76.9** | +4.0 |
| DMG | 0 | **+12,373** |

**DMG +12,373 阻断**：在 stress 参数下，baseline 将 2000 条碎片合并为 **1 个巨型簇**，DMG 阻断了 12,373 次危险合并，使结果保持为 **20 个有意义的簇**。这是本项目迄今最有说服力的单项证据。

CEG +698.8 和 ARB +76.9 在 realistic 场景的大幅提升表明，半真实数据的冲突模式密度显著高于纯合成数据，核心创新的效果在更真实的场景中**更加突出**。

### 1.3 参数扫描 — 系统化验证

`run_stage3_param_sweep.py` 实现了完整的网格搜索：

- **Candidate 网格**：steps×[16,24,32,48] × radius×[2,3,4] × neighbors×[48,64] = 24 配置
- **ANN 网格**：steps×[12,16,24,32] × tables×[3,4,6] × bits×[8,10] × probe×[0,1] × neighbors×[24,32,48] = 288 配置

每个配置同时评估 sparse + active 两个场景，并计算三重门控：
1. `quality_gate`：merges_applied 等效
2. `signature_gate`：唯一率 ≥ 20%, 最大桶 ≤ 25%
3. `all_gates_pass`：上述两项同时满足

**关键发现**：
- Candidate 最优配置：steps=32, radius=3, neighbors=48（与当前默认一致）
- ANN 在当前搜索空间内无"三门全通过 + 正加速"的配置
- 这为"Candidate/ANN 保留为可选实施例"的决策提供了系统化证据

### 1.4 Fallback 机制 — 工程健壮性提升

```python
unique_ratio, max_bucket_ratio = self._signature_bucket_quality(bucket_to_ids, total=len(clusters))
if unique_ratio < 0.18 or max_bucket_ratio > 0.90:
    self.merge_candidate_filter_fallbacks += 1
    return None  # 回退到精确计算
```

- 当签名退化（如全零向量输入）时，自动回退到精确匹配，避免质量损失
- 新增 `merge_candidate_filter_fallbacks` / `merge_ann_candidate_fallbacks` 计数器，可审计
- 两个 fallback 测试覆盖退化输入场景

### 1.5 `_projection_score` xorshift64* 优化

```python
# 旧版：每步调用 _mix64（3 次乘法 + 3 次移位）
sign_seed = seed ^ ((step + 1) * 0xD6E8FEB86659FD93)
sign = 1.0 if (self._mix64(sign_seed) & 1) == 0 else -1.0

# 新版：xorshift64*（仅移位和 XOR，无乘法）
state ^= (state >> 12)
state ^= ((state << 25) & mask_64)
state ^= (state >> 27)
sign = 1.0 if (state & 1) == 0 else -1.0
```

附加优化：power-of-two 维度用 `& dim_mask` 替代 `% dim`（HashEmbeddingProvider dim=256 恒适用）。

实测：32 步签名仅比 16 步慢 1.51×（而非 2.0×），部分得益于此优化。

### 1.6 `_hamming_neighbor_signatures` 泛化

原先需要 `_adjacent_signatures`（距离 1）+ `_two_hop_signatures`（距离 2）两个方法，现在用 `itertools.combinations` 实现任意 Hamming 距离的邻域生成。代码更简洁，支持 radius=3/4 等更大搜索范围。

---

## 2. 需要关注的问题

### P2-1: cluster.py ↔ models.py 默认参数漂移

**严重等级: P2**

| 参数 | cluster.py 默认 | models.py 默认 |
|------|----------------|---------------|
| `merge_ann_num_tables` | **4** | **3** |
| `merge_ann_max_neighbors` | **32** | **48** |

`pipeline.py` 通过 `PreferenceConfig` → `IncrementalClusterer` 传递参数，实际使用 models.py 默认值。直接构造 `IncrementalClusterer()` 的单元测试使用 cluster.py 默认值。

**影响**：测试用 tables=4 验证通过，但生产路径实际用 tables=3 运行。虽然两种配置都能正常工作，但参数漂移增加了维护负担和理解成本。

**建议**：将 cluster.py 和 models.py 的默认值统一。pipeline.py 已经显式传递所有参数，只需保持两处一致即可。

### P2-2: Candidate active 场景 benchmark 仍有边际质量风险

FINAL_REPORT 显示 candidate active merges: 77→76（丢失 1 合并）。这是在 benchmark 脚本自身参数下运行的结果。

但新测试 `test_candidate_filter_default_keeps_benchmark_active_outcome` 使用 **models.py 默认参数（radius=4）** 对相同的 benchmark 数据通过了 `assertEqual`。这意味着 radius=4 足以恢复等效性，但 FINAL_REPORT 的 benchmark 运行可能使用了不同的 radius 值。

**建议**：确认 benchmark 脚本的默认 radius 与 models.py 一致（应为 4），并重新运行 benchmark 以验证 77→76 是否已解决。

### P2-3: ANN 签名质量为性能交换

| 配置 | 唯一率 (benchmark) | 最大桶 | 运算量 |
|------|-------------------|--------|--------|
| R-021: 6表×48步 | **32.1%** | 10.0% | 2880 ops |
| R-023: 4表×32步 | 20.4% | 15.4% | 1280 ops |

ANN 签名唯一率从 32.1% 降至 20.4%，这是减少表数和步数的预期代价。当前 20.4% 刚好超过 fallback 阈值（18%），安全余量仅 2.4 个百分点。

**风险**：若输入分布变化（如更稀疏的嵌入），20.4% 可能跌破 18%，触发全面 fallback。

### P2-4: `arb_stale_penalty` 0.35→0.25 未记录理由

模型默认值变更但缺乏变更理由或关联的实验数据。

### P2-5: Hamming radius=4 覆盖率过高

| Radius | 桶探测数 | 覆盖率 |
|--------|---------|--------|
| 2 | 56/1024 | 5.5% |
| 3 | 176/1024 | 17.2% |
| **4** | **386/1024** | **37.7%** |

radius=4 使每个簇的邻域覆盖 37.7% 的签名空间。对于 240 个簇仅占 ~59 个桶的数据分布，这几乎是"全扫描"——候选筛选的裁剪效果被高 radius 抵消。

**数据佐证**：FINAL_REPORT 显示 candidate active `avg_speedup_ratio=-105.3%`，远低于 R-021 的 -29.3%（当时 radius=2）。虽然质量保住了（新 benchmark test 通过），但性能代价过高。

**建议**：寻找 radius 和 quality 的最优平衡点。radius=3（176/1024=17.2%）可能是更好的默认值——参数扫描已证实 radius=3, steps=32 是 Candidate 最优配置。

---

## 3. 低优先级问题

### P3-1: 半真实数据的种子固定与分布偏斜

`generate_semi_real_dataset.py` 使用固定种子 `20260211`。10 种模式按 `idx % 10` 均匀分配，但 stress profile 的第 9 模式（冲突重放）仅占 10%。考虑在 stress 场景增加冲突密度模式的权重。

### P3-2: 参数扫描网格过大

ANN 网格 288 配置 × sparse + active 场景 × 3 轮 = 1728 次 build_cluster_result 调用。对于大规模数据集，这可能需要小时级运行时间。建议增加 `--quick` 模式（仅扫描关键维度）。

### P3-3: FINAL_REPORT N=2000 的 CEG 增益与 N=1000 相同

Core scaling realistic 中 N=2000 和 N=1000 的 `ceg_conflict_priority_avg_gain` 均为 +2.29。这可能是正确的（CEG 增益与规模无关），但也可能是数据未刷新。建议确认。

---

## 4. 指标汇总（R-021 → R-023 变化）

| 维度 | R-021 (Opus 评审时) | R-023 (本轮) | 变化 |
|------|-------------------|-------------|------|
| 测试通过率 | 53/53 | **57/57** | +4 |
| 候选签名唯一率 (benchmark) | 10.8% | **24.6%** | +127% |
| ANN 签名唯一率 (benchmark) | 32.1% | 20.4% | -36% (性能换质量) |
| ANN active 加速率 | **-677%** | **-24.9%** | **27× 改善** |
| Candidate active 加速率 | -29.3% | -105.3% | ↓ (radius 扩大) |
| 半真实数据集 | 无 | **2000 条 ×2 profile** | ✓✓ |
| 参数扫描 | 无 | **24+288 配置** | ✓✓ |
| Fallback 防线 | 无 | **candidate + ANN** | ✓ |
| Benchmark 对齐测试 | 无 | **2 个 assertEqual** | ✓ |
| CEG 最大增益 | +17.0 | **+698.8** (semi-real) | ✓✓ |
| DMG 最大阻断 | +735 | **+12,373** (semi-real) | ✓✓ |

---

## 5. 对专利的影响

### 5.1 核心主张（权利要求 1, 4-11）— 证据链再次增强

| 区别特征 | 合成数据 (N=1000~2000) | 半真实数据 (N=2000) | 证据评估 |
|----------|----------------------|-------------------|---------|
| CEG | +2.29 ~ +17.0 | **+76.1 ~ +698.8** | **极充分** |
| ARB | +36.0 ~ +55.0 | **+76.9** (realistic) | **极充分** |
| DMG | 0 ~ +735 | **+12,373** (stress) | **极充分** |
| 语义精度 | 8/8 pass | — | 充分 |

半真实数据的加入使证据链从"合成数据自证"提升到"准真实场景验证"。DMG 在 stress 场景阻断 12,373 次危险合并、将单簇结果恢复为 20 个有意义的簇——这是技术效果主张最有力的支撑。

### 5.2 可选实施例（权利要求 12-14）— 系统化证据确认局限性

参数扫描结果为"Candidate/ANN 作为可选实施例而非核心主张"提供了系统化依据：

- Candidate：在 24 种配置中，无一在 active 场景同时实现"等效质量 + 正加速"
- ANN：在 288 种配置中，无一在 active 场景实现"质量门 + 签名门 + 正加速"三者兼得

**建议**：在专利文本中明确标注"Candidate/ANN 提供可扩展框架，在低合并率场景有效，高合并率场景需结合具体嵌入特性调参"。

---

## 6. 下一步建议（优先级排序）

### P1 — 建议修复

| 编号 | 任务 | 说明 |
|------|------|------|
| P1-1 | 统一 cluster.py ↔ models.py 默认参数 | `merge_ann_num_tables` 和 `merge_ann_max_neighbors` 两处不一致 |
| P1-2 | 重跑 benchmark（确认 radius=4 下 77→76 是否解决） | 新 benchmark 对齐测试通过但 FINAL_REPORT 数据可能未用最新参数 |

### P2 — 应当改进

| 编号 | 任务 |
|------|------|
| P2-1 | 评估 radius=3 vs radius=4 的性能/质量平衡 |
| P2-2 | 增加半真实数据的种子多样性（3-5 个种子取均值） |
| P2-3 | 为 arb_stale_penalty 变更补充理由/实验依据 |
| P2-4 | 专利文稿与最新半真实数据消融结果逐条对齐 |

### P3 — 可延后

| 编号 | 任务 |
|------|------|
| P3-1 | 参数扫描增加 `--quick` 模式 |
| P3-2 | 确认 N=2000 realistic CEG +2.29 是否正确 |
| P3-3 | 考虑 ANN 原生 SimHash（一次全维投影）替代逐 bit 投影 |

---

## 7. 评级详述

| 维度 | 评分 | 说明 |
|------|------|------|
| R-021 P1-1 修复 (候选签名) | **A** | 唯一率 10.8%→24.6%, 质量门 benchmark+test 均通过 |
| R-021 P1-2 修复 (ANN 性能) | **A-** | -677%→-24.9%（27× 改善），仍为负加速但可接受 |
| R-021 P1-3 修复 (测试覆盖) | **A** | 直接导入 benchmark 数据 + assertEqual，根因消除 |
| 半真实数据集 | **A** | 10 模式覆盖冲突语义核心场景，DMG +12373 极有说服力 |
| 参数扫描 | **A-** | 312 配置全面搜索，为"可选实施例"决策提供系统化依据 |
| Fallback 机制 | **A** | 设计合理，测试充分，可审计 |
| xorshift64* 优化 | **A** | 正确、有效，1.51× vs 预期 2.0× |
| 参数漂移 | **C+** | cluster.py ↔ models.py 两处不一致 |
| Candidate active 性能 | **C** | -105.3%（较 R-021 的 -29.3% 恶化，因 radius 增大） |
| 整体工程质量 | **A-** | 代码清晰，新增脚本设计合理，文档同步 |

**综合评级：A-**

较 R-021 (B+) 上升半级。主要驱动因素：
1. R-021 三个 P1 全部实质性修复
2. 半真实数据集提供了项目迄今最有说服力的核心证据
3. 参数扫描为工程决策提供系统化依据
4. Fallback + 签名缓存 + xorshift64* 三重工程改善

**未达 A 的原因**：
1. cluster.py ↔ models.py 默认参数漂移
2. Candidate active 性能因 radius 扩大而恶化
3. ANN 签名质量降低（32.1%→20.4%），安全余量仅 2.4%

---

## 8. 结论

R-023 是从"修复已知问题"到"强化证据体系"的转变。半真实数据集让 CEG/ARB/DMG 的证据从合成自证升级到准真实验证——特别是 DMG 在 stress 场景下阻断 12,373 次危险合并这一数据，可能成为专利技术效果主张中最有说服力的单项证据。

参数扫描（312 配置）为"Candidate/ANN 无法在 active 场景实现全门通过+正加速"提供了系统化的否定证据，这比逐个配置试错更有说服力，也为将其定位为"可选实施例而非核心主张"提供了坚实的工程依据。

**核心建议**：
1. 统一 cluster.py 和 models.py 的默认参数（30 分钟）
2. 用统一后的参数重跑 benchmark，确认 FINAL_REPORT 数据一致性
3. 开始专利文稿收口——**当前证据链已足够支撑核心权利要求的技术效果主张**，不应再延误文稿对齐

半真实数据 + 规模化实验 + 参数扫描三重交叉验证构成了专利申请所需的完整证据体系。下一步应以"专利文稿→证据 JSON→可复现命令"三者一致性为核心目标。

---

*评审结束。如有疑问请在 `.claude.md` 中追加讨论。*
