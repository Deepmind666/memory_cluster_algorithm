# Merge Upper-Bound Prune Benchmark

- generated_at: 2026-02-11T04:56:46.305627+00:00
- fragment_count: 100
- primary_similarity_threshold: 0.82
- primary_merge_threshold: 0.85

## Primary Scenario: merge_active_case
### Baseline (prune off)
- avg_ms: 16.025
- p95_ms: 17.493
- merge_attempts: 7
- merges_applied: 1

### Optimized (prune on)
- avg_ms: 16.914
- p95_ms: 16.748
- merge_attempts: 7
- merges_applied: 1
- merge_pairs_pruned_by_bound: 0

### Summary
- avg_ms_delta: 0.889
- avg_speedup_ratio: -0.055476
- cluster_count_equal: True
- merge_activity_present: True

## Secondary Scenario: realistic_068_082_case
- similarity_threshold: 0.68
- merge_threshold: 0.82
### Baseline (prune off)
- avg_ms: 12.534
- merge_attempts: 0
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 14.579
- merge_attempts: 0
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
### Summary
- avg_ms_delta: 2.045
- avg_speedup_ratio: -0.163156
- cluster_count_equal: True
- merge_activity_present: False

## Secondary Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (prune off)
- avg_ms: 218.614
- merge_attempts: 4950
- merges_applied: 0
### Optimized (prune on)
- avg_ms: 167.471
- merge_attempts: 4950
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2519
### Summary
- avg_ms_delta: -51.143
- avg_speedup_ratio: 0.233942
- cluster_count_equal: True
- merge_activity_present: False
