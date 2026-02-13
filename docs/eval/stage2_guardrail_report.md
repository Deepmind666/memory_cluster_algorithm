# Stage-2 Guardrail Check

- generated_at: 2026-02-13T12:08:58.442299+00:00
- passed: True
- blocker_failures: 0
- warning_failures: 1
- fast_profile_loss_at_synthetic_n240: True

## Checks
- [x] candidate_default_quality_synthetic (severity=blocker): Synthetic active profile default(r=4) must keep zero-loss quality gate across all sizes.
- [x] candidate_default_quality_realistic (severity=blocker): Semi-real realistic profile default(r=4) must keep zero-loss quality gate across all sizes.
- [x] candidate_default_quality_stress (severity=blocker): Semi-real stress profile default(r=4) must keep zero-loss quality gate across all sizes.
- [x] candidate_default_n240_synthetic (severity=blocker): Synthetic active N=240 must preserve merges/cluster count for default(r=4).
- [x] candidate_fast_n240_known_loss (severity=warning): Known limitation accepted: fast(r=3) can be lossy at synthetic active N=240.
- [x] ann_runtime_signature_gate (severity=blocker): ANN runtime signature gate must pass to avoid degenerate candidate routing.
- [x] ann_active_quality_ann_prune (severity=blocker): ANN active ann_prune must keep quality gate pass (cluster/merge/conflict equality).
- [x] ann_active_quality_hybrid_prune (severity=blocker): ANN active hybrid_prune must keep quality gate pass (cluster/merge/conflict equality).
- [x] ann_active_speed_regression_warn (severity=warning): ANN active speed must not degrade beyond floor -0.200; current=-0.096610.
- [ ] ann_active_positive_speed_target_warn (severity=warning): ANN active speed target is positive speedup (> 0.0).
- [x] candidate_benchmark_active_quality (severity=blocker): Candidate benchmark active case quality gate must pass.
- [x] candidate_active_speed_regression_warn (severity=warning): Candidate active speed must not degrade beyond floor -0.200; current=0.046391.

## Raw JSON
- {"generated_at": "2026-02-13T12:08:58.442299+00:00", "summary": {"passed": true, "check_count": 12, "blocker_failures": 0, "warning_failures": 1}, "known_limitations": {"fast_profile_loss_at_synthetic_n240": true, "ann_active_not_positive_speedup": true, "candidate_active_speed": 0.046391, "ann_active_speed": -0.09661}, "checks": [{"name": "candidate_default_quality_synthetic", "passed": true, "severity": "blocker", "detail": "Synthetic active profile default(r=4) must keep zero-loss quality gate across all sizes."}, {"name": "candidate_default_quality_realistic", "passed": true, "severity": "blocker", "detail": "Semi-real realistic profile default(r=4) must keep zero-loss quality gate across all sizes."}, {"name": "candidate_default_quality_stress", "passed": true, "severity": "blocker", "detail": "Semi-real stress profile default(r=4) must keep zero-loss quality gate across all sizes."}, {"name": "candidate_default_n240_synthetic", "passed": true, "severity": "blocker", "detail": "Synthetic active N=240 must preserve merges/cluster count for default(r=4)."}, {"name": "candidate_fast_n240_known_loss", "passed": true, "severity": "warning", "detail": "Known limitation accepted: fast(r=3) can be lossy at synthetic active N=240."}, {"name": "ann_runtime_signature_gate", "passed": true, "severity": "blocker", "detail": "ANN runtime signature gate must pass to avoid degenerate candidate routing."}, {"name": "ann_active_quality_ann_prune", "passed": true, "severity": "blocker", "detail": "ANN active ann_prune must keep quality gate pass (cluster/merge/conflict equality)."}, {"name": "ann_active_quality_hybrid_prune", "passed": true, "severity": "blocker", "detail": "ANN active hybrid_prune must keep quality gate pass (cluster/merge/conflict equality)."}, {"name": "ann_active_speed_regression_warn", "passed": true, "severity": "warning", "detail": "ANN active speed must not degrade beyond floor -0.200; current=-0.096610."}, {"name": "ann_active_positive_speed_target_warn", "passed": false, "severity": "warning", "detail": "ANN active speed target is positive speedup (> 0.0)."}, {"name": "candidate_benchmark_active_quality", "passed": true, "severity": "blocker", "detail": "Candidate benchmark active case quality gate must pass."}, {"name": "candidate_active_speed_regression_warn", "passed": true, "severity": "warning", "detail": "Candidate active speed must not degrade beyond floor -0.200; current=0.046391."}]}
