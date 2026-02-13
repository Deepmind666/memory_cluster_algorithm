from __future__ import annotations

import unittest

from scripts.run_core_claim_stability import compute_distribution_stats


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


if __name__ == "__main__":
    unittest.main()
