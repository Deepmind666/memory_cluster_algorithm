from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def _write_minimal_dataset(path: Path) -> None:
    rows = [
        {
            "id": "smoke_0001",
            "agent_id": "planner_agent",
            "timestamp": "2026-02-01T08:00:00+00:00",
            "content": "task=parser_refactor mode=fast alpha=0.6",
            "type": "policy",
            "tags": {"category": "method"},
            "meta": {"slots": {"task": "parser_refactor", "mode": "fast", "alpha": "0.6"}},
        },
        {
            "id": "smoke_0002",
            "agent_id": "verifier_agent",
            "timestamp": "2026-02-01T08:01:00+00:00",
            "content": "task=parser_refactor mode=safe alpha=0.6",
            "type": "result",
            "tags": {"category": "evidence"},
            "meta": {"slots": {"task": "parser_refactor", "mode": "safe", "alpha": "0.6"}},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class TestCoreClaimStabilityResumeSmoke(unittest.TestCase):
    def test_resume_fails_on_checkpoint_signature_mismatch(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "run_core_claim_stability.py"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            dataset = tmp / "mini.jsonl"
            output = tmp / "stability.json"
            checkpoint = tmp / "stability_checkpoint.json"
            _write_minimal_dataset(dataset)

            base_cmd = [
                sys.executable,
                str(script),
                "--input",
                str(dataset),
                "--output",
                str(output),
                "--runs",
                "1",
                "--warmup-runs",
                "0",
                "--similarity-threshold",
                "0.68",
                "--merge-threshold",
                "0.82",
                "--checkpoint",
                str(checkpoint),
            ]
            subprocess.run(base_cmd, cwd=repo_root, check=True, capture_output=True, text=True)

            mismatch_cmd = [
                *base_cmd,
                "--resume",
                "--similarity-threshold",
                "0.99",
            ]
            result = subprocess.run(mismatch_cmd, cwd=repo_root, check=False, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            combined = f"{result.stdout}\n{result.stderr}"
            self.assertIn("checkpoint signature mismatch", combined)


if __name__ == "__main__":
    unittest.main()

