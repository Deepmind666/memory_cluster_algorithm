# Core Scaling Benchmark Report

- generated_at: 2026-02-11T08:20:01.537293+00:00
- dataset: synthetic_core_scaling_case
- profile: stress
- runs_per_scenario: 4
- similarity_threshold: 1.1
- merge_threshold: 0.05
- counts: 500,1000

## Per Scale Summary
- N=500: ceg_gain=17.0, arb_gain=56.0, dmg_block_gain=403, dmg_mix_reduction=1, full_runtime_delta_ratio=0.021031
- N=1000: ceg_gain=17.0, arb_gain=55.0, dmg_block_gain=735, dmg_mix_reduction=1, full_runtime_delta_ratio=0.049617

## Scenario Runtime (avg_ms)
- N=500: baseline=2952.259, ceg=2955.942, arb=2980.28, dmg=3029.379, full=3014.347
- N=1000: baseline=11848.633, ceg=11829.908, arb=11893.012, dmg=12126.277, full=12436.531

## Notes
- This benchmark focuses on CEG/ARB/DMG evidence only.
- Candidate filter and ANN are excluded because they remain experimental.

## Summary (Raw JSON)
- {"counts": [500, 1000], "scales": [{"fragment_count": 500, "scenarios": {"baseline": {"runs": 4, "avg_ms": 2952.259, "p95_ms": 2980.126, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 0.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "ceg": {"runs": 4, "avg_ms": 2955.942, "p95_ms": 2964.89, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 17.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "arb": {"runs": 4, "avg_ms": 2980.28, "p95_ms": 3010.881, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 0.0, "detail_budget_avg": 276.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "dmg": {"runs": 4, "avg_ms": 3029.379, "p95_ms": 3012.322, "cluster_count": 4, "conflict_count": 1, "conflict_priority_avg": 0.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 403, "mixed_mode_clusters": 0}, "full": {"runs": 4, "avg_ms": 3014.347, "p95_ms": 3041.707, "cluster_count": 4, "conflict_count": 1, "conflict_priority_avg": 1.45, "detail_budget_avg": 237.0, "merges_blocked_by_guard": 403, "mixed_mode_clusters": 0}}, "summary": {"ceg_conflict_priority_avg_gain": 17.0, "arb_detail_budget_avg_gain": 56.0, "dmg_merge_block_gain": 403, "dmg_mixed_mode_clusters_reduction": 1, "full_conflict_priority_avg_gain": 1.45, "full_detail_budget_avg_gain": 17.0, "full_merge_block_gain": 403, "full_runtime_delta_ratio": 0.021031, "baseline_cluster_count": 1, "full_cluster_count": 4}}, {"fragment_count": 1000, "scenarios": {"baseline": {"runs": 4, "avg_ms": 11848.633, "p95_ms": 11947.262, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 0.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "ceg": {"runs": 4, "avg_ms": 11829.908, "p95_ms": 11891.19, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 17.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "arb": {"runs": 4, "avg_ms": 11893.012, "p95_ms": 11960.497, "cluster_count": 1, "conflict_count": 2, "conflict_priority_avg": 0.0, "detail_budget_avg": 275.0, "merges_blocked_by_guard": 0, "mixed_mode_clusters": 1}, "dmg": {"runs": 4, "avg_ms": 12126.277, "p95_ms": 12173.111, "cluster_count": 4, "conflict_count": 1, "conflict_priority_avg": 0.0, "detail_budget_avg": 220.0, "merges_blocked_by_guard": 735, "mixed_mode_clusters": 0}, "full": {"runs": 4, "avg_ms": 12436.531, "p95_ms": 12546.766, "cluster_count": 4, "conflict_count": 1, "conflict_priority_avg": 1.45, "detail_budget_avg": 241.75, "merges_blocked_by_guard": 735, "mixed_mode_clusters": 0}}, "summary": {"ceg_conflict_priority_avg_gain": 17.0, "arb_detail_budget_avg_gain": 55.0, "dmg_merge_block_gain": 735, "dmg_mixed_mode_clusters_reduction": 1, "full_conflict_priority_avg_gain": 1.45, "full_detail_budget_avg_gain": 21.75, "full_merge_block_gain": 735, "full_runtime_delta_ratio": 0.049617, "baseline_cluster_count": 1, "full_cluster_count": 4}}]}
