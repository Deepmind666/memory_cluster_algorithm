# Merge Candidate Filter Benchmark

- generated_at: 2026-02-11T03:10:16.731525+00:00
- fragment_count: 120
- bucket_dims: 10
- max_neighbors: 48

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (filter off)
- avg_ms: 297.209
- merge_attempts: 7140
- merges_applied: 0
### Optimized (filter on)
- avg_ms: 314.21
- merge_attempts: 3979
- merges_applied: 0
- merge_pairs_skipped_by_candidate_filter: 3161
### Summary
- avg_ms_delta: 17.001
- avg_speedup_ratio: -0.057202
- attempt_reduction_ratio: 0.442717
- cluster_count_equal: True
- merges_applied_equal: True
- merge_activity_present: False

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85
### Baseline (filter off)
- avg_ms: 253.536
- merge_attempts: 6468
- merges_applied: 21
### Optimized (filter on)
- avg_ms: 279.375
- merge_attempts: 4648
- merges_applied: 21
- merge_pairs_skipped_by_candidate_filter: 1820
### Summary
- avg_ms_delta: 25.839
- avg_speedup_ratio: -0.101915
- attempt_reduction_ratio: 0.281385
- cluster_count_equal: True
- merges_applied_equal: True
- merge_activity_present: True
