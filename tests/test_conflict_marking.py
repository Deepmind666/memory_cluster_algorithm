from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


class TestConflictMarking(unittest.TestCase):
    def test_conflicts_are_recorded(self) -> None:
        fragments = [
            MemoryFragment(
                id="c1",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:00:00+08:00",
                content="实验结论 alpha=0.7 在测试集上更快",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.7"}},
            ),
            MemoryFragment(
                id="c2",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:01:00+08:00",
                content="复现实验 alpha=0.2 在验证集更稳定",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.2"}},
            ),
            MemoryFragment(
                id="c3",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:02:00+08:00",
                content="参数冲突需要显式标记并保留证据",
                type="draft",
                tags={"category": "method"},
            ),
        ]

        result = build_cluster_result(
            fragments=fragments,
            preference_config=PreferenceConfig(),
            similarity_threshold=0.4,
            merge_threshold=0.9,
        )
        conflict_slots = {
            conflict.slot
            for cluster in result.clusters
            for conflict in cluster.conflicts
        }
        self.assertIn("alpha", conflict_slots)


if __name__ == "__main__":
    unittest.main()
