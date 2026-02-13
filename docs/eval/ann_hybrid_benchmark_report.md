# ANN Hybrid Benchmark

- generated_at: 2026-02-13T02:47:40.355534+00:00
- fragment_count: 120
- prune_dims: 48
- candidate_bucket_dims: 10
- candidate_max_neighbors: 48
- candidate_projection_steps: 32
- candidate_signature_radius: 4
- ann_num_tables: 3
- ann_bits_per_table: 10
- ann_probe_radius: 1
- ann_max_neighbors: 48
- ann_score_dims: 48
- ann_projection_steps: 32
- ann_cluster_entry_count: 82
- ann_signature_runtime_min_table_unique_ratio: 0.219512
- ann_signature_runtime_max_table_bucket_ratio: 0.487805
- ann_signature_runtime_table0_weight_spread: 4
- ann_signature_fragment_min_table_unique_ratio: 0.208333
- ann_signature_fragment_max_table_bucket_ratio: 0.441667
- ann_signature_fragment_table0_weight_spread: 4
- ann_signature_gate_pass_cluster_runtime: True
- ann_signature_gate_pass_cluster_strict: False
- ann_signature_gate_pass_fragment_strict: False

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95

### Variant: baseline_exact
- avg_ms: 296.223
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 237.449
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 3970
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 255.314
- merge_attempts: 4475
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2526
- merge_pairs_skipped_by_candidate_filter: 2665
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 268.355
- merge_attempts: 4167
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2265
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 2973
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 345.13
- merge_attempts: 4868
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2624
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 2272

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=0.198411, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=0.138102, attempt_reduction_ratio=0.373249, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=0.094078, attempt_reduction_ratio=0.416387, quality_gate_pass=True
- hybrid_prune: avg_speedup_ratio=-0.165102, attempt_reduction_ratio=0.318207, quality_gate_pass=True

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85

### Variant: baseline_exact
- avg_ms: 216.79
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 227.001
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 446
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 249.476
- merge_attempts: 3561
- merges_applied: 29
- merge_pairs_pruned_by_bound: 251
- merge_pairs_skipped_by_candidate_filter: 1410
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 253.308
- merge_attempts: 3302
- merges_applied: 29
- merge_pairs_pruned_by_bound: 138
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 1669
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 311.946
- merge_attempts: 4018
- merges_applied: 29
- merge_pairs_pruned_by_bound: 163
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 953

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=-0.047101, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=-0.150773, attempt_reduction_ratio=0.283645, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=-0.168449, attempt_reduction_ratio=0.335747, quality_gate_pass=True
- hybrid_prune: avg_speedup_ratio=-0.438932, attempt_reduction_ratio=0.191712, quality_gate_pass=True
