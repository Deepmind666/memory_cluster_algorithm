# Merge Upper-Bound Prune Benchmark

- generated_at: 2026-02-11T03:12:37.718163+00:00
- fragment_count: 100
- primary_similarity_threshold: 0.82
- primary_merge_threshold: 0.85

## Primary Scenario: merge_active_case
### Baseline (prune off)
- avg_ms: 15.632
- p95_ms: 16.824
- merge_attempts: 7
- merges_applied: 1

### Optimized (prune on)
- avg_ms: 15.629
- p95_ms: 16.083
- merge_attempts: 7
- merges_applied: 1
- merge_pairs_pruned_by_bound: 0

### Summary
- avg_ms_delta: -0.003
- avg_speedup_ratio: 0.000192
- cluster_count_equal: True
- merge_activity_present: True

## Secondary Scenario: realistic_068_082_case
- similarity_threshold: 0.68
- merge_threshold: 0.82
### Baseline (prune off)
- avg_ms: 11.624
- merge_attempts: 0
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 11.73
- merge_attempts: 0
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
### Summary
- avg_ms_delta: 0.106
- avg_speedup_ratio: -0.009119
- cluster_count_equal: True
- merge_activity_present: False

## Secondary Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (prune off)
- avg_ms: 200.096
- merge_attempts: 4950
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 165.723
- merge_attempts: 4950
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2519
### Summary
- avg_ms_delta: -34.373
- avg_speedup_ratio: 0.171783
- cluster_count_equal: True
- merge_activity_present: False
