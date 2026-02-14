from __future__ import annotations

import unittest

from scripts.check_ci_output_isolation import (
    validate_bundle_commands,
    validate_workflow_text,
)


class TestCiOutputIsolationUnit(unittest.TestCase):
    def test_validate_bundle_commands_passes_for_ci_outputs(self) -> None:
        commands = [
            ["python", "a.py", "--output", "outputs/ci_outputs/candidate_filter_benchmark.json"],
            ["python", "b.py", "--output", "outputs/ci_outputs/stage2_guardrail.json"],
            [
                "python",
                "c.py",
                "--candidate-synthetic",
                "outputs/ci_outputs/candidate_profile_validation_synthetic_active.json",
                "--candidate-benchmark",
                "outputs/ci_outputs/candidate_filter_benchmark.json",
                "--core-stability",
                "outputs/ci_outputs/core_claim_stability_ci_realistic.json",
            ],
        ]
        violations = validate_bundle_commands(commands)
        self.assertEqual(violations, [])

    def test_validate_bundle_commands_detects_root_json_path(self) -> None:
        commands = [["python", "a.py", "--output", "outputs/candidate_filter_benchmark.json"]]
        violations = validate_bundle_commands(commands)
        self.assertTrue(any("forbidden_root_json" in item for item in violations))
        self.assertTrue(any("json_not_in_ci_outputs" in item for item in violations))

    def test_validate_bundle_commands_detects_core_stability_root_path(self) -> None:
        commands = [["python", "a.py", "--core-stability", "outputs/core_claim_stability_ci_realistic.json"]]
        violations = validate_bundle_commands(commands)
        self.assertTrue(any("forbidden_root_json" in item for item in violations))
        self.assertTrue(any("json_not_in_ci_outputs" in item for item in violations))

    def test_validate_bundle_commands_detects_bundle_summary_root_path(self) -> None:
        commands = [["python", "a.py", "--output", "outputs/ci_guardrail_bundle_summary.json"]]
        violations = validate_bundle_commands(commands)
        self.assertTrue(any("forbidden_root_json" in item for item in violations))
        self.assertTrue(any("json_not_in_ci_outputs" in item for item in violations))

    def test_validate_workflow_text_detects_forbidden_root_path(self) -> None:
        text = "path: outputs/stage2_guardrail.json\n"
        violations = validate_workflow_text(
            workflow_name=".github/workflows/stage2-nightly-trend.yml",
            text=text,
        )
        self.assertTrue(any("forbidden_root_json" in item for item in violations))
        self.assertTrue(any("missing_required_path" in item for item in violations))

    def test_validate_workflow_text_passes_when_required_present(self) -> None:
        text = "\n".join(
            [
                "path: outputs/ci_outputs/stage2_guardrail.json",
                "path: outputs/ci_outputs/ci_guardrail_bundle_summary.json",
                "path: outputs/stage2_guardrail_trend.json",
            ]
        )
        violations = validate_workflow_text(
            workflow_name=".github/workflows/stage2-nightly-trend.yml",
            text=text,
        )
        self.assertEqual(violations, [])

    def test_validate_workflow_text_detects_missing_bundle_summary_required_path(self) -> None:
        text = "path: outputs/ci_outputs/stage2_guardrail.json\n"
        violations = validate_workflow_text(
            workflow_name=".github/workflows/stage2-nightly-trend.yml",
            text=text,
        )
        self.assertTrue(any("missing_required_path:outputs/ci_outputs/ci_guardrail_bundle_summary.json" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
