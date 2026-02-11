# Ablation Report (CN Fast-Track)

- generated_at: 2026-02-11T03:12:55.234689+00:00
- dataset: synthetic_conflict_memory_case_stress
- fragment_count: 100
- similarity_threshold: 1.1
- merge_threshold: 0.05

## Scenarios
- baseline: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=0.0, detail_budget_avg=220.0, merges_blocked_by_guard=0
- ceg: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=17.0, detail_budget_avg=220.0, merges_blocked_by_guard=0
- arb: cluster_count=1, mixed_mode_clusters=1, conflict_priority_avg=0.0, detail_budget_avg=278.0, merges_blocked_by_guard=0
- dmg: cluster_count=4, mixed_mode_clusters=0, conflict_priority_avg=0.0, detail_budget_avg=220.0, merges_blocked_by_guard=120
- full: cluster_count=4, mixed_mode_clusters=0, conflict_priority_avg=1.45, detail_budget_avg=241.25, merges_blocked_by_guard=120

## Summary
- ceg_top1_conflict_priority_gain: 17.0
- ceg_conflict_priority_avg_gain: 17.0
- arb_detail_budget_avg_gain: 58.0
- arb_avg_summary_chars_gain: 209.0
- dmg_mixed_mode_clusters_reduction: 1
- dmg_merge_block_gain: 120
- dmg_cluster_count_delta: 3
- full_mixed_mode_clusters_reduction_vs_baseline: 1
- full_detail_budget_avg_gain_vs_baseline: 21.25
- full_merge_block_gain_vs_baseline: 120
- sanity_baseline_cluster_count: 1
- sanity_full_cluster_count: 4
- sanity_baseline_conflict_count: 2
- sanity_full_conflict_count: 1
- mixed_mode_clusters_reduction: 1

## Summary (Raw JSON)
- {"ceg": {"top1_conflict_priority_gain": 17.0, "conflict_priority_avg_gain": 17.0}, "arb": {"detail_budget_avg_gain": 58.0, "avg_summary_chars_gain": 209.0}, "dmg": {"mixed_mode_clusters_reduction": 1, "merge_block_gain": 120, "cluster_count_delta": 3}, "full": {"mixed_mode_clusters_reduction_vs_baseline": 1, "detail_budget_avg_gain_vs_baseline": 21.25, "merge_block_gain_vs_baseline": 120}, "sanity_checks": {"baseline_cluster_count": 1, "full_cluster_count": 4, "baseline_conflict_count": 2, "full_conflict_count": 1}, "mixed_mode_clusters_reduction": 1}
