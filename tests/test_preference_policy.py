from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.preference import PreferencePolicyEngine


class TestPreferencePolicy(unittest.TestCase):
    def test_preference_can_change_retention_strength(self) -> None:
        now = datetime.now(timezone.utc)
        stale_ts = (now - timedelta(hours=10)).isoformat()
        fresh_ts = now.isoformat()

        config = PreferenceConfig.from_dict(
            {
                "category_strength": {
                    "method": "strong",
                    "evidence": "strong",
                    "noise": "discardable",
                },
                "source_weight": {
                    "verifier_agent": 1.6,
                    "writer_agent": 0.9,
                },
                "stale_after_hours": 2,
                "detail_budget": {"strong": 900, "weak": 400, "discardable": 120},
                "keep_conflicts": True,
            }
        )
        engine = PreferencePolicyEngine(config)

        fresh_evidence = MemoryFragment(
            id="p1",
            agent_id="verifier_agent",
            timestamp=fresh_ts,
            content="证据碎片",
            type="result",
            tags={"category": "evidence"},
        )
        stale_method = MemoryFragment(
            id="p2",
            agent_id="writer_agent",
            timestamp=stale_ts,
            content="旧方法草稿",
            type="draft",
            tags={"category": "method"},
        )

        decision_fresh = engine.decide_for_fragment(fresh_evidence)
        decision_stale = engine.decide_for_fragment(stale_method)

        self.assertEqual(decision_fresh.strength, "strong")
        self.assertIn(decision_stale.strength, {"weak", "discardable"})
        self.assertTrue(decision_stale.stale)


if __name__ == "__main__":
    unittest.main()
