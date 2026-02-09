from __future__ import annotations

from dataclasses import dataclass
import re

from .embed import cosine_similarity
from .models import MemoryCluster, MemoryFragment, utc_now_iso


@dataclass
class ClusterAssignment:
    cluster_id: str
    score: float
    created_new: bool


class IncrementalClusterer:
    """Incremental centroid-based clustering for memory fragments."""

    def __init__(
        self,
        similarity_threshold: float = 0.72,
        merge_threshold: float = 0.9,
        category_strict: bool = False,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.merge_threshold = merge_threshold
        self.category_strict = category_strict
        self._counter = 0
        self._id_pattern = re.compile(r"^cluster-(\d+)$")

    def assign(
        self,
        fragment: MemoryFragment,
        embedding: list[float],
        clusters: list[MemoryCluster],
    ) -> ClusterAssignment:
        if self._counter == 0 and clusters:
            self._sync_counter(clusters)

        best_cluster: MemoryCluster | None = None
        best_score = -1.0
        for cluster in clusters:
            if not self._is_compatible(fragment, cluster):
                continue
            score = cosine_similarity(embedding, cluster.centroid)
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster and best_score >= self.similarity_threshold:
            self._update_cluster(best_cluster, fragment, embedding)
            return ClusterAssignment(best_cluster.cluster_id, best_score, created_new=False)

        new_cluster = self._new_cluster(fragment, embedding)
        clusters.append(new_cluster)
        return ClusterAssignment(new_cluster.cluster_id, 1.0, created_new=True)

    def merge_clusters(self, clusters: list[MemoryCluster]) -> list[MemoryCluster]:
        if len(clusters) < 2:
            return clusters

        active = list(clusters)
        merged = True
        while merged:
            merged = False
            for i in range(len(active)):
                base = active[i]
                if base is None:
                    continue
                for j in range(i + 1, len(active)):
                    other = active[j]
                    if other is None:
                        continue
                    if not self._cluster_tags_compatible(base, other):
                        continue
                    score = cosine_similarity(base.centroid, other.centroid)
                    if score < self.merge_threshold:
                        continue
                    self._merge_pair(base, other)
                    active[j] = None
                    merged = True
            active = [item for item in active if item is not None]
        return active

    def _new_cluster(self, fragment: MemoryFragment, embedding: list[float]) -> MemoryCluster:
        self._counter += 1
        cluster_id = f"cluster-{self._counter:04d}"
        category = fragment.tags.get("category")
        tags = {"category": category} if category else {}
        cluster = MemoryCluster(
            cluster_id=cluster_id,
            centroid=list(embedding),
            fragment_ids=[fragment.id],
            source_distribution={fragment.agent_id: 1},
            tags=tags,
            backrefs=[fragment.id],
            last_updated=utc_now_iso(),
        )
        return cluster

    def _sync_counter(self, clusters: list[MemoryCluster]) -> None:
        max_seen = 0
        for cluster in clusters:
            match = self._id_pattern.match(cluster.cluster_id)
            if not match:
                continue
            max_seen = max(max_seen, int(match.group(1)))
        self._counter = max_seen

    def _update_cluster(
        self,
        cluster: MemoryCluster,
        fragment: MemoryFragment,
        embedding: list[float],
    ) -> None:
        count = max(len(cluster.fragment_ids), 1)
        updated = []
        for old_value, new_value in zip(cluster.centroid, embedding):
            updated.append(((old_value * count) + new_value) / (count + 1))
        cluster.centroid = updated
        cluster.fragment_ids.append(fragment.id)
        cluster.backrefs.append(fragment.id)
        cluster.source_distribution[fragment.agent_id] = cluster.source_distribution.get(fragment.agent_id, 0) + 1
        cluster.last_updated = utc_now_iso()
        cluster.version += 1

    def _merge_pair(self, base: MemoryCluster, other: MemoryCluster) -> None:
        size_base = max(len(base.fragment_ids), 1)
        size_other = max(len(other.fragment_ids), 1)
        total = size_base + size_other
        if len(base.centroid) == len(other.centroid):
            base.centroid = [
                (base.centroid[i] * size_base + other.centroid[i] * size_other) / total
                for i in range(len(base.centroid))
            ]
        base.fragment_ids.extend(other.fragment_ids)
        base.backrefs.extend(other.backrefs)
        for key, value in other.source_distribution.items():
            base.source_distribution[key] = base.source_distribution.get(key, 0) + value
        base.last_updated = utc_now_iso()
        base.version += 1

    def _is_compatible(self, fragment: MemoryFragment, cluster: MemoryCluster) -> bool:
        if not self.category_strict:
            return True
        category_f = fragment.tags.get("category")
        category_c = cluster.tags.get("category")
        if category_f and category_c and category_f != category_c:
            return False
        return True

    def _cluster_tags_compatible(self, cluster_a: MemoryCluster, cluster_b: MemoryCluster) -> bool:
        if not self.category_strict:
            return True
        category_a = cluster_a.tags.get("category")
        category_b = cluster_b.tags.get("category")
        if category_a and category_b and category_a != category_b:
            return False
        return True
