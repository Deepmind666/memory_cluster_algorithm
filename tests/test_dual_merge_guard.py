from __future__ import annotations

import unittest

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def _mixed_mode_cluster_count(result: object) -> int:
    clusters = getattr(result, "clusters")
    fragments = getattr(result, "fragments")
    by_id = {item.id: item for item in fragments}
    mixed = 0
    for cluster in clusters:
        if cluster.level != 1:
            continue
        mode_values: set[str] = set()
        for fid in cluster.fragment_ids:
            fragment = by_id.get(fid)
            if fragment is None:
                continue
            slots = fragment.meta.get("slots")
            if isinstance(slots, dict) and "mode" in slots:
                mode_values.add(str(slots["mode"]))
        if len(mode_values) > 1:
            mixed += 1
    return mixed


class TestDualMergeGuard(unittest.TestCase):
    def test_guard_blocks_conflicting_cluster_merge(self) -> None:
        fragments = [
            MemoryFragment(
                id="m1",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:00:00+00:00",
                content="Parser strategy mode fast for throughput",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "fast"}},
            ),
            MemoryFragment(
                id="m2",
                agent_id="writer_agent",
                timestamp="2026-02-09T09:01:00+00:00",
                content="Parser strategy mode safe for throughput",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "safe"}},
            ),
            MemoryFragment(
                id="m3",
                agent_id="planner_agent",
                timestamp="2026-02-09T09:02:00+00:00",
                content="Parser strategy mode fast keeps speed",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "fast"}},
            ),
            MemoryFragment(
                id="m4",
                agent_id="writer_agent",
                timestamp="2026-02-09T09:03:00+00:00",
                content="Parser strategy mode safe keeps correctness",
                type="draft",
                tags={"category": "method"},
                meta={"slots": {"mode": "safe"}},
            ),
        ]

        baseline = build_cluster_result(
            fragments=fragments,
            preference_config=PreferenceConfig(),
            similarity_threshold=1.1,
            merge_threshold=0.05,
        )
        guarded_pref = PreferenceConfig.from_dict(
            {
                "enable_dual_merge_guard": True,
                "merge_conflict_compat_threshold": 0.6,
            }
        )
        guarded = build_cluster_result(
            fragments=fragments,
            preference_config=guarded_pref,
            similarity_threshold=1.1,
            merge_threshold=0.05,
        )

        baseline_mixed = _mixed_mode_cluster_count(baseline)
        guarded_mixed = _mixed_mode_cluster_count(guarded)

        self.assertGreaterEqual(baseline_mixed, 1)
        self.assertEqual(guarded_mixed, 0)
        self.assertGreaterEqual(int(guarded.metrics.get("merges_blocked_by_guard") or 0), 1)


if __name__ == "__main__":
    unittest.main()
