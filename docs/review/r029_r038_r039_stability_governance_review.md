# R-029 Opus Review — R-038/R-039 Closure-Matrix Automation + Core-Claim Stability

- **Reviewer**: Claude Opus 4.6
- **Date**: 2026-02-13
- **Baseline**: R-039 Codex (commit 86ca2d4), 93/93 tests
- **Scope**: R-038 (closure-matrix automation) + R-039 (core-claim stability benchmark + governance v2.2)
- **Rating**: **A-**

## 1. Executive Summary

R-038 + R-039 is a substantive two-round delivery that (a) automates the review closure matrix with robust input validation and (b) introduces a repeated-run stability benchmark for the three core claims (CEG/ARB/DMG). The stability benchmark adds genuine patent evidence value by proving deterministic reproducibility of positive gains. Governance upgrades are well-targeted — the v2.2 checklist mandatory attachment and `closed_by_reviewer` status directly address R-028 suggestions. Three documentation synchronization issues were found (1 P1, 2 P2), one of which is a recurring pattern.

## 2. Independent Verification

| Check | Result |
|---|---|
| `python -m compileall -q src scripts tests` | PASS |
| `python -m unittest discover -s tests -p "test_*.py"` | **93/93 PASS** (3.844s) |
| `python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json` | `passed=true`, `violation_count=0` |
| `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md` | `passed=true`, `blocker=0`, `warning=1` |
| `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"` | `validation.passed=true`, `missing_*=[]` |
| Temporary files (`tmp_*.py`) | None found |

## 3. R-038 Assessment — Closure-Matrix Automation

### 3.1 Script Quality (`append_review_closure_round.py`)
- **Round ID validation**: Regex `^R-\d{3,4}[A-Za-z0-9-]*$` — correct and restrictive enough
- **Anchor matching**: `_first_insert_anchor_position` uses `startswith` on stripped lines against `_INSERT_BEFORE_HEADERS` tuple — correctly handles suffixed headers (e.g., `## Accepted Limitations (Non-blocking)`)
- **Duplicate protection**: Raises `ValueError` if `## {round_id} Findings Closure` already exists — correct
- **Last-Updated propagation**: Updates the `Last Updated:` line on every insert — correct
- **Fallback**: When no anchor headers found, appends to end — reasonable default

### 3.2 Test Quality (`test_review_closure_matrix_unit.py`)
- 5 tests covering: insertion position, duplicate rejection, no-anchor fallback, format validation (accept/reject)
- **Coverage gap**: No test for the `main()` CLI path (argparse + file I/O). Acceptable since the core logic is covered via `insert_round_section`.
- **Fixture realism**: `_MATRIX_TEXT` mirrors the real matrix structure — good

### 3.3 Verdict
Clean, focused utility. Test count correctly tracked: 84/84 → 89/89.

## 4. R-039 Assessment — Core-Claim Stability Benchmark

### 4.1 Script Quality (`run_core_claim_stability.py`)

**Strengths:**
- Well-structured 5-scenario design (baseline, ceg, arb, dmg, full) with per-run gain computation
- `compute_distribution_stats` provides comprehensive summary: mean/std/ci95/percentiles/positive_rate
- Stability gate (`ci95 lower > 0`) is a meaningful pass/fail criterion for patent evidence
- Warmup support prevents cold-start noise from tainting results

**Observations:**
- All algorithmic gains show `std=0` — the clustering algorithm is fully deterministic. The stability benchmark thus proves **reproducibility** (identical results every run) rather than **statistical robustness** (consistent results with variance). For patent evidence, deterministic positive gain is actually stronger than statistical positive gain. This is a valid and valuable finding.
- The DMG `gain=0` in realistic profile is correctly explained as "profile not triggered" (high merge_threshold means no conflicting merges occur). The next_phase_plan correctly identifies this as needing a profile-activation coverage metric.

### 4.2 Test Quality (`test_core_claim_stability_unit.py`)
- 4 tests covering: constant distribution, positive rate, single-value CI, empty input
- All directly test `compute_distribution_stats` — the core statistical function

### 4.3 Experiment Results Verification

| Profile | CEG gain | ARB gain | DMG block gain | Stability Gate |
|---|---|---|---|---|
| realistic-2000 (runs=12) | +76.1 (ci95=0, positive=100%) | +76.9 (ci95=0, positive=100%) | 0 (not triggered) | CEG/ARB: PASS, DMG: N/A |
| stress-2000 | +698.8 (ci95=0, positive=100%) | +4.0 (ci95=0, positive=100%) | +12373 (ci95=0, positive=100%) | All PASS |

Cross-checked against raw JSON artifacts — values match.

### 4.4 Governance Upgrades
- **REVIEW_CHECKLIST v2.2**: Added `送审附件必须包含 docs/review/review_closure_matrix.md` to §D — directly addresses R-028 P3-NEW-2 suggestion. Added `closed_by_reviewer` status documentation to §I.
- **review_closure_matrix.md v1.2**: Added `closed_by_reviewer` to legend, recorded R-028 P3-NEW-1 as `closed_by_reviewer` — correct and properly traced.
- **Evidence pack**: `CMD_CORE_STABILITY_REALISTIC` and `CMD_CORE_STABILITY_STRESS` added to COMMAND_CATALOG — verified present.

## 5. Document Consistency Check

| Document | Status | Notes |
|---|---|---|
| `docs/FINAL_REPORT.md` §2 | **FAIL** | Test count shows `84/84`, actual is `93/93` — see P1-1 |
| `docs/FINAL_REPORT.md` R-deltas | OK | R-038 and R-039 Deltas present, chronological, test progression 84→89→93 tracked |
| `WORK_PROGRESS.md` | OK | R-038 and R-039 entries complete with verification results (93/93) |
| `docs/design/next_phase_plan.md` | OK | R-038 and R-039 Plan Updates present |
| `.claude.md` | **WARN** | Lines 42/54 still reference `v2.1`, should be `v2.2` — see P2-2 |
| `README.md` | OK | Stability commands added to quick-run section |
| `docs/review/review_closure_matrix.md` | OK | v1.2, `closed_by_reviewer` added |
| `docs/REVIEW_CHECKLIST.md` | OK | v2.2, mandatory attachment rule added |
| Stress stability report artifact | **MISMATCH** | Report says `runs=12, warmup=2` but docs say `runs=4, warmup=1` — see P2-1 |

## 6. Findings

### P1-1: FINAL_REPORT §2 test count not updated (84/84 → 93/93)
- **Severity**: P1
- **Location**: `docs/FINAL_REPORT.md` line 7
- **Issue**: §2 self-check section still reads `84/84` but actual test count is `93/93`. Tests were added in both R-038 (+5) and R-039 (+4), but §2 was never updated. The R-delta sections correctly track the progression (`84/84 -> 89/89` in R-038, `89/89 -> 93/93` in R-039), but the header section was left stale.
- **Rule**: CLAUDE.md §3.2 — "每次新增/删除测试后，同一个提交内必须同步更新 FINAL_REPORT §2"
- **Pattern**: This is the same class of issue as R-027 P2-2 (R-031 test count 84→74 not reflected in §2), which was fixed in R-036. The fix addressed the historical case but didn't prevent the forward case.
- **Fix**: Update FINAL_REPORT §2 line 7 from `84/84` to `93/93`.

### P2-1: Stress stability report artifact/documentation runs mismatch
- **Severity**: P2
- **Location**: `outputs/core_claim_stability_semi_real_2000_stress.json` + `docs/eval/core_claim_stability_semi_real_2000_stress_report.md`
- **Issue**: The report artifact on disk records `runs: 12, warmup_runs: 2`, but all documentation references say `runs=4, warmup=1`:
  - WORK_PROGRESS verification command: `--runs 4 --warmup-runs 1`
  - FINAL_REPORT R-039 Delta: `runs=4`
  - r039 review doc: `runs=4, warmup=1`
  - CMD_CORE_STABILITY_STRESS in evidence pack: `--runs 4 --warmup-runs 1`
- **Rule**: CLAUDE.md §3.3 — report/JSON must come from the same run as the documented command
- **Impact**: Mitigated by the fact that all metrics are deterministic (std=0), so values are identical regardless of runs count. However, re-running the documented `CMD_CORE_STABILITY_STRESS` command with `--runs 4` will produce a report with `runs: 4` metadata, not matching the current artifact.
- **Fix**: Either (a) regenerate the report with `--runs 4 --warmup-runs 1` to match documentation, or (b) update all documentation to reflect `runs=12, warmup=2` if the 12-run result is preferred.

### P2-2: .claude.md checklist version reference not updated (v2.1 → v2.2)
- **Severity**: P2 (upgraded from P3 — recurring pattern)
- **Location**: `.claude.md` lines 42 and 54
- **Issue**: Both lines still reference `docs/REVIEW_CHECKLIST.md (v2.1)` but the checklist was upgraded to v2.2 in this round. This is the **same pattern** as R-028 P3-NEW-1 (v2.0→v2.1 residual on line 54). Despite that fix being applied, the forward upgrade from v2.1→v2.2 was missed again.
- **Root cause**: No automated check ensures `.claude.md` version references stay in sync with the actual file version. Manual sync is fragile during multi-file updates.
- **Fix**: Update both lines 42 and 54 from `(v2.1)` to `(v2.2)`.
- **Structural suggestion**: Consider adding a self-check step: `grep -c "v2.2" .claude.md` as part of SC-R0XX checklist when version bumps occur.

### P3-1: CI95 uses z-distribution instead of t-distribution
- **Severity**: P3 (no practical impact)
- **Location**: `scripts/run_core_claim_stability.py` line 41
- **Issue**: `ci95 = 1.96 * std / sqrt(n)` uses the normal-distribution z-value (1.96). For small samples (n=4 in stress), the correct 95% CI would use `t(n-1, 0.975)` — e.g., `t(3, 0.975) = 3.182`. However, since all algorithmic metrics have `std=0` (deterministic), CI95=0 regardless of the multiplier. **No practical impact.**
- **Fix (optional)**: Replace 1.96 with a t-distribution lookup if non-deterministic metrics are ever added.

### P3-2: Redundant `compute_distribution_stats` calls in `_build_summary`
- **Severity**: P3 (efficiency)
- **Location**: `scripts/run_core_claim_stability.py` lines 232-258
- **Issue**: Each gain series is passed through `compute_distribution_stats()` three times — once for the output dict value, twice for the stability gate bounds. Should cache the result.
- **Fix (optional)**: `stats = compute_distribution_stats(ceg_gain)` then reference `stats["mean"]` and `stats["ci95"]` in the gate.

## 7. R-028 Findings Follow-Up

| R-028 Finding | Status | Notes |
|---|---|---|
| P3-NEW-1: `.claude.md` v2.0 residual | CLOSED by Opus in R-028 | Verified: line 54 now says v2.1 (but see P2-2 for the new v2.1→v2.2 gap) |
| P3-NEW-2: Closure matrix should track reviewer-fixed items | **CLOSED** in R-039 | `closed_by_reviewer` status added to v1.2, R-028 P3-NEW-1 recorded |

## 8. Review Trajectory

| Round | Reviewer | Rating | Key Theme |
|---|---|---|---|
| R-019 | Opus | B | ANN + Evidence pack |
| R-020 | Opus | B- | _bucket_value degradation |
| R-021 | Opus | B+ | P0 fix + scaling |
| R-022 | Opus | A- | Semi-real + param sweep |
| R-023 | Opus | A | Candidate equiv + N=5000 |
| R-024 | Opus | A- | ANN diagnostic alignment |
| R-025 | Opus | A- | Stage-2 guardrail + tests |
| R-026 | Opus | A- | Speed gates + CI integration |
| R-027 | Opus | A | CI isolation + release + trend |
| R-028 | Opus | A | Review closure + matrix |
| **R-029** | **Opus** | **A-** | **Stability benchmark + governance** |

## 9. Conclusion

The core contribution is strong: a deterministic stability benchmark that proves CEG/ARB/DMG gains are reproducible across repeated runs with ci95-based gates. The closure-matrix automation is clean and well-tested. The governance upgrades (v2.2 checklist, v1.2 matrix with `closed_by_reviewer`) directly close R-028 suggestions.

The rating drops from A to A- due to:
1. **Recurring documentation sync failure**: FINAL_REPORT §2 test count was not updated — the exact same class of issue that was fixed in R-036 (P2-2). The lesson from that fix did not translate into a prevention mechanism.
2. **Artifact/command mismatch**: The stress stability report on disk was generated by a different command than what's documented, violating §3.3.
3. **Version reference drift recurrence**: `.claude.md` v2.1→v2.2 missed — same pattern as the v2.0→v2.1 residual fixed in R-028.

**Structural recommendation**: The version-reference and test-count sync issues keep recurring because they rely on manual discipline during multi-file updates. Consider adding a lightweight pre-commit check (e.g., a script that extracts the actual test count and checklist version, then greps all expected locations for matching values).

**Verdict**: Approved with P1-1 fix required in next round, P2-1/P2-2 fixes recommended.
