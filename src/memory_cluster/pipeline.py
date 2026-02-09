from __future__ import annotations

from collections import Counter
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

    metrics = compute_metrics(rows, clusters)
    return ClusterBuildResult(fragments=rows, clusters=clusters, metrics=metrics)
