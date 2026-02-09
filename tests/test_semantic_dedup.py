from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


class TestSemanticDedup(unittest.TestCase):
    def test_near_duplicate_fragments_reduce_backrefs(self) -> None:
        fragments = [
            MemoryFragment(
                id="d1",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:00:00+08:00",
                content="实现语义聚类模块并保留冲突证据链",
                type="draft",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="d2",
                agent_id="planner_agent",
                timestamp="2026-02-09T10:01:00+08:00",
                content="实现语义聚类模块并保留冲突证据链",
                type="decision",
                tags={"category": "method"},
            ),
            MemoryFragment(
                id="d3",
                agent_id="planner_agent",
                timestamp="2026-02-09T10:02:00+08:00",
                content="实现语义聚类模块并保留冲突证据链。",  # punctuation difference
                type="decision",
                tags={"category": "method"},
            ),
        ]
        pref = PreferenceConfig.from_dict({"semantic_dedup_threshold": 0.85})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=0.0,
            merge_threshold=0.95,
        )

        cluster = result.clusters[0]
        self.assertEqual(len(cluster.fragment_ids), 3)
        self.assertLess(len(cluster.backrefs), len(cluster.fragment_ids))


if __name__ == "__main__":
    unittest.main()
