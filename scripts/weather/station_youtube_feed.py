#!/usr/bin/env python3
"""Read one public YouTube channel Atom feed on explicit operator request.

No OAuth, cookies, scraping, shell commands, autoplay or background polling.
The only network destination is YouTube's fixed public channel-feed endpoint.
"""
from __future__ import annotations

import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

CHANNEL_RE = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")
VIDEO_RE = re.compile(r"[A-Za-z0-9_-]{11}\Z")
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"


def parse_feed(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    if root.tag != ATOM + "feed":
        raise ValueError("Expected YouTube Atom feed")
    result = []
    for entry in root.findall(ATOM + "entry")[:15]:
        video_id = (entry.findtext(YT + "videoId") or "").strip()
        if not VIDEO_RE.fullmatch(video_id):
            continue
        title = " ".join((entry.findtext(ATOM + "title") or "").split())[:180]
        published = (entry.findtext(ATOM + "published") or "")[:25]
        if not title:
            continue
        result.append({"title": title, "time": published,
                       "url": "https://www.youtube.com/watch?v=" + video_id})
    return {"rows": result}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not CHANNEL_RE.fullmatch(argv[1]):
        print(json.dumps({"error": "INVALID CHANNEL ID"}))
        return 2
    endpoint = "https://www.youtube.com/feeds/videos.xml?channel_id=" + argv[1]
    try:
        request = Request(endpoint, headers={"User-Agent": "Post-Apollo-WeatherStation/0.2"})
        with urlopen(request, timeout=12) as response:
            actual = urlsplit(response.geturl())
            if actual.scheme != "https" or actual.hostname not in ("youtube.com", "www.youtube.com"):
                raise ValueError("Unexpected feed redirect")
            payload = response.read(512 * 1024 + 1)
            if len(payload) > 512 * 1024:
                raise ValueError("Feed too large")
        print(json.dumps(parse_feed(payload), ensure_ascii=False))
        return 0
    except (HTTPError, URLError, OSError, ValueError, ET.ParseError) as error:
        # No secrets, URLs, or raw provider content in the UI error channel.
        print(json.dumps({"error": "CREATOR FEED UNAVAILABLE",
                          "kind": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
