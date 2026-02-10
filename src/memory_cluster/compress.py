from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable

from .embed import tokenize
from .models import ConflictRecord, MemoryCluster, MemoryFragment, utc_now_iso
from .preference import PreferenceDecision, PreferencePolicyEngine


KEY_VALUE_PATTERN = re.compile(r"([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]{0,32})\s*[:=：]\s*([^\s,;，；]{1,64})")
NEGATED_KEY_VALUE_PATTERN = re.compile(
    r"(?:不是|并非|不|非)\s*([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]{0,32})\s*[:=：]?\s*([^\s,;，；]{1,64})",
    re.IGNORECASE,
)
NEGATED_KEY_VALUE_EN_PATTERN = re.compile(
    r"\bnot\b\s*([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]{0,32})\s*[:=：]\s*([^\s,;，；]{1,64})",
    re.IGNORECASE,
)
NOT_EQUAL_PATTERN = re.compile(
    r"([A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]{0,32})\s*(?:!=|≠|不等于|is\s+not)\s*([^\s,;，；]{1,64})",
    re.IGNORECASE,
)
NEGATIVE_FLAG_PATTERN = re.compile(r"(?:不启用|未启用|禁用|关闭|不使用|不支持)\s*([A-Za-z0-9_\u4e00-\u9fff]{1,24})", re.IGNORECASE)
POSITIVE_FLAG_PATTERN = re.compile(r"(?:启用|开启|使用|支持)\s*([A-Za-z0-9_\u4e00-\u9fff]{1,24})", re.IGNORECASE)
NEGATIVE_FLAG_EN_PATTERN = re.compile(r"(?:disable|not\s+use|do\s+not\s+use)\s+([A-Za-z0-9_]{1,24})", re.IGNORECASE)
POSITIVE_FLAG_EN_PATTERN = re.compile(r"(?:enable|use)\s+([A-Za-z0-9_]{1,24})", re.IGNORECASE)
CONDITIONAL_SCOPE_PATTERN = re.compile(r"(?:如果|若|假如|当|if|when)\s+([^,;，；。]+)", re.IGNORECASE)
COUNTERFACTUAL_SCOPE_PATTERN = re.compile(
    r"(?:本应|本来|本该|理应|要是当时|如果当时|should\s+have|would\s+have)\s+([^,;，；。]+)",
    re.IGNORECASE,
)
CONDITIONAL_RESULT_MARKER_PATTERN = re.compile(r"(?:\bthen\b|->|=>|\u5219|\u90a3\u4e48)", re.IGNORECASE)
DOUBLE_NEGATION_PREFIX_PATTERN = re.compile(
    r"(?:\b(?:not|never|don't|dont|do\s+not)\s*$|(?:\u4e0d\u8981|\u522b|\u52ff|\u4e0d\u53ef|\u4e0d\u8be5|\u4e0d\u662f)\s*$)",
    re.IGNORECASE,
)
_EN_SLOT_COREFERENCE_ALIASES = {"it", "this", "that", "its", "this_setting", "that_setting"}
_ZH_SLOT_COREFERENCE_ALIASES = {
    "\u5b83",  # 它
    "\u5176",  # 其
    "\u8be5\u53c2\u6570",  # 该参数
    "\u8be5\u503c",  # 该值
    "\u8be5\u914d\u7f6e",  # 该配置
    "\u8be5\u6a21\u5f0f",  # 该模式
    "\u8be5\u9879",  # 该项
}
_SLOT_BLOCKLIST = {"if", "when", "then", "and", "or", "not", "true", "false"}
_FLAG_NAME_BLOCKLIST = {"if", "when", "then", "and", "or", "not", "do", "dont", "don't", "use"}
_TRAILING_VALUE_PUNCT = ".,;:!?，；。！？)]}）】>\"'"


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


def _clean_value(raw: str) -> str:
    text = (raw or "").strip()
    return text.rstrip(_TRAILING_VALUE_PUNCT)


def _collect_negated_matches(text: str) -> list[tuple[int, int, str, str]]:
    rows: list[tuple[int, int, str, str]] = []
    seen: set[tuple[int, int, str, str]] = set()
    for pattern in (NEGATED_KEY_VALUE_PATTERN, NEGATED_KEY_VALUE_EN_PATTERN, NOT_EQUAL_PATTERN):
        for match in pattern.finditer(text):
            item = (
                int(match.start()),
                int(match.end()),
                str(match.group(1) or ""),
                str(match.group(2) or ""),
            )
            if item in seen:
                continue
            seen.add(item)
            rows.append(item)
    rows.sort(key=lambda row: (row[0], row[1]))
    return rows


def _slice_conditional_scope(text: str) -> str:
    marker = CONDITIONAL_RESULT_MARKER_PATTERN.search(text or "")
    if not marker:
        return text
    return text[: marker.start()]


def _contains_double_negation_prefix(*, text: str, start: int, window: int = 16) -> bool:
    left = (text or "")[max(0, int(start) - max(1, int(window))) : max(0, int(start))]
    normalized = left.lower().replace("\u2019", "'")
    return bool(DOUBLE_NEGATION_PREFIX_PATTERN.search(normalized))


def _is_slot_alias(slot: str) -> bool:
    token = (slot or "").strip()
    if not token:
        return False
    lower = token.lower()
    return (lower in _EN_SLOT_COREFERENCE_ALIASES) or (token in _ZH_SLOT_COREFERENCE_ALIASES)


def _resolve_slot_name(raw_slot: str, previous_slot: str) -> str:
    token = (raw_slot or "").strip()
    if not token:
        return ""
    if _is_slot_alias(token):
        return previous_slot.strip()
    return token


def _is_valid_slot_name(slot: str) -> bool:
    token = (slot or "").strip()
    if not token:
        return False
    return token.lower() not in _SLOT_BLOCKLIST


def _extract_slot_values(fragment: MemoryFragment) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    content = fragment.content or ""
    masked_spans: list[tuple[int, int]] = []
    last_global_slot = ""

    def _in_masked_spans(start: int, end: int) -> bool:
        for left, right in masked_spans:
            if start >= left and end <= right:
                return True
        return False

    def _add_flag_pairs_from_text(
        text: str,
        *,
        offset: int = 0,
        slot_prefix: str = "",
        local_mask_spans: list[tuple[int, int]] | None = None,
    ) -> None:
        neg_spans: list[tuple[int, int]] = []
        for pattern in (NEGATIVE_FLAG_PATTERN, NEGATIVE_FLAG_EN_PATTERN):
            for match in pattern.finditer(text):
                start = offset + match.start()
                end = offset + match.end()
                if _in_masked_spans(start, end):
                    continue
                if _contains_double_negation_prefix(text=text, start=match.start()):
                    continue
                flag_name = match.group(1).strip().lower()
                if not flag_name or flag_name in _FLAG_NAME_BLOCKLIST:
                    continue
                pairs.append((f"{slot_prefix}flag:{flag_name}", "false"))
                neg_spans.append((start, end))

        for pattern in (POSITIVE_FLAG_PATTERN, POSITIVE_FLAG_EN_PATTERN):
            for match in pattern.finditer(text):
                start = offset + match.start()
                end = offset + match.end()
                if _in_masked_spans(start, end):
                    continue
                skip = False
                for left, right in neg_spans:
                    if start >= left and end <= right:
                        skip = True
                        break
                if skip:
                    continue
                flag_name = match.group(1).strip().lower()
                if not flag_name or flag_name in _FLAG_NAME_BLOCKLIST:
                    continue
                pairs.append((f"{slot_prefix}flag:{flag_name}", "true"))

        if local_mask_spans is not None:
            local_mask_spans.extend(neg_spans)

    for pattern, slot_prefix in (
        (CONDITIONAL_SCOPE_PATTERN, "cond:"),
        (COUNTERFACTUAL_SCOPE_PATTERN, "cf:"),
    ):
        for match in pattern.finditer(content):
            raw_scoped_text = match.group(1) or ""
            scoped_candidate = _slice_conditional_scope(raw_scoped_text) if slot_prefix == "cond:" else raw_scoped_text
            leading_ws = len(scoped_candidate) - len(scoped_candidate.lstrip())
            scoped_text = scoped_candidate.strip()
            if not scoped_text:
                continue
            scoped_span_start = match.start(1)
            scoped_span_start += leading_ws
            scoped_span_end = scoped_span_start + len(scoped_text)
            scoped_mask_spans: list[tuple[int, int]] = []
            last_scoped_slot = ""
            for neg_start, neg_end, raw_slot, raw_value in _collect_negated_matches(scoped_text):
                slot = _resolve_slot_name(raw_slot, last_scoped_slot)
                if not _is_valid_slot_name(slot):
                    continue
                value = _clean_value(raw_value)
                scoped_mask_spans.append((scoped_span_start + neg_start, scoped_span_start + neg_end))
                pairs.append((f"{slot_prefix}{slot}", f"!{value}"))
                last_scoped_slot = slot
            for scoped in KEY_VALUE_PATTERN.finditer(scoped_text):
                scoped_start = scoped_span_start + scoped.start()
                scoped_end = scoped_span_start + scoped.end()
                if _in_masked_spans(scoped_start, scoped_end):
                    continue
                slot = _resolve_slot_name(scoped.group(1), last_scoped_slot)
                if not _is_valid_slot_name(slot):
                    continue
                value = _clean_value(scoped.group(2))
                pairs.append((f"{slot_prefix}{slot}", value))
                last_scoped_slot = slot
            _add_flag_pairs_from_text(
                scoped_text,
                offset=scoped_span_start,
                slot_prefix=slot_prefix,
                local_mask_spans=scoped_mask_spans,
            )
            masked_spans.extend(scoped_mask_spans)
            masked_spans.append((scoped_span_start, scoped_span_end))

    for neg_start, neg_end, raw_slot, raw_value in _collect_negated_matches(content):
        if _in_masked_spans(neg_start, neg_end):
            continue
        slot = _resolve_slot_name(raw_slot, last_global_slot)
        if not _is_valid_slot_name(slot):
            continue
        value = _clean_value(raw_value)
        masked_spans.append((neg_start, neg_end))
        pairs.append((slot, f"!{value}"))
        last_global_slot = slot

    for match in KEY_VALUE_PATTERN.finditer(content):
        if _in_masked_spans(match.start(), match.end()):
            continue
        slot = _resolve_slot_name(match.group(1), last_global_slot)
        if not _is_valid_slot_name(slot):
            continue
        value = _clean_value(match.group(2))
        pairs.append((slot, value))
        last_global_slot = slot

    extra = fragment.meta.get("slots")
    if isinstance(extra, dict):
        for slot, value in extra.items():
            pairs.append((str(slot), str(value)))

    flags = fragment.meta.get("flags")
    if isinstance(flags, dict):
        for key, value in flags.items():
            normalized = "true" if bool(value) else "false"
            pairs.append((f"flag:{str(key).strip().lower()}", normalized))

    _add_flag_pairs_from_text(content)

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
