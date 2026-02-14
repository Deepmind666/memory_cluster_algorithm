# R-042 Stage-2 Guardrail CLI Integration Summary

- Date: 2026-02-14
- Owner: Codex
- Scope:
  - `run_stage2_guardrail.py --core-stability` CLI-level integration coverage
  - review checklist hardening against stale core-stability evidence

## 1. What Was Added
- New test file: `tests/test_stage2_guardrail_cli_smoke.py`
  - `test_cli_with_core_stability_completeness_passes`
    - builds minimal JSON fixtures for candidate/ANN/core-stability
    - calls `scripts/run_stage2_guardrail.py` via subprocess
    - asserts exit code `0`, `summary.passed=true`, `core_stability.incomplete_count=0`
  - `test_cli_fails_when_core_stability_incomplete`
    - feeds incomplete core-stability profile (`is_complete=false`)
    - asserts exit code `2`, blocker failure present

## 2. Process Hardening
- Updated `docs/REVIEW_CHECKLIST.md` to `v2.3`
- Added Stage-2 mandatory checklist item:
  - if core-stability evidence is referenced, guardrail command must include `--core-stability` inputs and output must satisfy `core_stability.incomplete_count=0`.

## 3. Validation
- `python -m unittest tests.test_stage2_guardrail tests.test_stage2_guardrail_cli_smoke tests.test_core_claim_stability_resume_smoke -v`: PASS (`9/9`)
- `python -m unittest discover -s tests -p "test_*.py"`: PASS (`100/100`)
- `python -m compileall -q src scripts tests`: PASS
- `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json`: PASS
- `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md --core-stability outputs/core_claim_stability_semi_real_5000_realistic.json --core-stability outputs/core_claim_stability_semi_real_5000_stress.json`: PASS (`check_count=14`, `blocker_failures=0`)
- `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report docs/patent_kit/10_区别特征_技术效果_实验映射.md`: PASS (`validation.passed=true`)

## 4. Outcome
- Stage-2 core-stability guard is now covered at unit level + CLI integration level.
- Checklist policy now prevents stale/incomplete stability evidence from silently entering review packets.

