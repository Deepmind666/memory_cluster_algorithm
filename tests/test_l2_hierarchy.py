from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


class TestL2Hierarchy(unittest.TestCase):
    def test_l2_clusters_generated_with_parent_child_links(self) -> None:
        fragments = [
            MemoryFragment(
                id="l21",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:00:00+08:00",
                content="method topic alpha first",
                type="decision",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="l22",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:01:00+08:00",
                content="method topic beta second",
                type="decision",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="l23",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:02:00+08:00",
                content="method topic gamma third",
                type="decision",
                tags={"category": "method"},
            ),
        ]
        pref = PreferenceConfig.from_dict({"enable_l2_clusters": True, "l2_min_children": 2})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=0.99,
            merge_threshold=0.99,
        )

        l2_clusters = [cluster for cluster in result.clusters if cluster.level == 2]
        self.assertEqual(len(l2_clusters), 1)
        topic = l2_clusters[0]
        self.assertEqual(len(topic.child_cluster_ids), 3)
        self.assertEqual(result.metrics["l2_cluster_count"], 1)
        self.assertEqual(result.metrics["l1_cluster_count"], 3)
        self.assertEqual(result.metrics["cluster_count"], 4)

        children = [cluster for cluster in result.clusters if cluster.level == 1]
        for child in children:
            self.assertEqual(child.parent_cluster_id, topic.cluster_id)

    def test_l2_disabled_keeps_single_level(self) -> None:
        fragments = [
            MemoryFragment(
                id="l24",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:00:00+08:00",
                content="requirement A",
                type="requirement",
                tags={"category": "requirement"},
            ),
            MemoryFragment(
                id="l25",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:01:00+08:00",
                content="requirement B",
                type="requirement",
                tags={"category": "requirement"},
            ),
        ]
        result = build_cluster_result(
            fragments=fragments,
            preference_config=PreferenceConfig(),
            similarity_threshold=0.99,
            merge_threshold=0.99,
        )
        self.assertEqual(result.metrics["l2_cluster_count"], 0)
        self.assertEqual(result.metrics["cluster_count"], result.metrics["l1_cluster_count"])


if __name__ == "__main__":
    unittest.main()
