"""Plain data types shared by the fetching and writing stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Channel:
    """One entry of the Init7 channel line-up."""

    id: str
    """Stable identifier, e.g. ``SRF1.ch``. Used as XMLTV channel id and M3U tvg-id."""
    name: str
    """Human readable name, e.g. ``SRF 1``."""
    stream_url: str
    logo: str | None = None
    group: str | None = None
    """Language group as published by Init7 (``de``, ``fr``, ``it``, ...)."""


@dataclass(frozen=True, slots=True)
class Credit:
    role: str
    name: str


@dataclass(frozen=True, slots=True)
class Programme:
    channel_id: str
    start: datetime
    stop: datetime
    title: str
    sub_title: str | None = None
    description: str | None = None
    categories: tuple[str, ...] = ()
    credits: tuple[Credit, ...] = ()
    year: str | None = None
    country: str | None = None
    icon: str | None = None
    episode_num: str | None = None
    episode_num_system: str | None = None
    rating: str | None = None
    rating_system: str | None = None
    star_rating: str | None = None
    premiere: bool = False
    subtitles: bool = False
    language: str | None = field(default=None, compare=False)
    """Language hint for text elements (taken from the channel group)."""
