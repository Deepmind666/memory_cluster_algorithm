from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def _membership_signature(result: object) -> list[tuple[str, ...]]:
    clusters = getattr(result, "clusters")
    l1 = [cluster for cluster in clusters if int(cluster.level) == 1]
    groups = [tuple(sorted(cluster.fragment_ids)) for cluster in l1]
    return sorted(groups)


class TestMergeUpperBoundPrune(unittest.TestCase):
    def test_prune_keeps_same_cluster_membership(self) -> None:
        fragments = [
            MemoryFragment(
                id="u1",
                agent_id="planner_agent",
                timestamp="2026-02-09T10:00:00+00:00",
                content="mode fast parser strategy for high throughput",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "fast"}},
            ),
            MemoryFragment(
                id="u2",
                agent_id="planner_agent",
                timestamp="2026-02-09T10:01:00+00:00",
                content="parser strategy mode fast for high speed",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "fast"}},
            ),
            MemoryFragment(
                id="u3",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:02:00+00:00",
                content="mode safe parser strategy for high reliability",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "safe"}},
            ),
            MemoryFragment(
                id="u4",
                agent_id="writer_agent",
                timestamp="2026-02-09T10:03:00+00:00",
                content="parser strategy mode safe for correctness",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "safe"}},
            ),
            MemoryFragment(
                id="u5",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:04:00+00:00",
                content="alpha equals 0.7 in experiment replay",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.7"}},
            ),
            MemoryFragment(
                id="u6",
                agent_id="verifier_agent",
                timestamp="2026-02-09T10:05:00+00:00",
                content="alpha equals 0.2 in stable experiment replay",
                type="result",
                tags={"category": "evidence"},
                meta={"slots": {"alpha": "0.2"}},
            ),
        ]

        pref_on = PreferenceConfig.from_dict({"enable_merge_upper_bound_prune": True, "merge_prune_dims": 48})
        pref_off = PreferenceConfig.from_dict({"enable_merge_upper_bound_prune": False, "merge_prune_dims": 48})

        on_result = build_cluster_result(
            fragments=fragments,
            preference_config=pref_on,
            similarity_threshold=0.68,
            merge_threshold=0.82,
        )
        off_result = build_cluster_result(
            fragments=fragments,
            preference_config=pref_off,
            similarity_threshold=0.68,
            merge_threshold=0.82,
        )

        self.assertEqual(_membership_signature(on_result), _membership_signature(off_result))
        self.assertEqual(int(on_result.metrics.get("cluster_count") or 0), int(off_result.metrics.get("cluster_count") or 0))

    def test_prune_emits_positive_pruned_pair_count(self) -> None:
        fragments: list[MemoryFragment] = []
        for idx in range(30):
            fragments.append(
                MemoryFragment(
                    id=f"p{idx:02d}",
                    agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                    timestamp=f"2026-02-09T10:{idx:02d}:00+00:00",
                    content=f"unique memory fragment token_{idx} variant_{idx * 7}",
                    type="log",
                    tags={"category": "noise" if idx % 3 == 0 else "method"},
                    meta={"slots": {"k": str(idx)}},
                )
            )

        pref = PreferenceConfig.from_dict(
            {
                "enable_merge_upper_bound_prune": True,
                "merge_prune_dims": 32,
            }
        )
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=2.0,
            merge_threshold=0.92,
        )

        self.assertGreater(int(result.metrics.get("merge_attempts") or 0), 0)
        self.assertGreater(int(result.metrics.get("merge_pairs_pruned_by_bound") or 0), 0)


if __name__ == "__main__":
    unittest.main()
