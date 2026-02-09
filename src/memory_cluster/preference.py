from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math

from .models import MemoryFragment, PreferenceConfig


def _parse_iso(ts: str) -> datetime:
    raw = (ts or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class PreferenceDecision:
    strength: str
    detail_budget: int
    source_weight: float
    stale: bool
    reasons: list[str] = field(default_factory=list)


class PreferencePolicyEngine:
    """
    Convert user preference config to retention policy decisions.

    Strength levels:
    - strong
    - weak
    - discardable
    """

    _ORDER = ("discardable", "weak", "strong")

    def __init__(self, config: PreferenceConfig) -> None:
        self.config = config

    def decide_for_fragment(self, fragment: MemoryFragment) -> PreferenceDecision:
        category = str(fragment.tags.get("category") or "general")
        strength = self.config.category_strength.get(category, "weak")
        reasons = [f"category={category}:{strength}"]

        if self._is_protected_fragment(fragment):
            if strength != "strong":
                strength = "strong"
                reasons.append("protected fragment forces strong retention")
            else:
                reasons.append("protected fragment keeps strong retention")

        source_weight = float(self.config.source_weight.get(fragment.agent_id, 1.0))
        if source_weight >= self.config.source_promote_threshold and strength == "weak":
            strength = "strong"
            reasons.append("source_weight promotes weak->strong")
        elif source_weight < self.config.source_demote_threshold and strength == "strong":
            strength = "weak"
            reasons.append("source_weight demotes strong->weak")

        stale = self._is_stale(fragment.timestamp)
        if stale and strength == "strong":
            strength = "weak"
            reasons.append("staleness demotes strong->weak")
        elif stale and strength == "weak":
            strength = "discardable"
            reasons.append("staleness demotes weak->discardable")

        detail_budget = int(self.config.detail_budget.get(strength, 350))
        return PreferenceDecision(
            strength=strength,
            detail_budget=detail_budget,
            source_weight=source_weight,
            stale=stale,
            reasons=reasons,
        )

    def pick_cluster_strength(self, fragment_decisions: list[PreferenceDecision]) -> str:
        if not fragment_decisions:
            return "weak"
        level = max(self._ORDER.index(item.strength) for item in fragment_decisions)
        return self._ORDER[level]

    def detail_budget_for_strength(self, strength: str) -> int:
        return int(self.config.detail_budget.get(strength, 350))

    def cluster_budget(
        self,
        strength: str,
        fragment_decisions: list[PreferenceDecision],
        conflict_count: int,
        source_distribution: dict[str, int],
        fragment_count: int,
    ) -> int:
        base_budget = self.detail_budget_for_strength(strength)
        if not self.config.enable_adaptive_budget:
            return base_budget

        conflict_density = float(conflict_count) / float(max(1, fragment_count))
        source_entropy = _normalized_entropy(source_distribution)
        stale_ratio = 0.0
        if fragment_decisions:
            stale_ratio = sum(1 for item in fragment_decisions if item.stale) / float(len(fragment_decisions))

        scale = (
            1.0
            + self.config.arb_conflict_weight * conflict_density
            + self.config.arb_entropy_weight * source_entropy
            - self.config.arb_stale_penalty * stale_ratio
        )
        scale = max(float(self.config.arb_min_scale), min(float(self.config.arb_max_scale), scale))
        return max(64, int(round(base_budget * scale)))

    def should_keep_conflicts(self) -> bool:
        return bool(self.config.keep_conflicts)

    def strict_conflict_split(self) -> bool:
        return bool(self.config.strict_conflict_split)

    def enable_conflict_graph(self) -> bool:
        return bool(self.config.enable_conflict_graph)

    def enable_dual_merge_guard(self) -> bool:
        return bool(self.config.enable_dual_merge_guard)

    def merge_conflict_compat_threshold(self) -> float:
        return float(self.config.merge_conflict_compat_threshold)

    def _is_stale(self, ts: str) -> bool:
        age = datetime.now(timezone.utc) - _parse_iso(ts)
        hours = age.total_seconds() / 3600.0
        return hours > self.config.stale_after_hours

    def _is_protected_fragment(self, fragment: MemoryFragment) -> bool:
        tags = fragment.tags or {}
        for tag in self.config.hard_keep_tags:
            if tag in tags:
                return True

        scope = str(tags.get("scope") or "")
        if scope and scope in set(self.config.protected_scopes):
            return True

        file_path = str(fragment.meta.get("file_path") or "")
        if not file_path:
            return False
        normalized = file_path.replace("\\", "/")
        for prefix in self.config.protected_path_prefixes:
            p = str(prefix).replace("\\", "/")
            if p and normalized.startswith(p):
                return True
        return False


def _normalized_entropy(source_distribution: dict[str, int]) -> float:
    values = [max(0, int(v)) for v in source_distribution.values() if int(v) > 0]
    total = sum(values)
    if total <= 0 or len(values) <= 1:
        return 0.0
    entropy = 0.0
    for value in values:
        p = value / float(total)
        entropy -= p * math.log(p + 1e-12)
    max_entropy = math.log(len(values))
    if max_entropy <= 0:
        return 0.0
    return max(0.0, min(1.0, entropy / max_entropy))
