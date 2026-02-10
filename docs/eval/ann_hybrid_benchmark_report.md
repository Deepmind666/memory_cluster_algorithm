# ANN Hybrid Benchmark

- generated_at: 2026-02-10T17:09:08.912401+00:00
- fragment_count: 120
- prune_dims: 48
- candidate_bucket_dims: 10
- candidate_max_neighbors: 24
- ann_num_tables: 6
- ann_bits_per_table: 10
- ann_probe_radius: 1
- ann_max_neighbors: 48
- ann_score_dims: 48

## Scenario: sparse_no_merge_case
- similarity_threshold: 2.0
- merge_threshold: 0.95

### Variant: baseline_exact
- avg_ms: 321.824
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 258.182
- merge_attempts: 7140
- merges_applied: 0
- merge_pairs_pruned_by_bound: 3970
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 200.13
- merge_attempts: 2580
- merges_applied: 0
- merge_pairs_pruned_by_bound: 1495
- merge_pairs_skipped_by_candidate_filter: 4560
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 285.224
- merge_attempts: 4353
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2408
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 2787
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 289.054
- merge_attempts: 4485
- merges_applied: 0
- merge_pairs_pruned_by_bound: 2540
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 2655

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=0.197754, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=0.378138, attempt_reduction_ratio=0.638655, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=0.113727, attempt_reduction_ratio=0.390336, quality_gate_pass=True
- hybrid_prune: avg_speedup_ratio=0.101826, attempt_reduction_ratio=0.371849, quality_gate_pass=True

## Scenario: merge_active_case
- similarity_threshold: 0.82
- merge_threshold: 0.85

### Variant: baseline_exact
- avg_ms: 259.054
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 0
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: prune_only
- avg_ms: 265.022
- merge_attempts: 4971
- merges_applied: 29
- merge_pairs_pruned_by_bound: 446
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: candidate_prune
- avg_ms: 217.566
- merge_attempts: 3115
- merges_applied: 29
- merge_pairs_pruned_by_bound: 334
- merge_pairs_skipped_by_candidate_filter: 1856
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: ann_prune
- avg_ms: 300.729
- merge_attempts: 4180
- merges_applied: 29
- merge_pairs_pruned_by_bound: 168
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 791
- merge_pairs_skipped_by_hybrid_candidates: 0

### Variant: hybrid_prune
- avg_ms: 305.436
- merge_attempts: 4597
- merges_applied: 29
- merge_pairs_pruned_by_bound: 357
- merge_pairs_skipped_by_candidate_filter: 0
- merge_pairs_skipped_by_ann_candidates: 0
- merge_pairs_skipped_by_hybrid_candidates: 374

### Comparison vs baseline_exact
- prune_only: avg_speedup_ratio=-0.023038, attempt_reduction_ratio=0.0, quality_gate_pass=True
- candidate_prune: avg_speedup_ratio=0.160152, attempt_reduction_ratio=0.373366, quality_gate_pass=True
- ann_prune: avg_speedup_ratio=-0.160874, attempt_reduction_ratio=0.159123, quality_gate_pass=True
- hybrid_prune: avg_speedup_ratio=-0.179044, attempt_reduction_ratio=0.075236, quality_gate_pass=True
