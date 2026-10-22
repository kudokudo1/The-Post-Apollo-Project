"""Radio Browser integration tests use injected directory payloads, not real internet."""
import sys
import uuid
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from headless_mpd import MediaBackendError
from radio_browser_catalog import RadioBrowserCatalogSource
from media_controller import MediaController
from test_headless_controller import FakeMpd

SAFE = "https://streams.radio-example.org/jazz-128"
def station(url=SAFE, name="Jazz Sample", codec="MP3", good=True, **extras):
    return {"url_resolved": url, "name": name, "codec": codec,
            "lastcheckok": good, "country": "United States",
            "tags": "jazz,downtempo", "bitrate": 128,
            "countrycode": "US",
            "stationuuid": str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
            **extras}


class RadioCatalogTests(unittest.TestCase):
    def test_popular_radio_returns_safe_bounded_station_refs(self):
        calls = []
        def fetch(params):
            calls.append(params)
            return [station(), station(url="http://radio.example.com/stream"),
                    station(url="https://radio.example.com:8080/a"),
                    station(url="https://radio.example.com/playlist.m3u"),
                    station(url="https://radio.example.com/direct?token=secret"),
                    station(url="https://127.0.0.1/private"),
                    station(url="https://good.example.com/a", good=False),
                    station(url="https://good.example.com/b", codec="AAC"),
                    station(), station(url="https://good.example.com/other", name=" "),
                    station(url="https://music.youtube.com/a")]
        cat = RadioBrowserCatalogSource(fetch=fetch)
        output = cat.search("")
        self.assertEqual(calls[0]["hidebroken"], "true")
        self.assertEqual(calls[0]["is_https"], "true")
        self.assertEqual(calls[0]["codec"], "MP3")
        self.assertEqual(output["totalObserved"], 1)
        self.assertEqual(output["items"][0]["ref"], {
            "source": "radio-browser", "kind": "station",
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, SAFE))})
        self.assertNotIn("streamUrl", output["items"][0])
        self.assertEqual(output["items"][0]["streamHost"], "streams.radio-example.org")
        with self.assertRaises(MediaBackendError) as blocked:
            cat.prepare(output["items"][0]["ref"])
        self.assertEqual(blocked.exception.code, "PLAYBACK_UNAVAILABLE")
        self.assertEqual(output["nextCursor"], None)

    def test_station_name_genre_country_and_paging(self):
        seen = []
        def fetch(params):
            seen.append(params)
            return [station(url="https://radio.example.com/%d" % i,
                            name="Station %d" % i) for i in range(150)]
        cat = RadioBrowserCatalogSource(fetch)
        page = cat.search("tag:jazz")
        self.assertEqual(seen[-1]["tag"], "jazz")
        self.assertEqual(len(page["items"]), 50)
        self.assertEqual(page["nextCursor"], "150")
        cat.search("country:US", page["nextCursor"])
        self.assertEqual(seen[-1]["countrycode"], "US")
        self.assertEqual(seen[-1]["offset"], "150")
        cat.search("ambient")
        self.assertEqual(seen[-1]["name"], "ambient")
        self.assertNotIn("tag", seen[-1])

    def test_invalid_queries_cursor_and_response_are_rejected(self):
        cat = RadioBrowserCatalogSource(fetch=lambda params: [])
        for query in [None, "\n", "a" * 121, "tag:"]:
            with self.assertRaises(MediaBackendError):
                cat.search(query)
        for cursor in ["-1", "hi", "10001", "1.5", "1" * 40]:
            with self.assertRaises(MediaBackendError):
                cat.search("jazz", cursor)
        for bad in [{}, None, [None] * 151]:
            with self.assertRaises(MediaBackendError):
                RadioBrowserCatalogSource(fetch=lambda params: bad).search("")

    def test_radio_browsing_does_not_touch_playback(self):
        backend = FakeMpd()
        ctl = MediaController(backend=backend)
        ctl.sources["radio-browser"] = RadioBrowserCatalogSource(
            fetch=lambda params: [station()])
        before = ctl.snapshot()
        out = ctl.dispatch("search", {"source": "radio-browser", "query": "tag:jazz"})
        self.assertEqual(out["browse"]["source"], "radio-browser")
        self.assertEqual(out["browse"]["items"][0]["ref"]["source"], "radio-browser")
        station_ref = out["browse"]["items"][0]["ref"]
        ctl.dispatch("select", {"ref": station_ref})
        self.assertEqual(ctl.snapshot()["selection"], station_ref)
        with self.assertRaises(MediaBackendError) as blocked:
            ctl.dispatch("load", {"ref": station_ref})
        self.assertEqual(blocked.exception.code, "PLAYBACK_UNAVAILABLE")
        after = ctl.snapshot()
        self.assertEqual(before["loaded"], after["loaded"])
        self.assertEqual(after["selection"], station_ref)
        self.assertEqual(before["session"]["state"], after["session"]["state"])
        self.assertFalse(any(call[0] in ("addid", "playid") for call in backend.calls))
        self.assertIn("radio-browser", [r["id"] for r in after["sources"]])


if __name__ == "__main__":
    unittest.main()
