from __future__ import annotations

import pytest

from tv7_epg.models import Channel

SAMPLE_M3U = """﻿#EXTM3U
#EXTINF:0 tvg-logo="https://example.test/srf1.png" tvg-name="SRF1.ch" group-title="de", SRF 1
udp://@233.50.230.80:5000
#EXTINF:0 tvg-logo="https://example.test/rts.png" tvg-name="RTS1.ch" group-title="fr", RTS 1 Télévision
udp://@233.50.230.81:5000
#EXTINF:0 tvg-name="AlJazeera.qa" group-title="qa", الجزيرة
udp://@233.50.230.82:5000
#EXTINF:0 group-title="tr", TRT Türk, Avrupa
udp://@233.50.230.83:5000
#EXTINF:0 tvg-name="SRF1.ch" group-title="de", SRF 1 duplicate
udp://@233.50.230.84:5000
#EXTINF:0 tvg-name="Orphan.ch", entry without URL
"""


@pytest.fixture
def srf1() -> Channel:
    return Channel(id="SRF1.ch", name="SRF 1", stream_url="udp://@233.50.230.80:5000", group="de")


def api_item(**overrides):
    """A raw EPG entry shaped like the real API response."""
    item = {
        "pk": "15c3f034-1a02-4de3-a76c-3cddd5f2b29c",
        "timeslot": {"lower": "2026-11-08T18:00:00Z", "upper": "2026-11-08T18:30:00Z", "bounds": "[)"},
        "channel": {"canonical_name": "SRF1.ch", "name": "SRF 1", "language": "de"},
        "title": "Tagesschau",
        "sub_title": None,
        "desc": None,
        "categories": [],
        "country": None,
        "date": None,
        "icons": [],
        "credits": [],
        "rating_system": None,
        "rating": None,
        "episode_num_system": None,
        "episode_num": None,
        "premiere": False,
        "subtitles": False,
        "star_rating": None,
    }
    item.update(overrides)
    return item
