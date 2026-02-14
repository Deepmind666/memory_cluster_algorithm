from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_ci_guardrail_bundle import (
    _build_bundle_commands,
    _write_core_stability_fixture,
    _write_semi_real_dataset,
)


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

    def test_build_bundle_commands_isolates_ci_outputs(self) -> None:
        ci_outputs = Path("outputs/ci_outputs")
        ci_reports = Path("outputs/ci_reports")
        core_realistic = ci_outputs / "core_claim_stability_ci_realistic.json"
        core_stress = ci_outputs / "core_claim_stability_ci_stress.json"
        commands = _build_bundle_commands(
            py="python",
            frag_count=120,
            size=240,
            runs=1,
            warmups=0,
            realistic_dataset=Path("outputs/ci_semi_real_240_realistic.jsonl"),
            stress_dataset=Path("outputs/ci_semi_real_240_stress.jsonl"),
            core_stability_realistic=core_realistic,
            core_stability_stress=core_stress,
            ci_outputs=ci_outputs,
            ci_reports=ci_reports,
        )
        self.assertEqual(len(commands), 6)
        outputs_seen: list[str] = []
        for command in commands:
            for idx, token in enumerate(command):
                if token in {
                    "--output",
                    "--candidate-synthetic",
                    "--candidate-realistic",
                    "--candidate-stress",
                    "--ann-hybrid",
                    "--candidate-benchmark",
                    "--core-stability",
                }:
                    outputs_seen.append(str(command[idx + 1]))
        self.assertTrue(outputs_seen)
        self.assertTrue(all(path.startswith("outputs/ci_outputs/") for path in outputs_seen))
        self.assertFalse(any(path == "outputs/stage2_guardrail.json" for path in outputs_seen))

        joined = [" ".join(item) for item in commands]
        self.assertTrue(
            any("--output outputs/ci_outputs/stage2_guardrail.json" in line for line in joined),
            "stage2 guardrail output should be isolated to outputs/ci_outputs/",
        )
        self.assertTrue(
            any("--candidate-benchmark outputs/ci_outputs/candidate_filter_benchmark.json" in line for line in joined),
            "stage2 guardrail should consume candidate benchmark from outputs/ci_outputs/",
        )
        self.assertTrue(
            any("--core-stability outputs/ci_outputs/core_claim_stability_ci_realistic.json" in line for line in joined),
            "stage2 guardrail should consume realistic core-stability fixture from outputs/ci_outputs/",
        )
        self.assertTrue(
            any("--core-stability outputs/ci_outputs/core_claim_stability_ci_stress.json" in line for line in joined),
            "stage2 guardrail should consume stress core-stability fixture from outputs/ci_outputs/",
        )

    def test_write_core_stability_fixture_generates_complete_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "core_stability.json"
            _write_core_stability_fixture(
                path,
                dataset="semi_real_5000_realistic_ci_fixture",
                runs=3,
                runs_completed=3,
                is_complete=True,
                similarity_threshold=0.68,
                merge_threshold=0.82,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("dataset"), "semi_real_5000_realistic_ci_fixture")
            self.assertEqual(payload.get("runs"), 3)
            self.assertEqual(payload.get("runs_completed"), 3)
            self.assertEqual(payload.get("is_complete"), True)


if __name__ == "__main__":
    unittest.main()
