# R-044 CI Bundle Strict Policy + Isolation Sync Summary

## Scope
- Add optional strict streak policy in `run_ci_guardrail_bundle.py`.
- Add CI summary artifact and enforce path isolation.
- Keep default CI semantics unchanged.

## Changes
1. CI bundle script
- File: `scripts/run_ci_guardrail_bundle.py`
- Added args:
  - `--strict-ann-positive-speed-streak`
  - `--trend-input`
  - `--summary-output`
- Added strict policy helpers:
  - `_load_trend_history(...)`
  - `_ann_not_positive_streak(...)`
  - `evaluate_strict_ann_positive_speed_policy(...)`
- Added summary output:
  - `outputs/ci_outputs/ci_guardrail_bundle_summary.json`

2. Isolation guard script
- File: `scripts/check_ci_output_isolation.py`
- Added forbidden root path:
  - `outputs/ci_guardrail_bundle_summary.json`
- Added required workflow paths:
  - `outputs/ci_outputs/ci_guardrail_bundle_summary.json` in both stage2 workflows.

3. Workflows
- Files:
  - `.github/workflows/stage2-quality-gate.yml`
  - `.github/workflows/stage2-nightly-trend.yml`
- Added uploaded artifact:
  - `outputs/ci_outputs/ci_guardrail_bundle_summary.json`

4. Tests
- `tests/test_ci_guardrail_bundle_unit.py`
  - strict streak count
  - strict trigger threshold
  - threshold=0 non-trigger behavior
- `tests/test_ci_output_isolation_unit.py`
  - bundle summary root-path violation
  - missing required summary artifact path in workflow text

## Validation
- `python -m unittest tests.test_ci_guardrail_bundle_unit tests.test_ci_output_isolation_unit -v` -> PASS (15/15)
- `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json` -> PASS (`passed=true`, `violation_count=0`)
- `python scripts/run_ci_guardrail_bundle.py --dataset-size 240 --benchmark-fragment-count 120 --runs 1 --warmup-runs 0` -> PASS (`stage2_guardrail_passed=true`, `strict_triggered=false`)
- `python -m unittest discover -s tests -p "test_*.py"` -> PASS (108/108)
- `python -m compileall -q src scripts tests` -> PASS
- `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md` -> PASS (`passed=true`, `blocker_failures=0`)
- `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"` -> PASS (`validation.passed=true`)

## Risk Notes
- Strict mode is intentionally optional; default pipeline behavior is unchanged.
- Trend-history based blocking can be enabled later after defining an explicit threshold policy per environment.
- ANN active positive-speed warning remains a known limitation and is still warning-level unless strict mode is enabled.

## Decision
- R-044 accepted as a governance hardening round.
- Ready for next algorithm/experiment round without changing current release gate semantics.
