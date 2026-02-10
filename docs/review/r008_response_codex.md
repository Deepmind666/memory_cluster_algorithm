# R-008 Review Response (Codex)

更新时间：2026-02-10  
输入评审：Claude4.6 R-008 严格评审  
目标：逐项对齐并给出处置状态（已修复/部分修复/暂缓）

---

## 1. P1 项响应

### P1-1 `cluster_count_equal=true` 结论空洞
- 评审意见：`similarity_threshold=2.0` 导致 0 次合并，`100==100` 结论不充分。
- 处置：**已修复**
- 修复内容：
  - `scripts/run_prune_benchmark.py` 增加多场景输出：
    - `merge_active_case`（primary）
    - `realistic_068_082_case`
    - `sparse_no_merge_case`
  - 在 summary 中新增 `merge_activity_present`，标记“是否发生真实 merge 活动”。
- 证据：
  - `scripts/run_prune_benchmark.py`
  - `outputs/prune_benchmark.json`
  - `docs/eval/prune_benchmark_report.md`

### P1-2 report 与 JSON 数据不一致
- 评审意见：`report.md` 与 `outputs/prune_benchmark.json` 数值来自不同运行。
- 处置：**已修复**
- 修复内容：
  - 报告内容改为完全由同次运行 `payload` 生成；
  - 新增 `generated_at` 字段用于对应同一批结果。
- 证据：
  - `scripts/run_prune_benchmark.py`
  - `docs/eval/prune_benchmark_report.md`
  - `outputs/prune_benchmark.json`

---

## 2. P2 项响应

### P2-1 `_parse_iso` 重复实现
- 处置：**已修复**
- 修复内容：
  - 新增共享工具：`src/memory_cluster/time_utils.py::parse_iso_utc`
  - `retrieve.py` 与 `preference.py` 已接入。
- 证据：
  - `src/memory_cluster/time_utils.py`
  - `src/memory_cluster/retrieve.py`
  - `src/memory_cluster/preference.py`
  - `tests/test_time_utils.py`

### P2-2 patent_kit 08/05 缺口
- 处置：**已修复（本轮范围）**
- 修复内容：
  - `08` 增加“最接近现有技术-区别特征-技术效果”三联表；
  - `05` 增加量化结果章节（ablation + prune benchmark 实测值）。
- 证据：
  - `docs/patent_kit/08_对比文件与绕开说明.md`
  - `docs/patent_kit/05_具体实施方式.md`

### P2-3 Prune 未入权利要求
- 处置：**已修复**
- 修复内容：
  - 新增从属权利要求 17（上界剪枝）。
- 证据：
  - `docs/patent_kit/06_权利要求书_草案.md`

### P2-4 bound_cache 重建冗余
- 处置：**暂缓**
- 理由：
  - 当前实现正确性与可解释性优先，重建开销在现规模下可接受；
  - 后续与 ANN/桶化一起做一轮性能重构更稳妥。

### P2-5 Windows GBK 乱码
- 处置：**暂缓**
- 理由：
  - 数据文件使用 UTF-8 正常，问题主要在控制台显示层；
  - 计划通过文档化与可选编码设置处理，不阻塞算法正确性。

### P2-6 ingest 无幂等
- 处置：**暂缓（高优先）**
- 理由：
  - 属于可靠性增强项，建议下一轮新增 `--skip-existing-id` 或幂等写入模式。

---

## 3. P3 项响应

- `embed/eval/store` 独立单测不足：**部分修复**（新增 `test_time_utils.py`，其余待补）
- Prune 正确性样本小：**待扩展**（计划引入更大规模样本）
- CEG 系数硬编码：**待配置化**
- DMG 过于保守：**待策略化**
- `conflict_graph` 弱类型：**待类型化**

---

## 4. 当前回归状态

- `python -m unittest discover -s tests -p "test_*.py" -q` -> **28/28 通过**（含后续可靠性闸门新增测试）
- `python scripts/run_prune_benchmark.py --output outputs/prune_benchmark.json --report docs/eval/prune_benchmark_report.md` -> 通过

---

## 5. 下一步计划（与 R-008 对齐）

1. 可靠性增强：
- 处理 ingest 幂等与 store 容错。

2. 性能增强：
- 优化 `bound_cache` 重建策略，减少重复构建。

3. 语义增强：
- 扩展冲突语义规则并补反例单测。
