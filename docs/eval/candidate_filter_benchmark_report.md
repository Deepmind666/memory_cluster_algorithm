# Merge Candidate Filter Benchmark

- generated_at: 2026-02-10T05:38:09.634982+00:00
- fragment_count: 120
- bucket_dims: 10
- max_neighbors: 16

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (filter off)
- avg_ms: 433.954
- merge_attempts: 7140
- merges_applied: 0
### Optimized (filter on)
- avg_ms: 248.932
- merge_attempts: 1784
- merges_applied: 0
- merge_pairs_skipped_by_candidate_filter: 5356
### Summary
- avg_ms_delta: -185.022
- avg_speedup_ratio: 0.426363
- attempt_reduction_ratio: 0.75014
- cluster_count_equal: True
- merge_activity_present: False

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85
### Baseline (filter off)
- avg_ms: 360.628
- merge_attempts: 6468
- merges_applied: 21
### Optimized (filter on)
- avg_ms: 289.128
- merge_attempts: 3593
- merges_applied: 21
- merge_pairs_skipped_by_candidate_filter: 5426
### Summary
- avg_ms_delta: -71.5
- avg_speedup_ratio: 0.198265
- attempt_reduction_ratio: 0.444496
- cluster_count_equal: True
- merge_activity_present: True
