# R-039 Core Claim Stability + Governance Update

- Date: 2026-02-13
- Owner: Codex
- Scope:
  - Core evidence strengthening for CEG/ARB/DMG
  - Review-governance hardening from R-028 suggestions

## 1. Implemented Changes
- Added `scripts/run_core_claim_stability.py`
  - repeated-run stability benchmark on external dataset
  - metrics: mean/std/ci95/p05/p50/p95/positive_rate
  - stability gate: `ci95 lower > 0` for core gains
- Added unit tests:
  - `tests/test_core_claim_stability_unit.py` (4 tests)
- Upgraded checklist:
  - `docs/REVIEW_CHECKLIST.md` `v2.1 -> v2.2`
  - mandatory review attachment: `docs/review/review_closure_matrix.md`
- Upgraded review matrix:
  - `docs/review/review_closure_matrix.md` `v1.1 -> v1.2`
  - new lifecycle status: `closed_by_reviewer`
  - R-028 reviewer direct fix recorded

## 2. Experiment Outputs
- realistic profile:
  - `outputs/core_claim_stability_semi_real_2000_realistic.json`
  - `docs/eval/core_claim_stability_semi_real_2000_realistic_report.md`
  - runs=12, warmup=2
- stress profile:
  - `outputs/core_claim_stability_semi_real_2000_stress.json`
  - `docs/eval/core_claim_stability_semi_real_2000_stress_report.md`
  - runs=4, warmup=1

## 3. Key Results
- realistic-2000:
  - CEG gain mean `+76.1`, ARB gain mean `+76.9`
  - DMG block gain `0` (profile activation not triggered)
- stress-2000:
  - CEG gain mean `+698.8`
  - ARB gain mean `+4.0`
  - DMG block gain mean `+12373`

## 4. Validation
- `python -m unittest discover -s tests -p "test_*.py"`: PASS (`93/93`)
- `python -m compileall -q src scripts tests`: PASS
- `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json`: PASS
- `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md`: PASS (`passed=true`, `blocker_failures=0`)
- `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"`: PASS (`validation.passed=true`)

## 5. Known Limits
- stress-2000 high-run experiment is expensive:
  - attempted `runs=12` timed out in local session
  - switched to `runs=4` to retain reproducible evidence without blocking pipeline
- full runtime speedup remains non-goal for core claims in this round
