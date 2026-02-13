from __future__ import annotations

import unittest

from scripts.run_core_claim_stability import (
    compute_activation_metrics,
    compute_distribution_stats,
    determine_new_runs,
)


class TestCoreClaimStabilityUnit(unittest.TestCase):
    def test_compute_distribution_stats_constant_values(self) -> None:
        stats = compute_distribution_stats([2.0, 2.0, 2.0, 2.0])
        self.assertEqual(stats["mean"], 2.0)
        self.assertEqual(stats["std"], 0.0)
        self.assertEqual(stats["ci95"], 0.0)
        self.assertEqual(stats["positive_rate"], 1.0)

    def test_compute_distribution_stats_positive_rate(self) -> None:
        stats = compute_distribution_stats([-1.0, 0.0, 1.0, 2.0])
        self.assertEqual(stats["count"], 4.0)
        self.assertEqual(stats["positive_rate"], 0.5)

    def test_compute_distribution_stats_single_value_ci95_zero(self) -> None:
        stats = compute_distribution_stats([3.5])
        self.assertEqual(stats["mean"], 3.5)
        self.assertEqual(stats["ci95"], 0.0)
        self.assertEqual(stats["std"], 0.0)

    def test_compute_distribution_stats_empty_values(self) -> None:
        stats = compute_distribution_stats([])
        self.assertEqual(stats["count"], 0.0)
        self.assertEqual(stats["mean"], 0.0)
        self.assertEqual(stats["positive_rate"], 0.0)

    def test_determine_new_runs_respects_remaining_and_cap(self) -> None:
        self.assertEqual(determine_new_runs(target_runs=10, existing_runs=3, max_new_runs=0), 7)
        self.assertEqual(determine_new_runs(target_runs=10, existing_runs=3, max_new_runs=2), 2)
        self.assertEqual(determine_new_runs(target_runs=5, existing_runs=5, max_new_runs=3), 0)

    def test_compute_activation_metrics(self) -> None:
        per_run = [
            {
                "baseline": {"merges_blocked_by_guard": 0.0, "mixed_mode_clusters": 3.0},
                "dmg": {"merges_blocked_by_guard": 5.0, "mixed_mode_clusters": 1.0},
            },
            {
                "baseline": {"merges_blocked_by_guard": 0.0, "mixed_mode_clusters": 2.0},
                "dmg": {"merges_blocked_by_guard": 0.0, "mixed_mode_clusters": 2.0},
            },
        ]
        metrics = compute_activation_metrics(per_run)
        self.assertEqual(metrics["runs"], 2.0)
        self.assertEqual(metrics["dmg_guard_activation_rate"], 0.5)
        self.assertEqual(metrics["dmg_mixed_mode_reduction_rate"], 0.5)
        self.assertEqual(metrics["baseline_mixed_mode_presence_rate"], 1.0)
        self.assertEqual(metrics["dmg_effective_profile"], True)


if __name__ == "__main__":
    unittest.main()
