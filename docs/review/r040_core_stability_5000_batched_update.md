# R-040 Core Stability 5000 Batched Update

- Date: 2026-02-13
- Owner: Codex
- Scope:
  - 5000-scale core stability evidence
  - DMG activation diagnostics
  - checkpoint/resume engineering for long-running stress profile

## 1. What Changed
- Upgraded `scripts/run_core_claim_stability.py`:
  - added checkpoint batching support:
    - `--checkpoint`
    - `--resume`
    - `--max-new-runs`
  - added profile activation diagnostics:
    - `dmg_guard_activation_rate`
    - `dmg_mixed_mode_reduction_rate`
    - `baseline_mixed_mode_presence_rate`
    - `dmg_effective_profile`
  - added execution status:
    - `runs_completed`
    - `is_complete`

## 2. Experiments Completed
- realistic-5000:
  - output: `outputs/core_claim_stability_semi_real_5000_realistic.json`
  - report: `docs/eval/core_claim_stability_semi_real_5000_realistic_report.md`
  - runs: 6 (single pass)
- stress-5000:
  - output: `outputs/core_claim_stability_semi_real_5000_stress.json`
  - report: `docs/eval/core_claim_stability_semi_real_5000_stress_report.md`
  - runs: 3 (batch1 + resume chain)
  - checkpoint: `outputs/core_claim_stability_semi_real_5000_stress_checkpoint.json`

## 3. Key Findings
- realistic-5000:
  - CEG gain: +181.1
  - ARB gain: +76.8
  - DMG activation rate: 0.0
  - interpretation: realistic profile has baseline mixed-mode conflicts, but DMG gate did not activate in this threshold/data combination.
- stress-5000:
  - CEG gain: +1748.8
  - ARB gain: +2.0
  - DMG merge-block gain: +30746
  - DMG activation rate: 1.0
  - interpretation: DMG is fully activated and effective under stress profile.

## 4. Governance and Evidence Sync
- `docs/review/review_closure_matrix.md` updated to `v1.3`:
  - R-028 P3-NEW-2 marked closed.
- `scripts/build_patent_evidence_pack.py` command catalog:
  - added 5000 realistic stability command
  - added 5000 stress batch + resume commands

## 5. Validation
- `python -m unittest discover -s tests -p "test_*.py"`: PASS (`95/95`)
- `python -m compileall -q src scripts tests`: PASS
- `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json`: PASS
- `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md`: PASS (`passed=true`, `blocker_failures=0`)
- `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"`: PASS (`validation.passed=true`)
