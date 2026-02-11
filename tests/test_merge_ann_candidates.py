from __future__ import annotations

import unittest

from src.memory_cluster.cluster import IncrementalClusterer
from src.memory_cluster.embed import HashEmbeddingProvider
from src.memory_cluster.models import MemoryCluster, MemoryFragment, PreferenceConfig
from src.memory_cluster.pipeline import build_cluster_result


def _sparse_fragments(count: int = 72) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    for idx in range(count):
        rows.append(
            MemoryFragment(
                id=f"af{idx:03d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-11T09:{idx % 60:02d}:00+00:00",
                content=f"isolated ann token block_{idx} variant_{idx * 17}",
                type="log",
                tags={"category": "noise"},
                meta={"slots": {"k": str(idx)}},
            )
        )
    return rows


def _active_fragments(count: int = 96) -> list[MemoryFragment]:
    rows: list[MemoryFragment] = []
    for idx in range(count):
        mode = ("fast", "safe", "balanced", "strict")[idx % 4]
        alpha = ("0.2", "0.4", "0.6", "0.8")[(idx * 5) % 4]
        rows.append(
            MemoryFragment(
                id=f"aa{idx:03d}",
                agent_id="planner_agent" if idx % 2 == 0 else "writer_agent",
                timestamp=f"2026-02-11T10:{idx % 60:02d}:00+00:00",
                content=(
                    f"ann candidate group_{idx % 10} mode {mode} alpha {alpha} "
                    f"variant_{idx} replay token_{idx * 13}"
                ),
                type="draft" if idx % 3 else "result",
                tags={"category": "method" if idx % 3 else "evidence"},
                meta={"slots": {"mode": mode, "alpha": alpha, "group": str(idx % 10)}},
            )
        )
    return rows


class TestMergeAnnCandidates(unittest.TestCase):
    def test_ann_signature_not_degenerate_on_nonnegative_embeddings(self) -> None:
        provider = HashEmbeddingProvider(dim=128)
        clusterer = IncrementalClusterer(
            enable_merge_ann_candidates=True,
            merge_ann_num_tables=4,
            merge_ann_bits_per_table=8,
            merge_ann_probe_radius=1,
            merge_ann_max_neighbors=16,
            merge_ann_score_dims=32,
        )
        vectors = [provider.embed(f"ann signature sample {idx} mode {idx % 4}") for idx in range(16)]
        signatures = {clusterer._ann_signature(vec, 0) for vec in vectors}
        self.assertGreater(len(signatures), 1)

    def test_ann_neighbor_degree_respects_cap(self) -> None:
        provider = HashEmbeddingProvider(dim=128)
        clusterer = IncrementalClusterer(
            enable_merge_ann_candidates=True,
            merge_ann_num_tables=4,
            merge_ann_bits_per_table=8,
            merge_ann_probe_radius=1,
            merge_ann_max_neighbors=3,
            merge_ann_score_dims=32,
        )
        clusters = [
            MemoryCluster(cluster_id=f"a{idx:03d}", centroid=provider.embed(f"ann cluster text {idx} mode fast"))
            for idx in range(30)
        ]
        neighbors = clusterer._build_ann_candidate_neighbors(clusters)
        self.assertIsNotNone(neighbors)
        for linked in (neighbors or {}).values():
            self.assertLessEqual(len(linked), 3)

    def test_ann_candidates_reduce_attempts_on_sparse_case(self) -> None:
        fragments = _sparse_fragments(72)
        pref_off = PreferenceConfig.from_dict({"enable_merge_ann_candidates": False})
        pref_on = PreferenceConfig.from_dict(
            {
                "enable_merge_ann_candidates": True,
                "merge_ann_num_tables": 4,
                "merge_ann_bits_per_table": 8,
                "merge_ann_probe_radius": 1,
                "merge_ann_max_neighbors": 12,
                "merge_ann_score_dims": 24,
            }
        )

        baseline = build_cluster_result(
            fragments=fragments,
            preference_config=pref_off,
            similarity_threshold=2.0,
            merge_threshold=0.95,
        )
        ann = build_cluster_result(
            fragments=fragments,
            preference_config=pref_on,
            similarity_threshold=2.0,
            merge_threshold=0.95,
        )

        self.assertGreater(int(baseline.metrics.get("merge_attempts") or 0), 0)
        self.assertLess(
            int(ann.metrics.get("merge_attempts") or 0),
            int(baseline.metrics.get("merge_attempts") or 0),
        )
        self.assertGreater(int(ann.metrics.get("merge_pairs_skipped_by_ann_candidates") or 0), 0)
        self.assertEqual(
            int(ann.metrics.get("cluster_count") or 0),
            int(baseline.metrics.get("cluster_count") or 0),
        )

    def test_ann_disabled_reports_zero_skips(self) -> None:
        fragments = _sparse_fragments(32)
        pref = PreferenceConfig.from_dict({"enable_merge_ann_candidates": False})
        result = build_cluster_result(
            fragments=fragments,
            preference_config=pref,
            similarity_threshold=1.8,
            merge_threshold=0.95,
        )
        self.assertEqual(int(result.metrics.get("merge_pairs_skipped_by_ann_candidates") or 0), 0)
        self.assertEqual(int(result.metrics.get("merge_pairs_skipped_by_hybrid_candidates") or 0), 0)

    def test_hybrid_candidate_ann_keeps_active_outcome(self) -> None:
        fragments = _active_fragments(96)
        baseline_pref = PreferenceConfig.from_dict(
            {
                "enable_merge_upper_bound_prune": True,
                "merge_prune_dims": 48,
            }
        )
        hybrid_pref = PreferenceConfig.from_dict(
            {
                **baseline_pref.to_dict(),
                "enable_merge_candidate_filter": True,
                "merge_candidate_bucket_dims": 10,
                "merge_candidate_max_neighbors": 24,
                "enable_merge_ann_candidates": True,
                "merge_ann_num_tables": 6,
                "merge_ann_bits_per_table": 10,
                "merge_ann_probe_radius": 1,
                "merge_ann_max_neighbors": 48,
                "merge_ann_score_dims": 48,
            }
        )

        baseline = build_cluster_result(
            fragments=fragments,
            preference_config=baseline_pref,
            similarity_threshold=0.82,
            merge_threshold=0.85,
        )
        hybrid = build_cluster_result(
            fragments=fragments,
            preference_config=hybrid_pref,
            similarity_threshold=0.82,
            merge_threshold=0.85,
        )

        self.assertEqual(
            int(hybrid.metrics.get("cluster_count") or 0),
            int(baseline.metrics.get("cluster_count") or 0),
        )
        self.assertEqual(
            int(hybrid.metrics.get("merges_applied") or 0),
            int(baseline.metrics.get("merges_applied") or 0),
        )
        self.assertEqual(
            int(hybrid.metrics.get("conflict_count") or 0),
            int(baseline.metrics.get("conflict_count") or 0),
        )
        self.assertGreater(int(hybrid.metrics.get("merge_pairs_skipped_by_hybrid_candidates") or 0), 0)
        self.assertLess(
            int(hybrid.metrics.get("merge_attempts") or 0),
            int(baseline.metrics.get("merge_attempts") or 0),
        )


if __name__ == "__main__":
    unittest.main()
