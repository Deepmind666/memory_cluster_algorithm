# FINAL REPORT

鏈€鍚庢洿鏂帮細2026-02-14

## 1. 褰撳墠鐘舵€?- 鏍稿績绠楁硶涓荤嚎绋冲畾锛歚CEG + ARB + DMG + 鍐茬獊璇箟绮惧害`銆?- Candidate 宸插畬鎴愨€滈粯璁ら浂鎹熷け妗ｂ€濅笌鈥滈珮鎬ц兘瀹為獙妗ｂ€濆垎灞傜鐞嗐€?- ANN 宸插畬鎴愯瘖鏂彛寰勫榻愶細鎶ュ憡鍚屾椂缁欏嚭 `fragment-level` 涓?`cluster-entry-level`锛屼笉鍐嶆贩娣嗏€滄姤鍛婂け璐ヤ絾杩愯姝ｅ父鈥濄€?- 涓撳埄璇佹嵁鍖呭彲鑷姩閲嶅缓骞舵牎楠岋細`outputs/patent_evidence_pack.json`銆?
## 2. 鑷煡缁撴灉
1. `python -m unittest discover -s tests -p "test_*.py"`锛歚108/108` 閫氳繃
2. `python scripts/run_ann_hybrid_benchmark.py --output outputs/ann_hybrid_benchmark.json --report docs/eval/ann_hybrid_benchmark_report.md --fragment-count 240 --runs 10 --warmup-runs 2`锛氶€氳繃  
3. 鍏抽敭杈撳嚭宸叉洿鏂帮細`outputs/ann_hybrid_benchmark.json`銆乣docs/eval/ann_hybrid_benchmark_report.md`

## 3. 鍏抽敭瀹為獙缁撹
### 3.1 Core锛坮ealistic/stress锛?- `outputs/core_scaling_realistic.json`锛圢=5000锛? 
  - `ceg_conflict_priority_avg_gain=+2.29`  
  - `arb_detail_budget_avg_gain=+35.8`
- `outputs/core_scaling_stress.json`锛圢=1000锛? 
  - `ceg_conflict_priority_avg_gain=+17.0`  
  - `arb_detail_budget_avg_gain=+55.0`  
  - `dmg_merge_block_gain=+735`

### 3.2 Semi-real锛?000锛?- `outputs/core_ablation_semi_real_5000_realistic.json`  
  - CEG `+181.1`锛孉RB `+76.8`
- `outputs/core_ablation_semi_real_5000_stress_runs2.json`  
  - CEG `+1748.8`锛孌MG block `+30746`

### 3.3 Candidate锛坄outputs/candidate_profile_validation_*.json`锛?- 宸插畬鎴愪笁妗ｅ楠岋細`N=240/1000/5000`
  - `outputs/candidate_profile_validation_synthetic_active.json`
  - `outputs/candidate_profile_validation_realistic.json`
  - `outputs/candidate_profile_validation_stress.json`
  - 姹囨€绘枃妗ｏ細`docs/eval/candidate_profile_validation_summary.md`
- 榛樿鍙戝竷妗ｏ紙璐ㄩ噺浼樺厛锛宍radius=4`锛?  - 涓夌粍鏁版嵁闆嗗潎閫氳繃璐ㄩ噺闂紙`cluster_count_equal=true` 涓?`merges_applied_equal=true`锛?- 楂樻€ц兘瀹為獙妗ｏ紙`radius=3`锛夊叧閿闄?  - 鍦?`synthetic_active` 鐨?`N=240` 鍑虹幇鏈夋崯锛歚merges_applied 77 -> 76`
  - 鍦?`semi_real_realistic` 鐨?`N=5000` 鍑虹幇鏄庢樉璐熷姞閫燂細`-16.9310%`
- 鍐崇瓥锛歚radius=3` 浠呬繚鐣欏疄楠岄厤缃紝涓嶅崌涓洪粯璁ゅ彂甯冨弬鏁?
### 3.4 ANN锛坄outputs/ann_hybrid_benchmark.json`锛?- active `ann_prune`
  - `quality_gate_pass=true`
  - `avg_speedup_ratio=-0.129717`
- 鍙屽彛寰勭鍚嶈瘖鏂紙宸插榻愯繍琛岄棬鎺э級
  - `fragment-level`锛堜弗鏍奸棬锛夛細`min_unique=0.1375`锛宍max_bucket=0.420833`锛宍gate=false`
  - `cluster-entry-level`锛堣繍琛屾椂闂級锛歚min_unique=0.212766`锛宍max_bucket=0.510638`锛宍gate=true`

璇存槑锛?- 杩愯鏃?fallback 鍙戠敓鍦?cluster-entry 璐ㄥ績灞傦紝鑰屼笉鏄?fragment 灞傘€? 
- 鍥犳 ANN 鐨勨€滆繍琛屽彲鐢ㄦ€р€濅笌鈥滀弗鏍肩鍚嶅垎鏁ｅ害鈥濋渶瑕佸垎寮€鎶ュ憡銆? 
- 鐩墠 ANN 浠嶆棤绋冲畾姝ｅ姞閫熻瘉鎹紝涓嶈繘鍏ユ牳蹇冧富寮犮€?
## 4. 涓撳埄鎺ㄨ繘鍐崇瓥
- 鏍稿績涓诲紶锛歚CEG / ARB / DMG / 鍐茬獊璇箟绮惧害`
- 鍙€夊疄鏂戒緥锛歚Prune / Candidate / ANN`
- 鍙傛暟绛栫暐锛?  - Candidate 榛樿锛歚signature_radius=4`锛堥浂鎹熷け浼樺厛锛?  - Candidate 楂樻€ц兘瀹為獙妗ｏ細`signature_radius=3, projection_steps=32, max_neighbors=48`锛堥渶澶嶉獙锛?  - ANN 榛樿锛歚num_tables=3, max_neighbors=48`锛堣交閲忓彲閫夛紝涓嶇撼鍏ユ牳蹇冩巿鏉冨彊浜嬶級

## 5. 椋庨櫓
1. Candidate 鍦?active 鍦烘櫙榛樿妗ｄ粛杞诲害璐熷姞閫燂紝浣嗗綋鍓嶄紭鍏堜繚闅滈浂鎹熷け銆? 
2. ANN 鎬ц兘浠嶅亸璐燂紝鍔犻€熸敹鐩婁笉绋冲畾銆? 
3. 澶ц妯?stress 鎴愭湰楂橈紙`N=5000, runs=1` 宸查渶闀挎椂杩愯锛夛紝闇€瑕佹壒娆″寲杩愯銆? 
4. 鏂囨。涓?JSON 蹇呴』鎸佺画鍚屾锛岄伩鍏嶈瘎瀹′笉涓€鑷淬€? 

## 6. 闈炴硶寰嬪０鏄?鏈枃浠朵粎鐢ㄤ簬宸ョ▼涓庝笓鍒╄崏妗堝噯澶囷紝涓嶆瀯鎴愭硶寰嬫剰瑙併€傛寮忕敵璇峰墠搴旂敱涓撳埄浠ｇ悊浜哄鏍搞€?
## R-028 Delta (2026-02-12)
- Added stage-2 fail-fast guardrail:
  - `scripts/run_stage2_guardrail.py`
  - output: `outputs/stage2_guardrail.json`
  - report: `docs/eval/stage2_guardrail_report.md`
- Current gate result:
  - `passed=true`
  - `blocker_failures=0`
  - known limitation retained: `fast_profile_loss_at_synthetic_n240=true` (non-blocking in default mode)
- Evidence chain updated:
  - `scripts/build_patent_evidence_pack.py` now includes `CMD_STAGE2_GUARDRAIL`
  - DF-06 now references guardrail metrics and files


## R-029 Delta (2026-02-13)
- Fixed report mismatch: test baseline updated to `74/74`.
- Stage-2 guardrail now includes speed regression warnings:
  - `ann_active_speed_regression_warn`
  - `candidate_active_speed_regression_warn`
  - `ann_active_positive_speed_target_warn`
- Current guardrail status: `passed=true`, `warning_failures=1` (ANN active speed still not positive).
- ANN decision: freeze as optional implementation for patent narrative; do not promote to core claim until stable positive active speedup is observed.
- DF-06 wording corrected to reflect default Candidate zero-loss profile and experimental-risk boundary.
## R-030 Delta (2026-02-13)
- Integrated Stage-2 guardrail into CI:
  - workflow: `.github/workflows/stage2-quality-gate.yml`
  - bundle runner: `scripts/run_ci_guardrail_bundle.py`
- CI bundle result (light profile):
  - `outputs/stage2_guardrail.json` -> `passed=true`, `blocker_failures=0`, `warning_failures=1`
- Reports are redirected to `outputs/ci_reports/` in CI to avoid tracked report churn.


## R-031 Delta (2026-02-13)
- Added nightly trend pipeline:
  - workflow: `.github/workflows/stage2-nightly-trend.yml`
  - trend updater: `scripts/update_guardrail_trend.py`
- Added unit tests:
  - `tests/test_guardrail_trend_unit.py`
- Local trend output generated:
  - `outputs/stage2_guardrail_trend.json`
- Current total tests: `74/74`.

## R-032 Delta (2026-02-13)
- Added release gate workflow:
  - `.github/workflows/release-with-stage2-gate.yml`
- Added gate-check unit tests:
  - `tests/test_check_stage2_gate_for_sha_unit.py`
- Enforced release rule:
  - `tag/release` is allowed only after target commit SHA passes `stage2-quality-gate` within the last 168 hours.
- Local reproducibility:
  - `python scripts/check_stage2_gate_for_sha.py --repo <owner/repo> --sha <commit_sha> --workflow-file stage2-quality-gate.yml --max-age-hours 168 --output outputs/release_gate_check.json`

## R-033 Delta (2026-02-13)
- Fixed CI output-path isolation P1:
  - `scripts/run_ci_guardrail_bundle.py` now writes all CI benchmark/guardrail JSON to `outputs/ci_outputs/*.json`.
  - `run_stage2_guardrail.py` in CI bundle now consumes all inputs from `outputs/ci_outputs/`.
- Workflow alignment:
  - `.github/workflows/stage2-quality-gate.yml` artifact paths switched to `outputs/ci_outputs/*.json`.
  - `.github/workflows/stage2-nightly-trend.yml` trend input switched to `outputs/ci_outputs/stage2_guardrail.json`.
- Regression protection:
  - `tests/test_ci_guardrail_bundle_unit.py` added command-level path isolation assertion.

## R-034 Delta (2026-02-13)
- Added CI output isolation guard script:
  - `scripts/check_ci_output_isolation.py`
- Added unit tests:
  - `tests/test_ci_output_isolation_unit.py`
- CI hardening:
  - `.github/workflows/stage2-quality-gate.yml` now runs output-isolation check before compile/tests.
  - `.github/workflows/stage2-nightly-trend.yml` now runs output-isolation check before compile/tests.
  - Both workflows upload `outputs/ci_outputs/output_isolation_check.json` artifact.
- Scope:
  - Enforces CI benchmark JSON must stay in `outputs/ci_outputs/*.json`.
  - Blocks accidental write-back to authoritative `outputs/*.json` root paths.

## R-035 Delta (2026-02-13)
- Upgraded review protocol:
  - `docs/REVIEW_CHECKLIST.md` updated to `v2.1`.
- Policy hardening in checklist:
  - CI output isolation section is now explicit P1 mandatory gate.
  - Required checks now include:
    - `check_ci_output_isolation.py` → `passed=true`
    - `violation_count=0`
    - both workflows include `Validate CI Output Isolation` step

## R-036 Delta (2026-02-13)
- R-027 review follow-up cleanup:
  - Reordered R-delta sections to chronological order (`R-031 -> R-032 -> R-033 -> R-034 -> R-035`).
  - Corrected R-031 historical test-count snapshot from `84/84` to `74/74`.
  - Aligned R-032 progress record with explicit full-test count (`79/79`) in `WORK_PROGRESS.md`.

## R-037 Delta (2026-02-13)
- Added review closure matrix:
  - `docs/review/review_closure_matrix.md`
- R-027 key findings mapped to closure records with evidence links:
  - P2-1, P2-2, P3-2 marked `closed`
  - carried P1-1 marked `closed` (R-033/R-034/R-035 chain)

## R-038 Delta (2026-02-13)
- Hardened review-closure automation:
  - `scripts/append_review_closure_round.py` now validates round-id format and handles anchor headers with suffixes.
  - Duplicate-round protection remains enforced (`exit=2` on duplicate section).
- Added unit coverage:
  - `tests/test_review_closure_matrix_unit.py` (5 tests).
- Test baseline update:
  - full suite `84/84 -> 89/89`.
- Docs sync:
  - `README.md` now includes closure-matrix template command.
  - `docs/review/review_closure_matrix.md` upgraded to `v1.1`.

## R-039 Delta (2026-02-13)
- Added core-claim stability benchmark script:
  - `scripts/run_core_claim_stability.py`
  - metrics: mean/std/CI95/p05/p50/p95/positive_rate for CEG/ARB/DMG gains.
- Added unit tests:
  - `tests/test_core_claim_stability_unit.py` (4 tests).
- Test baseline update:
  - full suite `89/89 -> 93/93`.
- Generated semi-real stability reports:
  - `docs/eval/core_claim_stability_semi_real_2000_realistic_report.md` (`runs=12`)
  - `docs/eval/core_claim_stability_semi_real_2000_stress_report.md` (`runs=4`)
- Key results:
  - realistic-2000: `CEG +76.1 (CI95 lower>0)` / `ARB +76.9 (CI95 lower>0)` / `DMG +0` (not triggered in this profile).
  - stress-2000: `CEG +698.8` / `ARB +4.0` / `DMG +12373` (all CI95 lower>0).
- Process hardening:
  - `docs/REVIEW_CHECKLIST.md` upgraded to `v2.2` and now requires `docs/review/review_closure_matrix.md` as a mandatory review attachment.
  - `docs/review/review_closure_matrix.md` upgraded to `v1.2`, added `closed_by_reviewer` lifecycle status.

## R-040 Delta (2026-02-13)
- Upgraded core stability script:
  - `scripts/run_core_claim_stability.py` now supports batched/resumable runs via `--checkpoint` + `--resume` + `--max-new-runs`.
  - Added DMG profile activation metrics:
    - `dmg_guard_activation_rate`
    - `dmg_mixed_mode_reduction_rate`
    - `baseline_mixed_mode_presence_rate`
    - `dmg_effective_profile`
- Large-scale reproducible stability runs completed:
  - `outputs/core_claim_stability_semi_real_5000_realistic.json` (`runs=6`, complete)
  - `outputs/core_claim_stability_semi_real_5000_stress.json` (`runs=3`, completed by checkpoint resume)
  - reports:
    - `docs/eval/core_claim_stability_semi_real_5000_realistic_report.md`
    - `docs/eval/core_claim_stability_semi_real_5000_stress_report.md`
- Key observations:
  - realistic-5000: CEG/ARB positive and stable; DMG activation rate `0.0` (profile not activated, now explicitly reported instead of being ambiguous).
  - stress-5000: DMG activation rate `1.0`; CEG/ARB/DMG gains all positive; full runtime CI upper bound remains non-stable (`full_runtime_ci95_upper_lt_0=false`).
- Evidence pipeline sync:
  - `scripts/build_patent_evidence_pack.py` command catalog now includes 5000-scale stability commands (realistic + stress batched resume chain).

## R-041 Delta (2026-02-14)
- Stage-2 guardrail enhanced with optional core-stability completeness gate:
  - `scripts/run_stage2_guardrail.py` adds repeatable `--core-stability <path>` input.
  - New blocker checks:
    - `core_stability_complete_semi_real_5000_realistic`
    - `core_stability_complete_semi_real_5000_stress`
  - Current guarded run result:
    - `check_count=14`
    - `blocker_failures=0`
    - `warning_failures=1` (known ANN active positive-speed target warning)
    - `core_stability.profile_count=2`, `core_stability.incomplete_count=0`
- Added CI-friendly resume mismatch smoke test:
  - `tests/test_core_claim_stability_resume_smoke.py`
  - Verifies `run_core_claim_stability.py --resume` fails when checkpoint signature mismatches current thresholds.
- Test baseline update:
  - full suite `93/93 -> 98/98`.
- Evidence command sync:
  - `CMD_STAGE2_GUARDRAIL` now includes two core-stability inputs for reproducible completeness checks in evidence rebuild.

## R-042 Delta (2026-02-14)
- Added CLI end-to-end smoke tests for stage-2 core-stability guard:
  - `tests/test_stage2_guardrail_cli_smoke.py`
  - verifies:
    - pass path: `--core-stability` profiles complete -> exit `0`
    - fail path: incomplete profile -> exit `2` + blocker failure recorded
- Process hardening update:
  - `docs/REVIEW_CHECKLIST.md` upgraded to `v2.3`
  - Stage-2 checklist now explicitly requires:
    - `--core-stability` inputs when stability evidence is cited
    - `core_stability.incomplete_count=0`
- Test baseline update:
  - full suite `98/98 -> 100/100`.

## R-043 Delta (2026-02-14)
- Integrated core-stability completeness check into CI bundle execution path:
  - `scripts/run_ci_guardrail_bundle.py` now auto-generates lightweight fixtures:
    - `outputs/ci_outputs/core_claim_stability_ci_realistic.json`
    - `outputs/ci_outputs/core_claim_stability_ci_stress.json`
  - Stage-2 guardrail invocation in CI bundle now always includes:
    - `--core-stability outputs/ci_outputs/core_claim_stability_ci_realistic.json`
    - `--core-stability outputs/ci_outputs/core_claim_stability_ci_stress.json`
- CI output isolation policy extended:
  - `scripts/check_ci_output_isolation.py` now treats `--core-stability` as guarded JSON output/input path.
  - Added root-path forbidden checks for CI core-stability fixture names.
- Workflow artifact sync:
  - `.github/workflows/stage2-quality-gate.yml` and `.github/workflows/stage2-nightly-trend.yml` now upload CI core-stability fixture JSON files.
- Test baseline update:
  - full suite `100/100 -> 102/102`.

## R-044 Delta (2026-02-14)
- Added optional strict policy to CI guardrail bundle:
  - `scripts/run_ci_guardrail_bundle.py` now supports:
    - `--strict-ann-positive-speed-streak`
    - `--trend-input`
    - `--summary-output`
  - New output:
    - `outputs/ci_outputs/ci_guardrail_bundle_summary.json`
  - Default behavior remains unchanged (`strict threshold = 0`, no blocking).
- Added strict-policy unit coverage:
  - `tests/test_ci_guardrail_bundle_unit.py`
  - validates streak counting and strict trigger behavior.
- Strengthened CI output isolation policy:
  - `scripts/check_ci_output_isolation.py` now treats
    - `outputs/ci_guardrail_bundle_summary.json`
    as forbidden root path.
  - Required workflow artifact paths now include:
    - `outputs/ci_outputs/ci_guardrail_bundle_summary.json`
    for both stage2 quality and nightly trend workflows.
- Workflow artifact sync:
  - `.github/workflows/stage2-quality-gate.yml`
  - `.github/workflows/stage2-nightly-trend.yml`
  - both now upload `outputs/ci_outputs/ci_guardrail_bundle_summary.json`.
- Test baseline update:
  - full suite `102/102 -> 108/108`.

## R-045 Delta (2026-02-14)
- Switched to patent-material handover phase (agent track), no new algorithm/test scope in this round.
- Added agent handover package in `docs/patent_kit/`:
  - `12_代理人交接包_一页纸.md`
  - `13_代理人交接包_权利要求策略说明.md`
  - `14_代理人交接包_证据索引与提交流程.md`
  - `15_代理人沟通邮件模板.md`
- Updated handover index:
  - `00_技术交底书_总览.md` now includes items 12-15.

## R-046 Delta (2026-02-14)
- Converted patent package into CNIPA-style formal draft documents:
  - `16_CNIPA_说明书_正式稿.md`
  - `17_CNIPA_权利要求书_正式稿.md`
  - `18_CNIPA_说明书摘要_正式稿.md`
  - `19_CNIPA_附图文字描述稿.md`
- Added drawing-ready textual script for figures:
  - figure list (`图1-图6`),
  - element IDs,
  - connection logic,
  - caption suggestions,
  - abstract-figure recommendation.
- Updated index:
  - `00_技术交底书_总览.md` now includes items 16-19.
