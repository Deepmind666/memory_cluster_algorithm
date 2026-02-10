# Merge Upper-Bound Prune Benchmark

- generated_at: 2026-02-10T02:47:33.100773+00:00
- fragment_count: 100
- primary_similarity_threshold: 0.82
- primary_merge_threshold: 0.85

## Primary Scenario: merge_active_case
### Baseline (prune off)
- avg_ms: 13.949
- p95_ms: 14.315
- merge_attempts: 7
- merges_applied: 1

### Optimized (prune on)
- avg_ms: 13.61
- p95_ms: 14.054
- merge_attempts: 7
- merges_applied: 1
- merge_pairs_pruned_by_bound: 0

### Summary
- avg_ms_delta: -0.339
- avg_speedup_ratio: 0.024303
- cluster_count_equal: True
- merge_activity_present: True

## Secondary Scenario: realistic_068_082_case
- similarity_threshold: 0.68
- merge_threshold: 0.82
### Baseline (prune off)
- avg_ms: 10.003
- merge_attempts: 0
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 9.921
- merge_attempts: 0
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
### Summary
- avg_ms_delta: -0.082
- avg_speedup_ratio: 0.008198
- cluster_count_equal: True
- merge_activity_present: False

## Secondary Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (prune off)
- avg_ms: 198.604
- merge_attempts: 4950
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 165.13
- merge_attempts: 4950
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2519
### Summary
- avg_ms_delta: -33.474
- avg_speedup_ratio: 0.168546
- cluster_count_equal: True
- merge_activity_present: False
