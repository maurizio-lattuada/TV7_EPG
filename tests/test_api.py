from datetime import UTC, datetime

from tests.conftest import api_item
from tv7_epg.api import programme_from_api
from tv7_epg.models import Credit


def test_minimal_item(srf1):
    programme = programme_from_api(api_item(), srf1)
    assert programme.channel_id == "SRF1.ch"
    assert programme.start == datetime(2026, 11, 8, 18, 0, tzinfo=UTC)
    assert programme.stop == datetime(2026, 11, 8, 18, 30, tzinfo=UTC)
    assert programme.title == "Tagesschau"
    assert programme.language == "de"


def test_full_item(srf1):
    item = api_item(
        title="Sábado Desportivo",
        sub_title="Folge 3: Grüezi\nmitenand",
        desc="Ein Krimi über Zürich & Genève <live>.\nZweite Zeile.",
        categories=["Series", "Sports News", "Series", ""],
        country="Schweiz",
        date="2019",
        icons=["not-a-url", {"src": "https://example.test/p.jpg"}],
        credits=[
            {"position": "Actor", "name": "Liza Del Sierra"},
            {"position": "director", "name": "Kendo D"},
            {"position": "actor", "name": None},
        ],
        rating_system="age",
        rating="12",
        episode_num_system="xmltv_ns",
        episode_num="3.0/4.",
        premiere=True,
        subtitles=True,
    )
    p = programme_from_api(item, srf1)
    assert p.title == "Sábado Desportivo"
    assert p.sub_title == "Folge 3: Grüezi mitenand"
    assert p.description == "Ein Krimi über Zürich & Genève <live>.\nZweite Zeile."
    assert p.categories == ("Series", "Sports News")
    assert p.year == "2019"
    assert p.icon == "https://example.test/p.jpg"
    assert p.credits == (Credit("actor", "Liza Del Sierra"), Credit("director", "Kendo D"))
    assert (p.rating, p.rating_system) == ("12", "age")
    assert (p.episode_num, p.episode_num_system) == ("3.0/4.", "xmltv_ns")
    assert p.premiere and p.subtitles


def test_unusable_items_are_skipped(srf1):
    assert programme_from_api(api_item(title="  "), srf1) is None
    assert programme_from_api(api_item(timeslot={"lower": "bad", "upper": None}), srf1) is None
    assert (
        programme_from_api(
            api_item(timeslot={"lower": "2026-11-08T18:30:00Z", "upper": "2026-11-08T18:00:00Z"}), srf1
        )
        is None
    )
    # Naive timestamps are ambiguous and therefore rejected.
    assert (
        programme_from_api(
            api_item(timeslot={"lower": "2026-11-08T18:00:00", "upper": "2026-11-08T18:30:00"}), srf1
        )
        is None
    )


def test_items_of_other_channels_are_ignored(srf1):
    item = api_item(channel={"canonical_name": "SRFzwei.ch"})
    assert programme_from_api(item, srf1) is None


def test_system_fields_dropped_without_value(srf1):
    p = programme_from_api(api_item(rating_system="age", episode_num_system="xmltv_ns"), srf1)
    assert p.rating_system is None and p.episode_num_system is None
