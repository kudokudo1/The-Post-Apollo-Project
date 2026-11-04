#!/usr/bin/env python3
"""Fetch a fixed publisher RSS feed for Weather Station, on explicit request.

Two independent publisher endpoints only. No arbitrary URL input, browser,
background polling, on-disk cache, credentials, or article-body retrieval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET


FEEDS = {
    "bbc-world": {
        "publisher": "BBC WORLD",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "feed_host": "feeds.bbci.co.uk",
        "article_hosts": ("bbc.co.uk", "bbc.com"),
    },
    "al-jazeera-english": {
        "publisher": "AL JAZEERA ENGLISH",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "feed_host": "www.aljazeera.com",
        "article_hosts": ("aljazeera.com",),
    },
}
MAX_BYTES = 1024 * 1024
MAX_ROWS = 20


def url_allowed(value: str, host: str) -> bool:
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and parsed.hostname == host
                and parsed.port in (None, 443)
                and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


def article_url(value: str, suffixes: tuple[str, ...]) -> str:
    candidate = str(value or "").strip()
    if len(candidate) > 2048 or any(c.isspace() for c in candidate):
        return ""
    try:
        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").lower()
        if (parsed.scheme != "https" or parsed.port not in (None, 443)
                or parsed.username or parsed.password):
            return ""
        if not any(host == suffix or host.endswith("." + suffix)
                   for suffix in suffixes):
            return ""
        return candidate
    except ValueError:
        return ""


class FeedOnlyRedirects(HTTPRedirectHandler):
    def __init__(self, allowed_host: str):
        super().__init__()
        self.allowed_host = allowed_host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not url_allowed(newurl, self.allowed_host):
            raise ValueError("UNEXPECTED_FEED_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def short_text(value: str, limit: int) -> str:
    no_markup = re.sub(r"<[^>]*>", " ", str(value or ""))
    decoded = html.unescape(no_markup)
    return " ".join(decoded.split())[:limit]


def utc_publication(value: str) -> tuple[str, int]:
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return "TIME NOT PROVIDED", -1
        instant = parsed.astimezone(timezone.utc)
        return instant.strftime("%Y-%m-%d %H:%M UTC"), int(instant.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return "TIME NOT PROVIDED", -1


def parse_rss(raw: bytes, feed_id: str) -> dict:
    config = FEEDS[feed_id]
    if len(raw) > MAX_BYTES or b"<!doctype" in raw.lower() or b"<!entity" in raw.lower():
        raise ValueError("INVALID_FEED")
    root = ET.fromstring(raw)
    if root.tag != "rss":
        raise ValueError("NOT_RSS")
    channel = root.find("channel")
    if channel is None:
        raise ValueError("MISSING_CHANNEL")
    rows = []
    seen = set()
    for item in channel.findall("item"):
        title = short_text(item.findtext("title"), 180)
        url = article_url(item.findtext("link"), config["article_hosts"])
        if not title or not url or url in seen:
            continue
        seen.add(url)
        time_label, seen_ms = utc_publication(item.findtext("pubDate") or "")
        rows.append({
            "title": title,
            "url": url,
            "source": config["publisher"],
            "detail": config["publisher"] + " // RSS HEADLINE",
            "time": time_label,
            "seenMillis": seen_ms,
            "language": "English",
            "domain": urlsplit(url).hostname or "",
            "summary": short_text(item.findtext("description"), 230),
        })
        if len(rows) >= MAX_ROWS:
            break
    if not rows:
        raise ValueError("EMPTY_OR_INVALID_FEED")
    return {"ok": True, "feedId": feed_id,
            "publisher": config["publisher"], "rows": rows}


def fetch_feed(feed_id: str) -> dict:
    config = FEEDS[feed_id]
    opener = build_opener(FeedOnlyRedirects(config["feed_host"]))
    request = Request(
        config["url"],
        headers={"User-Agent": "Post-Apollo-WeatherStation/0.9",
                 "Accept": "application/rss+xml, application/xml, text/xml"},
    )
    with opener.open(request, timeout=14) as response:
        if not url_allowed(response.geturl(), config["feed_host"]):
            raise ValueError("UNEXPECTED_FEED_HOST")
        payload = response.read(MAX_BYTES + 1)
    return parse_rss(payload, feed_id)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in FEEDS:
        print(json.dumps({"ok": False, "error": "INVALID_FEED_ID"}))
        return 2
    try:
        print(json.dumps(fetch_feed(argv[1]), separators=(",", ":"), ensure_ascii=True))
        return 0
    except (HTTPError, URLError, OSError, ValueError, ET.ParseError):
        print(json.dumps({"ok": False, "feedId": argv[1],
                          "error": "PUBLISHER RSS UNAVAILABLE"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
