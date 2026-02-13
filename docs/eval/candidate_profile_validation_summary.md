# Candidate Profile Validation Summary (R-026)

最后更新：2026-02-12

## 1. 目标
验证 Candidate 两套配置在 `N=240/1000/5000` 的可行性与风险：
- 默认发布档（质量优先）：`radius=4, steps=32, max_neighbors=48`
- 高性能实验档：`radius=3, steps=32, max_neighbors=48`

评估门：
- 质量门：`cluster_count_equal && merges_applied_equal`
- 速度门：`avg_speedup_ratio`

## 2. 复现实验命令
```bash
python scripts/run_candidate_profile_validation.py --dataset-label synthetic_active --output outputs/candidate_profile_validation_synthetic_active.json --report docs/eval/candidate_profile_validation_synthetic_active_report.md --sizes 240,1000,5000 --runs 2 --warmup-runs 1 --similarity-threshold 0.82 --merge-threshold 0.85

python scripts/run_candidate_profile_validation.py --dataset-input data/examples/semi_real_memory_fragments_5000_realistic.jsonl --dataset-label semi_real_realistic --output outputs/candidate_profile_validation_realistic.json --report docs/eval/candidate_profile_validation_realistic_report.md --sizes 240,1000,5000 --runs 2 --warmup-runs 1 --similarity-threshold 0.68 --merge-threshold 0.82

python scripts/run_candidate_profile_validation.py --dataset-input data/examples/semi_real_memory_fragments_5000_stress.jsonl --dataset-label semi_real_stress --output outputs/candidate_profile_validation_stress.json --report docs/eval/candidate_profile_validation_stress_report.md --sizes 240,1000,5000 --runs 1 --warmup-runs 0 --similarity-threshold 1.1 --merge-threshold 0.05
```

## 3. 结果概览
| 数据集 | runs | 默认档质量门 | 实验档质量门 | 实验档最差速度 | 结论 |
|---|---:|---:|---:|---:|---|
| synthetic_active | 2 | 3/3 通过 | 2/3 通过 | -24.3746% | 保持默认档 |
| semi_real_realistic | 2 | 3/3 通过 | 3/3 通过 | -16.9310% | 保持默认档 |
| semi_real_stress | 1 | 3/3 通过 | 3/3 通过 | -6.1214% | 保持默认档 |

## 4. 关键发现
1. `synthetic_active` 的 `N=240` 是关键反例：
- 默认档：`merges_applied_equal=true`
- 实验档：`merges_applied_equal=false`（`77 -> 76`），`cluster_count_equal=false`
- 说明 `radius=3` 不能作为发布默认档。

2. `semi_real_realistic` 中两档都通过质量门，但实验档在 `N=5000` 明显负加速（`-16.9310%`）。

3. `semi_real_stress` 中两档均触发 fallback（`merge_candidate_filter_fallbacks=1`，`skipped_by_candidate_filter=0`），说明该场景下 Candidate 筛选未实际生效，速度差主要来自额外开销。

## 5. 决策
- 发布默认配置继续固定为 `radius=4`（质量优先、零损失优先）。
- `radius=3` 仅保留为实验配置，不进入默认参数与核心专利叙事。

## 6. 输出文件
- `outputs/candidate_profile_validation_synthetic_active.json`
- `docs/eval/candidate_profile_validation_synthetic_active_report.md`
- `outputs/candidate_profile_validation_realistic.json`
- `docs/eval/candidate_profile_validation_realistic_report.md`
- `outputs/candidate_profile_validation_stress.json`
- `docs/eval/candidate_profile_validation_stress_report.md`
