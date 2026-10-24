#!/usr/bin/env python3
"""Offline regression checks for Weather NEWS's optional YouTube Atom adapter."""
import importlib.util
import io
import json
import pathlib
import unittest
from contextlib import redirect_stdout

root = pathlib.Path(__file__).resolve().parents[2]
source = root / "scripts" / "weather" / "station_youtube_feed.py"
spec = importlib.util.spec_from_file_location("station_youtube_feed", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

VIDEO = "aBc123_-xyz"
GOOD = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
 xmlns:yt="http://www.youtube.com/xml/schemas/2015">
 <entry><yt:videoId>aBc123_-xyz</yt:videoId>
  <title>House  hearing  recap</title>
  <published>2026-10-24T13:00:00+00:00</published>
 </entry>
 <entry><yt:videoId>invalid</yt:videoId>
  <title>Bad link</title>
 </entry>
</feed>'''


class ChannelFeedTests(unittest.TestCase):
    def test_atom_feed(self):
        result = module.parse_feed(GOOD)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["title"], "House hearing recap")
        self.assertEqual(result["rows"][0]["url"],
                         "https://www.youtube.com/watch?v=" + VIDEO)

    def test_nonfeed_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_feed(b"<html>error</html>")

    def test_bad_channel_rejected_before_network(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = module.main(["station_youtube_feed.py", "UC;rm -rf /"])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(output.getvalue())["error"],
                         "INVALID CHANNEL ID")

    def test_redirects_restricted(self):
        redirect = module.YouTubeOnlyRedirects()
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, "Redirect", {},
                                      "http://127.0.0.1/private")
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, "Redirect", {},
                                      "https://evil.example/steal")


if __name__ == "__main__":
    unittest.main()
