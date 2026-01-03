# Dictionary-Driven Translator

This project provides a generic, dictionary-driven translator that works with dictionary files in the form:

```
source_phrase = part_of_speech = target_text | optional metadata/example
```

- Multi-word phrases are supported for both source and target.
- Gloss variants are separated by `/` in the `target_text` field.
- Metadata after `|` uses `key=value` pairs separated by `;` (e.g., `negates_next=true; example=foo`).

## Files
- `dict_translator.py` — main translation logic and dictionary parsing.
- `rules.py` — sentence-structure adjustments applied after literal translation.
- `tests/test_translator.py` — unit tests for phrase matching, unknown word handling, punctuation safety, structure rules, and reverse translation.

## Usage
```python
from pathlib import Path
from dict_translator import DictionaryTranslator

translator = DictionaryTranslator(Path("./my_dictionary.txt"))
print(translator.translate("good morning"))  # => translated text
print(translator.translate("hola", direction="reverse"))  # reverse lookup
```

## Structure Rules
Two example rules are provided and can be extended:
1. **Adjective-before-noun reorder**: sequences tagged `NOUN ADJ` are reordered to `ADJ NOUN`.
2. **Negation metadata**: tokens with metadata `negates_next=true` inject a `not` before the following token.

## Running Tests
```
python -m pytest
```

## Dictionary Format Notes
- Lines starting with `#` or blank lines are ignored.
- Tokens are matched using longest-phrase first logic.
- Punctuation is tokenized and reattached safely during detokenization.
- Unknown words are passed through unchanged with POS set to `UNK`.
