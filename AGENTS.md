# AGENTS.md

## Repository Goal
Build and validate a single-machine prototype for:
- Multi-agent semantic memory fragment clustering
- Cluster-level compression with conflict marking
- Preference-driven retention and degradation policy
- Reversible provenance (backrefs) for auditability

Deliverables must include runnable code, tests, demo data, prior-art comparison, and Chinese patent drafting materials.

## Default Commands
- Run tests: `python -m unittest discover -s tests -p "test_*.py"`
- Compile check: `python -m compileall -q src scripts tests`
- Run Stage-2 guardrail: `python scripts/run_stage2_guardrail.py --output outputs/stage2_guardrail.json --report docs/eval/stage2_guardrail_report.md`
- Rebuild evidence pack: `python scripts/build_patent_evidence_pack.py --output outputs/patent_evidence_pack.json --report "docs/patent_kit/10_区别特征_技术效果_实验映射.md"`
- Run CI guardrail (local): `python scripts/run_ci_guardrail_bundle.py --dataset-size 240 --benchmark-fragment-count 120 --runs 1 --warmup-runs 0`

## Coding Rules
- Python 3.10+, zero external dependencies (stdlib only).
- Use type annotations for public functions and dataclasses.
- Keep modules small and testable; avoid monolithic scripts.
- Inline `from __future__ import annotations` in every module.

## Change Strategy
- Implement in small, verifiable steps.
- After each major step, append a timestamped entry to `WORK_PROGRESS.md`.
- Do not rewrite git history.
- Do not revert user-authored files unless explicitly requested.

## Documentation Rules
- Put design/algorithm docs in `docs/design/`.
- Put prior-art and design-around artifacts in `docs/prior_art/`.
- Put patent drafting materials in `docs/patent_kit/`.
- Keep `docs/FINAL_REPORT.md` updated with execution status and validation outputs.
- Evaluation reports go to `docs/eval/`.
- Review documents go to `docs/review/`.

## Quality Gate
Before completion, ensure:
- Code runs end-to-end on example data.
- All tests pass (`python -m unittest discover -s tests -p "test_*.py"`).
- Stage-2 guardrail passes (`passed=true`, `blocker_failures=0`).
- Evidence pack validates (`validation.passed=true`, `missing_*=[]`).
- Test count in `FINAL_REPORT.md` matches actual test count.

## Output Path Rules (CRITICAL)

### Full-scale benchmark outputs (tracked, authoritative)
```
outputs/ablation_metrics*.json
outputs/core_scaling_*.json
outputs/core_ablation_*.json
outputs/candidate_filter_benchmark.json
outputs/candidate_profile_validation_*.json
outputs/ann_hybrid_benchmark.json
outputs/stage2_guardrail.json
outputs/patent_evidence_pack.json
```

### CI lightweight outputs (ephemeral, NOT authoritative)
```
outputs/ci_outputs/*.json         # CI-scale benchmark JSONs
outputs/ci_reports/*.md           # CI-scale reports
outputs/ci_semi_real_*.jsonl      # CI-generated datasets
```

### Rule
- `run_ci_guardrail_bundle.py` must write benchmark JSONs to `outputs/ci_outputs/`, NOT to `outputs/` root.
- `run_stage2_guardrail.py` in CI mode must read from `outputs/ci_outputs/`.
- Only full-scale manual runs may write to `outputs/` root paths.
- The `build_patent_evidence_pack.py` always reads from `outputs/` root (full-scale).

## Locked Decisions (Do Not Change Without User Approval)
- Candidate default: `signature_radius=4` (zero-loss)
- Candidate experimental: `signature_radius=3` (lossy, not default)
- ANN: frozen as optional implementation, not core patent claim
- Core claims: CEG / ARB / DMG / Semantic Precision (Claims 1, 4-11)
- Optional claims: Prune / Candidate / ANN (Claims 12-14)
- Diagnostic granularity: cluster-entry level (matches runtime fallback)

## Known Limitations (Acceptable)
- ANN active speedup is negative (~-10%); this is documented and accepted
- Candidate fast profile (r=3) is lossy at synthetic N=240; this is documented as known limitation
- ANN `ann_active_positive_speed_target_warn` is expected to fail (warning, not blocker)
