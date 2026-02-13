from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expect JSON object: {path.as_posix()}")
    return payload


def _failed_check_names(guardrail_payload: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for item in guardrail_payload.get("checks") or []:
        if not isinstance(item, dict):
            continue
        if bool(item.get("passed")):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            failed.append(name)
    return failed


def build_trend_record(guardrail_payload: dict[str, Any], *, label: str) -> dict[str, Any]:
    summary = dict(guardrail_payload.get("summary") or {})
    known = dict(guardrail_payload.get("known_limitations") or {})
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "guardrail_generated_at": str(guardrail_payload.get("generated_at") or ""),
        "label": str(label),
        "passed": bool(summary.get("passed")),
        "blocker_failures": int(summary.get("blocker_failures") or 0),
        "warning_failures": int(summary.get("warning_failures") or 0),
        "ann_active_speed": known.get("ann_active_speed"),
        "candidate_active_speed": known.get("candidate_active_speed"),
        "ann_active_not_positive_speedup": bool(known.get("ann_active_not_positive_speedup")),
        "fast_profile_loss_at_synthetic_n240": bool(known.get("fast_profile_loss_at_synthetic_n240")),
        "failed_checks": _failed_check_names(guardrail_payload),
    }


def _avg_nonnull(rows: list[dict[str, Any]], key: str) -> float | None:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return round(sum(values) / float(len(values)), 6)


def update_trend_payload(
    *,
    current_payload: dict[str, Any] | None,
    guardrail_payload: dict[str, Any],
    label: str,
    retain: int,
) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    if current_payload and isinstance(current_payload.get("history"), list):
        history = [dict(item) for item in current_payload.get("history") if isinstance(item, dict)]
    history.append(build_trend_record(guardrail_payload, label=label))
    history = history[-max(1, int(retain)) :]

    pass_count = sum(1 for item in history if bool(item.get("passed")))
    blocker_fail_count = sum(1 for item in history if int(item.get("blocker_failures") or 0) > 0)
    warn_count = sum(1 for item in history if int(item.get("warning_failures") or 0) > 0)
    ann_not_positive_count = sum(1 for item in history if bool(item.get("ann_active_not_positive_speedup")))

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "history_count": len(history),
        "history": history,
        "summary": {
            "pass_rate": round(pass_count / float(len(history)), 6) if history else 0.0,
            "blocker_failure_rate": round(blocker_fail_count / float(len(history)), 6) if history else 0.0,
            "warning_presence_rate": round(warn_count / float(len(history)), 6) if history else 0.0,
            "ann_not_positive_rate": round(ann_not_positive_count / float(len(history)), 6) if history else 0.0,
            "ann_active_speed_avg": _avg_nonnull(history, "ann_active_speed"),
            "candidate_active_speed_avg": _avg_nonnull(history, "candidate_active_speed"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Append stage2 guardrail result into trend history JSON")
    parser.add_argument("--input", default="outputs/stage2_guardrail.json")
    parser.add_argument("--output", default="outputs/stage2_guardrail_trend.json")
    parser.add_argument("--label", default="local")
    parser.add_argument("--retain", type=int, default=90)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"missing input file: {input_path.as_posix()}")
    guardrail_payload = _read_json_object(input_path)

    output_path = Path(args.output)
    current_payload: dict[str, Any] | None = None
    if output_path.exists():
        current_payload = _read_json_object(output_path)

    updated = update_trend_payload(
        current_payload=current_payload,
        guardrail_payload=guardrail_payload,
        label=str(args.label),
        retain=max(1, int(args.retain)),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(updated, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
