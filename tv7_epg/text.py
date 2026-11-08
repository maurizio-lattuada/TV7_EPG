"""Text clean-up so that every string is valid in XML 1.0 and in M3U lines."""

from __future__ import annotations

import re
import unicodedata

# Characters that XML 1.0 does not allow at all, even escaped: C0 controls except
# TAB/LF/CR, lone surrogates and the two non-characters U+FFFE / U+FFFF.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")
_WHITESPACE_RUN = re.compile(r"\s+")


def clean(value: object) -> str | None:
    """Normalise a value coming from the API into display text.

    * converts to ``str`` and applies Unicode NFC, so that e.g. an ``ü`` sent as
      ``u`` + combining diaeresis becomes the single precomposed character,
    * drops characters that would make the XML document invalid,
    * trims surrounding whitespace.

    Returns ``None`` for missing or blank values so callers can skip the element.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value))
    text = _XML_ILLEGAL.sub("", text).strip()
    return text or None


def single_line(value: object) -> str | None:
    """Like :func:`clean`, but collapses all whitespace (incl. newlines) to one space."""
    text = clean(value)
    if text is None:
        return None
    return _WHITESPACE_RUN.sub(" ", text)
