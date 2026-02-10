from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .embed import EmbeddingProvider, cosine_similarity
from .time_utils import parse_iso_utc


_STRENGTH_BONUS = {
    "strong": 0.08,
    "weak": 0.03,
    "discardable": -0.02,
}
_CONFLICT_TOKENS = {"冲突", "矛盾", "conflict", "inconsistent", "disagree"}


class MemoryRetriever:
    """Retrieve relevant compressed clusters and optionally rehydrate raw fragments."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider

    def query(
        self,
        state: dict[str, Any],
        query_text: str,
        top_k: int = 5,
        offset: int = 0,
        cluster_level: str = "all",
        expand: bool = False,
    ) -> list[dict[str, Any]]:
        query_vec = self.embedding_provider.embed(query_text)
        clusters = state.get("clusters") or []
        fragments = state.get("fragments") or []
        fragment_map = {item.get("id"): item for item in fragments if isinstance(item, dict)}
        level_filter = (cluster_level or "all").lower()

        scored: list[tuple[float, dict[str, Any]]] = []
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            level = int(cluster.get("level") or 1)
            if level_filter == "l1" and level != 1:
                continue
            if level_filter == "l2" and level < 2:
                continue
            centroid = [float(x) for x in (cluster.get("centroid") or [])]
            summary_text = str(cluster.get("summary") or "")
            summary_vec = self.embedding_provider.embed(summary_text)
            semantic_score = max(cosine_similarity(query_vec, centroid), cosine_similarity(query_vec, summary_vec))
            keyword_bonus = self._keyword_bonus(query_text, summary_text)
            strength_bonus = self._strength_bonus(cluster)
            freshness_bonus = self._freshness_bonus(str(cluster.get("last_updated") or ""))
            conflict_bonus = self._conflict_focus_bonus(query_text, cluster)
            score = semantic_score + keyword_bonus + strength_bonus + freshness_bonus + conflict_bonus
            scored.append((score, self._sort_timestamp(str(cluster.get("last_updated") or "")), cluster))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        start = max(0, int(offset))
        end = start + max(1, int(top_k))
        output: list[dict[str, Any]] = []
        for score, _, cluster in scored[start:end]:
            record: dict[str, Any] = {
                "cluster_id": cluster.get("cluster_id"),
                "score": round(float(score), 6),
                "summary": cluster.get("summary"),
                "conflict_count": len(cluster.get("conflicts") or []),
                "conflict_priority": round(float(self._conflict_priority(cluster)), 6),
                "backrefs": cluster.get("backrefs") or [],
                "level": int(cluster.get("level") or 1),
            }
            if expand:
                record["fragments"] = [fragment_map.get(fid) for fid in record["backrefs"] if fid in fragment_map]
            output.append(record)
        return output

    def _keyword_bonus(self, query_text: str, summary_text: str) -> float:
        query_tokens = {token for token in query_text.lower().split() if token}
        if not query_tokens:
            return 0.0
        summary_lower = summary_text.lower()
        hits = sum(1 for token in query_tokens if token in summary_lower)
        return 0.05 * hits

    def _strength_bonus(self, cluster: dict[str, Any]) -> float:
        tags = cluster.get("tags") or {}
        if not isinstance(tags, dict):
            return 0.0
        strength = str(tags.get("retention_strength") or "weak").lower()
        return float(_STRENGTH_BONUS.get(strength, 0.0))

    def _freshness_bonus(self, ts: str) -> float:
        dt = parse_iso_utc(ts)
        if dt is None:
            return 0.0
        age_hours = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
        if age_hours <= 24:
            return 0.03
        if age_hours <= 72:
            return 0.015
        if age_hours <= 168:
            return 0.008
        return 0.0

    def _sort_timestamp(self, ts: str) -> float:
        dt = parse_iso_utc(ts)
        if dt is None:
            return 0.0
        return float(dt.timestamp())

    def _conflict_priority(self, cluster: dict[str, Any]) -> float:
        tags = cluster.get("tags") or {}
        if isinstance(tags, dict) and "conflict_priority" in tags:
            try:
                return float(tags.get("conflict_priority") or 0.0)
            except (TypeError, ValueError):
                return 0.0
        priorities: list[float] = []
        for row in (cluster.get("conflicts") or []):
            if not isinstance(row, dict):
                continue
            try:
                priorities.append(float(row.get("priority") or 0.0))
            except (TypeError, ValueError):
                continue
        if not priorities:
            return 0.0
        return max(priorities)

    def _conflict_focus_bonus(self, query_text: str, cluster: dict[str, Any]) -> float:
        lowered = query_text.lower()
        if not any(token in lowered for token in _CONFLICT_TOKENS):
            return 0.0
        priority = self._conflict_priority(cluster)
        return min(0.25, 0.05 * priority)
