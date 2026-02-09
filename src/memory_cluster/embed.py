from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from hashlib import blake2b


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_PATTERN.finditer(text or "")]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    length = min(len(vec_a), len(vec_b))
    dot = sum(vec_a[i] * vec_b[i] for i in range(length))
    norm_a = math.sqrt(sum(vec_a[i] * vec_a[i] for i in range(length)))
    norm_b = math.sqrt(sum(vec_b[i] * vec_b[i] for i in range(length)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class HashEmbeddingProvider(EmbeddingProvider):
    """
    Dependency-light deterministic embedding.

    It maps tokens to a fixed-size vector via stable hashing.
    """

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim

    def _index(self, token: str) -> int:
        digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, byteorder="big", signed=False)
        return value % self.dim

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vector = [0.0] * self.dim
        if not tokens:
            return vector
        for token in tokens:
            vector[self._index(token)] += 1.0
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]
