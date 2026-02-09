from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable

from .embed import tokenize
from .models import ConflictRecord, MemoryCluster, MemoryFragment, utc_now_iso
from .preference import PreferenceDecision, PreferencePolicyEngine


KEY_VALUE_PATTERN = re.compile(r"([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]{0,32})\s*[:=：]\s*([^\s,;，；]{1,64})")
NEGATIVE_FLAG_PATTERN = re.compile(r"(?:不启用|未启用|禁用|关闭|不使用|不支持)\s*([A-Za-z0-9_\u4e00-\u9fff]{1,24})", re.IGNORECASE)
POSITIVE_FLAG_PATTERN = re.compile(r"(?:启用|开启|使用|支持)\s*([A-Za-z0-9_\u4e00-\u9fff]{1,24})", re.IGNORECASE)
NEGATIVE_FLAG_EN_PATTERN = re.compile(r"(?:disable|not\s+use|do\s+not\s+use)\s+([A-Za-z0-9_]{1,24})", re.IGNORECASE)
POSITIVE_FLAG_EN_PATTERN = re.compile(r"(?:enable|use)\s+([A-Za-z0-9_]{1,24})", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _token_jaccard(tokens_a: Iterable[str], tokens_b: Iterable[str]) -> float:
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    if union == 0:
        return 0.0
    return inter / union


def _extract_slot_values(fragment: MemoryFragment) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    content = fragment.content or ""

    for match in KEY_VALUE_PATTERN.finditer(content):
        slot = match.group(1).strip()
        value = match.group(2).strip()
        pairs.append((slot, value))

    extra = fragment.meta.get("slots")
    if isinstance(extra, dict):
        for slot, value in extra.items():
            pairs.append((str(slot), str(value)))

    flags = fragment.meta.get("flags")
    if isinstance(flags, dict):
        for key, value in flags.items():
            normalized = "true" if bool(value) else "false"
            pairs.append((f"flag:{str(key).strip().lower()}", normalized))

    for match in NEGATIVE_FLAG_PATTERN.finditer(content):
        flag_name = match.group(1).strip().lower()
        pairs.append((f"flag:{flag_name}", "false"))
    for match in NEGATIVE_FLAG_EN_PATTERN.finditer(content):
        flag_name = match.group(1).strip().lower()
        pairs.append((f"flag:{flag_name}", "false"))

    for match in POSITIVE_FLAG_PATTERN.finditer(content):
        flag_name = match.group(1).strip().lower()
        pairs.append((f"flag:{flag_name}", "true"))
    for match in POSITIVE_FLAG_EN_PATTERN.finditer(content):
        flag_name = match.group(1).strip().lower()
        pairs.append((f"flag:{flag_name}", "true"))

    return pairs


class ClusterCompressor:
    """Compress cluster members with consensus + conflict preservation."""

    def __init__(self, semantic_dedup_threshold: float = 0.88, strict_conflict_split: bool = False) -> None:
        self.semantic_dedup_threshold = semantic_dedup_threshold
        self.strict_conflict_split = strict_conflict_split

    def compress(
        self,
        cluster: MemoryCluster,
        fragments: list[MemoryFragment],
        policy_engine: PreferencePolicyEngine,
        decisions: dict[str, PreferenceDecision],
    ) -> MemoryCluster:
        unique_fragments = self._deduplicate(fragments)
        unique_fragments.sort(key=lambda item: item.timestamp)
        cluster.backrefs = [item.id for item in unique_fragments]

        slot_values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        slot_events: dict[str, list[dict[str, str]]] = defaultdict(list)
        for fragment in unique_fragments:
            for slot, value in _extract_slot_values(fragment):
                slot_values[slot][value].append(fragment.id)
                slot_events[slot].append(
                    {
                        "timestamp": fragment.timestamp,
                        "fragment_id": fragment.id,
                        "value": value,
                        "agent_id": fragment.agent_id,
                    }
                )

        conflict_graph: dict[str, Any] = {}
        if policy_engine.enable_conflict_graph():
            conflict_graph = self._build_conflict_graph(slot_values=slot_values, slot_events=slot_events)

        conflicts: list[ConflictRecord] = []
        consensus: dict[str, str] = {}
        for slot, values in slot_values.items():
            if len(values) == 1:
                only_value = next(iter(values.keys()))
                consensus[slot] = only_value
                continue
            if policy_engine.should_keep_conflicts():
                evidences = sorted({frag_id for ids in values.values() for frag_id in ids})
                graph_meta = conflict_graph.get(slot) if isinstance(conflict_graph, dict) else {}
                conflicts.append(
                    ConflictRecord(
                        slot=slot,
                        values=sorted(values.keys()),
                        evidences=evidences,
                        last_seen=utc_now_iso(),
                        priority=float((graph_meta or {}).get("priority") or 0.0),
                        dominant_value=str((graph_meta or {}).get("dominant_value") or ""),
                        transition_count=int((graph_meta or {}).get("transition_count") or 0),
                    )
                )

        split_groups: list[dict[str, str | list[str]]] = []
        if self.strict_conflict_split and conflicts:
            split_groups = self._build_split_groups(slot_values=slot_values, conflicts=conflicts)

        fragment_decisions = [decisions[item.id] for item in unique_fragments if item.id in decisions]
        strength = policy_engine.pick_cluster_strength(fragment_decisions)
        detail_budget = policy_engine.cluster_budget(
            strength=strength,
            fragment_decisions=fragment_decisions,
            conflict_count=len(conflicts),
            source_distribution=cluster.source_distribution,
            fragment_count=len(unique_fragments),
        )
        summary = self._build_summary(
            cluster_id=cluster.cluster_id,
            unique_fragments=unique_fragments,
            consensus=consensus,
            conflicts=conflicts,
            conflict_graph=conflict_graph,
            split_groups=split_groups,
            strength=strength,
            detail_budget=detail_budget,
            include_trace_refs=policy_engine.config.enable_adaptive_budget,
        )

        cluster.consensus = consensus
        cluster.conflicts = conflicts
        cluster.conflict_graph = conflict_graph
        cluster.split_groups = split_groups
        cluster.summary = summary
        cluster.tags["retention_strength"] = strength
        cluster.tags["detail_budget"] = detail_budget
        cluster.tags["budget_policy"] = "adaptive" if policy_engine.config.enable_adaptive_budget else "static"
        cluster.tags["conflict_priority"] = round(max((item.priority for item in conflicts), default=0.0), 6)
        if split_groups:
            cluster.tags["split_recommended"] = True
        cluster.last_updated = utc_now_iso()
        cluster.version += 1
        return cluster

    def _deduplicate(self, fragments: list[MemoryFragment]) -> list[MemoryFragment]:
        seen_text: set[str] = set()
        seen_tokens: list[set[str]] = []
        output: list[MemoryFragment] = []
        for fragment in fragments:
            key = _normalize_text(fragment.content)
            if not key:
                key = fragment.id
            token_set = set(tokenize(fragment.content or ""))

            if key in seen_text:
                continue

            semantic_duplicate = False
            for existing in seen_tokens:
                score = _token_jaccard(token_set, existing)
                if score >= self.semantic_dedup_threshold:
                    semantic_duplicate = True
                    break
            if semantic_duplicate:
                continue

            seen_text.add(key)
            seen_tokens.append(token_set)
            output.append(fragment)
        return output

    def _build_split_groups(
        self,
        slot_values: dict[str, dict[str, list[str]]],
        conflicts: list[ConflictRecord],
    ) -> list[dict[str, str | list[str]]]:
        if not conflicts:
            return []
        anchor_slot = conflicts[0].slot
        value_map = slot_values.get(anchor_slot, {})
        groups: list[dict[str, str | list[str]]] = []
        for value, fragment_ids in sorted(value_map.items(), key=lambda x: x[0]):
            groups.append(
                {
                    "slot": anchor_slot,
                    "value": value,
                    "fragment_ids": sorted(set(fragment_ids)),
                }
            )
        return groups

    def _build_summary(
        self,
        cluster_id: str,
        unique_fragments: list[MemoryFragment],
        consensus: dict[str, str],
        conflicts: list[ConflictRecord],
        conflict_graph: dict[str, Any],
        split_groups: list[dict[str, str | list[str]]],
        strength: str,
        detail_budget: int,
        include_trace_refs: bool,
    ) -> str:
        consensus_count = len(consensus)
        conflict_count = len(conflicts)
        parts = [f"id={cluster_id}", f"n={len(unique_fragments)}", f"s={strength}", f"cons={consensus_count}"]
        if conflict_count:
            conflict_items = []
            for conflict in conflicts[:1]:
                options = "/".join(conflict.values[:3])
                conflict_items.append(f"{conflict.slot}:{options}")
            parts.append("conf=" + ";".join(conflict_items))
        else:
            parts.append("conf=0")
        if split_groups:
            parts.append(f"split={len(split_groups)}")
        if conflict_graph:
            parts.append(f"ceg={len(conflict_graph)}")

        payload = ";".join(parts)
        if len(payload) >= detail_budget:
            return payload[: max(0, detail_budget - 3)] + "..."

        if not include_trace_refs:
            return payload

        # Fill remaining budget with traceable snippets.
        refs: list[str] = []
        for fragment in unique_fragments:
            snippet = (fragment.content or "").replace("\n", " ").strip()
            if len(snippet) > 28:
                snippet = snippet[:25] + "..."
            candidate = payload + ";refs=" + "|".join(refs + [f"{fragment.id}:{snippet}"])
            if len(candidate) > detail_budget:
                break
            refs.append(f"{fragment.id}:{snippet}")

        if refs:
            return payload + ";refs=" + "|".join(refs)
        return payload

    def _build_conflict_graph(
        self,
        slot_values: dict[str, dict[str, list[str]]],
        slot_events: dict[str, list[dict[str, str]]],
    ) -> dict[str, Any]:
        graph: dict[str, Any] = {}
        for slot, value_map in slot_values.items():
            if len(value_map) <= 1:
                continue
            events = sorted(slot_events.get(slot) or [], key=lambda row: row.get("timestamp") or "")
            nodes: list[dict[str, Any]] = []
            node_lookup: dict[str, dict[str, Any]] = {}
            for value, evidences in value_map.items():
                node = {
                    "value": value,
                    "evidence_count": len(set(evidences)),
                    "evidences": sorted(set(evidences)),
                    "sources": [],
                    "last_seen": "",
                }
                node_lookup[value] = node
                nodes.append(node)

            edges: list[dict[str, str]] = []
            previous_value = ""
            for event in events:
                value = str(event.get("value") or "")
                if value not in node_lookup:
                    continue
                node = node_lookup[value]
                agent_id = str(event.get("agent_id") or "")
                if agent_id and agent_id not in node["sources"]:
                    node["sources"].append(agent_id)
                node["last_seen"] = str(event.get("timestamp") or node["last_seen"])

                if previous_value and previous_value != value:
                    edges.append(
                        {
                            "from": previous_value,
                            "to": value,
                            "fragment_id": str(event.get("fragment_id") or ""),
                            "timestamp": str(event.get("timestamp") or ""),
                            "kind": "switch",
                        }
                    )
                previous_value = value

            dominant_value = ""
            dominant_count = -1
            for node in nodes:
                count = int(node.get("evidence_count") or 0)
                if count > dominant_count:
                    dominant_count = count
                    dominant_value = str(node.get("value") or "")

            transition_count = len(edges)
            evidence_count = len({e for evidences in value_map.values() for e in evidences})
            priority = round((len(value_map) * 2.0) + (transition_count * 1.2) + (evidence_count * 0.3), 3)
            graph[slot] = {
                "nodes": nodes,
                "edges": edges,
                "transition_count": transition_count,
                "dominant_value": dominant_value,
                "priority": priority,
            }
        return graph
