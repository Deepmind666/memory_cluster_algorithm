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
