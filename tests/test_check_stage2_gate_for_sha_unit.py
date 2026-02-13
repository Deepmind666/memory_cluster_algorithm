from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from scripts.check_stage2_gate_for_sha import (
    _build_runs_url,
    _iso_to_utc,
    evaluate_gate,
    select_successful_run,
)


class TestCheckStage2GateForSha(unittest.TestCase):
    def test_iso_to_utc_supports_z_suffix(self) -> None:
        dt = _iso_to_utc("2026-02-13T00:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.isoformat(), "2026-02-13T00:00:00+00:00")

    def test_select_successful_run_prefers_latest_for_sha(self) -> None:
        now = datetime(2026, 2, 13, 12, 0, tzinfo=timezone.utc)
        runs = [
            {
                "id": 1,
                "head_sha": "abc123",
                "conclusion": "success",
                "updated_at": (now - timedelta(hours=4)).isoformat(),
            },
            {
                "id": 2,
                "head_sha": "abc123",
                "conclusion": "failure",
                "updated_at": (now - timedelta(hours=1)).isoformat(),
            },
            {
                "id": 3,
                "head_sha": "abc123",
                "conclusion": "success",
                "updated_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "id": 4,
                "head_sha": "other",
                "conclusion": "success",
                "updated_at": (now - timedelta(minutes=5)).isoformat(),
            },
        ]
        selected = select_successful_run(
            workflow_runs=runs,
            head_sha="abc123",
            max_age_hours=168.0,
            now=now,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(int((selected or {}).get("id") or 0), 3)

    def test_evaluate_gate_fails_for_stale_success(self) -> None:
        now = datetime(2026, 2, 13, 12, 0, tzinfo=timezone.utc)
        payload = {
            "workflow_runs": [
                {
                    "id": 10,
                    "head_sha": "abc123",
                    "conclusion": "success",
                    "updated_at": (now - timedelta(hours=8)).isoformat(),
                }
            ]
        }
        result = evaluate_gate(
            api_payload=payload,
            head_sha="abc123",
            max_age_hours=2.0,
            now=now,
        )
        self.assertFalse(bool(result.get("passed")))
        self.assertEqual(str(result.get("reason")), "no_recent_successful_stage2_quality_gate_run")

    def test_evaluate_gate_passes_with_recent_success(self) -> None:
        now = datetime(2026, 2, 13, 12, 0, tzinfo=timezone.utc)
        payload = {
            "workflow_runs": [
                {
                    "id": 99,
                    "html_url": "https://example.invalid/run/99",
                    "event": "push",
                    "status": "completed",
                    "head_sha": "abc123",
                    "conclusion": "success",
                    "created_at": (now - timedelta(hours=2)).isoformat(),
                    "updated_at": (now - timedelta(hours=1)).isoformat(),
                }
            ]
        }
        result = evaluate_gate(
            api_payload=payload,
            head_sha="abc123",
            max_age_hours=24.0,
            now=now,
        )
        self.assertTrue(bool(result.get("passed")))
        selected = dict(result.get("selected_run") or {})
        self.assertEqual(int(selected.get("id") or 0), 99)
        self.assertEqual(str(selected.get("conclusion")), "success")

    def test_build_runs_url_encodes_workflow_and_sha(self) -> None:
        url = _build_runs_url("owner/repo", "stage2 quality gate.yml", "abc/123")
        self.assertIn("owner/repo/actions/workflows/stage2%20quality%20gate.yml/runs", url)
        self.assertIn("head_sha=abc%2F123", url)
        self.assertIn("status=completed", url)


if __name__ == "__main__":
    unittest.main()
