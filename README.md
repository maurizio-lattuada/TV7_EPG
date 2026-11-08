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
* **Time range:** from 00:00 yesterday until 24:00 thirty days from today, using
  Europe/Zurich local time. Programmes that cross the start or end of that range are included.
  Init7 usually publishes only about one week ahead, so the guide ends wherever Init7's data ends.
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

### Why a self-hosted runner

The Init7 EPG API (`api.tv.init7.net`) answers **HTTP 403** to requests from outside
Init7 / Swiss networks, including GitHub's own runners. The generation step therefore runs
on a **self-hosted runner on a Mac connected through Init7** (labels `self-hosted`, `macOS`).
Tests and the Pages deployment still run on GitHub-hosted runners. The manual workflow
*Diagnose Init7 API access* shows what the API answers to a GitHub-hosted runner.

### One-time setup

1. *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
2. *Settings → Actions → General → Approval for running fork pull request workflows:*
   **Require approval for all external contributors**. The repository is public; the
   workflow never runs pull requests on the self-hosted runner, and this is a second safeguard.
3. Install the runner on the Mac: *Settings → Actions → Runners → New self-hosted runner →
   macOS*, run the commands shown there, then install it as a background service with
   `./svc.sh install && ./svc.sh start`. The runner needs [uv](https://docs.astral.sh/uv/)
   on its `PATH`; uv downloads the right Python version itself.
4. The Mac must be awake at 00:00 UTC. If it is off or asleep, the job waits in the queue
   until the runner is back. A queued job is cancelled after 24 hours. To wake the Mac
   every night: `sudo pmset repeat wakeorpoweron MTWRFSU 00:55:00`. That is Swiss local
   time, so it is just before 00:00 UTC in winter (01:00) and summer (02:00).

## Layout

```
tv7_epg/
  api.py       HTTP client (retries, pagination) and conversion of API entries
  playlist.py  M3U parsing and writing
  window.py    "yesterday … today+30" in local time, DST-safe
  xmltv.py     XMLTV document writer
  text.py      Unicode normalisation and XML-safe text
  cli.py       command line entry point and pipeline
```
