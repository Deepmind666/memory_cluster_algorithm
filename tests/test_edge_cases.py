from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


class TestEdgeCases(unittest.TestCase):
    def test_empty_fragment_list(self) -> None:
        result = build_cluster_result(fragments=[], preference_config=PreferenceConfig())
        self.assertEqual(result.metrics["fragment_count"], 0)
        self.assertEqual(result.metrics["cluster_count"], 0)
        self.assertEqual(result.clusters, [])

    def test_strict_conflict_split_generates_child_clusters(self) -> None:
        fragments = [
            MemoryFragment(
                id="s1",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:00:00+08:00",
                content="启用缓存",
                type="result",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="s2",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:01:00+08:00",
                content="不启用缓存",
                type="result",
                tags={"category": "method"},
            ),
        ]
        pref = PreferenceConfig.from_dict({"strict_conflict_split": True})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=0.0,
            merge_threshold=0.95,
        )

        self.assertGreaterEqual(result.metrics["cluster_count"], 2)
        split_clusters = [c for c in result.clusters if c.tags.get("split_from")]
        self.assertTrue(split_clusters)


if __name__ == "__main__":
    unittest.main()
