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
    if args.enable_l2_clusters:
        preference.enable_l2_clusters = True
    if args.l2_min_children:
        preference.l2_min_children = max(2, int(args.l2_min_children))
    if args.enable_conflict_graph:
        preference.enable_conflict_graph = True
    if args.enable_adaptive_budget:
        preference.enable_adaptive_budget = True
    if args.enable_dual_merge_guard:
        preference.enable_dual_merge_guard = True
    if args.merge_conflict_compat_threshold is not None:
        preference.merge_conflict_compat_threshold = float(args.merge_conflict_compat_threshold)
    if args.enable_merge_upper_bound_prune:
        preference.enable_merge_upper_bound_prune = True
    if args.merge_prune_dims is not None:
        preference.merge_prune_dims = max(0, int(args.merge_prune_dims))
    if args.hard_keep_tag:
        preference.hard_keep_tags = list(dict.fromkeys(preference.hard_keep_tags + list(args.hard_keep_tag)))
    if args.protect_path_prefix:
        preference.protected_path_prefixes = list(
            dict.fromkeys(preference.protected_path_prefixes + list(args.protect_path_prefix))
        )
    if args.protect_scope:
        preference.protected_scopes = list(dict.fromkeys(preference.protected_scopes + list(args.protect_scope)))

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
        cluster_level=args.cluster_level,
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
    build.add_argument("--enable-l2-clusters", action="store_true")
    build.add_argument("--l2-min-children", type=int, default=2)
    build.add_argument("--enable-conflict-graph", action="store_true")
    build.add_argument("--enable-adaptive-budget", action="store_true")
    build.add_argument("--enable-dual-merge-guard", action="store_true")
    build.add_argument("--merge-conflict-compat-threshold", type=float, default=None)
    build.add_argument("--enable-merge-upper-bound-prune", action="store_true")
    build.add_argument("--merge-prune-dims", type=int, default=None)
    build.add_argument("--hard-keep-tag", action="append", default=None)
    build.add_argument("--protect-path-prefix", action="append", default=None)
    build.add_argument("--protect-scope", action="append", default=None)
    build.add_argument("--embedding-dim", type=int, default=256)
    build.set_defaults(func=cmd_build)

    query = sub.add_parser("query", help="Query compressed cluster state")
    query.add_argument("--state", required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--cluster-level", choices=("all", "l1", "l2"), default="all")
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
