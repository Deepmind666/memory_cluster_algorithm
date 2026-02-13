# Merge Candidate Filter Benchmark

- generated_at: 2026-02-13T02:47:33.885383+00:00
- fragment_count: 120
- bucket_dims: 10
- max_neighbors: 48
- candidate_projection_steps: 32
- candidate_signature_radius: 4
- signature_unique_ratio: 0.4
- signature_max_bucket_ratio: 0.108333
- signature_gate_pass: True
- active_quality_gate_pass: True

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95
### Baseline (filter off)
- avg_ms: 298.545
- merge_attempts: 7140
- merges_applied: 0
### Optimized (filter on)
- avg_ms: 282.842
- merge_attempts: 3932
- merges_applied: 0
- merge_pairs_skipped_by_candidate_filter: 3208
### Summary
- avg_ms_delta: -15.703
- avg_speedup_ratio: 0.052598
- attempt_reduction_ratio: 0.4493
- cluster_count_equal: True
- merges_applied_equal: True
- signature_unique_ratio: 0.4
- signature_max_bucket_ratio: 0.108333
- signature_gate_pass: True
- quality_gate_pass: True
- merge_activity_present: False

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85
### Baseline (filter off)
- avg_ms: 248.827
- merge_attempts: 6468
- merges_applied: 21
### Optimized (filter on)
- avg_ms: 253.312
- merge_attempts: 4574
- merges_applied: 21
- merge_pairs_skipped_by_candidate_filter: 1894
### Summary
- avg_ms_delta: 4.485
- avg_speedup_ratio: -0.018025
- attempt_reduction_ratio: 0.292826
- cluster_count_equal: True
- merges_applied_equal: True
- signature_unique_ratio: 0.4
- signature_max_bucket_ratio: 0.108333
- signature_gate_pass: True
- quality_gate_pass: True
- merge_activity_present: True
