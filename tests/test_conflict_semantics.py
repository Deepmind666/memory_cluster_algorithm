from __future__ import annotations

import unittest

from src.memory_cluster.compress import _extract_slot_values
from src.memory_cluster.models import MemoryFragment


class TestConflictSemantics(unittest.TestCase):
    def test_negated_key_value_extracts_not_value(self) -> None:
        fragment = MemoryFragment(
            id="s1",
            agent_id="writer_agent",
            timestamp="2026-02-10T10:00:00+00:00",
            content="alpha != 0.7 and not recommended for this run",
            type="draft",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("alpha", "!0.7"), pairs)

    def test_conditional_scope_isolated_from_factual_slot(self) -> None:
        fragment = MemoryFragment(
            id="s2",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:01:00+00:00",
            content="if alpha=0.7 then increase throughput, final alpha=0.2",
            type="decision",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cond:alpha", "0.7"), pairs)
        self.assertIn(("alpha", "0.2"), pairs)

    def test_counterfactual_scope_extracts_cf_slot(self) -> None:
        fragment = MemoryFragment(
            id="s3",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:02:00+00:00",
            content="should have mode=safe for stability in replay",
            type="draft",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cf:mode", "safe"), pairs)


if __name__ == "__main__":
    unittest.main()