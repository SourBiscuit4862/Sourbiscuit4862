from __future__ import annotations

from typing import Dict, List


def apply_structure_rules(tokens: List[Dict], direction: str = "forward") -> List[Dict]:
    tokens = _adjective_before_noun(tokens)
    tokens = _apply_negation_rule(tokens)
    return tokens


def _adjective_before_noun(tokens: List[Dict]) -> List[Dict]:
    output: List[Dict] = []
    i = 0
    while i < len(tokens):
        current = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt and current.get("pos") == "NOUN" and nxt.get("pos") == "ADJ":
            output.append(nxt)
            output.append(current)
            i += 2
            continue
        output.append(current)
        i += 1
    return output


def _apply_negation_rule(tokens: List[Dict]) -> List[Dict]:
    output: List[Dict] = []
    i = 0
    while i < len(tokens):
        current = tokens[i]
        metadata = current.get("metadata", {}) or {}
        if metadata.get("negates_next", "").lower() == "true" and i + 1 < len(tokens):
            next_token = tokens[i + 1]
            output.append({"text": "not", "pos": "NEG", "metadata": metadata})
            output.append(next_token)
            i += 2
            continue
        output.append(current)
        i += 1
    return output
