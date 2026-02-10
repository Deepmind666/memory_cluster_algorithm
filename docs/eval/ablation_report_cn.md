# Ablation Report (CN Fast-Track)

- generated_at: 2026-02-10T05:04:17.454550+00:00
- dataset: synthetic_conflict_memory_case
- fragment_count: 9
- similarity_threshold: 1.1
- merge_threshold: 0.05

## Scenarios
- baseline: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=0.0, detail_budget_avg=220.0, merges_blocked_by_guard=0
- ceg: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=8.8, detail_budget_avg=220.0, merges_blocked_by_guard=0
- arb: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=0.0, detail_budget_avg=288.0, merges_blocked_by_guard=0
- dmg: cluster_count=3, mixed_mode_clusters=0, conflict_priority_avg=0.0, detail_budget_avg=220.0, merges_blocked_by_guard=4
- full: cluster_count=3, mixed_mode_clusters=0, conflict_priority_avg=0.0, detail_budget_avg=249.333, merges_blocked_by_guard=4

## Summary
- ceg_top1_conflict_priority_gain: 8.8
- ceg_conflict_priority_avg_gain: 8.8
- arb_detail_budget_avg_gain: 68.0
- arb_avg_summary_chars_gain: 209.0
- dmg_mixed_mode_clusters_reduction: 1
- dmg_merge_block_gain: 4
- dmg_cluster_count_delta: 2
- full_mixed_mode_clusters_reduction_vs_baseline: 1
- full_detail_budget_avg_gain_vs_baseline: 29.333
- full_merge_block_gain_vs_baseline: 4
- sanity_baseline_cluster_count: 1
- sanity_full_cluster_count: 3
- sanity_baseline_conflict_count: 2
- sanity_full_conflict_count: 0
- mixed_mode_clusters_reduction: 1

## Summary (Raw JSON)
- {"ceg": {"top1_conflict_priority_gain": 8.8, "conflict_priority_avg_gain": 8.8}, "arb": {"detail_budget_avg_gain": 68.0, "avg_summary_chars_gain": 209.0}, "dmg": {"mixed_mode_clusters_reduction": 1, "merge_block_gain": 4, "cluster_count_delta": 2}, "full": {"mixed_mode_clusters_reduction_vs_baseline": 1, "detail_budget_avg_gain_vs_baseline": 29.333, "merge_block_gain_vs_baseline": 4}, "sanity_checks": {"baseline_cluster_count": 1, "full_cluster_count": 3, "baseline_conflict_count": 2, "full_conflict_count": 0}, "mixed_mode_clusters_reduction": 1}
