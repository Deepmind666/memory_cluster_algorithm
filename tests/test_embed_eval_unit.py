from __future__ import annotations

import unittest

from src.memory_cluster.embed import HashEmbeddingProvider, cosine_similarity, tokenize
from src.memory_cluster.eval import compute_metrics
from src.memory_cluster.models import ConflictRecord, MemoryCluster, MemoryFragment


class TestEmbedEvalUnit(unittest.TestCase):
    def test_tokenize_keeps_cjk_ascii_and_underscore(self) -> None:
        path_cn = "\u8def\u5f84"
        mode_cn = "\u6a21\u5f0f"
        version_cn = "\u7248\u672c"
        tokens = tokenize(f"{path_cn} /tmp/a_b-1 {mode_cn}Fast {version_cn}v2")
        self.assertIn(path_cn, tokens)
        self.assertIn("a_b", tokens)
        self.assertIn("1", tokens)
        self.assertIn(f"{mode_cn}fast", tokens)
        self.assertIn(f"{version_cn}v2", tokens)

    def test_cosine_similarity_handles_zero_and_length_mismatch(self) -> None:
        self.assertEqual(cosine_similarity([], [1.0]), 0.0)
        self.assertEqual(cosine_similarity([0.0, 0.0], [1.0, 2.0]), 0.0)
        score = cosine_similarity([1.0, 1.0, 1.0], [1.0, 1.0])
        self.assertGreater(score, 0.99)

    def test_hash_embedding_is_deterministic_and_l2_normalized(self) -> None:
        provider = HashEmbeddingProvider(dim=64)
        vec_a = provider.embed("mode fast alpha 0.7")
        vec_b = provider.embed("mode fast alpha 0.7")
        vec_c = provider.embed("mode safe alpha 0.7")
        self.assertEqual(vec_a, vec_b)
        self.assertNotEqual(vec_a, vec_c)
        norm_sq = sum(value * value for value in vec_a)
        self.assertAlmostEqual(norm_sq, 1.0, places=6)

    def test_compute_metrics_prefers_l1_clusters_for_summary_fields(self) -> None:
        fragments = [
            MemoryFragment(id="f1", agent_id="a", timestamp="2026-02-12T00:00:00+00:00", content="dup", type="draft"),
            MemoryFragment(id="f2", agent_id="a", timestamp="2026-02-12T00:01:00+00:00", content="dup", type="draft"),
            MemoryFragment(id="f3", agent_id="b", timestamp="2026-02-12T00:02:00+00:00", content="uniq", type="result"),
        ]
        l1 = MemoryCluster(
            cluster_id="c1",
            centroid=[0.1, 0.2],
            level=1,
            summary="L1 summary",
            backrefs=["f1", "f2"],
            conflicts=[ConflictRecord(slot="mode", values=["fast", "safe"], evidences=["f1", "f2"], last_seen="now")],
            tags={"detail_budget": 220, "conflict_priority": 1.2},
        )
        l2 = MemoryCluster(
            cluster_id="c2",
            centroid=[0.1, 0.2],
            level=2,
            summary="L2 summary should not be counted into compressed_chars",
            backrefs=["f3"],
            conflicts=[ConflictRecord(slot="alpha", values=["0.2", "0.8"], evidences=["f3"], last_seen="now")],
            tags={"detail_budget": 99, "conflict_priority": 3.0},
        )
        metrics = compute_metrics(fragments, [l1, l2])
        self.assertEqual(int(metrics["l1_cluster_count"]), 1)
        self.assertEqual(int(metrics["l2_cluster_count"]), 1)
        self.assertEqual(int(metrics["compressed_chars"]), len("L1 summary"))
        self.assertEqual(int(metrics["compressed_chars_all"]), len(l1.summary) + len(l2.summary))
        self.assertEqual(int(metrics["conflict_count"]), 1)
        self.assertEqual(int(metrics["backref_count"]), 2)
        self.assertAlmostEqual(float(metrics["dedup_reduction"]), 1.0 - (2.0 / 3.0), places=6)

    def test_compute_metrics_falls_back_to_all_clusters_when_no_l1(self) -> None:
        fragments = [
            MemoryFragment(id="x1", agent_id="a", timestamp="2026-02-12T00:00:00+00:00", content="one", type="draft")
        ]
        only_l2 = MemoryCluster(
            cluster_id="z1",
            centroid=[0.2, 0.3],
            level=2,
            summary="fallback summary",
            backrefs=["x1"],
            conflicts=[ConflictRecord(slot="mode", values=["fast"], evidences=["x1"], last_seen="now")],
            tags={"detail_budget": 100, "conflict_priority": 0.5},
        )
        metrics = compute_metrics(fragments, [only_l2])
        self.assertEqual(int(metrics["compressed_chars"]), len("fallback summary"))
        self.assertEqual(int(metrics["conflict_count"]), 1)
        self.assertEqual(int(metrics["backref_count"]), 1)


if __name__ == "__main__":
    unittest.main()
