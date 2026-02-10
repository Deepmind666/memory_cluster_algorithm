# Merge Upper-Bound Prune Benchmark

- generated_at: 2026-02-10T03:52:38.148797+00:00
- fragment_count: 100
- primary_similarity_threshold: 0.82
- primary_merge_threshold: 0.85

## Primary Scenario: merge_active_case
### Baseline (prune off)
- avg_ms: 19.84
- p95_ms: 23.697
- merge_attempts: 7
- merges_applied: 1

### Optimized (prune on)
- avg_ms: 22.565
- p95_ms: 24.664
- merge_attempts: 7
- merges_applied: 1
- merge_pairs_pruned_by_bound: 0

### Summary
- avg_ms_delta: 2.725
- avg_speedup_ratio: -0.137349
- cluster_count_equal: True
- merge_activity_present: True

## Secondary Scenario: realistic_068_082_case
- similarity_threshold: 0.68
- merge_threshold: 0.82
### Baseline (prune off)
- avg_ms: 14.009
- merge_attempts: 0
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 12.982
- merge_attempts: 0
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
### Summary
- avg_ms_delta: -1.027
- avg_speedup_ratio: 0.07331
- cluster_count_equal: True
- merge_activity_present: False

## Secondary Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (prune off)
- avg_ms: 261.007
- merge_attempts: 4950
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 225.003
- merge_attempts: 4950
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2519
### Summary
- avg_ms_delta: -36.004
- avg_speedup_ratio: 0.137943
- cluster_count_equal: True
- merge_activity_present: False
