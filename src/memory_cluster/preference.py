from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

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

    def should_keep_conflicts(self) -> bool:
        return bool(self.config.keep_conflicts)

    def strict_conflict_split(self) -> bool:
        return bool(self.config.strict_conflict_split)

    def _is_stale(self, ts: str) -> bool:
        age = datetime.now(timezone.utc) - _parse_iso(ts)
        hours = age.total_seconds() / 3600.0
        return hours > self.config.stale_after_hours
