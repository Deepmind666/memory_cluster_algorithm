# ANN Hybrid Benchmark

- generated_at: 2026-02-11T03:12:22.756802+00:00
- fragment_count: 120
- prune_dims: 48
- candidate_bucket_dims: 10
- candidate_max_neighbors: 48
- ann_num_tables: 6
- ann_bits_per_table: 10
- ann_probe_radius: 1
- ann_max_neighbors: 48
- ann_score_dims: 48

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95

### Variant: baseline_exact
- avg_ms: 284.685
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 228.53
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 3970
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 302.952
- merge_attempts: 4479
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2534
- merge_pairs_skipped_by_candidate_filter: 2661
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 257.009
- merge_attempts: 4353
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2408
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 2787
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 364.884
- merge_attempts: 4353
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2408
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 2787

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=0.197253, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=-0.064166, attempt_reduction_ratio=0.372689, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=0.097216, attempt_reduction_ratio=0.390336, quality_gate_pass=True
- hybrid_prune: avg_speedup_ratio=-0.281711, attempt_reduction_ratio=0.390336, quality_gate_pass=True

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85

### Variant: baseline_exact
- avg_ms: 231.876
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 230.676
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 446
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 260.177
- merge_attempts: 3654
- merges_applied: 29
- merge_pairs_pruned_by_bound: 247
- merge_pairs_skipped_by_candidate_filter: 1317
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 254.366
- merge_attempts: 3469
- merges_applied: 28
- merge_pairs_pruned_by_bound: 72
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 1710
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 354.397
- merge_attempts: 3477
- merges_applied: 29
- merge_pairs_pruned_by_bound: 93
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 1494

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=0.005175, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=-0.122052, attempt_reduction_ratio=0.264937, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=-0.096991, attempt_reduction_ratio=0.302152, quality_gate_pass=False
- hybrid_prune: avg_speedup_ratio=-0.52839, attempt_reduction_ratio=0.300543, quality_gate_pass=True
