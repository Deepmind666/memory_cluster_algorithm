# R-041 Core Stability Guardrail + Resume Smoke Summary

- Date: 2026-02-14
- Owner: Codex
- Scope:
  - stage-2 optional guardrail for core-stability completeness
  - checkpoint signature mismatch smoke validation
  - external review evidence summary (runtime cost + batching rationale)

## 1. Changes Implemented
- `scripts/run_stage2_guardrail.py`
  - Added optional repeatable input: `--core-stability <path>`
  - Added blocker checks requiring `is_complete=true` for selected stability profiles.
  - Added `core_stability` block in output JSON/report:
    - `profile_count`
    - `incomplete_count`
    - per-profile completion status (`runs_completed`, `runs_target`, `is_complete`)
- `tests/test_stage2_guardrail.py`
  - Added two new unit tests:
    - optional core-stability checks pass when complete
    - incomplete core-stability profile triggers blocker failure
- `tests/test_core_claim_stability_resume_smoke.py` (new)
  - CLI smoke test:
    - generate checkpoint with one run
    - rerun with `--resume` and mismatched threshold
    - assert non-zero exit and `checkpoint signature mismatch`

## 2. Guardrail Run Snapshot (with core-stability inputs)
- Command:
  - `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md --core-stability outputs/core_claim_stability_semi_real_5000_realistic.json --core-stability outputs/core_claim_stability_semi_real_5000_stress.json`
- Result:
  - `passed=true`
  - `check_count=14`
  - `blocker_failures=0`
  - `warning_failures=1`
  - `core_stability.profile_count=2`
  - `core_stability.incomplete_count=0`

## 3. Runtime Cost and Batching Rationale (5000-scale)
- Source:
  - `outputs/core_claim_stability_semi_real_5000_realistic.json`
  - `outputs/core_claim_stability_semi_real_5000_stress.json`
- Realistic profile:
  - baseline elapsed mean: `1405.430917 ms`
  - full elapsed mean: `1387.499933 ms`
  - runtime delta mean: `-17.930983 ms` (CI95 `34.746794`)
- Stress profile:
  - baseline elapsed mean: `252909.038 ms`
  - full elapsed mean: `260482.276833 ms`
  - runtime delta mean: `+7573.238833 ms` (CI95 `19006.514092`)
- Operational implication:
  - one stress run executes 5 scenarios (`baseline/ceg/arb/dmg/full`)
  - rough per-run wall-time budget is about `5 * 260482 ms ≈ 21.7 minutes`
  - `runs=3` requires roughly one hour-level execution window
  - therefore checkpoint batching/resume is required for stable reproducibility and failure recovery in stress profile.

## 4. Self-Check
- `python -m unittest tests.test_stage2_guardrail tests.test_core_claim_stability_resume_smoke -v`: PASS (`7/7`)
- `python -m unittest discover -s tests -p "test_*.py"`: PASS (`98/98`)
- `python -m compileall -q src scripts tests`: PASS
- `python scripts/run_stage2_guardrail.py ... --core-stability ...`: PASS (`blocker=0`, `warning=1`)

