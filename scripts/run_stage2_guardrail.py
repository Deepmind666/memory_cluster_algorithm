from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing input file: {path.as_posix()}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _find_row(payload: dict[str, Any], *, fragment_count: int) -> dict[str, Any] | None:
    for row in payload.get("rows") or []:
        if int(row.get("fragment_count") or -1) == int(fragment_count):
            return row
    return None


def _check(*, name: str, passed: bool, severity: str, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "severity": str(severity),
        "detail": str(detail),
    }


def _active_ann_comparison(payload: dict[str, Any], variant: str) -> dict[str, Any]:
    for scenario in payload.get("scenarios") or []:
        if str(scenario.get("name")) != "merge_active_case":
            continue
        return ((scenario.get("comparisons_vs_baseline") or {}).get(variant) or {})
    return {}


def _active_candidate_summary(payload: dict[str, Any]) -> dict[str, Any]:
    for scenario in payload.get("scenarios") or []:
        if str(scenario.get("name")) != "merge_active_case":
            continue
        return dict(scenario.get("summary") or {})
    return {}


def evaluate_guardrails(
    *,
    candidate_synthetic: dict[str, Any],
    candidate_realistic: dict[str, Any],
    candidate_stress: dict[str, Any],
    ann_hybrid: dict[str, Any],
    candidate_benchmark: dict[str, Any] | None = None,
    allow_known_fast_loss: bool = True,
    candidate_active_speed_warn_floor: float = -0.20,
    ann_active_speed_warn_floor: float = -0.20,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    synth_summary = candidate_synthetic.get("summary") or {}
    realistic_summary = candidate_realistic.get("summary") or {}
    stress_summary = candidate_stress.get("summary") or {}

    checks.append(
        _check(
            name="candidate_default_quality_synthetic",
            passed=bool(synth_summary.get("default_all_quality_gate_pass")),
            severity="blocker",
            detail="Synthetic active profile default(r=4) must keep zero-loss quality gate across all sizes.",
        )
    )
    checks.append(
        _check(
            name="candidate_default_quality_realistic",
            passed=bool(realistic_summary.get("default_all_quality_gate_pass")),
            severity="blocker",
            detail="Semi-real realistic profile default(r=4) must keep zero-loss quality gate across all sizes.",
        )
    )
    checks.append(
        _check(
            name="candidate_default_quality_stress",
            passed=bool(stress_summary.get("default_all_quality_gate_pass")),
            severity="blocker",
            detail="Semi-real stress profile default(r=4) must keep zero-loss quality gate across all sizes.",
        )
    )

    row_n240 = _find_row(candidate_synthetic, fragment_count=240)
    default_n240_ok = bool(((row_n240 or {}).get("default_profile") or {}).get("quality_gate_pass"))
    checks.append(
        _check(
            name="candidate_default_n240_synthetic",
            passed=default_n240_ok,
            severity="blocker",
            detail="Synthetic active N=240 must preserve merges/cluster count for default(r=4).",
        )
    )

    fast_n240_ok = bool(((row_n240 or {}).get("fast_profile") or {}).get("quality_gate_pass"))
    fast_loss_known = row_n240 is not None and not fast_n240_ok
    checks.append(
        _check(
            name="candidate_fast_n240_known_loss",
            passed=(not fast_loss_known) if not allow_known_fast_loss else True,
            severity="warning" if allow_known_fast_loss else "blocker",
            detail=(
                "Known limitation accepted: fast(r=3) can be lossy at synthetic active N=240."
                if allow_known_fast_loss
                else "fast(r=3) quality loss at synthetic active N=240 is not allowed in strict mode."
            ),
        )
    )

    ann_runtime_gate = bool(ann_hybrid.get("signature_gate_pass_cluster_runtime"))
    checks.append(
        _check(
            name="ann_runtime_signature_gate",
            passed=ann_runtime_gate,
            severity="blocker",
            detail="ANN runtime signature gate must pass to avoid degenerate candidate routing.",
        )
    )

    ann_active_ann_prune = _active_ann_comparison(ann_hybrid, "ann_prune")
    ann_active_hybrid = _active_ann_comparison(ann_hybrid, "hybrid_prune")
    checks.append(
        _check(
            name="ann_active_quality_ann_prune",
            passed=bool(ann_active_ann_prune.get("quality_gate_pass")),
            severity="blocker",
            detail="ANN active ann_prune must keep quality gate pass (cluster/merge/conflict equality).",
        )
    )
    checks.append(
        _check(
            name="ann_active_quality_hybrid_prune",
            passed=bool(ann_active_hybrid.get("quality_gate_pass")),
            severity="blocker",
            detail="ANN active hybrid_prune must keep quality gate pass (cluster/merge/conflict equality).",
        )
    )

    ann_active_speed = float(ann_active_ann_prune.get("avg_speedup_ratio") or 0.0)
    checks.append(
        _check(
            name="ann_active_speed_regression_warn",
            passed=ann_active_speed >= float(ann_active_speed_warn_floor),
            severity="warning",
            detail=(
                "ANN active speed must not degrade beyond floor "
                f"{ann_active_speed_warn_floor:.3f}; current={ann_active_speed:.6f}."
            ),
        )
    )
    checks.append(
        _check(
            name="ann_active_positive_speed_target_warn",
            passed=ann_active_speed > 0.0,
            severity="warning",
            detail="ANN active speed target is positive speedup (> 0.0).",
        )
    )

    if candidate_benchmark is not None:
        checks.append(
            _check(
                name="candidate_benchmark_active_quality",
                passed=bool(candidate_benchmark.get("active_quality_gate_pass")),
                severity="blocker",
                detail="Candidate benchmark active case quality gate must pass.",
            )
        )
        candidate_active_summary = _active_candidate_summary(candidate_benchmark)
        candidate_active_speed = float(candidate_active_summary.get("avg_speedup_ratio") or 0.0)
        checks.append(
            _check(
                name="candidate_active_speed_regression_warn",
                passed=candidate_active_speed >= float(candidate_active_speed_warn_floor),
                severity="warning",
                detail=(
                    "Candidate active speed must not degrade beyond floor "
                    f"{candidate_active_speed_warn_floor:.3f}; current={candidate_active_speed:.6f}."
                ),
            )
        )
    else:
        candidate_active_speed = None

    blocker_failures = [item for item in checks if item.get("severity") == "blocker" and not item.get("passed")]
    warning_failures = [item for item in checks if item.get("severity") == "warning" and not item.get("passed")]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "passed": len(blocker_failures) == 0,
            "check_count": len(checks),
            "blocker_failures": len(blocker_failures),
            "warning_failures": len(warning_failures),
        },
        "known_limitations": {
            "fast_profile_loss_at_synthetic_n240": bool(fast_loss_known),
            "ann_active_not_positive_speedup": not (ann_active_speed > 0.0),
            "candidate_active_speed": candidate_active_speed,
            "ann_active_speed": ann_active_speed,
        },
        "checks": checks,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    known = payload.get("known_limitations") or {}
    lines = [
        "# Stage-2 Guardrail Check",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- passed: {summary.get('passed')}",
        f"- blocker_failures: {summary.get('blocker_failures')}",
        f"- warning_failures: {summary.get('warning_failures')}",
        f"- fast_profile_loss_at_synthetic_n240: {known.get('fast_profile_loss_at_synthetic_n240')}",
        "",
        "## Checks",
    ]
    for item in payload.get("checks") or []:
        lines.append(
            f"- [{('x' if item.get('passed') else ' ')}] {item.get('name')} "
            f"(severity={item.get('severity')}): {item.get('detail')}"
        )
    lines.extend(["", "## Raw JSON", f"- {json.dumps(payload, ensure_ascii=False)}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run stage-2 quality guardrails on benchmark outputs")
    parser.add_argument(
        "--candidate-synthetic",
        default="outputs/candidate_profile_validation_synthetic_active.json",
    )
    parser.add_argument(
        "--candidate-realistic",
        default="outputs/candidate_profile_validation_realistic.json",
    )
    parser.add_argument(
        "--candidate-stress",
        default="outputs/candidate_profile_validation_stress.json",
    )
    parser.add_argument("--ann-hybrid", default="outputs/ann_hybrid_benchmark.json")
    parser.add_argument("--candidate-benchmark", default="outputs/candidate_filter_benchmark.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument(
        "--strict-fast-profile",
        action="store_true",
        help="Treat known fast(r=3) quality loss at synthetic N=240 as blocker.",
    )
    parser.add_argument(
        "--allow-missing-candidate-benchmark",
        action="store_true",
        help="Do not fail when candidate_filter_benchmark.json is missing.",
    )
    parser.add_argument(
        "--candidate-active-speed-warn-floor",
        type=float,
        default=-0.20,
        help="Warning threshold floor for candidate active speedup ratio.",
    )
    parser.add_argument(
        "--ann-active-speed-warn-floor",
        type=float,
        default=-0.20,
        help="Warning threshold floor for ANN active speedup ratio.",
    )
    args = parser.parse_args()

    candidate_synthetic = _load_json(Path(args.candidate_synthetic))
    candidate_realistic = _load_json(Path(args.candidate_realistic))
    candidate_stress = _load_json(Path(args.candidate_stress))
    ann_hybrid = _load_json(Path(args.ann_hybrid))

    candidate_benchmark: dict[str, Any] | None
    candidate_benchmark_path = Path(args.candidate_benchmark)
    if candidate_benchmark_path.exists():
        candidate_benchmark = _load_json(candidate_benchmark_path)
    elif args.allow_missing_candidate_benchmark:
        candidate_benchmark = None
    else:
        raise FileNotFoundError(f"missing input file: {candidate_benchmark_path.as_posix()}")

    payload = evaluate_guardrails(
        candidate_synthetic=candidate_synthetic,
        candidate_realistic=candidate_realistic,
        candidate_stress=candidate_stress,
        ann_hybrid=ann_hybrid,
        candidate_benchmark=candidate_benchmark,
        allow_known_fast_loss=not bool(args.strict_fast_profile),
        candidate_active_speed_warn_floor=float(args.candidate_active_speed_warn_floor),
        ann_active_speed_warn_floor=float(args.ann_active_speed_warn_floor),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        _write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool((payload.get("summary") or {}).get("passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
