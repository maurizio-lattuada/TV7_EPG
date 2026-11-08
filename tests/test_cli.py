import gzip
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import SAMPLE_M3U
from tv7_epg import cli
from tv7_epg.api import FetchError
from tv7_epg.models import Programme


class FakeClient:
    def __init__(self, failing=()):
        self.failing = set(failing)

    def fetch_playlist(self):
        return SAMPLE_M3U

    def fetch_programmes(self, channel):
        if channel.id in self.failing:
            raise FetchError("boom")
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        slots = [now - timedelta(days=10), now, now, now + timedelta(hours=1)]  # one too old, one duplicate
        return [
            Programme(channel_id=channel.id, start=s, stop=s + timedelta(hours=1), title=f"{channel.name} – Sendung", language=channel.group)
            for s in slots
        ]


def _args(tmp_path, *extra):
    return cli.build_parser().parse_args(["-o", str(tmp_path), "--base-url", "https://u.github.io/TV7_EPG/", *extra])


def test_run_writes_all_outputs(tmp_path):
    cli.run(_args(tmp_path), client=FakeClient())

    xml_bytes = (tmp_path / "epg.xml").read_bytes()
    assert gzip.decompress((tmp_path / "epg.xml.gz").read_bytes()) == xml_bytes
    root = ET.fromstring(xml_bytes)
    assert [c.get("id") for c in root.findall("channel")] == ["SRF1.ch", "RTS1.ch", "AlJazeera.qa", "TRTTurkAvrupa"]
    programmes = root.findall("programme")
    assert len(programmes) == 4 * 2  # old one filtered, duplicate removed
    assert programmes[2].findtext("title") == "RTS 1 Télévision – Sendung"

    playlist = (tmp_path / "playlist.m3u").read_text(encoding="utf-8")
    assert playlist.startswith('#EXTM3U url-tvg="https://u.github.io/TV7_EPG/epg.xml.gz"')
    assert "الجزيرة" in playlist
    assert "index.html" in {p.name for p in tmp_path.iterdir()}


def test_channel_filter(tmp_path):
    cli.run(_args(tmp_path, "--channel", "RTS1.ch"), client=FakeClient())
    root = ET.parse(tmp_path / "epg.xml").getroot()
    assert [c.get("id") for c in root.findall("channel")] == ["RTS1.ch"]


def test_some_failures_are_tolerated(tmp_path):
    cli.run(_args(tmp_path, "--max-failure-ratio", "0.25"), client=FakeClient(failing={"RTS1.ch"}))
    assert (tmp_path / "epg.xml").exists()


def test_too_many_failures_abort_without_output(tmp_path):
    with pytest.raises(cli.GenerationError):
        cli.run(_args(tmp_path), client=FakeClient(failing={"RTS1.ch", "SRF1.ch"}))
    assert not (tmp_path / "epg.xml").exists()
