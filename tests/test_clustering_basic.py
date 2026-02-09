from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


class TestClusteringBasic(unittest.TestCase):
    def test_similar_fragments_cluster_together(self) -> None:
        fragments = [
            MemoryFragment(
                id="a1",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:00:00+08:00",
                content="实现语义聚类模块并保留 backrefs 索引",
                type="decision",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="a2",
                agent_id="writer_agent",
                timestamp="2026-02-09T09:01:00+08:00",
                content="请实现语义聚类模块，保留 backrefs 引用索引",
                type="draft",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="a3",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:02:00+08:00",
                content="会议安排到周三下午三点",
                type="log",
                tags={"category": "noise"},
            ),
        ]

        result = build_cluster_result(
            fragments=fragments,
            preference_config=PreferenceConfig(),
            similarity_threshold=0.25,
            merge_threshold=0.92,
        )

        self.assertEqual(result.metrics["fragment_count"], 3)
        self.assertEqual(result.metrics["cluster_count"], 2)
        sizes = sorted(len(cluster.fragment_ids) for cluster in result.clusters)
        self.assertEqual(sizes, [1, 2])


if __name__ == "__main__":
    unittest.main()
