from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def _sparse_fragments(count: int = 64) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    for idx in range(count):
        rows.append(
            MemoryFragment(
                id=f"cf{idx:03d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-10T12:{idx % 60:02d}:00+00:00",
                content=f"isolated token block_{idx} variant_{idx * 13}",
                type="log",
                tags={"category": "noise"},
                meta={"slots": {"k": str(idx)}},
            )
        )
    return rows


def _active_fragments(count: int = 80) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    for idx in range(count):
        mode = ("fast", "safe", "balanced", "strict")[idx % 4]
        alpha = ("0.2", "0.4", "0.6", "0.8")[(idx * 3) % 4]
        rows.append(
            MemoryFragment(
                id=f"ca{idx:03d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-10T13:{idx % 60:02d}:00+00:00",
                content=(
                    f"memory candidate group_{idx % 8} mode {mode} alpha {alpha} "
                    f"variant_{idx} replay token_{idx * 11}"
                ),
                type="draft" if idx % 3 else "result",
                tags={"category": "method" if idx % 3 else "evidence"},
                meta={"slots": {"mode": mode, "alpha": alpha, "group": str(idx % 8)}},
            )
        )
    return rows


class TestMergeCandidateFilter(unittest.TestCase):
    def test_candidate_filter_reduces_attempts_on_sparse_case(self) -> None:
        fragments = _sparse_fragments(64)

        pref_off = PreferenceConfig.from_dict({"enable_merge_candidate_filter": False})
        pref_on = PreferenceConfig.from_dict(
            {
                "enable_merge_candidate_filter": True,
                "merge_candidate_bucket_dims": 8,
                "merge_candidate_max_neighbors": 10,
            }
        )

        baseline = build_cluster_result(
            fragments=fragments,
            preference_config=pref_off,
            similarity_threshold=2.0,
            merge_threshold=0.95,
        )
        filtered = build_cluster_result(
            fragments=fragments,
            preference_config=pref_on,
            similarity_threshold=2.0,
            merge_threshold=0.95,
        )

        self.assertGreater(int(baseline.metrics.get("merge_attempts") or 0), 0)
        self.assertLess(
            int(filtered.metrics.get("merge_attempts") or 0),
            int(baseline.metrics.get("merge_attempts") or 0),
        )
        self.assertGreater(int(filtered.metrics.get("merge_pairs_skipped_by_candidate_filter") or 0), 0)
        self.assertEqual(
            int(filtered.metrics.get("cluster_count") or 0),
            int(baseline.metrics.get("cluster_count") or 0),
        )

    def test_candidate_filter_disabled_reports_zero_skips(self) -> None:
        fragments = _sparse_fragments(24)
        pref = PreferenceConfig.from_dict({"enable_merge_candidate_filter": False})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=1.8,
            merge_threshold=0.95,
        )
        self.assertEqual(int(result.metrics.get("merge_pairs_skipped_by_candidate_filter") or 0), 0)

    def test_candidate_filter_keeps_merge_outcome_on_active_case(self) -> None:
        fragments = _active_fragments(80)
        pref_off = PreferenceConfig.from_dict({"enable_merge_candidate_filter": False})
        pref_on = PreferenceConfig.from_dict(
            {
                "enable_merge_candidate_filter": True,
                "merge_candidate_bucket_dims": 10,
                "merge_candidate_max_neighbors": 16,
            }
        )
        baseline = build_cluster_result(
            fragments=fragments,
            preference_config=pref_off,
            similarity_threshold=0.82,
            merge_threshold=0.85,
        )
        filtered = build_cluster_result(
            fragments=fragments,
            preference_config=pref_on,
            similarity_threshold=0.82,
            merge_threshold=0.85,
        )
        self.assertEqual(
            int(filtered.metrics.get("cluster_count") or 0),
            int(baseline.metrics.get("cluster_count") or 0),
        )
        self.assertEqual(
            int(filtered.metrics.get("merges_applied") or 0),
            int(baseline.metrics.get("merges_applied") or 0),
        )
        self.assertLess(
            int(filtered.metrics.get("merge_attempts") or 0),
            int(baseline.metrics.get("merge_attempts") or 0),
        )
        self.assertGreater(int(filtered.metrics.get("merge_pairs_skipped_by_candidate_filter") or 0), 0)


if __name__ == "__main__":
    unittest.main()
