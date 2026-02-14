from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _candidate_profile_payload() -> dict:
    return {
        "summary": {"default_all_quality_gate_pass": True},
        "rows": [
            {
                "fragment_count": 240,
                "default_profile": {"quality_gate_pass": True},
                "fast_profile": {"quality_gate_pass": True},
            }
        ],
    }


def _ann_payload(*, ann_speedup: float) -> dict:
    return {
        "signature_gate_pass_cluster_runtime": True,
        "scenarios": [
            {
                "name": "merge_active_case",
                "comparisons_vs_baseline": {
                    "ann_prune": {"quality_gate_pass": True, "avg_speedup_ratio": float(ann_speedup)},
                    "hybrid_prune": {"quality_gate_pass": True, "avg_speedup_ratio": 0.01},
                },
            }
        ],
    }


def _candidate_benchmark_payload(*, speedup: float) -> dict:
    return {
        "active_quality_gate_pass": True,
        "scenarios": [
            {
                "name": "merge_active_case",
                "summary": {"avg_speedup_ratio": float(speedup)},
            }
        ],
    }


def _core_stability_payload(*, dataset: str, runs: int, runs_completed: int, is_complete: bool) -> dict:
    return {
        "dataset": dataset,
        "runs": int(runs),
        "runs_completed": int(runs_completed),
        "is_complete": bool(is_complete),
    }


class TestStage2GuardrailCliSmoke(unittest.TestCase):
    def test_cli_with_core_stability_completeness_passes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "run_stage2_guardrail.py"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            candidate_synth = tmp / "candidate_synth.json"
            candidate_realistic = tmp / "candidate_realistic.json"
            candidate_stress = tmp / "candidate_stress.json"
            ann_hybrid = tmp / "ann_hybrid.json"
            candidate_benchmark = tmp / "candidate_benchmark.json"
            core_realistic = tmp / "core_realistic.json"
            core_stress = tmp / "core_stress.json"
            output = tmp / "guardrail.json"

            _write_json(candidate_synth, _candidate_profile_payload())
            _write_json(candidate_realistic, _candidate_profile_payload())
            _write_json(candidate_stress, _candidate_profile_payload())
            _write_json(ann_hybrid, _ann_payload(ann_speedup=0.05))
            _write_json(candidate_benchmark, _candidate_benchmark_payload(speedup=0.03))
            _write_json(
                core_realistic,
                _core_stability_payload(
                    dataset="semi_real_5000_realistic",
                    runs=6,
                    runs_completed=6,
                    is_complete=True,
                ),
            )
            _write_json(
                core_stress,
                _core_stability_payload(
                    dataset="semi_real_5000_stress",
                    runs=3,
                    runs_completed=3,
                    is_complete=True,
                ),
            )

            command = [
                sys.executable,
                str(script),
                "--candidate-synthetic",
                str(candidate_synth),
                "--candidate-realistic",
                str(candidate_realistic),
                "--candidate-stress",
                str(candidate_stress),
                "--ann-hybrid",
                str(ann_hybrid),
                "--candidate-benchmark",
                str(candidate_benchmark),
                "--core-stability",
                str(core_realistic),
                "--core-stability",
                str(core_stress),
                "--output",
                str(output),
            ]
            result = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
            payload = json.loads(output.read_text(encoding="utf-8"))
            summary = dict(payload.get("summary") or {})
            core = dict(payload.get("core_stability") or {})
            self.assertTrue(bool(summary.get("passed")))
            self.assertEqual(int(summary.get("blocker_failures") or 0), 0)
            self.assertEqual(int(core.get("profile_count") or 0), 2)
            self.assertEqual(int(core.get("incomplete_count") or 0), 0)

    def test_cli_fails_when_core_stability_incomplete(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "run_stage2_guardrail.py"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            candidate_synth = tmp / "candidate_synth.json"
            candidate_realistic = tmp / "candidate_realistic.json"
            candidate_stress = tmp / "candidate_stress.json"
            ann_hybrid = tmp / "ann_hybrid.json"
            candidate_benchmark = tmp / "candidate_benchmark.json"
            core_incomplete = tmp / "core_incomplete.json"
            output = tmp / "guardrail_fail.json"

            _write_json(candidate_synth, _candidate_profile_payload())
            _write_json(candidate_realistic, _candidate_profile_payload())
            _write_json(candidate_stress, _candidate_profile_payload())
            _write_json(ann_hybrid, _ann_payload(ann_speedup=0.05))
            _write_json(candidate_benchmark, _candidate_benchmark_payload(speedup=0.03))
            _write_json(
                core_incomplete,
                _core_stability_payload(
                    dataset="semi_real_5000_stress",
                    runs=3,
                    runs_completed=1,
                    is_complete=False,
                ),
            )

            command = [
                sys.executable,
                str(script),
                "--candidate-synthetic",
                str(candidate_synth),
                "--candidate-realistic",
                str(candidate_realistic),
                "--candidate-stress",
                str(candidate_stress),
                "--ann-hybrid",
                str(ann_hybrid),
                "--candidate-benchmark",
                str(candidate_benchmark),
                "--core-stability",
                str(core_incomplete),
                "--output",
                str(output),
            ]
            result = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
            payload = json.loads(output.read_text(encoding="utf-8"))
            summary = dict(payload.get("summary") or {})
            core = dict(payload.get("core_stability") or {})
            self.assertFalse(bool(summary.get("passed")))
            self.assertGreater(int(summary.get("blocker_failures") or 0), 0)
            self.assertEqual(int(core.get("incomplete_count") or 0), 1)


if __name__ == "__main__":
    unittest.main()

