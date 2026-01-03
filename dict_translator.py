from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional


@dataclass
class DictionaryEntry:
    source_phrase: str
    part_of_speech: str
    target_text: str
    metadata: Dict[str, str]

    @property
    def normalized_source_tokens(self) -> Tuple[str, ...]:
        return tuple(self._tokenize(self.source_phrase, lower=True))

    def normalized_target_variants(self) -> List[Tuple[str, ...]]:
        return [tuple(self._tokenize(variant, lower=True)) for variant in self.target_text.split("/")]

    def raw_target_variants(self) -> List[Tuple[str, ...]]:
        return [tuple(self._tokenize(variant, lower=False)) for variant in self.target_text.split("/")]

    @staticmethod
    def _tokenize(phrase: str, lower: bool = True) -> List[str]:
        if not phrase.strip():
            return []
        tokens = [token.strip() for token in phrase.strip().split()]
        return [token.lower() if lower else token for token in tokens]


class DictionaryTranslator:
    """Dictionary driven translator supporting forward and reverse modes."""

    def __init__(self, dictionary_path: Path):
        self.dictionary_path = Path(dictionary_path)
        self.forward_map: Dict[Tuple[str, ...], List[DictionaryEntry]] = {}
        self.reverse_map: Dict[Tuple[str, ...], List[DictionaryEntry]] = {}
        self.max_forward_key_len = 0
        self.max_reverse_key_len = 0
        self._load_dictionary()

    def _load_dictionary(self) -> None:
        entries = list(self._parse_dictionary(self.dictionary_path))
        for entry in entries:
            self._index_entry(entry)

    @staticmethod
    def _parse_dictionary(path: Path) -> Iterable[DictionaryEntry]:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            body, meta = (stripped.split("|", 1) + [""])[:2]
            parts = [part.strip() for part in body.split("=", 2)]
            if len(parts) < 3:
                raise ValueError(f"Invalid dictionary line: {line}")
            source_phrase, part_of_speech, target_text = parts
            metadata: Dict[str, str] = {}
            if meta.strip():
                metadata = DictionaryTranslator._parse_metadata(meta)
            entry = DictionaryEntry(
                source_phrase=source_phrase,
                part_of_speech=part_of_speech,
                target_text=target_text,
                metadata=metadata,
            )
            yield entry

    @staticmethod
    def _parse_metadata(meta: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for pair in meta.split(";"):
            if not pair.strip():
                continue
            if "=" not in pair:
                continue
            key, value = [segment.strip() for segment in pair.split("=", 1)]
            result[key] = value
        return result

    def _index_entry(self, entry: DictionaryEntry) -> None:
        key = entry.normalized_source_tokens
        if not key:
            return
        self.forward_map.setdefault(key, []).append(entry)
        self.max_forward_key_len = max(self.max_forward_key_len, len(key))

        for variant in entry.normalized_target_variants():
            if not variant:
                continue
            reverse_entry = DictionaryEntry(
                source_phrase=" ".join(variant),
                part_of_speech=entry.part_of_speech,
                target_text=entry.source_phrase,
                metadata=entry.metadata,
            )
            rev_key = variant
            self.reverse_map.setdefault(rev_key, []).append(reverse_entry)
            self.max_reverse_key_len = max(self.max_reverse_key_len, len(rev_key))

    WORD_RE = re.compile(r"[\w']+|[^\w\s]")

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        return cls.WORD_RE.findall(text)

    @staticmethod
    def detokenize(tokens: List[str]) -> str:
        output: List[str] = []
        for i, tok in enumerate(tokens):
            if i == 0:
                output.append(tok)
                continue
            if re.match(r"[^\w\s]", tok):
                output[-1] = output[-1].rstrip()
                output.append(tok)
            elif output[-1].endswith("'"):
                output.append(tok)
            else:
                output.append(" " + tok)
        return "".join(output)

    def translate(self, text: str, direction: str = "forward") -> str:
        annotated_tokens = self.translate_tokens(text, direction=direction)
        return self.detokenize([t["text"] for t in annotated_tokens])

    def translate_tokens(self, text: str, direction: str = "forward") -> List[Dict[str, Optional[str]]]:
        tokens = self.tokenize(text)
        lower_tokens = [tok.lower() for tok in tokens]
        output: List[Dict[str, Optional[str]]] = []
        i = 0
        key_map = self.forward_map if direction == "forward" else self.reverse_map
        max_len = self.max_forward_key_len if direction == "forward" else self.max_reverse_key_len
        while i < len(tokens):
            tok = tokens[i]
            if re.match(r"[^\w\s]", tok):
                output.append({"text": tok, "pos": None, "metadata": {}})
                i += 1
                continue
            match_len, entry = self._find_longest_match(lower_tokens, i, key_map, max_len)
            if entry is None:
                output.append({"text": tok, "pos": "UNK", "metadata": {}})
                i += 1
                continue
            variant_tokens = self._select_variant(entry, direction=direction)
            for variant_token in variant_tokens:
                output.append({"text": variant_token, "pos": entry.part_of_speech, "metadata": entry.metadata})
            i += match_len
        from rules import apply_structure_rules

        return apply_structure_rules(output, direction=direction)

    def _find_longest_match(
        self,
        tokens: List[str],
        start_idx: int,
        key_map: Dict[Tuple[str, ...], List[DictionaryEntry]],
        max_len: int,
    ) -> Tuple[int, Optional[DictionaryEntry]]:
        for size in range(max_len, 0, -1):
            window = tuple(tokens[start_idx : start_idx + size])
            if len(window) != size:
                continue
            if window in key_map:
                return size, key_map[window][0]
        return 0, None

    def _select_variant(self, entry: DictionaryEntry, direction: str = "forward") -> Tuple[str, ...]:
        metadata = entry.metadata or {}
        key = "preferred_variant" if direction == "forward" else "reverse_variant"
        chosen_index: Optional[int] = None
        if key in metadata:
            try:
                idx = int(metadata[key])
                if idx >= 1:
                    chosen_index = idx - 1
            except ValueError:
                chosen_index = None
        variants = entry.raw_target_variants()
        if chosen_index is not None and chosen_index < len(variants):
            return variants[chosen_index]
        return variants[0] if variants else tuple()
