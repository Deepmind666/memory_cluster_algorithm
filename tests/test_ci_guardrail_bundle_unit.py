from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_ci_guardrail_bundle import _write_semi_real_dataset


class TestCiGuardrailBundleUnit(unittest.TestCase):
    def test_write_semi_real_dataset_generates_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "realistic.jsonl"
            _write_semi_real_dataset(path, fragment_count=120, seed=42, profile="realistic")
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 120)
            row = json.loads(lines[0])
            self.assertIn("id", row)
            self.assertIn("agent_id", row)
            self.assertIn("timestamp", row)
            self.assertIn("content", row)
            self.assertIn("meta", row)
            self.assertEqual((row.get("meta") or {}).get("profile"), "realistic")

    def test_write_semi_real_dataset_enforces_minimum_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "stress.jsonl"
            _write_semi_real_dataset(path, fragment_count=10, seed=42, profile="stress")
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 80)


if __name__ == "__main__":
    unittest.main()
