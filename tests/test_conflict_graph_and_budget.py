from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result
from src.memory_cluster.preference import PreferenceDecision, PreferencePolicyEngine


class TestConflictGraphAndBudget(unittest.TestCase):
    def test_conflict_graph_contains_priority_and_transitions(self) -> None:
        fragments = [
            MemoryFragment(
                id="g1",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:00:00+00:00",
                content="alpha=0.7",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.7"}},
            ),
            MemoryFragment(
                id="g2",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:01:00+00:00",
                content="alpha=0.2",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.2"}},
            ),
            MemoryFragment(
                id="g3",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:02:00+00:00",
                content="alpha=0.7 again",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.7"}},
            ),
        ]
        pref = PreferenceConfig.from_dict({"enable_conflict_graph": True})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=0.0,
            merge_threshold=0.95,
        )

        target = next(cluster for cluster in result.clusters if cluster.conflicts)
        self.assertIn("alpha", target.conflict_graph)
        graph = target.conflict_graph["alpha"]
        self.assertGreaterEqual(int(graph.get("transition_count") or 0), 2)
        self.assertGreater(float(target.tags.get("conflict_priority") or 0.0), 0.0)

        conflict = next(item for item in target.conflicts if item.slot == "alpha")
        self.assertGreater(conflict.priority, 0.0)
        self.assertIn(conflict.dominant_value, {"0.7", "0.2"})

    def test_adaptive_budget_adjusts_with_conflict_and_entropy(self) -> None:
        pref = PreferenceConfig.from_dict(
            {
                "enable_adaptive_budget": True,
                "detail_budget": {"strong": 100, "weak": 80, "discardable": 60},
                "arb_conflict_weight": 0.5,
                "arb_entropy_weight": 0.4,
                "arb_stale_penalty": 0.3,
                "arb_min_scale": 0.7,
                "arb_max_scale": 1.8,
            }
        )
        engine = PreferencePolicyEngine(pref)

        fresh = PreferenceDecision(strength="strong", detail_budget=100, source_weight=1.0, stale=False)
        stale = PreferenceDecision(strength="strong", detail_budget=100, source_weight=1.0, stale=True)

        high_budget = engine.cluster_budget(
            strength="strong",
            fragment_decisions=[fresh, fresh, fresh],
            conflict_count=3,
            source_distribution={"a": 1, "b": 1, "c": 1},
            fragment_count=3,
        )
        low_budget = engine.cluster_budget(
            strength="strong",
            fragment_decisions=[fresh, stale, stale],
            conflict_count=0,
            source_distribution={"a": 3},
            fragment_count=3,
        )

        self.assertGreater(high_budget, low_budget)
        self.assertGreaterEqual(high_budget, 100)
        self.assertLessEqual(low_budget, 100)


if __name__ == "__main__":
    unittest.main()
