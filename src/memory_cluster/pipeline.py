from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from .cluster import IncrementalClusterer
from .compress import ClusterCompressor
from .embed import HashEmbeddingProvider
from .eval import compute_metrics
from .models import ClusterBuildResult, MemoryCluster, MemoryFragment, PreferenceConfig, utc_now_iso
from .preference import PreferencePolicyEngine


def _build_source_distribution(fragments: list[MemoryFragment]) -> dict[str, int]:
    counter = Counter(item.agent_id for item in fragments)
    return dict(counter)


def _merge_source_distribution(clusters: list[MemoryCluster]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for cluster in clusters:
        for source, count in cluster.source_distribution.items():
            merged[source] = merged.get(source, 0) + int(count)
    return merged


def _centroid_average(vectors: list[list[float]]) -> list[float]:
    valid = [vec for vec in vectors if vec]
    if not valid:
        return []
    dim = len(valid[0])
    aligned = [vec for vec in valid if len(vec) == dim]
    if not aligned:
        return []
    return [sum(vec[i] for vec in aligned) / len(aligned) for i in range(dim)]


def _pick_parent_strength(clusters: list[MemoryCluster]) -> str:
    order = {"discardable": 0, "weak": 1, "strong": 2}
    best = "weak"
    best_score = -1
    for cluster in clusters:
        strength = str(cluster.tags.get("retention_strength") or "weak").lower()
        score = order.get(strength, 1)
        if score > best_score:
            best_score = score
            best = strength
    return best


def _build_l2_clusters(clusters: list[MemoryCluster], min_children: int = 2) -> list[MemoryCluster]:
    grouped: dict[str, list[MemoryCluster]] = defaultdict(list)
    for cluster in clusters:
        if cluster.level != 1:
            continue
        key = str(cluster.tags.get("category") or "uncategorized")
        grouped[key].append(cluster)

    output: list[MemoryCluster] = []
    counter = 0
    for category, members in sorted(grouped.items(), key=lambda item: item[0]):
        if len(members) < max(2, int(min_children)):
            continue

        counter += 1
        topic_id = f"topic-{counter:04d}"
        child_ids = sorted(cluster.cluster_id for cluster in members)
        fragment_ids = sorted({fid for cluster in members for fid in cluster.fragment_ids})
        centroid = _centroid_average([cluster.centroid for cluster in members])
        source_distribution = _merge_source_distribution(members)
        consensus: dict[str, str] = {}
        if members:
            seed = members[0].consensus
            for slot, value in seed.items():
                if all(cluster.consensus.get(slot) == value for cluster in members):
                    consensus[slot] = value

        parent_strength = _pick_parent_strength(members)
        l2 = MemoryCluster(
            cluster_id=topic_id,
            centroid=centroid,
            fragment_ids=fragment_ids,
            source_distribution=source_distribution,
            tags={
                "category": category,
                "retention_strength": parent_strength,
                "cluster_level": "L2",
                "child_cluster_count": len(child_ids),
            },
            consensus=consensus,
            child_cluster_ids=child_ids,
            level=2,
            summary=(
                f"id={topic_id};level=L2;cat={category};children={len(child_ids)};"
                f"frags={len(fragment_ids)};cons={len(consensus)}"
            ),
            backrefs=fragment_ids,
            last_updated=utc_now_iso(),
        )
        output.append(l2)
        for child in members:
            child.parent_cluster_id = topic_id

    return output


def _split_conflicted_clusters(
    clusters: list[MemoryCluster],
    fragment_map: dict[str, MemoryFragment],
    embedding_map: dict[str, list[float]],
    compressor: ClusterCompressor,
    policy_engine: PreferencePolicyEngine,
    decisions: dict[str, object],
) -> list[MemoryCluster]:
    output: list[MemoryCluster] = []
    for cluster in clusters:
        if not cluster.split_groups or len(cluster.split_groups) <= 1:
            output.append(cluster)
            continue

        for index, group in enumerate(cluster.split_groups, start=1):
            group_ids = [str(fid) for fid in (group.get("fragment_ids") or [])]
            members = [fragment_map[fid] for fid in group_ids if fid in fragment_map]
            if not members:
                continue

            vectors = [embedding_map.get(member.id, []) for member in members]
            dim = len(next((vec for vec in vectors if vec), []))
            centroid = [0.0] * dim
            valid_vectors = [vec for vec in vectors if len(vec) == dim and dim > 0]
            if valid_vectors:
                for i in range(dim):
                    centroid[i] = sum(vec[i] for vec in valid_vectors) / len(valid_vectors)

            child = MemoryCluster(
                cluster_id=f"{cluster.cluster_id}-s{index}",
                centroid=centroid,
                fragment_ids=[member.id for member in members],
                source_distribution=_build_source_distribution(members),
                tags={
                    **cluster.tags,
                    "split_from": cluster.cluster_id,
                    "split_slot": str(group.get("slot") or ""),
                    "split_value": str(group.get("value") or ""),
                },
                backrefs=[member.id for member in members],
                last_updated=utc_now_iso(),
                level=1,
            )
            compressor.compress(
                cluster=child,
                fragments=members,
                policy_engine=policy_engine,
                decisions=decisions,
            )
            output.append(child)
    return output


def build_cluster_result(
    fragments: Iterable[MemoryFragment],
    preference_config: PreferenceConfig | None = None,
    similarity_threshold: float = 0.72,
    merge_threshold: float = 0.9,
    category_strict: bool = False,
    embedding_dim: int = 256,
) -> ClusterBuildResult:
    rows = sorted(list(fragments), key=lambda item: item.timestamp)
    provider = HashEmbeddingProvider(dim=embedding_dim)
    clusterer = IncrementalClusterer(
        similarity_threshold=similarity_threshold,
        merge_threshold=merge_threshold,
        category_strict=category_strict,
    )

    clusters: list[MemoryCluster] = []
    embedding_by_id: dict[str, list[float]] = {}
    for fragment in rows:
        vector = provider.embed(fragment.content)
        embedding_by_id[fragment.id] = vector
        clusterer.assign(fragment=fragment, embedding=vector, clusters=clusters)

    clusters = clusterer.merge_clusters(clusters)

    pref = preference_config or PreferenceConfig()
    policy_engine = PreferencePolicyEngine(pref)
    decisions = {fragment.id: policy_engine.decide_for_fragment(fragment) for fragment in rows}

    by_id = {fragment.id: fragment for fragment in rows}
    compressor = ClusterCompressor(
        semantic_dedup_threshold=pref.semantic_dedup_threshold,
        strict_conflict_split=pref.strict_conflict_split or policy_engine.strict_conflict_split(),
    )
    for cluster in clusters:
        members = [by_id[fid] for fid in cluster.fragment_ids if fid in by_id]
        compressor.compress(
            cluster=cluster,
            fragments=members,
            policy_engine=policy_engine,
            decisions=decisions,
        )

    if pref.strict_conflict_split:
        clusters = _split_conflicted_clusters(
            clusters=clusters,
            fragment_map=by_id,
            embedding_map=embedding_by_id,
            compressor=compressor,
            policy_engine=policy_engine,
            decisions=decisions,
        )

    if pref.enable_l2_clusters:
        clusters.extend(_build_l2_clusters(clusters=clusters, min_children=pref.l2_min_children))

    metrics = compute_metrics(rows, clusters)
    return ClusterBuildResult(fragments=rows, clusters=clusters, metrics=metrics)
