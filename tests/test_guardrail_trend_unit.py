from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.update_guardrail_trend import build_trend_record, update_trend_payload


def _guardrail_payload(*, passed: bool, blocker: int, warning: int, ann_speed: float, candidate_speed: float) -> dict:
    return {
        "generated_at": "2026-02-13T02:00:00+00:00",
        "summary": {
            "passed": bool(passed),
            "blocker_failures": int(blocker),
            "warning_failures": int(warning),
        },
        "known_limitations": {
            "ann_active_not_positive_speedup": ann_speed <= 0.0,
            "fast_profile_loss_at_synthetic_n240": True,
            "ann_active_speed": ann_speed,
            "candidate_active_speed": candidate_speed,
        },
        "checks": [
            {"name": "check_ok", "passed": True},
            {"name": "check_failed", "passed": False},
        ],
    }


class TestGuardrailTrendUnit(unittest.TestCase):
    def test_build_trend_record_extracts_fields(self) -> None:
        payload = _guardrail_payload(passed=True, blocker=0, warning=1, ann_speed=-0.1, candidate_speed=0.02)
        row = build_trend_record(payload, label="ci")
        self.assertTrue(bool(row.get("label") == "ci"))
        self.assertEqual(int(row.get("blocker_failures") or 0), 0)
        self.assertEqual(int(row.get("warning_failures") or 0), 1)
        self.assertIn("check_failed", list(row.get("failed_checks") or []))

    def test_update_trend_payload_appends_and_retains(self) -> None:
        current = {
            "history": [
                build_trend_record(_guardrail_payload(passed=True, blocker=0, warning=0, ann_speed=-0.05, candidate_speed=0.1), label="a"),
                build_trend_record(_guardrail_payload(passed=False, blocker=1, warning=1, ann_speed=-0.2, candidate_speed=-0.1), label="b"),
            ]
        }
        updated = update_trend_payload(
            current_payload=current,
            guardrail_payload=_guardrail_payload(passed=True, blocker=0, warning=1, ann_speed=-0.1, candidate_speed=0.02),
            label="c",
            retain=2,
        )
        history = list(updated.get("history") or [])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1].get("label"), "c")
        self.assertIn("summary", updated)

    def test_cli_like_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "guardrail.json"
            output_path = Path(tmp_dir) / "trend.json"
            input_path.write_text(
                json.dumps(_guardrail_payload(passed=True, blocker=0, warning=1, ann_speed=-0.1, candidate_speed=0.02)),
                encoding="utf-8",
            )
            updated = update_trend_payload(
                current_payload=None,
                guardrail_payload=json.loads(input_path.read_text(encoding="utf-8")),
                label="manual",
                retain=90,
            )
            output_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
            loaded = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(int(loaded.get("history_count") or 0), 1)
            self.assertIn("pass_rate", dict(loaded.get("summary") or {}))


if __name__ == "__main__":
    unittest.main()
