from __future__ import annotations

import unittest

from scripts.run_stage2_guardrail import evaluate_guardrails


def _candidate_payload(default_ok: bool, fast_n240_ok: bool) -> dict:
    return {
        "summary": {
            "default_all_quality_gate_pass": bool(default_ok),
        },
        "rows": [
            {
                "fragment_count": 240,
                "default_profile": {"quality_gate_pass": bool(default_ok)},
                "fast_profile": {"quality_gate_pass": bool(fast_n240_ok)},
            }
        ],
    }


def _ann_payload(quality_ok: bool, runtime_signature_ok: bool) -> dict:
    return {
        "signature_gate_pass_cluster_runtime": bool(runtime_signature_ok),
        "scenarios": [
            {
                "name": "merge_active_case",
                "comparisons_vs_baseline": {
                    "ann_prune": {"quality_gate_pass": bool(quality_ok)},
                    "hybrid_prune": {"quality_gate_pass": bool(quality_ok)},
                },
            }
        ],
    }


def _core_stability_payload(*, is_complete: bool, runs_completed: int, runs: int, dataset: str) -> dict:
    return {
        "name": dataset,
        "payload": {
            "dataset": dataset,
            "is_complete": bool(is_complete),
            "runs_completed": int(runs_completed),
            "runs": int(runs),
        },
    }


class TestStage2Guardrail(unittest.TestCase):
    def test_passes_with_known_fast_loss_allowed(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=True, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark={"active_quality_gate_pass": True},
            allow_known_fast_loss=True,
        )
        self.assertTrue((payload.get("summary") or {}).get("passed"))
        self.assertTrue((payload.get("known_limitations") or {}).get("fast_profile_loss_at_synthetic_n240"))
        self.assertGreaterEqual(int((payload.get("summary") or {}).get("warning_failures") or 0), 1)

    def test_fails_when_default_quality_breaks(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=False, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark={"active_quality_gate_pass": True},
            allow_known_fast_loss=True,
        )
        self.assertFalse((payload.get("summary") or {}).get("passed"))
        self.assertGreater(int((payload.get("summary") or {}).get("blocker_failures") or 0), 0)

    def test_strict_mode_blocks_known_fast_loss(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=True, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark={"active_quality_gate_pass": True},
            allow_known_fast_loss=False,
        )
        self.assertFalse((payload.get("summary") or {}).get("passed"))
        blocker_names = {
            str(item.get("name"))
            for item in (payload.get("checks") or [])
            if item.get("severity") == "blocker" and not item.get("passed")
        }
        self.assertIn("candidate_fast_n240_known_loss", blocker_names)

    def test_supports_missing_candidate_benchmark_payload(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=True, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark=None,
            allow_known_fast_loss=True,
        )
        self.assertTrue((payload.get("summary") or {}).get("passed"))
        check_names = {str(item.get("name")) for item in (payload.get("checks") or [])}
        self.assertNotIn("candidate_benchmark_active_quality", check_names)

    def test_optional_core_stability_checks_pass_when_complete(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=True, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark={"active_quality_gate_pass": True},
            core_stability_profiles=[
                _core_stability_payload(
                    is_complete=True,
                    runs_completed=6,
                    runs=6,
                    dataset="semi_real_5000_realistic",
                ),
                _core_stability_payload(
                    is_complete=True,
                    runs_completed=3,
                    runs=3,
                    dataset="semi_real_5000_stress",
                ),
            ],
            allow_known_fast_loss=True,
        )
        self.assertTrue((payload.get("summary") or {}).get("passed"))
        core = payload.get("core_stability") or {}
        self.assertEqual(core.get("profile_count"), 2)
        self.assertEqual(core.get("incomplete_count"), 0)

    def test_core_stability_incomplete_is_blocker(self) -> None:
        payload = evaluate_guardrails(
            candidate_synthetic=_candidate_payload(default_ok=True, fast_n240_ok=False),
            candidate_realistic=_candidate_payload(default_ok=True, fast_n240_ok=True),
            candidate_stress=_candidate_payload(default_ok=True, fast_n240_ok=True),
            ann_hybrid=_ann_payload(quality_ok=True, runtime_signature_ok=True),
            candidate_benchmark={"active_quality_gate_pass": True},
            core_stability_profiles=[
                _core_stability_payload(
                    is_complete=False,
                    runs_completed=1,
                    runs=3,
                    dataset="semi_real_5000_stress",
                ),
            ],
            allow_known_fast_loss=True,
        )
        self.assertFalse((payload.get("summary") or {}).get("passed"))
        self.assertEqual((payload.get("core_stability") or {}).get("incomplete_count"), 1)
        failed_blockers = {
            str(item.get("name"))
            for item in (payload.get("checks") or [])
            if item.get("severity") == "blocker" and not item.get("passed")
        }
        self.assertIn("core_stability_complete_semi_real_5000_stress", failed_blockers)


if __name__ == "__main__":
    unittest.main()
