from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
import re

from .embed import cosine_similarity
from .models import MemoryCluster, MemoryFragment, utc_now_iso


@dataclass
class ClusterAssignment:
    cluster_id: str
    score: float
    created_new: bool


@dataclass
class _CandidateState:
    signatures_by_id: dict[str, tuple[int, ...]]
    bucket_to_ids: dict[tuple[int, ...], set[str]]
    centroids_by_id: dict[str, list[float]]
    neighbors: dict[str, set[str]]


@dataclass
class _AnnState:
    signatures_by_id: dict[str, list[int]]
    tables: list[dict[int, set[str]]]
    vectors_by_id: dict[str, list[float]]
    neighbors: dict[str, set[str]]


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
        merge_candidate_projection_steps: int = 32,
        merge_candidate_signature_radius: int = 4,
        enable_merge_ann_candidates: bool = False,
        merge_ann_num_tables: int = 3,
        merge_ann_bits_per_table: int = 10,
        merge_ann_probe_radius: int = 1,
        merge_ann_max_neighbors: int = 48,
        merge_ann_score_dims: int = 32,
        merge_ann_projection_steps: int = 32,
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
        self.merge_candidate_projection_steps = max(1, int(merge_candidate_projection_steps))
        self.merge_candidate_signature_radius = max(0, int(merge_candidate_signature_radius))
        self.enable_merge_ann_candidates = enable_merge_ann_candidates
        self.merge_ann_num_tables = max(1, int(merge_ann_num_tables))
        self.merge_ann_bits_per_table = max(1, int(merge_ann_bits_per_table))
        self.merge_ann_probe_radius = max(0, min(1, int(merge_ann_probe_radius)))
        self.merge_ann_max_neighbors = max(1, int(merge_ann_max_neighbors))
        self.merge_ann_score_dims = max(1, int(merge_ann_score_dims))
        self.merge_ann_projection_steps = max(1, int(merge_ann_projection_steps))
        self._counter = 0
        self._id_pattern = re.compile(r"^cluster-(\d+)$")
        self.merge_attempts = 0
        self.merges_applied = 0
        self.merges_blocked_by_guard = 0
        self.merge_pairs_pruned_by_bound = 0
        self.merge_pairs_skipped_by_candidate_filter = 0
        self.merge_pairs_skipped_by_ann_candidates = 0
        self.merge_pairs_skipped_by_hybrid_candidates = 0
        self.merge_candidate_filter_fallbacks = 0
        self.merge_ann_candidate_fallbacks = 0
        self._projection_plan_cache: dict[tuple[int, int, int], tuple[int, int, int, bool, int]] = {}

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
        candidate_state = self._build_candidate_state(active)
        ann_state = self._build_ann_state(active)
        candidate_filter_neighbors = candidate_state.neighbors if candidate_state is not None else None
        ann_neighbors = ann_state.neighbors if ann_state is not None else None
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
                        candidate_state=candidate_state,
                        ann_state=ann_state,
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
            "merge_candidate_filter_fallbacks": int(self.merge_candidate_filter_fallbacks),
            "merge_ann_candidate_fallbacks": int(self.merge_ann_candidate_fallbacks),
        }

    def _build_candidate_neighbors(self, clusters: list[MemoryCluster]) -> dict[str, set[str]] | None:
        state = self._build_candidate_state(clusters)
        return state.neighbors if state is not None else None

    def _build_candidate_state(self, clusters: list[MemoryCluster]) -> _CandidateState | None:
        if not self.enable_merge_candidate_filter:
            return None
        if len(clusters) < 2:
            return _CandidateState(signatures_by_id={}, bucket_to_ids={}, centroids_by_id={}, neighbors={})

        signatures: dict[str, tuple[int, ...]] = {}
        bucket_to_ids: dict[tuple[int, ...], set[str]] = {}
        centroids_by_id: dict[str, list[float]] = {}
        for cluster in clusters:
            cid = cluster.cluster_id
            centroid = cluster.centroid or []
            centroids_by_id[cid] = centroid
            signature = self._candidate_signature(centroid)
            signatures[cid] = signature
            bucket_to_ids.setdefault(signature, set()).add(cid)

        unique_ratio, max_bucket_ratio = self._signature_bucket_quality(bucket_to_ids, total=len(clusters))
        if unique_ratio < 0.18 or max_bucket_ratio > 0.90:
            self.merge_candidate_filter_fallbacks += 1
            return None

        state = _CandidateState(
            signatures_by_id=signatures,
            bucket_to_ids=bucket_to_ids,
            centroids_by_id=centroids_by_id,
            neighbors={},
        )
        for cid in sorted(centroids_by_id.keys()):
            state.neighbors[cid] = self._build_candidate_neighbors_from_state(cid, state)
        return state

    def _build_candidate_neighbors_from_state(self, base_cluster_id: str, state: _CandidateState) -> set[str]:
        signature = state.signatures_by_id.get(base_cluster_id) or ()
        candidate_ids = self._collect_bucket_candidates(
            base_cluster_id=base_cluster_id,
            signature=signature,
            bucket_to_ids=state.bucket_to_ids,
            max_hamming_distance=self.merge_candidate_signature_radius,
        )
        if not candidate_ids:
            return set()
        base_vector = state.centroids_by_id.get(base_cluster_id) or []
        ranked = sorted(
            candidate_ids,
            key=lambda peer_id: (
                -self._approx_cosine(base_vector, state.centroids_by_id.get(peer_id) or []),
                peer_id,
            ),
        )
        return set(self._cap_neighbor_ids(ranked, self.merge_candidate_max_neighbors))

    def _candidate_state_drop_cluster(self, state: _CandidateState, cluster_id: str) -> None:
        old_signature = state.signatures_by_id.pop(cluster_id, None)
        if old_signature is not None:
            bucket = state.bucket_to_ids.get(old_signature)
            if bucket is not None:
                bucket.discard(cluster_id)
                if not bucket:
                    state.bucket_to_ids.pop(old_signature, None)
        state.centroids_by_id.pop(cluster_id, None)
        state.neighbors.pop(cluster_id, None)

    def _candidate_state_upsert_cluster(self, state: _CandidateState, cluster_id: str, centroid: list[float]) -> None:
        new_signature = self._candidate_signature(centroid)
        old_signature = state.signatures_by_id.get(cluster_id)
        if old_signature is not None and old_signature != new_signature:
            old_bucket = state.bucket_to_ids.get(old_signature)
            if old_bucket is not None:
                old_bucket.discard(cluster_id)
                if not old_bucket:
                    state.bucket_to_ids.pop(old_signature, None)
        state.signatures_by_id[cluster_id] = new_signature
        state.bucket_to_ids.setdefault(new_signature, set()).add(cluster_id)
        state.centroids_by_id[cluster_id] = list(centroid)

    def _build_ann_candidate_neighbors(
        self,
        clusters: list[MemoryCluster],
        ann_signature_cache: dict[str, list[int]] | None = None,
    ) -> dict[str, set[str]] | None:
        state = self._build_ann_state(clusters, ann_signature_cache=ann_signature_cache)
        return state.neighbors if state is not None else None

    def _build_ann_state(
        self,
        clusters: list[MemoryCluster],
        ann_signature_cache: dict[str, list[int]] | None = None,
    ) -> _AnnState | None:
        if not self.enable_merge_ann_candidates:
            return None
        if len(clusters) < 2:
            return _AnnState(signatures_by_id={}, tables=[], vectors_by_id={}, neighbors={})

        vectors_by_id: dict[str, list[float]] = {cluster.cluster_id: (cluster.centroid or []) for cluster in clusters}
        signatures_by_id = ann_signature_cache or self._build_ann_signature_cache(clusters)
        quality = self._ann_signature_quality(signatures_by_id)
        if quality["unique_ratio"] < 0.18 or quality["max_bucket_ratio"] > 0.90:
            self.merge_ann_candidate_fallbacks += 1
            return None

        tables = self._build_ann_tables(signatures_by_id)
        state = _AnnState(
            signatures_by_id={cid: list(values) for cid, values in signatures_by_id.items()},
            tables=tables,
            vectors_by_id=vectors_by_id,
            neighbors={},
        )
        for cid in sorted(vectors_by_id.keys()):
            state.neighbors[cid] = self._build_ann_neighbors_from_state(cid, state)
        return state

    def _build_ann_neighbors_from_state(self, base_cluster_id: str, state: _AnnState) -> set[str]:
        base_signatures = state.signatures_by_id.get(base_cluster_id) or []
        candidates: set[str] = set()
        for table_idx, signature in enumerate(base_signatures):
            if table_idx >= len(state.tables):
                break
            for probe in self._ann_probe_signatures(signature):
                for peer_id in state.tables[table_idx].get(probe, set()):
                    if peer_id != base_cluster_id:
                        candidates.add(peer_id)

        if not candidates:
            return set()

        base_vector = state.vectors_by_id.get(base_cluster_id) or []
        ranked = sorted(
            candidates,
            key=lambda peer_id: (
                -self._approx_cosine(base_vector, state.vectors_by_id.get(peer_id) or []),
                peer_id,
            ),
        )
        return set(self._cap_neighbor_ids(ranked, self.merge_ann_max_neighbors))

    def _ann_state_drop_cluster(self, state: _AnnState, cluster_id: str) -> None:
        signatures = state.signatures_by_id.pop(cluster_id, None)
        if signatures is not None:
            for table_idx, signature in enumerate(signatures):
                if table_idx >= len(state.tables):
                    break
                bucket = state.tables[table_idx].get(int(signature))
                if bucket is None:
                    continue
                bucket.discard(cluster_id)
                if not bucket:
                    state.tables[table_idx].pop(int(signature), None)
        state.vectors_by_id.pop(cluster_id, None)
        state.neighbors.pop(cluster_id, None)

    def _ann_state_upsert_cluster(self, state: _AnnState, cluster_id: str, vector: list[float]) -> None:
        old_signatures = state.signatures_by_id.get(cluster_id)
        if old_signatures is not None:
            for table_idx, signature in enumerate(old_signatures):
                if table_idx >= len(state.tables):
                    break
                bucket = state.tables[table_idx].get(int(signature))
                if bucket is None:
                    continue
                bucket.discard(cluster_id)
                if not bucket:
                    state.tables[table_idx].pop(int(signature), None)

        new_signatures = [self._ann_signature(vector, table_idx) for table_idx in range(self.merge_ann_num_tables)]
        state.signatures_by_id[cluster_id] = new_signatures
        state.vectors_by_id[cluster_id] = list(vector)
        while len(state.tables) < self.merge_ann_num_tables:
            state.tables.append({})
        for table_idx, signature in enumerate(new_signatures):
            state.tables[table_idx].setdefault(int(signature), set()).add(cluster_id)

    def _build_ann_signature_cache(self, clusters: list[MemoryCluster]) -> dict[str, list[int]]:
        cache: dict[str, list[int]] = {}
        for cluster in clusters:
            vector = cluster.centroid or []
            cache[cluster.cluster_id] = [self._ann_signature(vector, table_idx) for table_idx in range(self.merge_ann_num_tables)]
        return cache

    def _build_ann_tables(self, signatures_by_id: dict[str, list[int]]) -> list[dict[int, set[str]]]:
        tables: list[dict[int, set[str]]] = [{} for _ in range(self.merge_ann_num_tables)]
        for cluster_id, signatures in signatures_by_id.items():
            for table_idx in range(self.merge_ann_num_tables):
                signature = int(signatures[table_idx]) if table_idx < len(signatures) else 0
                tables[table_idx].setdefault(signature, set()).add(cluster_id)
        return tables

    def _ann_signature_quality(self, signatures_by_id: dict[str, list[int]]) -> dict[str, float]:
        total = max(1, len(signatures_by_id))
        unique_ratios: list[float] = []
        max_bucket_ratios: list[float] = []
        for table_idx in range(self.merge_ann_num_tables):
            counts: dict[int, int] = {}
            for signatures in signatures_by_id.values():
                signature = int(signatures[table_idx]) if table_idx < len(signatures) else 0
                counts[signature] = counts.get(signature, 0) + 1
            unique_ratios.append(len(counts) / float(total))
            max_bucket_ratios.append(max(counts.values()) / float(total))
        return {
            "unique_ratio": float(min(unique_ratios) if unique_ratios else 0.0),
            "max_bucket_ratio": float(max(max_bucket_ratios) if max_bucket_ratios else 1.0),
        }

    def _signature_bucket_quality(
        self,
        bucket_to_ids: dict[tuple[int, ...], set[str]],
        *,
        total: int,
    ) -> tuple[float, float]:
        all_total = max(1, int(total))
        unique_ratio = len(bucket_to_ids) / float(all_total)
        largest_bucket = max((len(ids) for ids in bucket_to_ids.values()), default=0)
        max_bucket_ratio = largest_bucket / float(all_total)
        return float(unique_ratio), float(max_bucket_ratio)

    def _ann_signature(self, vector: list[float], table_idx: int) -> int:
        if not vector:
            return 0
        mean_value = self._vector_mean(vector)
        signature = 0
        for bit_idx in range(self.merge_ann_bits_per_table):
            seed = self._mix64(
                ((table_idx + 1) * 911_382_323) ^ ((bit_idx + 1) * 3_571_231) ^ (len(vector) * 1_315_423_911)
            )
            score = self._projection_score(
                vector,
                seed=seed,
                steps=self.merge_ann_projection_steps,
                mean_value=mean_value,
            )
            if score >= 0.0:
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
        mean_value = self._vector_mean(vector)
        output: list[int] = []
        for bit_idx in range(self.merge_candidate_bucket_dims):
            seed = self._mix64((613 * 2_654_435_761) ^ ((bit_idx + 1) * 1_543_271) ^ (len(vector) * 131))
            score = self._projection_score(
                vector,
                seed=seed,
                steps=self.merge_candidate_projection_steps,
                mean_value=mean_value,
            )
            output.append(1 if score >= 0.0 else 0)
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

    def _two_hop_signatures(self, signature: tuple[int, ...]) -> list[tuple[int, ...]]:
        if len(signature) < 2:
            return []
        output: list[tuple[int, ...]] = []
        for left in range(len(signature)):
            for right in range(left + 1, len(signature)):
                row = list(signature)
                row[left] = 1 - row[left]
                row[right] = 1 - row[right]
                output.append(tuple(row))
        return output

    def _hamming_neighbor_signatures(
        self,
        signature: tuple[int, ...],
        max_hamming_distance: int,
    ) -> list[tuple[int, ...]]:
        if not signature:
            return []
        max_dist = max(0, min(int(max_hamming_distance), len(signature)))
        keys: list[tuple[int, ...]] = [signature]
        if max_dist <= 0:
            return keys

        idxs = list(range(len(signature)))
        for dist in range(1, max_dist + 1):
            for combo in itertools.combinations(idxs, dist):
                row = list(signature)
                for idx in combo:
                    row[idx] = 1 - row[idx]
                keys.append(tuple(row))
        return keys

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

    def _vector_mean(self, vector: list[float]) -> float:
        if not vector:
            return 0.0
        return sum(float(value) for value in vector) / float(len(vector))

    def _mix64(self, value: int) -> int:
        mask = (1 << 64) - 1
        x = int(value) & mask
        x ^= (x >> 30)
        x = (x * 0xBF58476D1CE4E5B9) & mask
        x ^= (x >> 27)
        x = (x * 0x94D049BB133111EB) & mask
        x ^= (x >> 31)
        return x & mask

    def _coprime_stride(self, seed: int, dim: int) -> int:
        if dim <= 1:
            return 1
        stride = int(self._mix64(seed ^ 0xC2B2AE3D27D4EB4F) % (dim - 1)) + 1
        while math.gcd(stride, dim) != 1:
            stride += 1
            if stride >= dim:
                stride = 1
        return stride

    def _projection_plan(self, *, seed: int, dim: int, steps: int) -> tuple[int, int, int, bool, int]:
        limit = max(1, min(int(steps), dim))
        key = (int(seed) & ((1 << 64) - 1), int(dim), int(limit))
        cached = self._projection_plan_cache.get(key)
        if cached is not None:
            return cached

        start = int(self._mix64(seed ^ 0x9E3779B97F4A7C15) % dim)
        stride = self._coprime_stride(seed, dim)
        power_of_two_dim = (dim & (dim - 1)) == 0
        dim_mask = dim - 1
        plan = (limit, start, stride, power_of_two_dim, dim_mask)
        self._projection_plan_cache[key] = plan
        return plan

    def _projection_score(
        self,
        vector: list[float],
        *,
        seed: int,
        steps: int,
        mean_value: float,
    ) -> float:
        if not vector:
            return 0.0
        dim = len(vector)
        limit, start, stride, power_of_two_dim, dim_mask = self._projection_plan(seed=seed, dim=dim, steps=steps)
        total = 0.0
        # Faster deterministic pseudo-random signs using xorshift64* state updates.
        state = self._mix64(seed ^ 0xD6E8FEB86659FD93)
        mask_64 = (1 << 64) - 1
        idx = start
        for _ in range(limit):
            centered = float(vector[idx]) - mean_value
            state ^= (state >> 12)
            state &= mask_64
            state ^= ((state << 25) & mask_64)
            state ^= (state >> 27)
            state &= mask_64
            sign = 1.0 if (state & 1) == 0 else -1.0
            total += centered * sign
            if power_of_two_dim:
                idx = (idx + stride) & dim_mask
            else:
                idx = (idx + stride) % dim
        return total

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
        candidate_state: _CandidateState | None,
        ann_state: _AnnState | None,
    ) -> None:
        if gate_mode == "none":
            return
        active_ids = {item.cluster_id for item in active if item is not None}

        def _clean_neighbor_map(mapping: dict[str, set[str]] | None) -> None:
            if mapping is None:
                return
            mapping.pop(removed_cluster_id, None)
            for cid in list(mapping.keys()):
                if cid not in active_ids:
                    mapping.pop(cid, None)
                    continue
                mapping[cid].discard(removed_cluster_id)
                mapping[cid] = {peer for peer in mapping[cid] if peer in active_ids and peer != cid}

        if gate_mode in {"candidate_filter", "hybrid"} and candidate_state is not None:
            self._candidate_state_drop_cluster(candidate_state, removed_cluster_id)
            self._candidate_state_upsert_cluster(candidate_state, base.cluster_id, base.centroid or [])
            _clean_neighbor_map(candidate_state.neighbors)
            candidate_state.neighbors[base.cluster_id] = self._build_candidate_neighbors_from_state(
                base.cluster_id,
                candidate_state,
            )

        if gate_mode in {"ann", "hybrid"} and ann_state is not None:
            self._ann_state_drop_cluster(ann_state, removed_cluster_id)
            self._ann_state_upsert_cluster(ann_state, base.cluster_id, base.centroid or [])
            _clean_neighbor_map(ann_state.neighbors)
            ann_state.neighbors[base.cluster_id] = self._build_ann_neighbors_from_state(base.cluster_id, ann_state)

    def _compute_candidate_neighbors_for_cluster(
        self,
        *,
        base: MemoryCluster,
        clusters: list[MemoryCluster],
    ) -> set[str]:
        signatures_by_id: dict[str, tuple[int, ...]] = {}
        bucket_to_ids: dict[tuple[int, ...], set[str]] = {}
        centroids_by_id: dict[str, list[float]] = {}
        for cluster in clusters:
            cid = cluster.cluster_id
            centroid = cluster.centroid or []
            centroids_by_id[cid] = centroid
            signature = self._candidate_signature(centroid)
            signatures_by_id[cid] = signature
            bucket_to_ids.setdefault(signature, set()).add(cid)

        state = _CandidateState(
            signatures_by_id=signatures_by_id,
            bucket_to_ids=bucket_to_ids,
            centroids_by_id=centroids_by_id,
            neighbors={},
        )
        if base.cluster_id not in state.signatures_by_id:
            return set()
        return self._build_candidate_neighbors_from_state(base.cluster_id, state)

    def _collect_bucket_candidates(
        self,
        *,
        base_cluster_id: str,
        signature: tuple[int, ...],
        bucket_to_ids: dict[tuple[int, ...], set[str]],
        max_hamming_distance: int,
    ) -> list[str]:
        if not signature:
            return []
        keys = self._hamming_neighbor_signatures(signature, max_hamming_distance)
        output: list[str] = []
        seen: set[str] = set()
        for key in keys:
            for peer_id in bucket_to_ids.get(key, []):
                if peer_id == base_cluster_id or peer_id in seen:
                    continue
                seen.add(peer_id)
                output.append(peer_id)
                if len(output) >= max(1, self.merge_candidate_max_neighbors * 8):
                    return output
        return output

    def _compute_ann_neighbors_for_cluster(
        self,
        *,
        base: MemoryCluster,
        clusters: list[MemoryCluster],
        ann_signature_cache: dict[str, list[int]] | None = None,
    ) -> set[str]:
        signatures_by_id = {cid: list(values) for cid, values in (ann_signature_cache or {}).items()}
        vectors_by_id: dict[str, list[float]] = {}
        for cluster in clusters:
            cid = cluster.cluster_id
            vectors_by_id[cid] = cluster.centroid or []
            if cid not in signatures_by_id:
                signatures_by_id[cid] = [
                    self._ann_signature(cluster.centroid or [], table_idx) for table_idx in range(self.merge_ann_num_tables)
                ]
        state = _AnnState(
            signatures_by_id=signatures_by_id,
            tables=self._build_ann_tables(signatures_by_id),
            vectors_by_id=vectors_by_id,
            neighbors={},
        )
        if base.cluster_id not in state.signatures_by_id:
            return set()
        return self._build_ann_neighbors_from_state(base.cluster_id, state)

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
