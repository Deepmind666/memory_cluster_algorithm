# Next Phase Plan (R-026 Draft)

最后更新：2026-02-12

## 1. 本轮结论
- 核心专利主线继续锁定：`CEG + ARB + DMG + 冲突语义精度`。
- R-023 指出的 ANN 诊断口径问题已处理：benchmark 现在同时输出 `fragment-level` 与 `cluster-entry-level`。
- Candidate 策略明确分为两档：默认零损失档（发布）与高性能实验档（需复验）。
- ANN 保持“可选实施例”定位，当前不作为核心授权论据。

## 2. 已完成动作（R-026）
1. `scripts/run_ann_hybrid_benchmark.py`
- 新增 `cluster-entry` 诊断（与运行时 fallback 同口径）。
- 输出双门控状态：
  - `signature_gate_pass_fragment_strict`
  - `signature_gate_pass_cluster_runtime`
- `signature_gate_pass` 别名对齐到运行时门控，避免认知歧义。

2. `tests/test_merge_ann_candidates.py`
- 新增回归测试：验证 cluster-entry 签名质量满足运行时门控。
- 全量单测由 `57` 增至 `58`。

3. 基准重跑
- 重跑 `ann_hybrid_benchmark`，输出更新到：
  - `outputs/ann_hybrid_benchmark.json`
  - `docs/eval/ann_hybrid_benchmark_report.md`

4. 文档同步
- 更新 `docs/FINAL_REPORT.md`，固化：
  - Candidate 双档策略
  - ANN 默认策略与可选实施例定位
  - ANN 双口径签名诊断解释

5. Candidate 三档复验（新增）
- 新增脚本：`scripts/run_candidate_profile_validation.py`
- 已完成 `N=240/1000/5000` 复验：
  - `synthetic_active`（runs=2）
  - `semi_real_realistic`（runs=2）
  - `semi_real_stress`（runs=1，成本受限）
- 新增总结文档：`docs/eval/candidate_profile_validation_summary.md`
- 结论：默认 `radius=4` 保持；`radius=3` 继续仅作为实验参数

## 3. 下一阶段任务（按优先级）
1. P0 证据链收口
- 基于最新输出重建专利证据包：`scripts/build_patent_evidence_pack.py`
- 同步校验：
  - `docs/patent_kit/10_区别特征_技术效果_实验映射.md`
  - `docs/patent_kit/11_主张_证据_命令对照.md`

2. P1 Candidate 回归自动化
- 将 `run_candidate_profile_validation.py` 纳入固定回归命令集（至少周级重跑一次）。
- 新增 fail-fast 门：
  - `synthetic_active@N=240` 若 `radius=3` 再次有损，自动标红；
  - 默认档 `radius=4` 任一规模质量门失败则阻断发布。

3. P1 ANN 决策收敛
- 保持默认 `tables=3` 轻量档，继续收集运行证据。
- 如果后续仍无稳定正加速，正式冻结为“仅可选实施例”，停止性能优化投入。

4. P2 工程稳健性
- 增补 `embed.py / eval.py / store.py` 细粒度单测。
- 增加性能回归告警脚本（避免无意退化）。

## 4. 风险与应对
1. 风险：文档指标与输出 JSON 脱节。  
- 应对：每轮收口前强制重建 evidence pack 并核对缺失项。

2. 风险：大规模 stress 运行成本高。  
- 应对：批次化运行 + 固定随机种子 + 记录批次元数据。

3. 风险：ANN 叙事拖累专利主线。  
- 应对：持续明确 ANN 为可选实施例，不纳入核心授权论据。

## R-028 Plan Update (2026-02-12)
Completed in this round:
- Candidate regression fail-fast guardrail implemented (`scripts/run_stage2_guardrail.py`).
- Guardrail output/report generated (`outputs/stage2_guardrail.json`, `docs/eval/stage2_guardrail_report.md`).
- `build_patent_evidence_pack.py` integrated with guardrail command + DF-06 metrics.
- Fine-grained tests added for `embed/eval/store` and guardrail logic.

Next priorities:
1. Add scale-level performance regression alarms (threshold-based) for Candidate/ANN.
2. Freeze ANN as optional implementation unless stable positive speedup appears on active workloads.
3. Keep weekly rerun protocol: candidate profile trio + guardrail + evidence pack rebuild.
## R-029 Plan Update (2026-02-13)
Completed:
- Added speed-regression warning checks to stage-2 guardrail.
- Added `candidate_benchmark=None` guardrail unit-test path.
- Updated DF-06 narrative to "default candidate zero-loss + experimental acceleration risk".
- ANN formally frozen as optional implementation for patent claim scope.

Next:
1. Keep weekly guardrail + evidence-pack rebuild.
2. Only unfreeze ANN if active scenario speedup is stably positive across repeated runs.
3. Add optional CI hook to fail release on any blocker in `run_stage2_guardrail.py`.

## R-030 Plan Update (2026-02-13)
Completed:
- Stage-2 guardrail integrated into GitHub Actions (`.github/workflows/stage2-quality-gate.yml`).
- Lightweight CI bundle script added (`scripts/run_ci_guardrail_bundle.py`).
- CI reports redirected to `outputs/ci_reports/` to avoid tracked report churn.

Next:
1. Optional: add a dedicated release job that requires `stage2-quality-gate` success before tag publish.
2. Optional: add trend storage for warning metrics (candidate/ann active speed) to monitor regressions over time.
3. Keep ANN frozen as optional path until active speedup turns positive and stable.

## R-030b Plan Update (2026-02-13)
Completed:
- CI bundle made self-contained (internal semi-real dataset generator).
- Added unit tests for CI bundle data generation path.
- Test baseline updated to `71/71`.

Next:
1. Keep stage2-quality-gate as mandatory PR gate.
2. Optionally add nightly job with larger `runs` for more stable speed-warning trend.

## R-031 Plan Update (2026-02-13)
Completed:
- Nightly trend workflow added (`stage2-nightly-trend.yml`).
- Guardrail trend updater script added (`update_guardrail_trend.py`).
- Trend unit tests added (`test_guardrail_trend_unit.py`).
- Test baseline now `74/74`.

Next:
1. Decide whether to persist trend history externally (artifact download + dashboard) for longer retention.
2. Keep ANN frozen until `ann_active_positive_speed_target_warn` turns consistently green.
3. If needed, tighten warning floor after 2+ weeks of stable nightly data.

## R-032 Plan Update (2026-02-13)
Completed:
- Added release gate workflow: `.github/workflows/release-with-stage2-gate.yml`.
- Added gate checker unit tests: `tests/test_check_stage2_gate_for_sha_unit.py`.
- Release workflow now enforces: target SHA must have a successful `stage2-quality-gate` run within 168 hours before tag/release creation.

Next:
1. Keep `stage2-quality-gate` as required status check for `main` branch protection.
2. Monitor release-gate failures for one week; adjust `max-age-hours` only if process latency requires it.
3. If needed, add optional changelog artifact upload to the release workflow.

## R-033 Plan Update (2026-02-13)
Completed:
- Closed P1 CI output-path isolation:
  - `run_ci_guardrail_bundle.py` writes CI JSON outputs to `outputs/ci_outputs/`.
  - Guardrail invocation in CI bundle reads candidate/ANN inputs from `outputs/ci_outputs/`.
- Synced workflows:
  - `stage2-quality-gate.yml` uploads `outputs/ci_outputs/*.json`.
  - `stage2-nightly-trend.yml` reads trend input from `outputs/ci_outputs/stage2_guardrail.json`.
- Added regression test coverage for command path isolation in `test_ci_guardrail_bundle_unit.py`.

Next:
1. Run one full GitHub Actions cycle to verify artifact layout and trend ingestion on hosted runner.
2. Keep full-scale authoritative outputs in `outputs/` root and CI outputs in `outputs/ci_outputs/` only.
3. If stable for one week, enforce a checklist item that rejects CI scripts writing benchmark JSON to `outputs/` root.

## R-034 Plan Update (2026-02-13)
Completed:
- Added explicit CI output-path policy checker: `scripts/check_ci_output_isolation.py`.
- Added regression unit tests: `tests/test_ci_output_isolation_unit.py`.
- Integrated checker into both workflows:
  - `stage2-quality-gate.yml`
  - `stage2-nightly-trend.yml`
- Added checker artifact output:
  - `outputs/ci_outputs/output_isolation_check.json`

Next:
1. Observe 3-5 CI runs; if no false positives, escalate this checker to mandatory branch protection evidence.
2. Add a checklist item in `docs/REVIEW_CHECKLIST.md` binding CI-output policy to P1 gate.
3. Keep running full-scale guardrail/evidence rebuild from authoritative `outputs/` root only.

## R-035 Plan Update (2026-02-13)
Completed:
- Upgraded `docs/REVIEW_CHECKLIST.md` to v2.1.
- Promoted CI output isolation checks to explicit P1 release gate terms.
- Bound checklist to automation:
  - `check_ci_output_isolation.py` must report `passed=true` and `violation_count=0`;
  - both CI workflows must include `Validate CI Output Isolation`.

Next:
1. Keep collecting CI run evidence to verify zero false positives for the isolation checker.
2. If stable, require the checker artifact in review attachments by default.
3. Continue core algorithm track (CEG/ARB/DMG) while keeping CI/patent evidence pipeline stable.

## R-036 Plan Update (2026-02-13)
Completed:
- Closed R-027 review leftovers:
  - Fixed `FINAL_REPORT.md` R-delta ordering to chronological `R-031 -> R-032 -> R-033 -> R-034 -> R-035`.
  - Corrected R-031 historical test count from `84/84` to `74/74`.
  - Completed R-032 `WORK_PROGRESS.md` verification line with explicit full-test count (`79/79`).

Next:
1. Keep R-delta sections append-only and chronological to avoid review ambiguity.
2. Keep each `WORK_PROGRESS` verification block with explicit full-test count.
3. Continue algorithm-track improvements with current CI/patent evidence guardrails unchanged.

## R-037 Plan Update (2026-02-13)
Completed:
- Added `docs/review/review_closure_matrix.md` as a structured review-closure board.
- Mapped R-027 key findings to closure statuses and evidence references.
- Added accepted-limitation entries to separate warnings from real defects.

Next:
1. Keep this matrix updated per review round (`open -> closed/waived` lifecycle).
2. Use the matrix as mandatory attachment in review submissions.
3. Continue algorithm and experiment-track work with current guardrails unchanged.

## R-038 Plan Update (2026-02-13)
Completed:
- Hardened closure-matrix append script:
  - strict round-id validation (`R-XXX` / `R-XXXX` + suffix),
  - robust anchor matching for suffixed headers.
- Added dedicated unit tests for closure-matrix automation:
  - `tests/test_review_closure_matrix_unit.py` (5 tests).
- Synced documentation command entry:
  - `README.md`,
  - `docs/review/review_closure_matrix.md` (`v1.1`).

Next:
1. Add CI smoke check for `append_review_closure_round.py` (dry-run/fixture mode) to prevent tooling regression.
2. Keep review matrix as required artifact in each review handoff package.
3. Continue algorithm-track optimization with current Stage-2 guardrail rules unchanged.

## R-039 Plan Update (2026-02-13)
Completed:
- Added repeated-run core-claim stability benchmark:
  - `scripts/run_core_claim_stability.py`
  - outputs confidence-style statistics for CEG/ARB/DMG gains.
- Added dedicated unit tests:
  - `tests/test_core_claim_stability_unit.py` (4 tests).
- Ran semi-real stability experiments:
  - realistic-2000 (`runs=12`): CEG/ARB gates pass; DMG not activated in this profile.
  - stress-2000 (`runs=4`): CEG/ARB/DMG gates all pass.
- Upgraded review governance:
  - `docs/REVIEW_CHECKLIST.md` v2.2 adds mandatory `review_closure_matrix.md` attachment.
  - `docs/review/review_closure_matrix.md` v1.2 adds `closed_by_reviewer`.

Next:
1. Run stability benchmark at 5000-scale with batched execution (`runs>=3`) for stress profile to reduce runtime timeout risk.
2. Add profile-activation coverage metric (DMG activation ratio) to avoid misreading "DMG=0" as regression under realistic profile.
3. Integrate stability outputs into evidence-pack command catalog after one more reproducible run.

## R-040 Plan Update (2026-02-13)
Completed:
- Added batched/resumable execution to `run_core_claim_stability.py`:
  - checkpoint chain: `--checkpoint`, `--resume`, `--max-new-runs`.
- Added DMG activation diagnostics:
  - `dmg_guard_activation_rate`,
  - `dmg_mixed_mode_reduction_rate`,
  - `baseline_mixed_mode_presence_rate`,
  - `dmg_effective_profile`.
- Completed 5000-scale stability runs:
  - realistic-5000 (`runs=6`, complete),
  - stress-5000 (`runs=3`, completed by two-step checkpoint resume).
- Integrated new reproducibility commands into `build_patent_evidence_pack.py` command catalog.

Next:
1. Add stage2 guardrail optional checker for core stability completeness (`is_complete=true` on selected benchmark profiles).
2. Add CI-friendly smoke test for checkpoint signature mismatch path (`--resume` with wrong dataset/thresholds should fail).
3. Prepare R-040 evidence summary for external review package (include 5000-stress runtime cost and batching rationale).

## R-041 Plan Update (2026-02-14)
Completed:
- Added optional core-stability completeness checks to `run_stage2_guardrail.py`:
  - new CLI arg (repeatable): `--core-stability <path>`
  - blocker checks enforce `is_complete=true` for selected stability profiles.
- Added CI-friendly checkpoint mismatch smoke test:
  - `tests/test_core_claim_stability_resume_smoke.py`
  - validates `run_core_claim_stability.py --resume` fails on signature mismatch.
- Expanded stage-2 guardrail unit coverage:
  - `tests/test_stage2_guardrail.py` now includes pass/fail cases for optional core-stability checks.
- Synced reproducibility commands:
  - `README.md` and evidence command catalog now include `run_stage2_guardrail.py` with two 5000-scale core-stability inputs.

Next:
1. Add one CLI integration test for `run_stage2_guardrail.py` that verifies `--core-stability` path parsing and output fields end-to-end.
2. Add optional weekly stability rerun checklist item in stage2/nightly process docs (avoid stale `is_complete` evidence).
3. Keep ANN frozen as optional implementation unless active profile positive speedup becomes stable across repeated runs.

## R-042 Plan Update (2026-02-14)
Completed:
- Added CLI integration smoke tests for `run_stage2_guardrail.py`:
  - new file `tests/test_stage2_guardrail_cli_smoke.py`
  - covers both pass path (all core-stability profiles complete) and blocker path (incomplete profile causes exit code `2`).
- Strengthened process checklist for stale-evidence prevention:
  - `docs/REVIEW_CHECKLIST.md` upgraded to `v2.3`.
  - added Stage-2 item requiring `--core-stability` inputs and `core_stability.incomplete_count=0` whenever core stability evidence is referenced.

Next:
1. Add a CI smoke invocation for `run_stage2_guardrail.py --core-stability ...` on lightweight fixture outputs.
2. Keep weekly/nightly rerun discipline for stability artifacts to avoid stale `is_complete` snapshots.
3. Continue ANN optional-path freeze policy until active speedup is stably positive.

## R-043 Plan Update (2026-02-14)
Completed:
- Implemented CI smoke invocation for `run_stage2_guardrail.py --core-stability ...` in real bundle execution path:
  - `run_ci_guardrail_bundle.py` now creates CI fixture core-stability JSONs and passes them into guardrail command.
- Extended CI path-isolation checks:
  - `check_ci_output_isolation.py` now validates `--core-stability` paths.
- Synced workflow artifacts:
  - stage2 quality/nightly workflows now upload CI core-stability fixture JSON files.
- Added/updated unit tests:
  - `tests/test_ci_guardrail_bundle_unit.py`
  - `tests/test_ci_output_isolation_unit.py`

Next:
1. Optionally promote a strict mode in CI bundle to fail when ANN active positive-speed warning persists for a configurable streak.
2. Keep core-stability fixture contract minimal and stable (`dataset/runs/runs_completed/is_complete`) to avoid CI flakiness.
3. Continue algorithm-track improvements while keeping stage2 gate deterministic on hosted runners.

## R-044 Plan Update (2026-02-14)
Completed:
- Implemented optional strict streak policy in CI bundle:
  - `run_ci_guardrail_bundle.py` now calculates ANN active non-positive speed streak from trend history.
  - strict mode can be enabled via `--strict-ann-positive-speed-streak N`.
  - default remains non-blocking (`N=0`) to avoid changing current gate semantics.
- Added CI bundle summary artifact:
  - `outputs/ci_outputs/ci_guardrail_bundle_summary.json`
  - includes stage2 status, strict policy snapshot, and strict-failure reason.
- Hardened output isolation governance:
  - `check_ci_output_isolation.py` now enforces summary JSON cannot be written to `outputs/` root.
  - required workflow paths now include the new summary artifact.
- Extended tests:
  - strict-policy unit tests in `tests/test_ci_guardrail_bundle_unit.py`
  - workflow-required-path regression tests in `tests/test_ci_output_isolation_unit.py`

Next:
1. Keep strict streak threshold disabled in default CI, and only enable it intentionally in dedicated branches/environments after trend stabilization.
2. If enabled later, set threshold based on historical trend variance to avoid false blockers from one-off runner noise.
3. Continue core algorithm/experiment track while maintaining CI guardrail determinism and isolation guarantees.

## R-045 Plan Update (2026-02-14)
Completed:
- Entered patent material drafting handover phase.
- Added agent handover package documents in `docs/patent_kit/` (12-15):
  - one-page technical brief,
  - claim strategy note,
  - evidence index + submission flow,
  - email template.
- Updated `00_技术交底书_总览.md` index for direct package delivery.

Next:
1. Send `docs/patent_kit/00-15` package to patent agent.
2. Wait for first formal CNIPA-format draft from agent.
3. Perform technical-fact-only proofreading on agent draft (no new R&D/testing expansion).

## R-046 Plan Update (2026-02-14)
Completed:
- Produced CNIPA-style formal draft set in `docs/patent_kit/16-19`:
  - formal specification draft,
  - formal claims draft,
  - formal abstract draft,
  - figure drawing textual script.
- Expanded index file `00_技术交底书_总览.md` to include 16-19 for one-click handover.

Next:
1. Send `docs/patent_kit/00-19` full package to patent agent.
2. Ask agent to return first CNIPA submission draft based on 16-19 as primary text and 00-15 as supporting evidence.
3. Perform technical consistency check only (title, terms, step chain, claim support), then finalize for CPC filing.

## R-047 Plan Update (2026-02-14)
Completed:
- Completed full figure drawing delivery as SVG (`图1-图6 + 摘要附图`).
- Added visual figure index document (`20_CNIPA_附图清单_预览.md`) for quick review/export.
- Applied review-driven formal claim wording fixes:
  - replaced disputed "可选地" claim wording with limiting expression,
  - added independent device claim.

Next:
1. Export SVG to agent-preferred formats (if needed: PNG/PDF) while keeping SVG as master.
2. Have patent agent perform final legal polishing on 16-20 package.
3. Run final terminology consistency pass on agent-returned draft before CPC submission.
