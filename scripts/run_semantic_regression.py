from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.memory_cluster.compress import _extract_slot_values
from src.memory_cluster.models import MemoryFragment


def _fragment(fragment_id: str, content: str) -> MemoryFragment:
    return MemoryFragment(
        id=fragment_id,
        agent_id="semantic_regression_agent",
        timestamp="2026-02-10T14:00:00+00:00",
        content=content,
        type="decision",
    )


def _normalize_pairs(rows: list[tuple[str, str]]) -> set[tuple[str, str]]:
    return {(str(slot), str(value)) for slot, value in rows}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    fragment = _fragment(str(case["id"]), str(case["content"]))
    extracted = _normalize_pairs(_extract_slot_values(fragment))
    expected = _normalize_pairs([(str(s), str(v)) for s, v in (case.get("expected") or [])])
    forbidden = _normalize_pairs([(str(s), str(v)) for s, v in (case.get("forbidden") or [])])

    missing = sorted(expected - extracted)
    violations = sorted(forbidden.intersection(extracted))
    passed = (not missing) and (not violations)

    return {
        "id": case.get("id"),
        "description": case.get("description"),
        "content": case.get("content"),
        "passed": passed,
        "expected": sorted(expected),
        "forbidden": sorted(forbidden),
        "extracted": sorted(extracted),
        "missing_expected": missing,
        "forbidden_violations": violations,
    }


def build_cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "cond_then_boundary",
            "description": "condition scope should stop before then-clause consequence",
            "content": "if mode=fast then cache=true, final cache=false",
            "expected": [("cond:mode", "fast"), ("cache", "true"), ("cache", "false")],
            "forbidden": [("cond:cache", "true")],
        },
        {
            "id": "negated_prefix_en",
            "description": "english not-prefix should become negated slot value",
            "content": "not mode=fast; mode=safe",
            "expected": [("mode", "!fast"), ("mode", "safe")],
            "forbidden": [],
        },
        {
            "id": "double_negation_flag",
            "description": "double-negation on negative flag should not emit false",
            "content": "do not disable cache, enable cache",
            "expected": [("flag:cache", "true")],
            "forbidden": [("flag:cache", "false")],
        },
        {
            "id": "coref_en_it",
            "description": "cross-sentence it= should resolve to previous slot",
            "content": "mode=fast. it=safe",
            "expected": [("mode", "fast"), ("mode", "safe")],
            "forbidden": [("it", "safe")],
        },
        {
            "id": "coref_zh_alias",
            "description": "Chinese pronoun alias should resolve to previous slot",
            "content": "\u6a21\u5f0f=fast\uff0c\u5b83=safe",
            "expected": [("\u6a21\u5f0f", "fast"), ("\u6a21\u5f0f", "safe")],
            "forbidden": [("\u5b83", "safe")],
        },
        {
            "id": "scoped_coref",
            "description": "coreference inside conditional scope keeps cond prefix",
            "content": "if mode=fast and it=safe then fallback mode=safe",
            "expected": [("cond:mode", "fast"), ("cond:mode", "safe"), ("mode", "safe")],
            "forbidden": [("cond:it", "safe")],
        },
        {
            "id": "counterfactual_negation",
            "description": "counterfactual negation should remain scoped",
            "content": "should have alpha!=0.7, final alpha=0.2",
            "expected": [("cf:alpha", "!0.7"), ("alpha", "0.2")],
            "forbidden": [],
        },
        {
            "id": "conditional_flag_isolation",
            "description": "conditional flag should not leak into factual namespace",
            "content": "if enable cache then rollback, alpha=0.2",
            "expected": [("cond:flag:cache", "true"), ("alpha", "0.2")],
            "forbidden": [("flag:cache", "true")],
        },
    ]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    case_count = len(results)
    passed = sum(1 for row in results if bool(row.get("passed")))
    failed = case_count - passed

    expected_total = sum(len(row.get("expected") or []) for row in results)
    expected_hit = 0
    forbidden_total = sum(len(row.get("forbidden") or []) for row in results)
    forbidden_violations = sum(len(row.get("forbidden_violations") or []) for row in results)
    for row in results:
        missing = len(row.get("missing_expected") or [])
        expected_hit += max(0, len(row.get("expected") or []) - missing)

    expected_hit_rate = 1.0
    if expected_total > 0:
        expected_hit_rate = expected_hit / float(expected_total)

    return {
        "case_count": case_count,
        "passed_cases": passed,
        "failed_cases": failed,
        "case_pass_rate": round((passed / float(case_count)) if case_count > 0 else 1.0, 6),
        "expected_pairs_total": expected_total,
        "expected_pairs_hit": expected_hit,
        "expected_hit_rate": round(expected_hit_rate, 6),
        "forbidden_pairs_total": forbidden_total,
        "forbidden_violations": forbidden_violations,
    }


def write_report(report_path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    lines = [
        "# Semantic Precision Regression Report",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- case_count: {summary.get('case_count')}",
        f"- passed_cases: {summary.get('passed_cases')}",
        f"- failed_cases: {summary.get('failed_cases')}",
        f"- case_pass_rate: {summary.get('case_pass_rate')}",
        f"- expected_hit_rate: {summary.get('expected_hit_rate')}",
        f"- forbidden_violations: {summary.get('forbidden_violations')}",
        "",
    ]
    for row in payload.get("results") or []:
        lines.extend(
            [
                f"## Case: {row.get('id')}",
                f"- description: {row.get('description')}",
                f"- passed: {row.get('passed')}",
                f"- missing_expected: {row.get('missing_expected')}",
                f"- forbidden_violations: {row.get('forbidden_violations')}",
                "",
            ]
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run semantic precision regression suite")
    parser.add_argument("--output", required=True, help="Path to output JSON metrics")
    parser.add_argument("--report", required=False, help="Optional markdown report path")
    args = parser.parse_args()

    cases = build_cases()
    results = [evaluate_case(case) for case in cases]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "semantic_precision_regression_v1",
        "summary": summarize(results),
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.report:
        write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
