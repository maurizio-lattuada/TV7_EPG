"""Reading the Init7 channel line-up (M3U) and writing a Kodi-ready playlist."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Iterable

from .models import Channel
from .text import single_line

log = logging.getLogger(__name__)

_ATTRIBUTE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
_NON_ID_CHARS = re.compile(r"[^0-9A-Za-z.]+")


def _parse_extinf(line: str) -> tuple[dict[str, str], str]:
    """Split ``#EXTINF:<duration> key="value" ..., Display Name``."""
    header = line.removeprefix("#EXTINF:")
    # The display name follows the first comma that is not inside a quoted value.
    in_quotes = False
    for index, char in enumerate(header):
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            attributes_part, name = header[:index], header[index + 1 :]
            break
    else:
        attributes_part, name = header, ""
    attributes = {key.lower(): value for key, value in _ATTRIBUTE.findall(attributes_part)}
    return attributes, name.strip()


def _fallback_id(name: str) -> str:
    """Derive an ASCII id from a display name, e.g. ``TRT Türk`` -> ``TRTTurk``."""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _NON_ID_CHARS.sub("", ascii_only) or "channel"


def parse_m3u(content: str) -> list[Channel]:
    """Parse an extended M3U playlist into channels, keeping the playlist order.

    Entries without a stream URL are ignored; duplicate ids keep the first entry.
    """
    channels: list[Channel] = []
    seen: set[str] = set()
    pending: tuple[dict[str, str], str] | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip().lstrip("﻿")
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            pending = _parse_extinf(line)
            continue
        if line.startswith("#"):
            continue
        if pending is None:
            continue

        attributes, display_name = pending
        pending = None
        name = single_line(display_name) or single_line(attributes.get("tvg-name")) or line
        channel_id = (
            single_line(attributes.get("tvg-id"))
            or single_line(attributes.get("tvg-name"))
            or _fallback_id(name)
        )
        if channel_id in seen:
            log.warning("Skipping duplicate channel id %s (%s)", channel_id, name)
            continue
        seen.add(channel_id)
        channels.append(
            Channel(
                id=channel_id,
                name=name,
                stream_url=line,
                logo=single_line(attributes.get("tvg-logo")),
                group=single_line(attributes.get("group-title")),
            )
        )
    return channels


def _attr(value: str) -> str:
    # M3U has no escaping mechanism; double quotes would end the attribute.
    return value.replace('"', "'")


def render_m3u(channels: Iterable[Channel], guide_url: str | None = None) -> str:
    """Render a playlist whose ``tvg-id`` values match the XMLTV channel ids."""
    header = "#EXTM3U"
    if guide_url:
        header += f' url-tvg="{_attr(guide_url)}" x-tvg-url="{_attr(guide_url)}"'
    lines = [header]
    for channel in channels:
        attributes = [f'tvg-id="{_attr(channel.id)}"', f'tvg-name="{_attr(channel.name)}"']
        if channel.logo:
            attributes.append(f'tvg-logo="{_attr(channel.logo)}"')
        if channel.group:
            attributes.append(f'group-title="{_attr(channel.group)}"')
        # Commas are fine in the display name: everything after the first one is the name.
        lines.append(f"#EXTINF:-1 {' '.join(attributes)},{channel.name}")
        lines.append(channel.stream_url)
    return "\n".join(lines) + "\n"
