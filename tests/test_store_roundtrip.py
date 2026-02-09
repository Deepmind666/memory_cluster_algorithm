from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result
from src.memory_cluster.store import FragmentStore, load_result, save_result


class TestStoreRoundtrip(unittest.TestCase):
    def test_store_and_result_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "memory_store.jsonl"
            result_path = Path(tmp_dir) / "cluster_state.json"

            store = FragmentStore(store_path)
            fragment_v1 = MemoryFragment(
                id="r1",
                agent_id="planner_agent",
                timestamp="2026-02-09T11:00:00+08:00",
                content="初版需求",
                type="requirement",
                tags={"category": "requirement"},
                version=1,
            )
            fragment_v2 = MemoryFragment(
                id="r1",
                agent_id="planner_agent",
                timestamp="2026-02-09T11:01:00+08:00",
                content="初版需求（修订版）",
                type="requirement",
                tags={"category": "requirement"},
                version=2,
            )
            store.append_fragments([fragment_v1, fragment_v2])

            latest = store.load_latest_by_id()
            self.assertEqual(len(latest), 1)
            self.assertEqual(latest[0].version, 2)

            result = build_cluster_result(
                fragments=latest,
                preference_config=PreferenceConfig(),
                similarity_threshold=0.7,
                merge_threshold=0.9,
            )
            save_result(result_path, result)
            loaded = load_result(result_path)

            self.assertIn("clusters", loaded)
            self.assertIn("fragments", loaded)
            self.assertEqual(loaded["fragments"][0]["id"], "r1")
            self.assertTrue(loaded["clusters"][0]["backrefs"])


if __name__ == "__main__":
    unittest.main()
