"""HTTP access to the Init7 TV7 services."""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any

from . import __version__
from .models import Channel, Credit, Programme
from .text import clean, single_line

log = logging.getLogger(__name__)

PLAYLIST_URL = "https://api.init7.net/tvchannels.m3u"
EPG_URL = "https://api.tv.init7.net/api/epg/"
USER_AGENT = f"tv7-epg/{__version__} (+https://github.com/maurizio-lattuada/TV7_EPG)"

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_PAGE_SIZE = 1000


class FetchError(RuntimeError):
    """Raised when a resource could not be downloaded after all retries."""

    def __init__(self, message: str, *, status: int | None = None, body: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        """HTTP status code, if the server answered at all."""
        self.body = body
        """Start of the error response body, useful for diagnostics."""


def _error_body(error: urllib.error.HTTPError, limit: int = 500) -> str | None:
    try:
        raw = error.read(limit)
    except Exception:  # the body is best-effort diagnostics only
        return None
    text = raw.decode("utf-8", errors="replace").strip()
    return " ".join(text.split()) or None


class Init7Client:
    def __init__(
        self,
        *,
        timeout: float = 60.0,
        retries: int = 4,
        backoff: float = 2.0,
        epg_url: str = EPG_URL,
        playlist_url: str = PLAYLIST_URL,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.epg_url = epg_url
        self.playlist_url = playlist_url

    # -- low level -----------------------------------------------------------------

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*"}
        )
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 2):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as error:
                if error.code not in _RETRYABLE_STATUS:
                    raise FetchError(
                        f"GET {url} failed with HTTP {error.code}",
                        status=error.code,
                        body=_error_body(error),
                    ) from error
                last_error = error
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                last_error = error
            if attempt <= self.retries:
                delay = self.backoff * 2 ** (attempt - 1) + random.uniform(0, 1)
                log.debug("GET %s failed (%s), retry %d in %.1fs", url, last_error, attempt, delay)
                time.sleep(delay)
        raise FetchError(f"GET {url} failed after {self.retries + 1} attempts: {last_error}")

    def _get_json(self, url: str) -> Any:
        try:
            return json.loads(self._get(url).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FetchError(f"GET {url} returned invalid JSON: {error}") from error

    # -- public API ----------------------------------------------------------------

    def fetch_playlist(self) -> str:
        return self._get(self.playlist_url).decode("utf-8-sig")

    def iter_epg_items(self, channel_id: str) -> Iterator[Mapping[str, Any]]:
        """Yield the raw EPG entries of one channel, following pagination."""
        query = urllib.parse.urlencode({"channel__canonical_name": channel_id, "limit": _PAGE_SIZE})
        url: str | None = f"{self.epg_url}?{query}"
        allowed_host = urllib.parse.urlsplit(self.epg_url).netloc
        while url:
            page = self._get_json(url)
            yield from page.get("results") or ()
            url = page.get("next")
            if url and urllib.parse.urlsplit(url).netloc != allowed_host:
                raise FetchError(f"Unexpected pagination link {url!r}")

    def fetch_programmes(self, channel: Channel) -> list[Programme]:
        programmes = []
        for item in self.iter_epg_items(channel.id):
            programme = programme_from_api(item, channel)
            if programme is not None:
                programmes.append(programme)
        return programmes


# -- conversion ------------------------------------------------------------------------


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _first_icon(icons: object) -> str | None:
    if not isinstance(icons, list):
        return None
    for icon in icons:
        if isinstance(icon, Mapping):
            icon = icon.get("src") or icon.get("url")
        url = single_line(icon)
        if url and url.startswith(("http://", "https://")):
            return url
    return None


def _credits(raw: object) -> tuple[Credit, ...]:
    if not isinstance(raw, list):
        return ()
    result = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            continue
        role = single_line(entry.get("position"))
        name = single_line(entry.get("name"))
        if role and name:
            result.append(Credit(role=role.lower(), name=name))
    return tuple(result)


def _year(raw: object) -> str | None:
    text = single_line(raw)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[:8] if len(digits) >= 4 else None


def programme_from_api(item: Mapping[str, Any], channel: Channel) -> Programme | None:
    """Convert one API entry; returns ``None`` for unusable entries."""
    item_channel = item.get("channel")
    if isinstance(item_channel, Mapping):
        canonical = item_channel.get("canonical_name")
        if canonical and canonical != channel.id:
            return None

    timeslot = item.get("timeslot") or {}
    start = _parse_time(timeslot.get("lower"))
    stop = _parse_time(timeslot.get("upper"))
    title = single_line(item.get("title"))
    if start is None or stop is None or stop <= start or title is None:
        return None

    categories = tuple(
        dict.fromkeys(c for c in (single_line(c) for c in item.get("categories") or ()) if c)
    )
    episode_num = single_line(item.get("episode_num"))
    rating = single_line(item.get("rating"))
    return Programme(
        channel_id=channel.id,
        start=start,
        stop=stop,
        title=title,
        sub_title=single_line(item.get("sub_title")),
        description=clean(item.get("desc")),
        categories=categories,
        credits=_credits(item.get("credits")),
        year=_year(item.get("date")),
        country=single_line(item.get("country")),
        icon=_first_icon(item.get("icons")),
        episode_num=episode_num,
        episode_num_system=single_line(item.get("episode_num_system")) if episode_num else None,
        rating=rating,
        rating_system=single_line(item.get("rating_system")) if rating else None,
        star_rating=single_line(item.get("star_rating")),
        premiere=item.get("premiere") is True,
        subtitles=item.get("subtitles") is True,
        language=channel.group,
    )
