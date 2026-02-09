from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .embed import HashEmbeddingProvider
from .models import MemoryFragment, PreferenceConfig
from .pipeline import build_cluster_result
from .retrieve import MemoryRetriever
from .store import FragmentStore, load_result, save_result


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _load_fragments_from_jsonl(path: str | Path) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(MemoryFragment.from_dict(json.loads(line)))
    return rows


def cmd_ingest(args: argparse.Namespace) -> int:
    fragments = _load_fragments_from_jsonl(args.input)
    store = FragmentStore(args.store)
    inserted = store.append_fragments(fragments)
    print(json.dumps({"status": "ok", "inserted": inserted, "store": args.store}, ensure_ascii=False))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    store = FragmentStore(args.store)
    fragments = store.load_latest_by_id()
    if not fragments:
        print(json.dumps({"status": "error", "message": "no fragments in store"}, ensure_ascii=False))
        return 1

    preference = PreferenceConfig()
    if args.preferences:
        preference = PreferenceConfig.from_dict(_load_json(args.preferences))
    if args.strict_conflict_split:
        preference.strict_conflict_split = True

    result = build_cluster_result(
        fragments=fragments,
        preference_config=preference,
        similarity_threshold=args.similarity_threshold,
        merge_threshold=args.merge_threshold,
        category_strict=args.category_strict,
        embedding_dim=args.embedding_dim,
    )
    save_result(args.output, result)
    print(json.dumps({"status": "ok", "output": args.output, "metrics": result.metrics}, ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    state = load_result(args.state)
    retriever = MemoryRetriever(HashEmbeddingProvider(dim=args.embedding_dim))
    results = retriever.query(
        state=state,
        query_text=args.query,
        top_k=args.top_k,
        offset=args.offset,
        expand=args.expand,
    )
    print(json.dumps({"status": "ok", "results": results}, ensure_ascii=False, indent=2))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    state = load_result(args.state)
    metrics = state.get("metrics") or {}
    payload = {"status": "ok", "metrics": metrics}
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Memory cluster CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest jsonl fragments into store")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--store", required=True)
    ingest.set_defaults(func=cmd_ingest)

    build = sub.add_parser("build", help="Build clusters from stored fragments")
    build.add_argument("--store", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--preferences", required=False)
    build.add_argument("--similarity-threshold", type=float, default=0.72)
    build.add_argument("--merge-threshold", type=float, default=0.9)
    build.add_argument("--category-strict", action="store_true")
    build.add_argument("--strict-conflict-split", action="store_true")
    build.add_argument("--embedding-dim", type=int, default=256)
    build.set_defaults(func=cmd_build)

    query = sub.add_parser("query", help="Query compressed cluster state")
    query.add_argument("--state", required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--expand", action="store_true")
    query.add_argument("--embedding-dim", type=int, default=256)
    query.set_defaults(func=cmd_query)

    evaluate = sub.add_parser("eval", help="Print metrics from cluster state")
    evaluate.add_argument("--state", required=True)
    evaluate.add_argument("--output", required=False)
    evaluate.set_defaults(func=cmd_eval)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
