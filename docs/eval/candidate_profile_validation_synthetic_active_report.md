# Candidate Profile Validation

- generated_at: 2026-02-13T02:47:35.273147+00:00
- dataset_label: synthetic_active_ci
- source: synthetic_candidate_filter_case
- runs: 1
- warmup_runs: 0
- sizes: [240]
- similarity_threshold: 0.82
- merge_threshold: 0.85

## Per Size
### N=240
- default(r=4): speedup=-0.20409, quality_gate=True, merges_equal=True
- fast(r=3): speedup=-0.117487, quality_gate=False, merges_equal=False

## Summary
- default_all_quality_gate_pass: True
- fast_all_quality_gate_pass: False
- fast_min_speedup_ratio: -0.117487
- fast_any_positive_speedup: False
- recommendation: keep_default_radius4

## Raw JSON
- {"generated_at": "2026-02-13T02:47:35.273147+00:00", "sizes": [240], "runs": 1, "warmup_runs": 0, "similarity_threshold": 0.82, "merge_threshold": 0.85, "rows": [{"fragment_count": 240, "baseline": {"runs": 1, "avg_ms": 392.385, "p95_ms": 392.385, "metrics": {"fragment_count": 240, "cluster_count": 18, "l1_cluster_count": 18, "l2_cluster_count": 0, "original_chars": 17948, "compressed_chars": 802, "compressed_chars_all": 802, "compression_ratio": 0.044685, "dedup_reduction": 0.0, "avg_cluster_size": 13.333333, "conflict_count": 4, "conflict_cluster_rate": 0.222222, "conflict_priority_avg": 0.0, "backref_count": 240, "backref_count_all": 240, "detail_budget_avg": 220.0, "fragment_type_distribution": {"result": 80, "draft": 160}, "source_distribution": {"planner_agent": 120, "writer_agent": 120}, "merge_attempts": 2509, "merges_applied": 77, "merges_blocked_by_guard": 0, "merge_pairs_pruned_by_bound": 0, "merge_pairs_skipped_by_candidate_filter": 0, "merge_pairs_skipped_by_ann_candidates": 0, "merge_pairs_skipped_by_hybrid_candidates": 0, "merge_candidate_filter_fallbacks": 0, "merge_ann_candidate_fallbacks": 0}}, "default_profile": {"params": {"bucket_dims": 10, "max_neighbors": 48, "projection_steps": 32, "signature_radius": 4}, "case": {"runs": 1, "avg_ms": 472.467, "p95_ms": 472.467, "metrics": {"fragment_count": 240, "cluster_count": 18, "l1_cluster_count": 18, "l2_cluster_count": 0, "original_chars": 17948, "compressed_chars": 802, "compressed_chars_all": 802, "compression_ratio": 0.044685, "dedup_reduction": 0.0, "avg_cluster_size": 13.333333, "conflict_count": 4, "conflict_cluster_rate": 0.222222, "conflict_priority_avg": 0.0, "backref_count": 240, "backref_count_all": 240, "detail_budget_avg": 220.0, "fragment_type_distribution": {"result": 80, "draft": 160}, "source_distribution": {"planner_agent": 120, "writer_agent": 120}, "merge_attempts": 1872, "merges_applied": 77, "merges_blocked_by_guard": 0, "merge_pairs_pruned_by_bound": 0, "merge_pairs_skipped_by_candidate_filter": 637, "merge_pairs_skipped_by_ann_candidates": 0, "merge_pairs_skipped_by_hybrid_candidates": 0, "merge_candidate_filter_fallbacks": 0, "merge_ann_candidate_fallbacks": 0}}, "summary": {"avg_ms_delta": 80.082, "avg_speedup_ratio": -0.20409, "attempt_reduction_ratio": 0.253886, "baseline_merge_attempts": 2509, "optimized_merge_attempts": 1872, "baseline_merges_applied": 77, "optimized_merges_applied": 77, "merges_applied_equal": true, "optimized_pairs_skipped_by_candidate_filter": 637, "cluster_count_equal": true, "merge_activity_present": true}, "quality_gate_pass": true}, "fast_profile": {"params": {"bucket_dims": 10, "max_neighbors": 48, "projection_steps": 32, "signature_radius": 3}, "case": {"runs": 1, "avg_ms": 438.485, "p95_ms": 438.485, "metrics": {"fragment_count": 240, "cluster_count": 19, "l1_cluster_count": 19, "l2_cluster_count": 0, "original_chars": 17948, "compressed_chars": 843, "compressed_chars_all": 843, "compression_ratio": 0.046969, "dedup_reduction": 0.0, "avg_cluster_size": 12.631579, "conflict_count": 4, "conflict_cluster_rate": 0.210526, "conflict_priority_avg": 0.0, "backref_count": 240, "backref_count_all": 240, "detail_budget_avg": 220.0, "fragment_type_distribution": {"result": 80, "draft": 160}, "source_distribution": {"planner_agent": 120, "writer_agent": 120}, "merge_attempts": 1799, "merges_applied": 76, "merges_blocked_by_guard": 0, "merge_pairs_pruned_by_bound": 0, "merge_pairs_skipped_by_candidate_filter": 744, "merge_pairs_skipped_by_ann_candidates": 0, "merge_pairs_skipped_by_hybrid_candidates": 0, "merge_candidate_filter_fallbacks": 0, "merge_ann_candidate_fallbacks": 0}}, "summary": {"avg_ms_delta": 46.1, "avg_speedup_ratio": -0.117487, "attempt_reduction_ratio": 0.282981, "baseline_merge_attempts": 2509, "optimized_merge_attempts": 1799, "baseline_merges_applied": 77, "optimized_merges_applied": 76, "merges_applied_equal": false, "optimized_pairs_skipped_by_candidate_filter": 744, "cluster_count_equal": false, "merge_activity_present": true}, "quality_gate_pass": false}}], "summary": {"default_all_quality_gate_pass": true, "fast_all_quality_gate_pass": false, "fast_min_speedup_ratio": -0.117487, "fast_any_positive_speedup": false, "recommendation": "keep_default_radius4"}, "dataset_label": "synthetic_active_ci", "source": "synthetic_candidate_filter_case"}
