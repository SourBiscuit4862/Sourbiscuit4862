import textwrap
from pathlib import Path

import pytest

from dict_translator import DictionaryTranslator


def write_dictionary(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "sample.dict"
    path.write_text(textwrap.dedent(contents).strip() + "\n", encoding="utf-8")
    return path


def test_longest_match_phrase(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        good morning = PHRASE = buenos dias
        good = ADJ = bueno
        morning = NOUN = manana
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("good morning")
    assert result == "buenos dias"


def test_unknown_word_passthrough(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        hello = INTJ = hola
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("hello friend")
    assert result == "hola friend"


def test_punctuation_preserved(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        hello = INTJ = hola
        world = NOUN = mundo
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("hello, world!")
    assert result == "hola, mundo!"


def test_adjective_reordered(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        casa = NOUN = house
        roja = ADJ = red
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("casa roja")
    assert result == "red house"


def test_negation_rule(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        na = PART = not | negates_next=true
        correr = VERB = run
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("na correr")
    assert result == "not run"


def test_reverse_translation(tmp_path: Path):
    dictionary = write_dictionary(
        tmp_path,
        """
        hello = INTJ = hola/alo
        """,
    )
    translator = DictionaryTranslator(dictionary)
    result = translator.translate("hola", direction="reverse")
    assert result == "hello"
