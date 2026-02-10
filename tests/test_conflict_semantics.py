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

    def test_chinese_negation_prefix_does_not_break_slot(self) -> None:
        fragment = MemoryFragment(
            id="s4",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:03:00+00:00",
            content="不是 mode=fast，最终 mode=safe",
            type="decision",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("mode", "!fast"), pairs)
        self.assertIn(("mode", "safe"), pairs)
        self.assertNotIn(("是", "!mode=fast"), pairs)

    def test_conditional_scope_flag_should_not_pollute_global_flag(self) -> None:
        fragment = MemoryFragment(
            id="s5",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:04:00+00:00",
            content="如果 启用cache 则回退，最终 alpha=0.2",
            type="decision",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cond:flag:cache", "true"), pairs)
        self.assertIn(("alpha", "0.2"), pairs)
        self.assertNotIn(("flag:cache", "true"), pairs)

    def test_chinese_conditional_negation_keeps_scoped_semantics(self) -> None:
        fragment = MemoryFragment(
            id="s6",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:05:00+00:00",
            content="如果 不是 mode=fast 且 不启用cache 则回退，最终 mode=safe 并启用cache",
            type="decision",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cond:mode", "!fast"), pairs)
        self.assertIn(("cond:flag:cache", "false"), pairs)
        self.assertIn(("mode", "safe"), pairs)
        self.assertIn(("flag:cache", "true"), pairs)

    def test_chinese_counterfactual_scope_keeps_negation(self) -> None:
        fragment = MemoryFragment(
            id="s7",
            agent_id="planner_agent",
            timestamp="2026-02-10T10:06:00+00:00",
            content="本应 不使用gpu 且 mode=safe，实际 mode=fast 并使用gpu",
            type="draft",
        )
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cf:flag:gpu", "false"), pairs)
        self.assertIn(("cf:mode", "safe"), pairs)
        self.assertIn(("mode", "fast"), pairs)
        self.assertIn(("flag:gpu", "true"), pairs)


if __name__ == "__main__":
    unittest.main()
