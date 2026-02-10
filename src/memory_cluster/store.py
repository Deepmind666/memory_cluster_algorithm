from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any

from .models import ClusterBuildResult, MemoryFragment


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _lock_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".lock")


@dataclass
class StoreReadStats:
    total_lines: int = 0
    parsed_lines: int = 0
    skipped_blank: int = 0
    skipped_invalid: int = 0
    decode_errors: int = 0
    schema_errors: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total_lines": int(self.total_lines),
            "parsed_lines": int(self.parsed_lines),
            "skipped_blank": int(self.skipped_blank),
            "skipped_invalid": int(self.skipped_invalid),
            "decode_errors": int(self.decode_errors),
            "schema_errors": int(self.schema_errors),
        }


@dataclass
class StoreAppendStats:
    attempted: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    store_invalid_lines: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "attempted": int(self.attempted),
            "inserted": int(self.inserted),
            "skipped_existing": int(self.skipped_existing),
            "store_invalid_lines": int(self.store_invalid_lines),
        }


class _FileLock:
    """Simple lock-file guard for cross-process write sections."""

    def __init__(self, path: Path, timeout_s: float = 3.0, poll_s: float = 0.05, stale_lock_s: float = 30.0) -> None:
        self.path = _lock_path(path)
        self.timeout_s = max(0.1, float(timeout_s))
        self.poll_s = max(0.01, float(poll_s))
        self.stale_lock_s = max(1.0, float(stale_lock_s))

    def __enter__(self) -> "_FileLock":
        _ensure_parent(self.path)
        started = time.monotonic()
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    age_s = time.time() - self.path.stat().st_mtime
                    if age_s > self.stale_lock_s:
                        self.path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass

                if (time.monotonic() - started) > self.timeout_s:
                    raise TimeoutError(f"acquire lock timeout: {self.path}") from None
                time.sleep(self.poll_s)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass


class FragmentStore:
    """Append-only JSONL store for memory fragments with id-level roundtrip support."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.last_read_stats = StoreReadStats()
        self.last_append_stats = StoreAppendStats()

    def append_fragments(self, fragments: list[MemoryFragment], idempotent: bool = False) -> int:
        return int(self.append_fragments_with_stats(fragments=fragments, idempotent=idempotent).inserted)

    def append_fragments_with_stats(
        self,
        fragments: list[MemoryFragment],
        idempotent: bool = False,
        lock_timeout_s: float = 3.0,
    ) -> StoreAppendStats:
        stats = StoreAppendStats(attempted=len(fragments))
        _ensure_parent(self.path)
        with _FileLock(self.path, timeout_s=lock_timeout_s):
            existing_keys: set[tuple[str, int]] = set()
            if idempotent:
                existing_rows, read_stats = self.load_fragments_with_stats(strict=False)
                stats.store_invalid_lines = int(read_stats.skipped_invalid)
                existing_keys = {(item.id, int(item.version)) for item in existing_rows}

            pending: list[MemoryFragment] = []
            seen_batch: set[tuple[str, int]] = set()
            for fragment in fragments:
                key = (str(fragment.id), int(fragment.version))
                if idempotent and (key in existing_keys or key in seen_batch):
                    stats.skipped_existing += 1
                    continue
                pending.append(fragment)
                seen_batch.add(key)

            with self.path.open("a", encoding="utf-8") as handle:
                for fragment in pending:
                    handle.write(json.dumps(fragment.to_dict(), ensure_ascii=False) + "\n")
            stats.inserted = len(pending)

        self.last_append_stats = stats
        return stats

    def load_fragments(self, strict: bool = False) -> list[MemoryFragment]:
        rows, _ = self.load_fragments_with_stats(strict=strict)
        return rows

    def load_fragments_with_stats(self, strict: bool = False) -> tuple[list[MemoryFragment], StoreReadStats]:
        stats = StoreReadStats()
        if not self.path.exists():
            self.last_read_stats = stats
            return [], stats

        rows: list[MemoryFragment] = []
        with self.path.open("r", encoding="utf-8-sig") as handle:
            for lineno, raw_line in enumerate(handle, start=1):
                stats.total_lines += 1
                line = raw_line.strip()
                if not line:
                    stats.skipped_blank += 1
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    stats.skipped_invalid += 1
                    stats.decode_errors += 1
                    if strict:
                        raise ValueError(f"invalid json in store at line {lineno}: {exc.msg}") from exc
                    continue

                try:
                    rows.append(MemoryFragment.from_dict(payload))
                    stats.parsed_lines += 1
                except Exception as exc:  # defensive parse guard
                    stats.skipped_invalid += 1
                    stats.schema_errors += 1
                    if strict:
                        raise ValueError(f"invalid fragment payload in store at line {lineno}: {exc}") from exc
                    continue

        self.last_read_stats = stats
        return rows, stats

    def load_latest_by_id(self, strict: bool = False) -> list[MemoryFragment]:
        rows, _ = self.load_latest_by_id_with_stats(strict=strict)
        return rows

    def load_latest_by_id_with_stats(self, strict: bool = False) -> tuple[list[MemoryFragment], StoreReadStats]:
        rows, stats = self.load_fragments_with_stats(strict=strict)
        latest: dict[str, MemoryFragment] = {}
        for fragment in rows:
            current = latest.get(fragment.id)
            if current is None or fragment.version >= current.version:
                latest[fragment.id] = fragment
        return list(latest.values()), stats


def save_result(path: str | Path, result: ClusterBuildResult) -> None:
    target = Path(path)
    _ensure_parent(target)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, ensure_ascii=False, indent=2)


def load_result(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    with target.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)
