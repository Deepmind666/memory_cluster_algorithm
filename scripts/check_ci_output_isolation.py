from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Iterable, Sequence

try:
    from scripts.run_ci_guardrail_bundle import _build_bundle_commands
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from run_ci_guardrail_bundle import _build_bundle_commands


_OUTPUT_FLAGS = {
    "--output",
    "--candidate-synthetic",
    "--candidate-realistic",
    "--candidate-stress",
    "--ann-hybrid",
    "--candidate-benchmark",
}

_FORBIDDEN_ROOT_JSON_PATHS = {
    "outputs/candidate_filter_benchmark.json",
    "outputs/candidate_profile_validation_synthetic_active.json",
    "outputs/candidate_profile_validation_realistic.json",
    "outputs/candidate_profile_validation_stress.json",
    "outputs/ann_hybrid_benchmark.json",
    "outputs/stage2_guardrail.json",
}

_REQUIRED_WORKFLOW_PATHS: dict[str, set[str]] = {
    ".github/workflows/stage2-quality-gate.yml": {
        "outputs/ci_outputs/stage2_guardrail.json",
        "outputs/ci_outputs/candidate_filter_benchmark.json",
        "outputs/ci_outputs/candidate_profile_validation_synthetic_active.json",
        "outputs/ci_outputs/candidate_profile_validation_realistic.json",
        "outputs/ci_outputs/candidate_profile_validation_stress.json",
        "outputs/ci_outputs/ann_hybrid_benchmark.json",
    },
    ".github/workflows/stage2-nightly-trend.yml": {
        "outputs/ci_outputs/stage2_guardrail.json",
    },
}


def _extract_output_paths(commands: Sequence[Sequence[str]]) -> list[str]:
    found: list[str] = []
    for command in commands:
        for idx, token in enumerate(command):
            if token not in _OUTPUT_FLAGS:
                continue
            next_idx = idx + 1
            if next_idx >= len(command):
                continue
            found.append(str(command[next_idx]).replace("\\", "/"))
    return found


def validate_bundle_commands(commands: Sequence[Sequence[str]]) -> list[str]:
    violations: list[str] = []
    paths = _extract_output_paths(commands)
    if not paths:
        violations.append("bundle_commands:no_output_paths_found")
        return violations

    for path in paths:
        if path in _FORBIDDEN_ROOT_JSON_PATHS:
            violations.append(f"bundle_commands:forbidden_root_json:{path}")
        if path.startswith("outputs/") and path.endswith(".json") and not path.startswith("outputs/ci_outputs/"):
            violations.append(f"bundle_commands:json_not_in_ci_outputs:{path}")
    return violations


def validate_workflow_text(*, workflow_name: str, text: str) -> list[str]:
    violations: list[str] = []
    body = str(text)
    json_paths = set(re.findall(r"outputs/[A-Za-z0-9_./-]+\.json", body))
    for path in _FORBIDDEN_ROOT_JSON_PATHS:
        if path in json_paths:
            violations.append(f"{workflow_name}:forbidden_root_json:{path}")
    for path in sorted(_REQUIRED_WORKFLOW_PATHS.get(workflow_name, set())):
        if path not in body:
            violations.append(f"{workflow_name}:missing_required_path:{path}")
    return violations


def validate_workflows(paths: Iterable[Path]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        if not path.exists():
            violations.append(f"workflow:missing_file:{path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        violations.extend(validate_workflow_text(workflow_name=path.as_posix(), text=text))
    return violations


def _default_bundle_commands() -> list[list[str]]:
    return _build_bundle_commands(
        py="python",
        frag_count=120,
        size=240,
        runs=1,
        warmups=0,
        realistic_dataset=Path("outputs/ci_semi_real_240_realistic.jsonl"),
        stress_dataset=Path("outputs/ci_semi_real_240_stress.jsonl"),
        ci_outputs=Path("outputs/ci_outputs"),
        ci_reports=Path("outputs/ci_reports"),
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CI output-path isolation policy")
    parser.add_argument(
        "--workflows",
        nargs="*",
        default=[
            ".github/workflows/stage2-quality-gate.yml",
            ".github/workflows/stage2-nightly-trend.yml",
        ],
        help="Workflow files to validate",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    command_violations = validate_bundle_commands(_default_bundle_commands())
    workflow_paths = [Path(item) for item in (args.workflows or [])]
    workflow_violations = validate_workflows(workflow_paths)
    violations = [*command_violations, *workflow_violations]

    payload: dict[str, object] = {
        "passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
        "checked_workflows": [item.as_posix() for item in workflow_paths],
    }
    if args.output:
        _write_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
