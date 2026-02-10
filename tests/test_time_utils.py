from __future__ import annotations

import unittest

from src.memory_cluster.time_utils import parse_iso_utc


class TestTimeUtils(unittest.TestCase):
    def test_parse_iso_accepts_z_suffix(self) -> None:
        dt = parse_iso_utc("2026-02-10T10:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(str(dt.tzinfo), "UTC")

    def test_parse_iso_returns_none_on_invalid(self) -> None:
        self.assertIsNone(parse_iso_utc("not-a-date"))


if __name__ == "__main__":
    unittest.main()
