from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.memory_cluster.models import MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result
from src.memory_cluster.store import save_result


def load_fragments(path: Path) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(MemoryFragment.from_dict(json.loads(line)))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run memory cluster benchmark")
    parser.add_argument("--input", required=True)
    parser.add_argument("--preferences", required=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--similarity-threshold", type=float, default=0.72)
    parser.add_argument("--merge-threshold", type=float, default=0.9)
    args = parser.parse_args()

    fragments = load_fragments(Path(args.input))
    pref = PreferenceConfig()
    if args.preferences:
        with Path(args.preferences).open("r", encoding="utf-8-sig") as handle:
            pref = PreferenceConfig.from_dict(json.load(handle))

    durations = []
    last_result = None
    for _ in range(max(1, args.runs)):
        start = time.perf_counter()
        last_result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=args.similarity_threshold,
            merge_threshold=args.merge_threshold,
        )
        durations.append((time.perf_counter() - start) * 1000.0)

    avg_ms = sum(durations) / len(durations)
    p95_ms = sorted(durations)[int(round((len(durations) - 1) * 0.95))]

    payload = {
        "runs": len(durations),
        "avg_ms": round(avg_ms, 3),
        "p95_ms": round(p95_ms, 3),
        "metrics": last_result.metrics if last_result else {},
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    if last_result:
        state_path = out_path.with_name("cluster_state.json")
        save_result(state_path, last_result)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
