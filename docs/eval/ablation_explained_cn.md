# 消融实验解读（CN 快申）

最后更新：2026-02-10  
原始数据：`outputs/ablation_metrics.json`  
自动报告：`docs/eval/ablation_report_cn.md`

## 1. 实验目的
验证三项新增能力不是“写在文档里”，而是会改变可测指标：
1. CEG：冲突证据图
2. ARB：自适应预算
3. DMG：双通道合并门控

## 2. 场景说明
- 使用 `synthetic_conflict_memory_case` 数据。
- 同时包含：
  - 语义接近但槽位冲突的 `mode=fast/safe` 片段
  - 参数冲突 `alpha=0.7/0.2` 片段
  - 噪声与任务保护片段

## 3. 关键结论
### 3.1 CEG 生效
- 对比 baseline，CEG 组的冲突优先级相关指标显著提升：
  - `top1_conflict_priority_gain = +8.8`
  - `conflict_priority_avg_gain = +8.8`
- 说明冲突不仅被记录，还被结构化成可排序、可检索的“证据图强度”。

### 3.2 ARB 生效
- 对比 baseline，ARB 组预算与摘要长度上升：
  - `detail_budget_avg_gain = +68.0`
  - `avg_summary_chars_gain = +209.0`
- 说明预算已从固定值改为按簇复杂度动态分配。

### 3.3 DMG 生效
- 对比 baseline，DMG 组减少了错误混合簇：
  - `mixed_mode_clusters_reduction = 1`
  - `merge_block_gain = +4`
  - `cluster_count_delta = +2`
- 说明“语义像但槽位冲突”的簇被门控阻断，不再直接合并。

## 4. 解释边界
- DMG 使簇更分离，可能降低“把冲突放在同一簇”的概率，这是策略取舍，不是 bug。
- FULL 组合结果需要结合业务目标解释：是追求“冲突集中展示”还是“冲突隔离避免误合并”。

## 5. 复现实验
```powershell
python scripts/run_ablation.py --output outputs/ablation_metrics.json --report docs/eval/ablation_report_cn.md
```
