from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.preference import PreferencePolicyEngine


class TestProtectedPreferences(unittest.TestCase):
    def test_scope_protection_promotes_to_strong(self) -> None:
        config = PreferenceConfig.from_dict(
            {
                "category_strength": {"noise": "discardable"},
                "protected_scopes": ["current_task"],
            }
        )
        engine = PreferencePolicyEngine(config)
        fragment = MemoryFragment(
            id="s1",
            agent_id="writer_agent",
            timestamp="2026-02-09T10:00:00+00:00",
            content="temporary noisy detail",
            type="log",
            tags={"category": "noise", "scope": "current_task"},
        )
        decision = engine.decide_for_fragment(fragment)
        self.assertEqual(decision.strength, "strong")

    def test_path_protection_promotes_to_strong(self) -> None:
        config = PreferenceConfig.from_dict(
            {
                "category_strength": {"noise": "discardable"},
                "protected_path_prefixes": ["src/", "docs/patent_kit/"],
            }
        )
        engine = PreferencePolicyEngine(config)
        fragment = MemoryFragment(
            id="p1",
            agent_id="writer_agent",
            timestamp="2026-02-09T10:00:00+00:00",
            content="path protected",
            type="log",
            tags={"category": "noise"},
            meta={"file_path": "src/memory_cluster/pipeline.py"},
        )
        decision = engine.decide_for_fragment(fragment)
        self.assertEqual(decision.strength, "strong")


if __name__ == "__main__":
    unittest.main()
