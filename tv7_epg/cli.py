"""Command line entry point: ``python -m tv7_epg`` / ``tv7-epg``."""

from __future__ import annotations

import argparse
import gzip
import html
import logging
import os
import sys
import tempfile
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .api import FetchError, Init7Client
from .models import Channel, Programme
from .playlist import parse_m3u, render_m3u
from .window import DEFAULT_TIMEZONE, TimeWindow, build_window
from .xmltv import render_xmltv

log = logging.getLogger("tv7_epg")

GUIDE_NAME = "epg.xml"
PLAYLIST_NAME = "playlist.m3u"


class GenerationError(RuntimeError):
    pass


def collect_programmes(
    client: Init7Client,
    channels: Sequence[Channel],
    window: TimeWindow,
    *,
    workers: int,
    max_failure_ratio: float,
) -> list[Programme]:
    """Download all channels in parallel and keep the programmes inside ``window``."""
    collected: dict[tuple[str, datetime], Programme] = {}
    failed: list[str] = []
    errors: list[FetchError] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(client.fetch_programmes, channel): channel for channel in channels}
        for done, future in enumerate(as_completed(futures), start=1):
            channel = futures[future]
            try:
                programmes = future.result()
            except FetchError as error:
                failed.append(channel.id)
                errors.append(error)
                log.warning("Channel %s failed: %s", channel.id, error)
                continue
            kept = 0
            for programme in programmes:
                if window.overlaps(programme.start, programme.stop):
                    # Same channel + start time means the same slot; last one wins.
                    collected[(programme.channel_id, programme.start)] = programme
                    kept += 1
            log.info("[%3d/%d] %-28s %5d programmes", done, len(channels), channel.id, kept)

    if channels and len(failed) / len(channels) > max_failure_ratio:
        forbidden = [error for error in errors if error.status == 403]
        if len(forbidden) == len(errors):
            sample = next((error.body for error in forbidden if error.body), None)
            raise GenerationError(
                f"Access denied (HTTP 403) for {len(failed)} of {len(channels)} channels. "
                "The Init7 EPG API requires authentication and only accepts unauthenticated "
                "requests from Init7 customer connections, so this machine's network is not "
                "allowed. Run the generator from a computer on an Init7 connection (e.g. the "
                "self-hosted GitHub runner)."
                + (f" Server response: {sample[:300]}" if sample else "")
            )
        raise GenerationError(
            f"{len(failed)} of {len(channels)} channels failed, above the allowed "
            f"{max_failure_ratio:.0%}: {', '.join(sorted(failed))}"
        )
    if not collected:
        raise GenerationError("No programmes found inside the requested time window")

    order = {channel.id: index for index, channel in enumerate(channels)}
    return sorted(collected.values(), key=lambda p: (order[p.channel_id], p.start))


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _index_page(base_url: str | None, generated: datetime, window: TimeWindow, stats: str) -> bytes:
    def link(name: str) -> str:
        href = f"{base_url.rstrip('/')}/{name}" if base_url else name
        return f'<li><a href="{html.escape(href)}">{html.escape(href)}</a></li>'

    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TV7 EPG</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem">
<h1>Init7 TV7 programme guide</h1>
<ul>{link(GUIDE_NAME + ".gz")}{link(GUIDE_NAME)}{link(PLAYLIST_NAME)}</ul>
<p>Generated {generated:%Y-%m-%d %H:%M} UTC &middot; {html.escape(stats)}<br>
Covers {window.start:%Y-%m-%d %H:%M %Z} to {window.end:%Y-%m-%d %H:%M %Z}</p>
</body>
</html>
""".encode("utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tv7-epg",
        description="Generate a Kodi-compatible XMLTV guide and M3U playlist for Init7 TV7.",
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--days-back", type=int, default=1, help="full days before today (default: 1)")
    parser.add_argument("--days-ahead", type=int, default=30, help="full days after today (default: 30)")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help=f"defines 'today' (default: {DEFAULT_TIMEZONE})")
    parser.add_argument("--base-url", help="public URL the files are served from; enables url-tvg in the playlist")
    parser.add_argument("--channel", action="append", dest="channels", metavar="ID", help="only this channel id (repeatable)")
    parser.add_argument("--workers", type=int, default=8, help="parallel downloads (default: 8)")
    parser.add_argument("--max-failure-ratio", type=float, default=0.2, help="abort if more channels fail (default: 0.2)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def run(args: argparse.Namespace, client: Init7Client | None = None) -> None:
    client = client or Init7Client()
    window = build_window(args.days_back, args.days_ahead, args.timezone)
    log.info("Time window: %s -> %s", window.start.isoformat(), window.end.isoformat())

    channels = parse_m3u(client.fetch_playlist())
    if args.channels:
        wanted = set(args.channels)
        channels = [channel for channel in channels if channel.id in wanted]
    if not channels:
        raise GenerationError("The channel playlist is empty")
    log.info("Channels: %d", len(channels))

    programmes = collect_programmes(
        client, channels, window, workers=args.workers, max_failure_ratio=args.max_failure_ratio
    )
    with_data = len({p.channel_id for p in programmes})
    stats = f"{len(channels)} channels ({with_data} with programmes), {len(programmes)} programmes"
    log.info("Collected %s", stats)

    guide = render_xmltv(channels, programmes)
    guide_url = f"{args.base_url.rstrip('/')}/{GUIDE_NAME}.gz" if args.base_url else None
    out: Path = args.output_dir
    _write_atomic(out / GUIDE_NAME, guide)
    _write_atomic(out / f"{GUIDE_NAME}.gz", gzip.compress(guide, compresslevel=9, mtime=0))
    _write_atomic(out / PLAYLIST_NAME, render_m3u(channels, guide_url).encode("utf-8"))
    _write_atomic(out / "index.html", _index_page(args.base_url, datetime.now(UTC), window, stats))
    log.info("Wrote %s", ", ".join(str(out / n) for n in (GUIDE_NAME, f"{GUIDE_NAME}.gz", PLAYLIST_NAME)))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        run(args)
    except (GenerationError, FetchError, ValueError) as error:
        log.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
