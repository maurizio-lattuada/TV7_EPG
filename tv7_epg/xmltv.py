"""XMLTV document generation (the guide format read by Kodi's IPTV Simple Client)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import UTC, datetime

from . import __version__
from .models import Channel, Programme

GENERATOR_URL = "https://github.com/maurizio-lattuada/TV7_EPG"

# Init7 groups channels mostly by language code, but a few groups use country
# codes. Map those to the ISO 639-1 language when it is unambiguous; groups that
# do not identify a language (e.g. "qa", which holds Al Jazeera *English*) get no
# lang attribute at all, because a wrong hint is worse than none.
_GROUP_TO_LANGUAGE: dict[str, str | None] = {
    "al": "sq",  # Albania -> Albanian
    "ba": "bs",  # Bosnia and Herzegovina -> Bosnian
    "gr": "el",  # Greece -> Greek
    "me": None,  # Montenegro: several languages
    "qa": None,  # Qatar: channels broadcast in English and Arabic
}

# Credit roles allowed by the XMLTV DTD, in the order the DTD requires them.
_CREDIT_ORDER = (
    "director",
    "actor",
    "writer",
    "adapter",
    "producer",
    "composer",
    "editor",
    "presenter",
    "commentator",
    "guest",
)
_CREDIT_ALIASES = {
    "author": "writer",
    "screenplay": "writer",
    "host": "presenter",
    "moderator": "presenter",
    "music": "composer",
}


def language_for_group(group: str | None) -> str | None:
    """Return a two letter language code for an Init7 channel group, if plausible."""
    if not group:
        return None
    code = group.strip().lower()
    code = _GROUP_TO_LANGUAGE.get(code, code)
    return code if code and len(code) == 2 and code.isalpha() else None


def format_time(value: datetime) -> str:
    """XMLTV timestamp, always expressed in UTC: ``YYYYMMDDhhmmss +0000``."""
    return value.astimezone(UTC).strftime("%Y%m%d%H%M%S %z")


def _text(parent: ET.Element, tag: str, text: str, lang: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, tag, {"lang": lang} if lang else {})
    element.text = text
    return element


def _channel_element(channel: Channel) -> ET.Element:
    element = ET.Element("channel", {"id": channel.id})
    _text(element, "display-name", channel.name, language_for_group(channel.group))
    if channel.logo:
        ET.SubElement(element, "icon", {"src": channel.logo})
    return element


def _programme_element(programme: Programme) -> ET.Element:
    lang = language_for_group(programme.language)
    element = ET.Element(
        "programme",
        {
            "start": format_time(programme.start),
            "stop": format_time(programme.stop),
            "channel": programme.channel_id,
        },
    )
    # Child order follows the XMLTV DTD.
    _text(element, "title", programme.title, lang)
    if programme.sub_title:
        _text(element, "sub-title", programme.sub_title, lang)
    if programme.description:
        _text(element, "desc", programme.description, lang)

    by_role: dict[str, list[str]] = {}
    for credit in programme.credits:
        role = _CREDIT_ALIASES.get(credit.role, credit.role)
        if role in _CREDIT_ORDER and credit.name not in by_role.setdefault(role, []):
            by_role[role].append(credit.name)
    if any(by_role.values()):
        credits = ET.SubElement(element, "credits")
        for role in _CREDIT_ORDER:
            for name in by_role.get(role, ()):
                _text(credits, role, name)

    if programme.year:
        _text(element, "date", programme.year)
    for category in programme.categories:
        _text(element, "category", category, "en")
    if programme.icon:
        ET.SubElement(element, "icon", {"src": programme.icon})
    if programme.country:
        _text(element, "country", programme.country)
    if programme.episode_num:
        _text(element, "episode-num", programme.episode_num).set(
            "system", programme.episode_num_system or "onscreen"
        )
    if programme.premiere:
        ET.SubElement(element, "premiere")
    if programme.subtitles:
        ET.SubElement(element, "subtitles")
    if programme.rating:
        rating = ET.SubElement(
            element, "rating", {"system": programme.rating_system} if programme.rating_system else {}
        )
        _text(rating, "value", programme.rating)
    if programme.star_rating:
        _text(ET.SubElement(element, "star-rating"), "value", programme.star_rating)
    return element


def render_xmltv(channels: Iterable[Channel], programmes: Iterable[Programme]) -> bytes:
    """Return the complete XMLTV document as UTF-8 encoded bytes."""
    root = ET.Element(
        "tv",
        {
            "generator-info-name": f"tv7-epg/{__version__}",
            "generator-info-url": GENERATOR_URL,
            "source-info-name": "Init7 TV7",
            "source-info-url": "https://www.init7.net/",
        },
    )
    root.extend(_channel_element(channel) for channel in channels)
    root.extend(_programme_element(programme) for programme in programmes)
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
        f"{body}\n"
    )
    return document.encode("utf-8")
