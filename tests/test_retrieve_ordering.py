from __future__ import annotations

import unittest

from src.memory_cluster.retrieve import MemoryRetriever


class DummyEmbeddingProvider:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = mapping

    def embed(self, text: str) -> list[float]:
        return list(self.mapping.get(text, [0.0, 0.0]))


class TestRetrieverOrdering(unittest.TestCase):
    def test_strength_bonus_breaks_similarity_ties(self) -> None:
        provider = DummyEmbeddingProvider({"q": [1.0, 0.0], "same": [0.0, 1.0]})
        retriever = MemoryRetriever(provider)  # type: ignore[arg-type]
        state = {
            "clusters": [
                {
                    "cluster_id": "weak",
                    "centroid": [1.0, 0.0],
                    "summary": "same",
                    "tags": {"retention_strength": "weak"},
                    "last_updated": "2026-01-01T00:00:00+00:00",
                },
                {
                    "cluster_id": "strong",
                    "centroid": [1.0, 0.0],
                    "summary": "same",
                    "tags": {"retention_strength": "strong"},
                    "last_updated": "2026-01-01T00:00:00+00:00",
                },
            ],
            "fragments": [],
        }

        results = retriever.query(state=state, query_text="q", top_k=2)
        self.assertEqual(results[0]["cluster_id"], "strong")
        self.assertEqual(results[1]["cluster_id"], "weak")

    def test_offset_pages_results(self) -> None:
        provider = DummyEmbeddingProvider({"q": [1.0, 0.0], "same": [0.0, 1.0]})
        retriever = MemoryRetriever(provider)  # type: ignore[arg-type]
        state = {
            "clusters": [
                {
                    "cluster_id": "first",
                    "centroid": [1.0, 0.0],
                    "summary": "same",
                    "tags": {"retention_strength": "strong"},
                    "last_updated": "2026-02-09T00:00:00+00:00",
                },
                {
                    "cluster_id": "second",
                    "centroid": [1.0, 0.0],
                    "summary": "same",
                    "tags": {"retention_strength": "weak"},
                    "last_updated": "2026-02-09T00:00:00+00:00",
                },
                {
                    "cluster_id": "third",
                    "centroid": [1.0, 0.0],
                    "summary": "same",
                    "tags": {"retention_strength": "discardable"},
                    "last_updated": "2026-02-09T00:00:00+00:00",
                },
            ],
            "fragments": [],
        }

        results = retriever.query(state=state, query_text="q", top_k=1, offset=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["cluster_id"], "second")


if __name__ == "__main__":
    unittest.main()
