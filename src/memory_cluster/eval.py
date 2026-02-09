from __future__ import annotations

from collections import Counter
from typing import Any

from .models import MemoryCluster, MemoryFragment


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def compute_metrics(fragments: list[MemoryFragment], clusters: list[MemoryCluster]) -> dict[str, Any]:
    fragment_count = len(fragments)
    cluster_count = len(clusters)
    l1_clusters = [item for item in clusters if int(item.level) == 1]
    l1_cluster_count = len(l1_clusters)
    l2_cluster_count = sum(1 for item in clusters if int(item.level) >= 2)
    original_chars = sum(len(item.content or "") for item in fragments)
    compressed_chars = sum(len(item.summary or "") for item in l1_clusters) if l1_clusters else sum(
        len(item.summary or "") for item in clusters
    )
    compressed_chars_all = sum(len(item.summary or "") for item in clusters)
    unique_text_count = len({_normalize(item.content) for item in fragments if _normalize(item.content)})
    conflicts = sum(len(item.conflicts) for item in l1_clusters) if l1_clusters else sum(
        len(item.conflicts) for item in clusters
    )
    clusters_with_conflict = sum(1 for item in (l1_clusters if l1_clusters else clusters) if item.conflicts)
    total_backrefs = sum(len(item.backrefs) for item in l1_clusters) if l1_clusters else sum(
        len(item.backrefs) for item in clusters
    )
    total_backrefs_all = sum(len(item.backrefs) for item in clusters)

    type_distribution = Counter(item.type for item in fragments)
    source_distribution = Counter(item.agent_id for item in fragments)

    compression_ratio = (compressed_chars / original_chars) if original_chars else 0.0
    dedup_reduction = 1.0 - (unique_text_count / fragment_count) if fragment_count else 0.0
    cluster_denominator = l1_cluster_count if l1_cluster_count else cluster_count
    avg_cluster_size = (fragment_count / cluster_denominator) if cluster_denominator else 0.0
    conflict_cluster_rate = (clusters_with_conflict / cluster_denominator) if cluster_denominator else 0.0

    return {
        "fragment_count": fragment_count,
        "cluster_count": cluster_count,
        "l1_cluster_count": l1_cluster_count,
        "l2_cluster_count": l2_cluster_count,
        "original_chars": original_chars,
        "compressed_chars": compressed_chars,
        "compressed_chars_all": compressed_chars_all,
        "compression_ratio": round(compression_ratio, 6),
        "dedup_reduction": round(dedup_reduction, 6),
        "avg_cluster_size": round(avg_cluster_size, 6),
        "conflict_count": conflicts,
        "conflict_cluster_rate": round(conflict_cluster_rate, 6),
        "backref_count": total_backrefs,
        "backref_count_all": total_backrefs_all,
        "fragment_type_distribution": dict(type_distribution),
        "source_distribution": dict(source_distribution),
    }
