# memory_cluster_algorithm

## 项目背景
本项目聚焦多 Agent 协同场景下的共享记忆治理问题：在长期对话与工具调用中，记忆碎片会快速膨胀并出现重复、冲突和溯源困难。仓库提供一个单机可运行的“语义聚类 + 冲突显式 + 偏好保留 + 可逆回溯”原型，并同步产出中国发明专利草案素材。

## 仓库命名说明
仓库名 `memory_cluster_algorithm` 即当前技术方向（记忆碎片聚类压缩），不再是旧版“运行态反馈代码优化”方向。

## 目标
- 实现可运行的多 Agent 记忆碎片聚类压缩原型。
- 输出可复现测试、基准和示例数据。
- 产出 prior-art 对比与专利交底材料草案。
- 全过程可审计（日志、命令、指标）。

## 环境依赖
- Windows PowerShell 5.1+（或 PowerShell 7+）
- Python 3.10+（当前实测 3.14）
- 依赖安装：
```powershell
python -m pip install -r requirements.txt
```

## 核心目录
- `src/memory_cluster/`：算法与 CLI 实现。
- `tests/`：单元测试。
- `data/examples/`：多 Agent 示例碎片与偏好配置。
- `docs/design/`：算法规格。
- `docs/prior_art/`：检索记录、特征矩阵、绕开策略。
- `docs/patent_kit/`：专利交底草案包。
- `docs/FINAL_REPORT.md`：端到端结果总报告。

## 新手入口
- `docs/design/beginner_plain_guide.md`：初学者“人话版”思路说明。

## 快速运行
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state_l2.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85 --enable-l2-clusters --l2-min-children 2
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state_full.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85 --strict-conflict-split --enable-conflict-graph --enable-adaptive-budget --enable-dual-merge-guard --enable-merge-upper-bound-prune --merge-prune-dims 48 --enable-merge-candidate-filter --merge-candidate-bucket-dims 10 --merge-candidate-max-neighbors 48 --enable-merge-ann-candidates --merge-ann-num-tables 6 --merge-ann-bits-per-table 10 --merge-ann-probe-radius 1 --merge-ann-max-neighbors 48 --merge-ann-score-dims 48 --enable-l2-clusters --l2-min-children 2
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "alpha 冲突参数" --top-k 3 --offset 0 --expand
python -m src.memory_cluster.cli query --state outputs/cluster_state_l2.json --query "method topic" --top-k 3 --cluster-level l2 --expand
python scripts/run_ablation.py --output outputs/ablation_metrics.json --report docs/eval/ablation_report_cn.md
python scripts/run_ablation.py --output outputs/ablation_metrics_large.json --report docs/eval/ablation_report_large_cn.md --fragment-count 100 --similarity-threshold 0.68 --merge-threshold 0.82 --dataset-label synthetic_conflict_memory_case_large
python scripts/run_ablation.py --output outputs/ablation_metrics_stress.json --report docs/eval/ablation_report_stress_cn.md --fragment-count 100 --similarity-threshold 1.1 --merge-threshold 0.05 --dataset-label synthetic_conflict_memory_case_stress
python scripts/run_prune_benchmark.py --output outputs/prune_benchmark.json --report docs/eval/prune_benchmark_report.md
python scripts/run_candidate_filter_benchmark.py --output outputs/candidate_filter_benchmark.json --report docs/eval/candidate_filter_benchmark_report.md
python scripts/run_ann_hybrid_benchmark.py --output outputs/ann_hybrid_benchmark.json --report docs/eval/ann_hybrid_benchmark_report.md
python scripts/run_semantic_regression.py --output outputs/semantic_regression_metrics.json --report docs/eval/semantic_regression_report.md
python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_2000_realistic.jsonl --output outputs/core_claim_stability_semi_real_2000_realistic.json --report docs/eval/core_claim_stability_semi_real_2000_realistic_report.md --runs 12 --warmup-runs 2 --similarity-threshold 0.68 --merge-threshold 0.82
python scripts/run_core_claim_stability.py --input data/examples/semi_real_memory_fragments_2000_stress.jsonl --output outputs/core_claim_stability_semi_real_2000_stress.json --report docs/eval/core_claim_stability_semi_real_2000_stress_report.md --runs 4 --warmup-runs 1 --similarity-threshold 1.1 --merge-threshold 0.05
python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report docs/patent_kit/10_区别特征_技术效果_实验映射.md
python -m unittest discover -s tests -p "test_*.py" -v
```

## 可靠性说明（ingest/build）
- `ingest` 默认启用幂等写入（按 `id + version` 去重），可用 `--no-idempotent` 关闭。
- 输入 JSONL 默认容错（坏行跳过并统计），可用 `--strict-input` 改为遇错即失败。
- `build` 读取存储默认容错（坏行跳过并统计），可用 `--strict-store` 改为遇错即失败。
- 候选筛选默认关闭（exact 模式）；仅在大规模性能场景按需开启 `--enable-merge-candidate-filter`。
- ANN 候选默认关闭；开启参数为 `--enable-merge-ann-candidates` 及 `--merge-ann-*`，当前为实验特性，需配合 benchmark 验证收益。
- 建议每次规则改动后执行 `run_semantic_regression.py`，验证条件边界、否定窗口、跨句指代不回归。

## 进展与质量门禁
- 进展日志：`WORK_PROGRESS.md`
- 质量清单：`docs/REVIEW_CHECKLIST.md`
- 日志追加脚本：`scripts/append_progress.ps1`
- 评审闭环矩阵模板追加脚本：`scripts/append_review_closure_round.py`
- CI 阶段二门禁：`.github/workflows/stage2-quality-gate.yml`
- 本地复用同款门禁（轻量参数）：
```powershell
python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json
python scripts/run_ci_guardrail_bundle.py --dataset-size 240 --benchmark-fragment-count 120 --runs 1 --warmup-runs 0
python scripts/append_review_closure_round.py --round R-0XX --rows 3
```
- 门禁输出：
  - `outputs/ci_outputs/output_isolation_check.json`
  - `outputs/ci_outputs/stage2_guardrail.json`
  - `outputs/ci_reports/stage2_guardrail_report.md`

### Stage-2 趋势追踪（Nightly）
- 定时工作流：`.github/workflows/stage2-nightly-trend.yml`
- 本地可复现：
```powershell
python scripts/check_ci_output_isolation.py --output outputs/ci_outputs/output_isolation_check.json
python scripts/run_ci_guardrail_bundle.py --dataset-size 240 --benchmark-fragment-count 120 --runs 3 --warmup-runs 1
python scripts/update_guardrail_trend.py --input outputs/ci_outputs/stage2_guardrail.json --output outputs/stage2_guardrail_trend.json --label local --retain 90
```
- 趋势文件：
  - `outputs/stage2_guardrail_trend.json`

### Release 门禁（先过 Stage-2 再发版）
- 发布工作流：`.github/workflows/release-with-stage2-gate.yml`（手动触发）
- 行为：先校验目标 SHA 最近 168 小时内有成功的 `stage2-quality-gate` 运行，再允许打 tag 和创建 release。
- 本地可复现校验脚本（需要 GitHub token）：
```powershell
$env:GITHUB_TOKEN="<your_token>"
python scripts/check_stage2_gate_for_sha.py --repo Deepmind666/memory_cluster_algorithm --sha <commit_sha> --workflow-file stage2-quality-gate.yml --max-age-hours 168 --output outputs/release_gate_check.json
```
- 校验输出：
  - `outputs/release_gate_check.json`

## 合规说明
- 本仓库提供技术实现与撰写辅助，不构成法律意见。
- 发明人应为自然人，正式申请文本请由专利代理人/律师复核。
