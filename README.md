# TV7 EPG for Kodi

Generates an [XMLTV](https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd) programme guide
and a matching M3U playlist for [Init7 TV7](https://www.init7.net/), ready for Kodi's
**PVR IPTV Simple Client**. A GitHub Actions job rebuilds both files every night and
publishes them on GitHub Pages.

| File | URL |
|------|-----|
| Guide (gzip, recommended) | https://maurizio-lattuada.github.io/TV7_EPG/epg.xml.gz |
| Guide (plain XML) | https://maurizio-lattuada.github.io/TV7_EPG/epg.xml |
| Playlist | https://maurizio-lattuada.github.io/TV7_EPG/playlist.m3u |

## What it covers

* **Channels:** the full TV7 line-up from `https://api.init7.net/tvchannels.m3u`
  (about 240 channels in many languages).
* **Time range:** from 00:00 yesterday until 24:00 three days from today, using
  Europe/Zurich local time. Programmes that cross the start or end of that range are included.
* **Programme details:** title, subtitle, description, categories, cast and crew,
  episode numbering, age rating, premiere and subtitle flags. Text is written as UTF-8
  and normalised to Unicode NFC, so umlauts, accents and non-Latin scripts show correctly.
* **Channel ids:** the guide's channel ids are Init7's canonical names (e.g. `SRF1.ch`),
  and the playlist uses the same values as `tvg-id`, so Kodi matches them automatically.

## Kodi setup (Windows, Linux, Android, ...)

1. Install **PVR IPTV Simple Client** from *Add-ons → Install from repository → PVR clients*.
2. Open its *Configure* dialog:
   * **General:** set *Location* to *Remote path (Internet address)* and *M3U playlist URL*
     to `https://maurizio-lattuada.github.io/TV7_EPG/playlist.m3u`.
   * **EPG:** set *Location* to *Remote path* and *XMLTV URL* to
     `https://maurizio-lattuada.github.io/TV7_EPG/epg.xml.gz`. The playlist also points
     to the guide through `url-tvg`, so this step is optional but explicit is safer.
   * **Channel logos:** *Remote path*. The logos come from the playlist.
3. Restart Kodi, or disable and re-enable the add-on.

The streams are Init7's multicast addresses (`udp://@…`), so **they only play on an Init7
connection**, with a router that forwards multicast (IGMP proxy).

## Running locally

Requires Python 3.14 or newer. The tool itself uses only the standard library.

```bash
python -m tv7_epg --output-dir dist
python -m tv7_epg --channel SRF1.ch --channel RTS1.ch -v   # quick test with two channels
python -m tv7_epg --help
```

Options include `--days-back`, `--days-ahead`, `--timezone`, `--workers` and
`--max-failure-ratio`. If more channels than that ratio fail to download, the run
stops with an error and writes no files.

Tests:

```bash
uv run pytest        # or: pip install pytest && python -m pytest
```

## Automation

`.github/workflows/epg.yml` runs:

* every day at **00:00 UTC**. GitHub sometimes starts scheduled jobs a few minutes late,
* on every push to `main`,
* manually, via *Actions → Build and publish EPG → Run workflow*.

Each run tests the code, generates `dist/` and deploys it to GitHub Pages. Pull requests
only run the tests. The generated files are never committed, so the repository stays small.

One-time setup: *Settings → Pages → Build and deployment → Source: **GitHub Actions***.

## Layout

```
tv7_epg/
  api.py       HTTP client (retries, pagination) and conversion of API entries
  playlist.py  M3U parsing and writing
  window.py    "yesterday … today+3" in local time, DST-safe
  xmltv.py     XMLTV document writer
  text.py      Unicode normalisation and XML-safe text
  cli.py       command line entry point and pipeline
```
