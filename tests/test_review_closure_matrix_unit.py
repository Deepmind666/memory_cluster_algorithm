from __future__ import annotations

import unittest

from scripts.append_review_closure_round import (
    insert_round_section,
    validate_round_id,
)


_MATRIX_TEXT = """# Review Closure Matrix

Version: v1.0
Last Updated: 2026-02-13
Owner: Codex (implementation), Claude Opus (review)

## Purpose
Track reviewer findings.

## R-027 Findings Closure
| Source Review | Finding ID | Severity | Finding Summary | Status | Resolved In | Evidence |
|---|---|---|---|---|---|---|
| R-027 | P2-1 | P2 | sample | `closed` | R-036 | docs/FINAL_REPORT.md |

## Accepted Limitations (Non-blocking)
| Item | Severity | Status | Evidence |
|---|---|---|---|
| sample | warning | `waived` | outputs/stage2_guardrail.json |

## Current Open Findings
No open findings.

## Maintenance Rule
1. append rows
"""


class TestReviewClosureMatrixUnit(unittest.TestCase):
    def test_insert_round_section_places_block_before_accepted_limitations(self) -> None:
        updated = insert_round_section(
            matrix_text=_MATRIX_TEXT,
            round_id="R-038",
            source_review="R-038",
            rows=2,
            updated_date="2026-02-14",
        )
        self.assertIn("## R-038 Findings Closure", updated)
        self.assertIn("<FINDING_1>", updated)
        self.assertIn("<FINDING_2>", updated)
        self.assertLess(
            updated.index("## R-038 Findings Closure"),
            updated.index("## Accepted Limitations (Non-blocking)"),
        )
        self.assertIn("Last Updated: 2026-02-14", updated)

    def test_insert_round_section_rejects_duplicate_round_id(self) -> None:
        with self.assertRaises(ValueError):
            insert_round_section(
                matrix_text=_MATRIX_TEXT,
                round_id="R-027",
                source_review="R-027",
                rows=1,
                updated_date="2026-02-14",
            )

    def test_insert_round_section_appends_when_no_anchor_headers(self) -> None:
        matrix_text = """# Review Closure Matrix
Last Updated: 2026-02-13
## Purpose
text
"""
        updated = insert_round_section(
            matrix_text=matrix_text,
            round_id="R-039",
            source_review="R-039",
            rows=1,
            updated_date="2026-02-14",
        )
        self.assertTrue(updated.rstrip().endswith("| R-039 | <FINDING_1> | <P0/P1/P2/P3> | <summary> | `open` | <pending> | <artifact/path> |"))
        self.assertIn("Last Updated: 2026-02-14", updated)

    def test_validate_round_id_accepts_expected_formats(self) -> None:
        self.assertEqual(validate_round_id("R-028"), "R-028")
        self.assertEqual(validate_round_id("R-1024A"), "R-1024A")

    def test_validate_round_id_rejects_invalid_formats(self) -> None:
        with self.assertRaises(ValueError):
            validate_round_id("")
        with self.assertRaises(ValueError):
            validate_round_id("r-028")
        with self.assertRaises(ValueError):
            validate_round_id("R028")


if __name__ == "__main__":
    unittest.main()
