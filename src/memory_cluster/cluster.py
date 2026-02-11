from __future__ import annotations

from dataclasses import dataclass
import math
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
        enable_merge_upper_bound_prune: bool = False,
        merge_prune_dims: int = 48,
        enable_merge_candidate_filter: bool = False,
        merge_candidate_bucket_dims: int = 10,
        merge_candidate_max_neighbors: int = 48,
        enable_merge_ann_candidates: bool = False,
        merge_ann_num_tables: int = 4,
        merge_ann_bits_per_table: int = 8,
        merge_ann_probe_radius: int = 0,
        merge_ann_max_neighbors: int = 24,
        merge_ann_score_dims: int = 32,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.merge_threshold = merge_threshold
        self.category_strict = category_strict
        self.enable_dual_merge_guard = enable_dual_merge_guard
        self.merge_conflict_compat_threshold = merge_conflict_compat_threshold
        self.enable_merge_upper_bound_prune = enable_merge_upper_bound_prune
        self.merge_prune_dims = max(0, int(merge_prune_dims))
        self.enable_merge_candidate_filter = enable_merge_candidate_filter
        self.merge_candidate_bucket_dims = max(1, int(merge_candidate_bucket_dims))
        self.merge_candidate_max_neighbors = max(1, int(merge_candidate_max_neighbors))
        self.enable_merge_ann_candidates = enable_merge_ann_candidates
        self.merge_ann_num_tables = max(1, int(merge_ann_num_tables))
        self.merge_ann_bits_per_table = max(1, int(merge_ann_bits_per_table))
        self.merge_ann_probe_radius = max(0, min(1, int(merge_ann_probe_radius)))
        self.merge_ann_max_neighbors = max(1, int(merge_ann_max_neighbors))
        self.merge_ann_score_dims = max(1, int(merge_ann_score_dims))
        self._counter = 0
        self._id_pattern = re.compile(r"^cluster-(\d+)$")
        self.merge_attempts = 0
        self.merges_applied = 0
        self.merges_blocked_by_guard = 0
        self.merge_pairs_pruned_by_bound = 0
        self.merge_pairs_skipped_by_candidate_filter = 0
        self.merge_pairs_skipped_by_ann_candidates = 0
        self.merge_pairs_skipped_by_hybrid_candidates = 0

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
        candidate_filter_neighbors = self._build_candidate_neighbors(active)
        ann_neighbors = self._build_ann_candidate_neighbors(active)
        gate_mode = "none"
        if candidate_filter_neighbors is not None and ann_neighbors is not None:
            gate_mode = "hybrid"
        elif candidate_filter_neighbors is not None:
            gate_mode = "candidate_filter"
        elif ann_neighbors is not None:
            gate_mode = "ann"

        merged = True
        while merged:
            merged = False
            bound_cache = self._build_bound_cache(active)
            for i in range(len(active)):
                base = active[i]
                if base is None:
                    continue
                for j in range(i + 1, len(active)):
                    other = active[j]
                    if other is None:
                        continue
                    if gate_mode == "candidate_filter":
                        allowed = self._pair_allowed_in_map(
                            base.cluster_id, other.cluster_id, candidate_filter_neighbors
                        )
                        if not allowed:
                            self.merge_pairs_skipped_by_candidate_filter += 1
                            continue
                    elif gate_mode == "ann":
                        allowed = self._pair_allowed_in_map(base.cluster_id, other.cluster_id, ann_neighbors)
                        if not allowed:
                            self.merge_pairs_skipped_by_ann_candidates += 1
                            continue
                    elif gate_mode == "hybrid":
                        allowed = self._pair_allowed_in_map(
                            base.cluster_id, other.cluster_id, candidate_filter_neighbors
                        ) or self._pair_allowed_in_map(base.cluster_id, other.cluster_id, ann_neighbors)
                        if not allowed:
                            self.merge_pairs_skipped_by_hybrid_candidates += 1
                            continue
                    if not self._cluster_tags_compatible(base, other):
                        continue
                    self.merge_attempts += 1
                    if self.enable_merge_upper_bound_prune and self.merge_prune_dims > 0:
                        upper_bound = self._cosine_upper_bound_from_cache(base, other, bound_cache)
                        if upper_bound < self.merge_threshold:
                            self.merge_pairs_pruned_by_bound += 1
                            continue
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
                    removed_cluster_id = other.cluster_id
                    active[j] = None
                    self._refresh_bound_cache_entry(base, bound_cache)
                    bound_cache.pop(removed_cluster_id, None)
                    self._refresh_neighbors_after_merge(
                        active=active,
                        base=base,
                        removed_cluster_id=removed_cluster_id,
                        gate_mode=gate_mode,
                        candidate_filter_neighbors=candidate_filter_neighbors,
                        ann_neighbors=ann_neighbors,
                    )
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
            "merge_pairs_pruned_by_bound": int(self.merge_pairs_pruned_by_bound),
            "merge_pairs_skipped_by_candidate_filter": int(self.merge_pairs_skipped_by_candidate_filter),
            "merge_pairs_skipped_by_ann_candidates": int(self.merge_pairs_skipped_by_ann_candidates),
            "merge_pairs_skipped_by_hybrid_candidates": int(self.merge_pairs_skipped_by_hybrid_candidates),
        }

    def _build_candidate_neighbors(self, clusters: list[MemoryCluster]) -> dict[str, set[str]] | None:
        if not self.enable_merge_candidate_filter:
            return None
        if len(clusters) < 2:
            return {}

        signatures: dict[str, tuple[int, ...]] = {}
        bucket_to_ids: dict[tuple[int, ...], list[str]] = {}
        for cluster in clusters:
            signature = self._candidate_signature(cluster.centroid)
            signatures[cluster.cluster_id] = signature
            bucket_to_ids.setdefault(signature, []).append(cluster.cluster_id)

        neighbors: dict[str, set[str]] = {}
        centroid_by_id = {cluster.cluster_id: (cluster.centroid or []) for cluster in clusters}
        explore_k = max(4, self.merge_candidate_max_neighbors)
        for cluster in clusters:
            cid = cluster.cluster_id
            signature = signatures.get(cid) or ()
            picked: list[str] = []

            for peer_id in bucket_to_ids.get(signature, []):
                if peer_id != cid:
                    picked.append(peer_id)

            for adjacent in self._adjacent_signatures(signature):
                if len(picked) >= self.merge_candidate_max_neighbors:
                    break
                for peer_id in bucket_to_ids.get(adjacent, []):
                    if peer_id != cid:
                        picked.append(peer_id)
                        if len(picked) >= self.merge_candidate_max_neighbors:
                            break

            deduped = self._cap_neighbor_ids(picked, max(1, self.merge_candidate_max_neighbors * 3))
            ranked = sorted(
                deduped,
                key=lambda peer_id: (
                    -self._approx_cosine(centroid_by_id.get(cid) or [], centroid_by_id.get(peer_id) or []),
                    peer_id,
                ),
            )
            all_ranked = sorted(
                [peer_id for peer_id in centroid_by_id.keys() if peer_id != cid],
                key=lambda peer_id: (
                    -self._approx_cosine(centroid_by_id.get(cid) or [], centroid_by_id.get(peer_id) or []),
                    peer_id,
                ),
            )
            exploratory = all_ranked[:explore_k]
            merged = self._cap_neighbor_ids(ranked + exploratory, max(1, self.merge_candidate_max_neighbors * 6))
            merged_ranked = sorted(
                merged,
                key=lambda peer_id: (
                    -self._approx_cosine(centroid_by_id.get(cid) or [], centroid_by_id.get(peer_id) or []),
                    peer_id,
                ),
            )
            neighbors[cid] = set(self._cap_neighbor_ids(merged_ranked, self.merge_candidate_max_neighbors))
        return neighbors

    def _build_ann_candidate_neighbors(self, clusters: list[MemoryCluster]) -> dict[str, set[str]] | None:
        if not self.enable_merge_ann_candidates:
            return None
        if len(clusters) < 2:
            return {}

        vectors: dict[str, list[float]] = {cluster.cluster_id: (cluster.centroid or []) for cluster in clusters}
        tables: list[dict[int, list[str]]] = [{} for _ in range(self.merge_ann_num_tables)]
        signatures_by_id: dict[str, list[int]] = {}
        for cluster in clusters:
            cid = cluster.cluster_id
            vector = vectors.get(cid) or []
            signatures: list[int] = []
            for table_idx in range(self.merge_ann_num_tables):
                signature = self._ann_signature(vector, table_idx)
                signatures.append(signature)
                tables[table_idx].setdefault(signature, []).append(cid)
            signatures_by_id[cid] = signatures

        neighbors: dict[str, set[str]] = {}
        for cluster in clusters:
            cid = cluster.cluster_id
            candidates: set[str] = set()
            for table_idx, signature in enumerate(signatures_by_id.get(cid) or []):
                probes = self._ann_probe_signatures(signature)
                for probe in probes:
                    for peer_id in tables[table_idx].get(probe, []):
                        if peer_id != cid:
                            candidates.add(peer_id)

            if not candidates:
                neighbors[cid] = set()
                continue

            ranked = sorted(
                candidates,
                key=lambda peer_id: (
                    -self._approx_cosine(
                        vectors.get(cid) or [],
                        vectors.get(peer_id) or [],
                    ),
                    peer_id,
                ),
            )
            neighbors[cid] = set(self._cap_neighbor_ids(ranked, self.merge_ann_max_neighbors))
        return neighbors

    def _ann_signature(self, vector: list[float], table_idx: int) -> int:
        values: list[float] = []
        for bit_idx in range(self.merge_ann_bits_per_table):
            values.append(self._bucket_value(vector, seed_a=(table_idx + 1) * 911, seed_b=(bit_idx + 1) * 3571))
        threshold = self._median(values)
        signature = 0
        for bit_idx in range(self.merge_ann_bits_per_table):
            if values[bit_idx] > threshold:
                signature |= (1 << bit_idx)
        return signature

    def _ann_probe_signatures(self, signature: int) -> list[int]:
        if self.merge_ann_probe_radius <= 0:
            return [signature]
        probes = [signature]
        for bit_idx in range(self.merge_ann_bits_per_table):
            probes.append(signature ^ (1 << bit_idx))
        return probes

    def _approx_cosine(self, vec_a: list[float], vec_b: list[float]) -> float:
        dim = min(len(vec_a), len(vec_b), self.merge_ann_score_dims)
        if dim <= 0:
            return -1.0
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for idx in range(dim):
            a = float(vec_a[idx])
            b = float(vec_b[idx])
            dot += a * b
            norm_a += a * a
            norm_b += b * b
        if norm_a <= 0.0 or norm_b <= 0.0:
            return -1.0
        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def _candidate_signature(self, vector: list[float]) -> tuple[int, ...]:
        if not vector:
            return ()
        values: list[float] = []
        for bit_idx in range(self.merge_candidate_bucket_dims):
            values.append(self._bucket_value(vector, seed_a=613, seed_b=(bit_idx + 1) * 1543))
        threshold = self._median(values)
        output: list[int] = []
        for value in values:
            output.append(1 if value > threshold else 0)
        return tuple(output)

    def _adjacent_signatures(self, signature: tuple[int, ...]) -> list[tuple[int, ...]]:
        if not signature:
            return []
        output: list[tuple[int, ...]] = []
        for idx in range(len(signature)):
            row = list(signature)
            row[idx] = 1 - row[idx]
            output.append(tuple(row))
        return output

    def _build_bound_cache(self, clusters: list[MemoryCluster]) -> dict[str, dict[str, object]]:
        if not self.enable_merge_upper_bound_prune or self.merge_prune_dims <= 0:
            return {}
        cache: dict[str, dict[str, object]] = {}
        for cluster in clusters:
            self._refresh_bound_cache_entry(cluster, cache)
        return cache

    def _refresh_bound_cache_entry(
        self,
        cluster: MemoryCluster,
        cache: dict[str, dict[str, object]],
    ) -> None:
        if not self.enable_merge_upper_bound_prune or self.merge_prune_dims <= 0:
            return
        vector = cluster.centroid or []
        dim = min(len(vector), self.merge_prune_dims)
        prefix = vector[:dim]
        prefix_norm_sq = sum(value * value for value in prefix)
        full_norm_sq = sum(value * value for value in vector)
        cache[cluster.cluster_id] = {
            "prefix": prefix,
            "prefix_norm_sq": prefix_norm_sq,
            "full_norm_sq": full_norm_sq,
        }

    def _cosine_upper_bound_from_cache(
        self,
        cluster_a: MemoryCluster,
        cluster_b: MemoryCluster,
        cache: dict[str, dict[str, object]],
    ) -> float:
        if not self.enable_merge_upper_bound_prune or self.merge_prune_dims <= 0:
            return 1.0
        row_a = cache.get(cluster_a.cluster_id)
        row_b = cache.get(cluster_b.cluster_id)
        if not row_a or not row_b:
            return 1.0

        norm_sq_a = float(row_a.get("full_norm_sq") or 0.0)
        norm_sq_b = float(row_b.get("full_norm_sq") or 0.0)
        if norm_sq_a <= 0.0 or norm_sq_b <= 0.0:
            return -1.0

        prefix_a = row_a.get("prefix") or []
        prefix_b = row_b.get("prefix") or []
        prefix_dot = sum(float(x) * float(y) for x, y in zip(prefix_a, prefix_b))

        prefix_norm_sq_a = float(row_a.get("prefix_norm_sq") or 0.0)
        prefix_norm_sq_b = float(row_b.get("prefix_norm_sq") or 0.0)
        rem_sq_a = max(0.0, norm_sq_a - prefix_norm_sq_a)
        rem_sq_b = max(0.0, norm_sq_b - prefix_norm_sq_b)

        upper_dot = prefix_dot + math.sqrt(rem_sq_a * rem_sq_b)
        denom = math.sqrt(norm_sq_a) * math.sqrt(norm_sq_b)
        if denom <= 0.0:
            return -1.0
        bound = upper_dot / denom
        return max(-1.0, min(1.0, float(bound)))

    def _bucket_value(self, vector: list[float], *, seed_a: int, seed_b: int) -> float:
        if not vector:
            return 0.0
        dim = len(vector)
        idx_1 = (seed_a * 131 + seed_b * 17 + 11) % dim
        idx_2 = (seed_a * 173 + seed_b * 37 + 29) % dim
        idx_3 = (seed_a * 199 + seed_b * 53 + 47) % dim
        return float(vector[idx_1]) + (0.5 * float(vector[idx_2])) + (0.25 * float(vector[idx_3]))

    def _median(self, rows: list[float]) -> float:
        if not rows:
            return 0.0
        ordered = sorted(float(value) for value in rows)
        mid = len(ordered) // 2
        if len(ordered) % 2 == 1:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2.0

    def _pair_allowed_in_map(
        self,
        left_id: str,
        right_id: str,
        neighbor_map: dict[str, set[str]] | None,
    ) -> bool:
        if neighbor_map is None:
            return True
        left = neighbor_map.get(left_id) or set()
        if right_id in left:
            return True
        right = neighbor_map.get(right_id) or set()
        return left_id in right

    def _cap_neighbor_ids(self, rows: list[str], limit: int) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for item in rows:
            if item in seen:
                continue
            seen.add(item)
            output.append(item)
            if len(output) >= max(1, int(limit)):
                break
        return output

    def _refresh_neighbors_after_merge(
        self,
        *,
        active: list[MemoryCluster | None],
        base: MemoryCluster,
        removed_cluster_id: str,
        gate_mode: str,
        candidate_filter_neighbors: dict[str, set[str]] | None,
        ann_neighbors: dict[str, set[str]] | None,
    ) -> None:
        if gate_mode == "none":
            return
        active_clusters = [item for item in active if item is not None]
        active_ids = {item.cluster_id for item in active_clusters}

        def _drop_removed(mapping: dict[str, set[str]] | None) -> None:
            if mapping is None:
                return
            mapping.pop(removed_cluster_id, None)
            for cid in list(mapping.keys()):
                if cid not in active_ids:
                    mapping.pop(cid, None)
                    continue
                linked = {peer for peer in (mapping.get(cid) or set()) if peer in active_ids and peer != cid}
                mapping[cid] = linked

        _drop_removed(candidate_filter_neighbors)
        _drop_removed(ann_neighbors)

        if gate_mode in {"candidate_filter", "hybrid"} and candidate_filter_neighbors is not None:
            candidate_filter_neighbors[base.cluster_id] = self._compute_candidate_neighbors_for_cluster(
                base=base,
                clusters=active_clusters,
            )

        if gate_mode in {"ann", "hybrid"} and ann_neighbors is not None:
            ann_neighbors[base.cluster_id] = self._compute_ann_neighbors_for_cluster(
                base=base,
                clusters=active_clusters,
            )

    def _compute_candidate_neighbors_for_cluster(
        self,
        *,
        base: MemoryCluster,
        clusters: list[MemoryCluster],
    ) -> set[str]:
        signature = self._candidate_signature(base.centroid or [])
        adjacent = set(self._adjacent_signatures(signature))
        rows: list[tuple[float, str]] = []
        all_rows: list[tuple[float, str]] = []
        for cluster in clusters:
            if cluster.cluster_id == base.cluster_id:
                continue
            score = self._approx_cosine(base.centroid or [], cluster.centroid or [])
            all_rows.append((score, cluster.cluster_id))
            peer_signature = self._candidate_signature(cluster.centroid or [])
            if peer_signature == signature or peer_signature in adjacent:
                rows.append((score, cluster.cluster_id))
        rows.sort(key=lambda item: (-float(item[0]), item[1]))
        all_rows.sort(key=lambda item: (-float(item[0]), item[1]))
        explore_k = max(4, self.merge_candidate_max_neighbors)
        ids = [cid for _, cid in rows]
        ids.extend(cid for _, cid in all_rows[:explore_k])
        centroid_by_id = {cluster.cluster_id: (cluster.centroid or []) for cluster in clusters}
        base_vector = base.centroid or []
        merged_ids = self._cap_neighbor_ids(ids, max(1, self.merge_candidate_max_neighbors * 6))
        merged_ids.sort(
            key=lambda cid: (
                -self._approx_cosine(base_vector, centroid_by_id.get(cid) or []),
                cid,
            )
        )
        return set(self._cap_neighbor_ids(merged_ids, self.merge_candidate_max_neighbors))

    def _compute_ann_neighbors_for_cluster(
        self,
        *,
        base: MemoryCluster,
        clusters: list[MemoryCluster],
    ) -> set[str]:
        base_signatures = [self._ann_signature(base.centroid or [], table_idx) for table_idx in range(self.merge_ann_num_tables)]
        rows: list[tuple[float, str]] = []
        for cluster in clusters:
            if cluster.cluster_id == base.cluster_id:
                continue
            matched = False
            for table_idx in range(self.merge_ann_num_tables):
                peer_sig = self._ann_signature(cluster.centroid or [], table_idx)
                probes = self._ann_probe_signatures(base_signatures[table_idx])
                if peer_sig in probes:
                    matched = True
                    break
            if not matched:
                continue
            score = self._approx_cosine(base.centroid or [], cluster.centroid or [])
            rows.append((score, cluster.cluster_id))
        rows.sort(key=lambda item: (-float(item[0]), item[1]))
        ids = [cid for _, cid in rows]
        return set(self._cap_neighbor_ids(ids, self.merge_ann_max_neighbors))

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
