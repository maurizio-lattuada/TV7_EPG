import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta, timezone

from tv7_epg.models import Channel, Credit, Programme
from tv7_epg.xmltv import format_time, language_for_group, render_xmltv

START = datetime(2026, 11, 8, 18, 0, tzinfo=UTC)


def _programme(**overrides):
    values = dict(channel_id="SRF1.ch", start=START, stop=START + timedelta(minutes=30), title="Tagesschau", language="de")
    values.update(overrides)
    return Programme(**values)


def _render(channels, programmes):
    data = render_xmltv(channels, programmes)
    return data, ET.fromstring(data)


def test_document_header_and_utf8_bytes(srf1):
    data, root = _render([srf1], [_programme(title="Zürich – Genève ✓")])
    assert data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    assert "Zürich – Genève ✓".encode() in data  # written as real UTF-8, not entities
    assert root.tag == "tv"


def test_special_characters_survive_round_trip(srf1):
    texts = {
        "title": "Fußball: Österreich – Schweiz & Co. <live>",
        "sub_title": "Épisode « spécial » – l'été à Genève",
        "description": 'Ñandú, Ångström, "Zitat", Τηλεόραση, Türkçe ğüşıöç, العربية, 中文\nZeile 2',
    }
    _, root = _render([srf1], [_programme(**texts)])
    programme = root.find("programme")
    assert programme.findtext("title") == texts["title"]
    assert programme.findtext("sub-title") == texts["sub_title"]
    assert programme.findtext("desc") == texts["description"]
    assert programme.find("title").get("lang") == "de"


def test_channel_element(srf1):
    channel = Channel(id="RTS1.ch", name="RTS 1 Télévision", stream_url="udp://x", logo="https://e.test/a.png?x=1&y=2", group="fr")
    _, root = _render([channel], [])
    element = root.find("channel")
    assert element.get("id") == "RTS1.ch"
    assert element.findtext("display-name") == "RTS 1 Télévision"
    assert element.find("display-name").get("lang") == "fr"
    assert element.find("icon").get("src") == "https://e.test/a.png?x=1&y=2"


def test_times_are_utc():
    cet = timezone(timedelta(hours=1))
    assert format_time(datetime(2026, 11, 8, 19, 0, tzinfo=cet)) == "20261108180000 +0000"


def test_full_programme_element_order(srf1):
    p = _programme(
        sub_title="Sub",
        description="Desc",
        credits=(Credit("presenter", "Host"), Credit("actor", "A"), Credit("director", "D"), Credit("host", "Host"), Credit("grip", "X")),
        year="2019",
        categories=("News",),
        icon="https://e.test/i.jpg",
        country="Schweiz",
        episode_num="3.0/4.",
        episode_num_system="xmltv_ns",
        premiere=True,
        subtitles=True,
        rating="12",
        rating_system="age",
        star_rating="7/10",
    )
    _, root = _render([srf1], [p])
    element = root.find("programme")
    assert element.attrib == {"start": "20261108180000 +0000", "stop": "20261108183000 +0000", "channel": "SRF1.ch"}
    assert [c.tag for c in element] == [
        "title", "sub-title", "desc", "credits", "date", "category", "icon", "country",
        "episode-num", "premiere", "subtitles", "rating", "star-rating",
    ]
    assert [(c.tag, c.text) for c in element.find("credits")] == [("director", "D"), ("actor", "A"), ("presenter", "Host")]
    assert element.find("episode-num").get("system") == "xmltv_ns"
    assert element.find("rating").get("system") == "age"
    assert element.find("rating").findtext("value") == "12"
    assert element.find("star-rating").findtext("value") == "7/10"


def test_language_mapping():
    assert language_for_group("de") == "de"
    assert language_for_group("al") == "sq"
    assert language_for_group("QA") is None  # country code without a single language
    assert language_for_group("Deutsch") is None
    assert language_for_group(None) is None
