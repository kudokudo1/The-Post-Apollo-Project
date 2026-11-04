#!/usr/bin/env python3
"""M9 pure/offline contracts for two fixed publisher RSS feeds."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/weather/station_publisher_rss.py"
spec = importlib.util.spec_from_file_location("station_publisher_rss", MODULE)
assert spec and spec.loader
rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rss)

assert set(rss.FEEDS) == {"bbc-world", "al-jazeera-english"}
assert rss.FEEDS["bbc-world"]["url"] == "https://feeds.bbci.co.uk/news/world/rss.xml"
assert rss.FEEDS["al-jazeera-english"]["url"] == "https://www.aljazeera.com/xml/rss/all.xml"
assert rss.MAX_BYTES == 1024 * 1024
assert rss.MAX_ROWS == 20

assert rss.url_allowed("https://feeds.bbci.co.uk/news/world/rss.xml", "feeds.bbci.co.uk")
assert not rss.url_allowed("http://feeds.bbci.co.uk/news/world/rss.xml", "feeds.bbci.co.uk")
assert not rss.url_allowed("https://evil.example/", "feeds.bbci.co.uk")
assert not rss.url_allowed("https://feeds.bbci.co.uk:8080/", "feeds.bbci.co.uk")
assert not rss.url_allowed("https://user:pass@feeds.bbci.co.uk/", "feeds.bbci.co.uk")
assert rss.article_url("https://www.bbc.com/news/articles/123", ("bbc.com",))
assert not rss.article_url("https://bbc.com.evil.example/a", ("bbc.com",))
assert not rss.article_url("http://www.bbc.com/news", ("bbc.com",))
assert not rss.article_url("https://www.bbc.com:2222/news", ("bbc.com",))
assert not rss.article_url("https://user:pass@www.bbc.com/news", ("bbc.com",))
assert not rss.article_url("https://example.net/news", ("bbc.com",))
assert rss.utc_publication("Tue, 03 Nov 2026 22:10:00 GMT")[0] == "2026-11-03 22:10 UTC"
assert rss.utc_publication("bad date") == ("TIME NOT PROVIDED", -1)

bbc = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>BBC World</title>
<item><title>Storm &amp; flooding in Europe</title>
<link>https://www.bbc.com/news/articles/one</link>
<pubDate>Tue, 03 Nov 2026 22:10:00 GMT</pubDate>
<description><![CDATA[<p>Short &amp; safe summary.</p>]]></description></item>
<item><title>Duplicate link</title><link>https://www.bbc.com/news/articles/one</link></item>
<item><title>Bad publisher</title><link>https://evil.example/a</link></item>
<item><title>Non-HTTPS</title><link>http://www.bbc.com/news/articles/two</link></item>
<item><title>Untimed headline</title><link>https://www.bbc.co.uk/news/articles/two</link></item>
</channel></rss>"""
parsed = rss.parse_rss(bbc, "bbc-world")
assert parsed["ok"] and parsed["publisher"] == "BBC WORLD"
assert parsed["feedId"] == "bbc-world" and len(parsed["rows"]) == 2
first, second = parsed["rows"]
assert first["title"] == "Storm & flooding in Europe"
assert first["detail"] == "BBC WORLD // RSS HEADLINE"
assert first["source"] == "BBC WORLD" and first["language"] == "English"
assert first["summary"] == "Short & safe summary."
assert first["seenMillis"] == 1793743800000
assert first["domain"] == "www.bbc.com"
assert second["time"] == "TIME NOT PROVIDED"
assert second["seenMillis"] == -1
assert "body" not in first
assert rss.parse_rss(bbc.replace(b"bbc.com", b"bbc.co.uk"), "bbc-world")["ok"]

aj = b"""<rss version="2.0"><channel>
<item><title>International news</title>
<link>https://www.aljazeera.com/news/2026/11/3/test</link>
<pubDate>Tue, 03 Nov 2026 23:00:00 GMT</pubDate>
<description>Short official summary</description></item>
<item><title>Wrong BBC item</title>
<link>https://www.bbc.com/news/world</link></item>
</channel></rss>"""
actual = rss.parse_rss(aj, "al-jazeera-english")
assert len(actual["rows"]) == 1
assert actual["publisher"] == "AL JAZEERA ENGLISH"
assert actual["rows"][0]["domain"] == "www.aljazeera.com"

for malformed in (
    b"<html><body>not RSS</body></html>",
    b"<rss version='2.0'><channel></channel></rss>",
    b"<!DOCTYPE rss><rss><channel/></rss>",
    b"<!ENTITY x 'z'><rss><channel/></rss>",
    b"z" * (rss.MAX_BYTES + 1),
):
    try:
        rss.parse_rss(malformed, "bbc-world")
        raise AssertionError("malformed feed accepted")
    except (ValueError, rss.ET.ParseError):
        pass

class Response:
    def __init__(self, url, payload):
        self.url, self.payload = url, payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read(self, n):
        assert n == rss.MAX_BYTES + 1
        return self.payload

class FakeOpener:
    def __init__(self, redirected=False):
        self.redirected = redirected
        self.calls = []
    def open(self, request, timeout=0):
        self.calls.append((request.full_url, timeout))
        return Response("https://www.evil.example/" if self.redirected
                        else request.full_url, bbc)

original = rss.build_opener
try:
    opener = FakeOpener()
    rss.build_opener = lambda handler: opener
    assert rss.fetch_feed("bbc-world")["rows"][0]["title"] == "Storm & flooding in Europe"
    assert opener.calls == [(rss.FEEDS["bbc-world"]["url"], 14)]
    rss.build_opener = lambda handler: FakeOpener(redirected=True)
    try:
        rss.fetch_feed("bbc-world")
        raise AssertionError("cross-host final response accepted")
    except ValueError:
        pass
finally:
    rss.build_opener = original

for argv in (["station_publisher_rss.py"], ["station_publisher_rss.py","https://evil.example"]):
    output = StringIO()
    with redirect_stdout(output):
        assert rss.main(argv) == 2
    assert json.loads(output.getvalue())["error"] == "INVALID_FEED_ID"

# No network access is needed by any of these tests.
print("Weather M9 publisher RSS parser / host boundary / normalization: PASS")
