from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable


_LAST_UPDATED_PREFIX = "Last Updated:"
_ROUND_TITLE_SUFFIX = "Findings Closure"
_ROUND_ID_PATTERN = re.compile(r"^R-\d{3,4}[A-Za-z0-9-]*$")
_INSERT_BEFORE_HEADERS = (
    "## Accepted Limitations",
    "## Current Open Findings",
    "## Maintenance Rule",
)


def build_round_block(*, round_id: str, source_review: str, rows: int) -> str:
    count = max(1, int(rows))
    lines = [
        f"## {round_id} Findings Closure",
        "| Source Review | Finding ID | Severity | Finding Summary | Status | Resolved In | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for idx in range(count):
        finding_slot = f"<FINDING_{idx + 1}>"
        lines.append(
            f"| {source_review} | {finding_slot} | <P0/P1/P2/P3> | <summary> | `open` | <pending> | <artifact/path> |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_round_id(round_id: str) -> str:
    value = round_id.strip()
    if not value:
        raise ValueError("round id cannot be empty")
    if not _ROUND_ID_PATTERN.match(value):
        raise ValueError(f"invalid round id format: {value}")
    return value


def _update_last_updated_line(*, text: str, updated_date: str) -> str:
    output: list[str] = []
    replaced = False
    for line in text.splitlines():
        if line.startswith(_LAST_UPDATED_PREFIX):
            output.append(f"{_LAST_UPDATED_PREFIX} {updated_date}")
            replaced = True
        else:
            output.append(line)
    if replaced:
        return "\n".join(output).rstrip() + "\n"
    return text


def _first_insert_anchor_position(text: str, headers: Iterable[str]) -> int | None:
    header_prefixes = tuple(item.strip() for item in headers)
    offset = 0
    positions: list[int] = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in header_prefixes):
            positions.append(offset)
        offset += len(line)
    if positions:
        return min(positions)
    return None


def insert_round_section(
    *,
    matrix_text: str,
    round_id: str,
    source_review: str,
    rows: int,
    updated_date: str,
) -> str:
    title = f"## {round_id} {_ROUND_TITLE_SUFFIX}"
    if title in matrix_text:
        raise ValueError(f"round section already exists: {round_id}")

    block = build_round_block(round_id=round_id, source_review=source_review, rows=rows)
    anchor = _first_insert_anchor_position(matrix_text, _INSERT_BEFORE_HEADERS)
    if anchor is None:
        stripped = matrix_text.rstrip()
        merged = f"{stripped}\n\n{block}"
    else:
        prefix = matrix_text[:anchor].rstrip()
        suffix = matrix_text[anchor:].lstrip("\n")
        merged = f"{prefix}\n\n{block}\n{suffix}"

    return _update_last_updated_line(text=merged, updated_date=updated_date)


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a review closure round section to review_closure_matrix.md")
    parser.add_argument("--matrix", default="docs/review/review_closure_matrix.md")
    parser.add_argument("--round", required=True, dest="round_id", help="Round id, e.g. R-028")
    parser.add_argument("--source-review", help="Source review label (default: same as --round)")
    parser.add_argument("--rows", type=int, default=3, help="Number of placeholder finding rows")
    args = parser.parse_args()

    matrix_path = Path(str(args.matrix))
    if not matrix_path.exists():
        raise FileNotFoundError(f"matrix file not found: {matrix_path.as_posix()}")

    try:
        round_id = validate_round_id(str(args.round_id))
    except ValueError as exc:
        print(str(exc))
        return 2
    source_review = str(args.source_review).strip() if args.source_review else round_id
    today = datetime.now().strftime("%Y-%m-%d")

    original = matrix_path.read_text(encoding="utf-8")
    try:
        updated = insert_round_section(
            matrix_text=original,
            round_id=round_id,
            source_review=source_review,
            rows=int(args.rows),
            updated_date=today,
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    matrix_path.write_text(updated, encoding="utf-8")
    print(f"appended {round_id} section to {matrix_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
