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
        enable_dual_merge_guard: bool = False,
        merge_conflict_compat_threshold: float = 0.55,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.merge_threshold = merge_threshold
        self.category_strict = category_strict
        self.enable_dual_merge_guard = enable_dual_merge_guard
        self.merge_conflict_compat_threshold = merge_conflict_compat_threshold
        self._counter = 0
        self._id_pattern = re.compile(r"^cluster-(\d+)$")
        self.merge_attempts = 0
        self.merges_applied = 0
        self.merges_blocked_by_guard = 0

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
        return self.merge_clusters_with_lookup(clusters=clusters, fragment_lookup=None)

    def merge_clusters_with_lookup(
        self,
        clusters: list[MemoryCluster],
        fragment_lookup: dict[str, MemoryFragment] | None,
    ) -> list[MemoryCluster]:
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
                    self.merge_attempts += 1
                    score = cosine_similarity(base.centroid, other.centroid)
                    if score < self.merge_threshold:
                        continue
                    if self.enable_dual_merge_guard and fragment_lookup:
                        compat = self._conflict_compatibility(base, other, fragment_lookup)
                        if compat < self.merge_conflict_compat_threshold:
                            self.merges_blocked_by_guard += 1
                            continue
                    self._merge_pair(base, other)
                    self.merges_applied += 1
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

    def snapshot_stats(self) -> dict[str, int]:
        return {
            "merge_attempts": int(self.merge_attempts),
            "merges_applied": int(self.merges_applied),
            "merges_blocked_by_guard": int(self.merges_blocked_by_guard),
        }

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

    def _extract_slots(self, fragment: MemoryFragment) -> dict[str, set[str]]:
        output: dict[str, set[str]] = {}
        slots = fragment.meta.get("slots")
        if isinstance(slots, dict):
            for slot, value in slots.items():
                key = str(slot)
                output.setdefault(key, set()).add(str(value))
        flags = fragment.meta.get("flags")
        if isinstance(flags, dict):
            for key, value in flags.items():
                slot = f"flag:{str(key).strip().lower()}"
                output.setdefault(slot, set()).add("true" if bool(value) else "false")
        return output

    def _slot_profile(
        self,
        cluster: MemoryCluster,
        fragment_lookup: dict[str, MemoryFragment],
    ) -> dict[str, set[str]]:
        profile: dict[str, set[str]] = {}
        for fid in cluster.fragment_ids:
            fragment = fragment_lookup.get(fid)
            if fragment is None:
                continue
            slots = self._extract_slots(fragment)
            for slot, values in slots.items():
                profile.setdefault(slot, set()).update(values)
        return profile

    def _conflict_compatibility(
        self,
        cluster_a: MemoryCluster,
        cluster_b: MemoryCluster,
        fragment_lookup: dict[str, MemoryFragment],
    ) -> float:
        profile_a = self._slot_profile(cluster_a, fragment_lookup)
        profile_b = self._slot_profile(cluster_b, fragment_lookup)
        overlap = sorted(set(profile_a.keys()).intersection(profile_b.keys()))
        if not overlap:
            return 1.0

        scores: list[float] = []
        for slot in overlap:
            set_a = profile_a.get(slot) or set()
            set_b = profile_b.get(slot) or set()
            if not set_a or not set_b:
                continue
            inter = len(set_a.intersection(set_b))
            union = len(set_a.union(set_b))
            if union == 0:
                continue
            score = inter / float(union)
            if score == 0.0:
                return 0.0
            scores.append(score)

        if not scores:
            return 1.0
        return sum(scores) / float(len(scores))
