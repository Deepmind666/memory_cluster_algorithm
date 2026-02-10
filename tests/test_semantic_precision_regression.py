from __future__ import annotations

import unittest

from src.memory_cluster.compress import _extract_slot_values
from src.memory_cluster.models import MemoryFragment


def _fragment(fragment_id: str, content: str) -> MemoryFragment:
    return MemoryFragment(
        id=fragment_id,
        agent_id="planner_agent",
        timestamp="2026-02-10T14:00:00+00:00",
        content=content,
        type="decision",
    )


class TestSemanticPrecisionRegression(unittest.TestCase):
    def test_conditional_then_clause_not_misclassified_as_conditional(self) -> None:
        fragment = _fragment("r1", "if mode=fast then cache=true, final cache=false")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cond:mode", "fast"), pairs)
        self.assertNotIn(("cond:cache", "true"), pairs)
        self.assertIn(("cache", "true"), pairs)
        self.assertIn(("cache", "false"), pairs)

    def test_english_not_prefix_extracts_negated_slot(self) -> None:
        fragment = _fragment("r2", "not mode=fast; mode=safe")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("mode", "!fast"), pairs)
        self.assertIn(("mode", "safe"), pairs)

    def test_double_negation_does_not_emit_false_flag(self) -> None:
        fragment = _fragment("r3", "do not disable cache, enable cache")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("flag:cache", "true"), pairs)
        self.assertNotIn(("flag:cache", "false"), pairs)

    def test_cross_sentence_coreference_for_it(self) -> None:
        fragment = _fragment("r4", "mode=fast. it=safe")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("mode", "fast"), pairs)
        self.assertIn(("mode", "safe"), pairs)
        self.assertNotIn(("it", "safe"), pairs)

    def test_cross_sentence_coreference_for_chinese_alias(self) -> None:
        fragment = _fragment("r5", "\u6a21\u5f0f=fast\uff0c\u5b83=safe")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("\u6a21\u5f0f", "fast"), pairs)
        self.assertIn(("\u6a21\u5f0f", "safe"), pairs)
        self.assertNotIn(("\u5b83", "safe"), pairs)

    def test_conditional_coreference_keeps_scope(self) -> None:
        fragment = _fragment("r6", "if mode=fast and it=safe then fallback mode=safe")
        pairs = _extract_slot_values(fragment)
        self.assertIn(("cond:mode", "fast"), pairs)
        self.assertIn(("cond:mode", "safe"), pairs)
        self.assertNotIn(("cond:it", "safe"), pairs)
        self.assertIn(("mode", "safe"), pairs)


if __name__ == "__main__":
    unittest.main()
