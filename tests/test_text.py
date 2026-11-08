import unicodedata

from tv7_epg.text import clean, single_line


def test_nfc_normalisation_composes_umlauts():
    decomposed = unicodedata.normalize("NFD", "Zürich Ångström façade")
    assert decomposed != "Zürich Ångström façade"
    assert clean(decomposed) == "Zürich Ångström façade"


def test_removes_xml_illegal_characters_but_keeps_text():
    assert clean("Fu\x00ß\x0bball\x1f – Ünïcödé ✓") == "Fußball – Ünïcödé ✓"


def test_keeps_newlines_in_clean_but_not_in_single_line():
    assert clean("  Line 1\nLine 2  ") == "Line 1\nLine 2"
    assert single_line("  Line 1\n\tLine 2  ") == "Line 1 Line 2"


def test_blank_values_become_none():
    assert clean(None) is None
    assert clean("   ") is None
    assert clean("\x00") is None


def test_non_string_values():
    assert clean(2024) == "2024"
