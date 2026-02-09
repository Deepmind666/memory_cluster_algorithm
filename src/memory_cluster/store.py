from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ClusterBuildResult, MemoryFragment


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class FragmentStore:
    """Append-only JSONL store for memory fragments with id-level roundtrip support."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append_fragments(self, fragments: list[MemoryFragment]) -> int:
        _ensure_parent(self.path)
        with self.path.open("a", encoding="utf-8") as handle:
            for fragment in fragments:
                handle.write(json.dumps(fragment.to_dict(), ensure_ascii=False) + "\n")
        return len(fragments)

    def load_fragments(self) -> list[MemoryFragment]:
        if not self.path.exists():
            return []
        rows: list[MemoryFragment] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                rows.append(MemoryFragment.from_dict(payload))
        return rows

    def load_latest_by_id(self) -> list[MemoryFragment]:
        latest: dict[str, MemoryFragment] = {}
        for fragment in self.load_fragments():
            current = latest.get(fragment.id)
            if current is None or fragment.version >= current.version:
                latest[fragment.id] = fragment
        return list(latest.values())


def save_result(path: str | Path, result: ClusterBuildResult) -> None:
    target = Path(path)
    _ensure_parent(target)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, ensure_ascii=False, indent=2)


def load_result(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)
