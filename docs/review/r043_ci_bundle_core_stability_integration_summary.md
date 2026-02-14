# R-043 CI Bundle Core-Stability Integration Summary

- Date: 2026-02-14
- Owner: Codex
- Scope:
  - integrate core-stability completeness checks into CI bundle default execution path
  - expand output-isolation guard to include `--core-stability` paths

## 1. Implementation
- `scripts/run_ci_guardrail_bundle.py`
  - added `_write_core_stability_fixture(...)`
  - writes two CI fixture files:
    - `outputs/ci_outputs/core_claim_stability_ci_realistic.json`
    - `outputs/ci_outputs/core_claim_stability_ci_stress.json`
  - injects both files into guardrail command via repeated `--core-stability` arguments.
- `scripts/check_ci_output_isolation.py`
  - added `--core-stability` to protected output/input flags
  - added root-path forbidden checks for CI core-stability fixture JSON names
  - default bundle command construction updated with core-stability fixture paths
- workflow artifacts
  - `.github/workflows/stage2-quality-gate.yml` now uploads both CI core-stability fixture JSON files
  - `.github/workflows/stage2-nightly-trend.yml` now uploads both CI core-stability fixture JSON files

## 2. Test Coverage
- `tests/test_ci_guardrail_bundle_unit.py`
  - validates bundle command includes both `--core-stability` CI paths
  - validates fixture payload generation keys/values
- `tests/test_ci_output_isolation_unit.py`
  - validates root-path violation detection for `--core-stability outputs/core_claim_stability_ci_realistic.json`

## 3. Validation
- `python -m unittest tests.test_ci_guardrail_bundle_unit tests.test_ci_output_isolation_unit -v`: PASS (`9/9`)
- `python scripts/run_ci_guardrail_bundle.py --dataset-size 240 --benchmark-fragment-count 120 --runs 1 --warmup-runs 0`: PASS
  - guardrail result: `check_count=14`, `blocker_failures=0`, `warning_failures=1`
- `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json`: PASS (`passed=true`, `violation_count=0`)
- `python -m unittest discover -s tests -p "test_*.py"`: PASS (`102/102`)
- `python -m compileall -q src scripts tests`: PASS

## 4. Outcome
- Core-stability completeness gate is now part of CI default behavior, not only local/manual execution.
- CI isolation guard now explicitly covers the new core-stability path surface.

