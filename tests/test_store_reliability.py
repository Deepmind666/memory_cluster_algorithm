from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.memory_cluster.models import MemoryFragment
from src.memory_cluster.store import FragmentStore


class TestStoreReliability(unittest.TestCase):
    def test_idempotent_append_skips_same_id_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            store = FragmentStore(store_path)
            fragment = MemoryFragment(
                id="i1",
                agent_id="planner_agent",
                timestamp="2026-02-10T10:00:00+00:00",
                content="same payload",
                type="draft",
            )

            first = store.append_fragments_with_stats([fragment], idempotent=True)
            second = store.append_fragments_with_stats([fragment], idempotent=True)

            self.assertEqual(first.inserted, 1)
            self.assertEqual(second.inserted, 0)
            self.assertEqual(second.skipped_existing, 1)
            self.assertEqual(len(store.load_fragments()), 1)

    def test_idempotent_append_allows_newer_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            store = FragmentStore(store_path)
            v1 = MemoryFragment(
                id="i2",
                agent_id="planner_agent",
                timestamp="2026-02-10T10:00:00+00:00",
                content="version 1",
                type="draft",
                version=1,
            )
            v2 = MemoryFragment(
                id="i2",
                agent_id="planner_agent",
                timestamp="2026-02-10T10:01:00+00:00",
                content="version 2",
                type="draft",
                version=2,
            )

            s1 = store.append_fragments_with_stats([v1], idempotent=True)
            s2 = store.append_fragments_with_stats([v2], idempotent=True)
            latest = store.load_latest_by_id()

            self.assertEqual(s1.inserted, 1)
            self.assertEqual(s2.inserted, 1)
            self.assertEqual(len(latest), 1)
            self.assertEqual(latest[0].version, 2)

    def test_idempotent_append_dedups_duplicates_within_same_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            store = FragmentStore(store_path)
            fragment = MemoryFragment(
                id="i2b",
                agent_id="planner_agent",
                timestamp="2026-02-10T10:00:00+00:00",
                content="same batch duplicate",
                type="draft",
                version=3,
            )

            stats = store.append_fragments_with_stats([fragment, fragment], idempotent=True)
            self.assertEqual(stats.inserted, 1)
            self.assertEqual(stats.skipped_existing, 1)
            self.assertEqual(len(store.load_fragments()), 1)

    def test_load_fragments_skips_invalid_lines_when_not_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            valid = MemoryFragment(
                id="i3",
                agent_id="planner_agent",
                timestamp="2026-02-10T10:00:00+00:00",
                content="valid line",
                type="draft",
            )
            lines = [
                json.dumps(valid.to_dict(), ensure_ascii=False),
                "{bad-json-line",
                json.dumps({"agent_id": "planner_agent", "content": "missing id"}, ensure_ascii=False),
            ]
            store_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            store = FragmentStore(store_path)
            rows, stats = store.load_fragments_with_stats(strict=False)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, "i3")
            self.assertEqual(stats.skipped_invalid, 2)
            self.assertEqual(stats.decode_errors, 1)
            self.assertEqual(stats.schema_errors, 1)

    def test_load_fragments_raises_on_invalid_when_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            store_path.write_text('{"id":"ok","agent_id":"a","timestamp":"2026-02-10T10:00:00+00:00","content":"x","type":"draft"}\n{bad\n', encoding="utf-8")

            store = FragmentStore(store_path)
            with self.assertRaises(ValueError):
                store.load_fragments(strict=True)

    def test_load_fragments_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            payload = '{"id":"bom1","agent_id":"a","timestamp":"2026-02-10T10:00:00+00:00","content":"x","type":"draft"}\n'
            store_path.write_text(payload, encoding="utf-8-sig")

            store = FragmentStore(store_path)
            rows = store.load_fragments(strict=False)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, "bom1")

    def test_load_latest_by_id_with_stats_propagates_read_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "store.jsonl"
            lines = [
                '{"id":"v1","agent_id":"a","timestamp":"2026-02-10T10:00:00+00:00","content":"x","type":"draft","version":1}',
                '{"id":"v1","agent_id":"a","timestamp":"2026-02-10T10:01:00+00:00","content":"x2","type":"draft","version":2}',
                "{bad-json-line",
            ]
            store_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            store = FragmentStore(store_path)
            latest, stats = store.load_latest_by_id_with_stats(strict=False)
            self.assertEqual(len(latest), 1)
            self.assertEqual(latest[0].version, 2)
            self.assertEqual(stats.total_lines, 3)
            self.assertEqual(stats.parsed_lines, 2)
            self.assertEqual(stats.decode_errors, 1)


if __name__ == "__main__":
    unittest.main()
