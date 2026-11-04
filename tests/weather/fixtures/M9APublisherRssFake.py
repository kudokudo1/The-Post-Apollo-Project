#!/usr/bin/env python3
"""M9a CI-only publisher helper: fixed synthetic rows, never connects to network."""
import json
import sys

FEEDS = {
    "bbc-world": {
        "title": "M9A BBC WORLD SYNTHETIC HEADLINE",
        "source": "BBC WORLD",
        "url": "https://www.bbc.com/news/articles/m9a-test",
        "domain": "www.bbc.com",
    },
    "al-jazeera-english": {
        "title": "M9A AL JAZEERA SYNTHETIC HEADLINE",
        "source": "AL JAZEERA ENGLISH",
        "url": "https://www.aljazeera.com/news/2026/11/4/m9a-test",
        "domain": "www.aljazeera.com",
    },
}

if len(sys.argv) != 2 or sys.argv[1] not in FEEDS:
    print(json.dumps({"ok": False, "error": "INVALID_FEED_ID"}))
    raise SystemExit(2)

feed_id = sys.argv[1]
record = FEEDS[feed_id]
result = {
    "ok": True,
    "feedId": feed_id,
    "publisher": record["source"],
    "rows": [{
        "title": record["title"],
        "url": record["url"],
        "source": record["source"],
        "detail": record["source"] + " // RSS HEADLINE // SYNTHETIC FIXTURE",
        "time": "2026-11-04 04:44 UTC",
        "seenMillis": 1793767440000,
        "language": "English",
        "domain": record["domain"],
        "summary": "Synthetic CI data; no public publisher request was made.",
    }],
}
print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
