# Review Closure Matrix

Version: v1.3
Last Updated: 2026-02-13  
Owner: Codex (implementation), Claude Opus (review)

## Purpose
Track reviewer findings as structured closure records:
- finding id and severity
- closure status and resolution round
- concrete evidence files/commands

This matrix is the fast-check handoff artifact for each review cycle.

## Legend
- `open`: not yet fixed
- `in_progress`: partial fix, pending verification
- `closed`: fixed and verified
- `closed_by_reviewer`: fixed directly by reviewer and verified
- `waived`: accepted limitation (documented, not treated as bug)

## R-027 Findings Closure
| Source Review | Finding ID | Severity | Finding Summary | Status | Resolved In | Evidence |
|---|---|---|---|---|---|---|
| R-027 | P2-1 | P2 | `FINAL_REPORT` R-delta order was non-chronological | `closed` | R-036 | `docs/FINAL_REPORT.md` (R-031 -> R-032 -> R-033 -> R-034 -> R-035) |
| R-027 | P2-2 | P2 | `FINAL_REPORT` R-031 test snapshot should be `74/74` | `closed` | R-036 | `docs/FINAL_REPORT.md` (`R-031 Delta` now `Current total tests: 74/74`) |
| R-027 | P3-2 | P3 | `WORK_PROGRESS` R-032 verification missed explicit full test count | `closed` | R-036 | `WORK_PROGRESS.md` (`R-032` line now includes `79/79`) |
| R-026 (carried into R-027) | P1-1 | P1 | CI bundle overwrote authoritative `outputs/*.json` | `closed` | R-033 + R-034 + R-035 | `scripts/run_ci_guardrail_bundle.py`, `scripts/check_ci_output_isolation.py`, `docs/REVIEW_CHECKLIST.md` v2.1 |

## R-028 Findings Closure
| Source Review | Finding ID | Severity | Finding Summary | Status | Resolved In | Evidence |
|---|---|---|---|---|---|---|
| R-028 | P3-NEW-1 | P3 | `.claude.md` Cross-Reference retained `v2.0` label | `closed_by_reviewer` | R-028 | `.claude.md` + `docs/review/r028_r036_r037_closure_matrix_review.md` |
| R-028 | P3-NEW-2 | P3 | closure matrix should track reviewer-direct-fix items | `closed` | R-039 + R-040 | `docs/review/review_closure_matrix.md` (`closed_by_reviewer` status + R-028 mapping) |

## Accepted Limitations (Non-blocking)
| Item | Severity | Status | Evidence |
|---|---|---|---|
| ANN active speed target not positive | warning | `waived` | `outputs/stage2_guardrail.json` (`ann_active_positive_speed_target_warn=false`) |
| Candidate fast profile (`r=3`) lossy at synthetic N=240 | warning | `waived` | `outputs/stage2_guardrail.json` (`fast_profile_loss_at_synthetic_n240=true`) |

## Current Open Findings
No open findings from R-027.

## Maintenance Rule
For each new review round:
1. append new findings rows with initial `open` status
2. after fix, update `status/resolved in/evidence`
3. if accepted as limitation, mark `waived` with explicit artifact reference
4. template command:
   - `python scripts/append_review_closure_round.py --round R-0XX --rows 3`
5. if reviewer directly patches issue, use `closed_by_reviewer`
