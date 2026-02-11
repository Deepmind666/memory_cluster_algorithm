# Ablation Report (CN Fast-Track)

- generated_at: 2026-02-11T03:12:54.721921+00:00
- dataset: synthetic_conflict_memory_case_large
- fragment_count: 100
- similarity_threshold: 0.68
- merge_threshold: 0.82

## Scenarios
- baseline: cluster_count=10, mixed_mode_clusters=2, conflict_priority_avg=0.0, detail_budget_avg=207.0, merges_blocked_by_guard=0
- ceg: cluster_count=10, mixed_mode_clusters=2, conflict_priority_avg=2.29, detail_budget_avg=207.0, merges_blocked_by_guard=0
- arb: cluster_count=10, mixed_mode_clusters=2, conflict_priority_avg=0.0, detail_budget_avg=245.2, merges_blocked_by_guard=0
- dmg: cluster_count=10, mixed_mode_clusters=2, conflict_priority_avg=0.0, detail_budget_avg=207.0, merges_blocked_by_guard=0
- full: cluster_count=10, mixed_mode_clusters=2, conflict_priority_avg=2.29, detail_budget_avg=245.2, merges_blocked_by_guard=0

## Summary
- ceg_top1_conflict_priority_gain: 5.8
- ceg_conflict_priority_avg_gain: 2.29
- arb_detail_budget_avg_gain: 38.2
- arb_avg_summary_chars_gain: 64.4
- dmg_mixed_mode_clusters_reduction: 0
- dmg_merge_block_gain: 0
- dmg_cluster_count_delta: 0
- full_mixed_mode_clusters_reduction_vs_baseline: 0
- full_detail_budget_avg_gain_vs_baseline: 38.2
- full_merge_block_gain_vs_baseline: 0
- sanity_baseline_cluster_count: 10
- sanity_full_cluster_count: 10
- sanity_baseline_conflict_count: 4
- sanity_full_conflict_count: 4
- mixed_mode_clusters_reduction: 0

## Summary (Raw JSON)
- {"ceg": {"top1_conflict_priority_gain": 5.8, "conflict_priority_avg_gain": 2.29}, "arb": {"detail_budget_avg_gain": 38.2, "avg_summary_chars_gain": 64.4}, "dmg": {"mixed_mode_clusters_reduction": 0, "merge_block_gain": 0, "cluster_count_delta": 0}, "full": {"mixed_mode_clusters_reduction_vs_baseline": 0, "detail_budget_avg_gain_vs_baseline": 38.2, "merge_block_gain_vs_baseline": 0}, "sanity_checks": {"baseline_cluster_count": 10, "full_cluster_count": 10, "baseline_conflict_count": 4, "full_conflict_count": 4}, "mixed_mode_clusters_reduction": 0}
