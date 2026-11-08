from tests.conftest import SAMPLE_M3U
from tv7_epg.playlist import parse_m3u, render_m3u


def test_parse_m3u_reads_channels_in_order():
    channels = parse_m3u(SAMPLE_M3U)
    assert [c.id for c in channels] == ["SRF1.ch", "RTS1.ch", "AlJazeera.qa", "TRTTurkAvrupa"]


def test_parse_m3u_keeps_unicode_names_and_attributes():
    rts, aljazeera, trt = parse_m3u(SAMPLE_M3U)[1:]
    assert rts.name == "RTS 1 Télévision"
    assert rts.logo == "https://example.test/rts.png"
    assert rts.group == "fr"
    assert aljazeera.name == "الجزيرة"
    assert trt.name == "TRT Türk, Avrupa"  # commas after the first belong to the name
    assert trt.stream_url == "udp://@233.50.230.83:5000"


def test_duplicate_ids_keep_first_entry():
    srf = parse_m3u(SAMPLE_M3U)[0]
    assert srf.name == "SRF 1"
    assert srf.stream_url.endswith(":5000") and "80" in srf.stream_url


def test_render_m3u_round_trip_and_guide_header():
    channels = parse_m3u(SAMPLE_M3U)
    text = render_m3u(channels, "https://example.test/epg.xml.gz")
    lines = text.splitlines()
    assert lines[0] == '#EXTM3U url-tvg="https://example.test/epg.xml.gz" x-tvg-url="https://example.test/epg.xml.gz"'
    assert 'tvg-id="SRF1.ch"' in lines[1] and lines[1].endswith(",SRF 1")
    assert [c.id for c in parse_m3u(text)] == [c.id for c in channels]
    assert [c.name for c in parse_m3u(text)] == [c.name for c in channels]


def test_render_m3u_neutralises_quotes():
    from tv7_epg.models import Channel

    text = render_m3u([Channel(id='A"B', name='Say "hi"', stream_url="udp://x")])
    assert 'tvg-id="A\'B"' in text
