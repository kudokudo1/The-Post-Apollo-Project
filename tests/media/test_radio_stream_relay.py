"""Contract and offline integration tests for guarded Radio Browser MP3 relay."""
import http.client
import io
import ipaddress
import socket
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from headless_mpd import MediaBackendError, MpdBackend
from radio_browser_catalog import RadioBrowserCatalogSource
from radio_stream_relay import (RadioStreamRelay, public_endpoint, open_public_mp3_stream)
from media_controller import MediaController
from test_headless_controller import FakeMpd

URL_A = "https://radio.example.net/jazz.mp3"
URL_B = "https://radio.example.net/ambient.mp3"


def station(url, name):
    return {"stationuuid": str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
            "url_resolved": url, "codec": "MP3", "lastcheckok": True,
            "name": name, "countrycode": "US", "tags": "jazz",
            "bitrate": 128}


class StubResponse:
    def __init__(self, status=200, mime="audio/mpeg", content=b"MP3-CONTENT"):
        self.status = status
        self.mime = mime
        self.buffer = io.BytesIO(content)

    def getheader(self, name, default=""):
        return self.mime if name.lower() == "content-type" else default

    def read(self, n):
        return self.buffer.read(n)


class RelayFake:
    def __init__(self):
        self.registered = {}
        self.counter = 0

    def register(self, url):
        self.counter += 1
        endpoint = "http://127.0.0.1:38000/radio/" + ("%064x" % self.counter)
        self.registered[endpoint] = url
        return endpoint

    def owns(self, url):
        return url in self.registered


class GuardedFakeMpd(FakeMpd):
    required_kinds = ("mpd-local-track", "mpd-https-stream", "mpd-guarded-radio")

    def queue(self):
        return [{"queueId": i["id"],
                 "ref": {"source": "local-mpd", "kind": "track", "id": i["uri"]}}
                for i in self.queue_items]


class RadioRelayTests(unittest.TestCase):
    def test_dns_pin_refuses_private_loopback_linklocal_mixed_and_empty(self):
        def fake(*addresses):
            return [((socket.AF_INET6 if ":" in a else socket.AF_INET),
                     socket.SOCK_STREAM, 6, "", (a, 443))
                    for a in addresses]
        for samples in [("127.0.0.1",), ("10.0.0.2",),
                        ("192.168.1.4", "8.8.8.8"), ("169.254.1.1",),
                        ("224.0.0.1",), ("ff02::1",)]:
            with self.assertRaises(MediaBackendError) as e:
                public_endpoint("radio.example.net", resolve=lambda *a, x=samples, **k: fake(*x))
            self.assertEqual(e.exception.code, "STREAM_DNS_BLOCKED")
        self.assertEqual(public_endpoint("radio.example.net",
                         resolve=lambda *a, **k: fake("8.8.8.8")), "8.8.8.8")
        with self.assertRaises(MediaBackendError):
            public_endpoint("radio.example.net", resolve=lambda *a, **k: [])

    def test_pinned_request_rejects_redirect_wrong_mime_and_non_https(self):
        class StubConnection:
            def __init__(self, host, pinned_ip):
                self.host, self.ip = host, pinned_ip
                self.response = StubResponse()
                self.requests = []
                self.closed = False

            def request(self, method, target, headers):
                self.requests.append((method, target, headers))

            def getresponse(self):
                return self.response

            def close(self):
                self.closed = True

        with patch("radio_stream_relay._PinnedHTTPSConnection", StubConnection):
            connection, response = open_public_mp3_stream(
                URL_A, resolver=lambda host: "8.8.8.8")
            self.assertEqual(connection.host, "radio.example.net")
            self.assertEqual(connection.ip, "8.8.8.8")
            self.assertEqual(connection.requests[0][1], "/jazz.mp3")
            self.assertEqual(connection.requests[0][2]["Icy-MetaData"], "0")
            self.assertEqual(response.status, 200)
            connection.close()
        for bad in ["http://radio.example.net/audio",
                    "https://127.0.0.1/audio",
                    "https://radio.example.net:1234/audio",
                    "https://radio.example.net/audio?secret=1"]:
            with self.assertRaises(MediaBackendError):
                open_public_mp3_stream(bad, resolver=lambda host: "8.8.8.8")

        class RedirectConnection(StubConnection):
            def __init__(self, host, pinned_ip):
                super().__init__(host, pinned_ip)
                self.response = StubResponse(status=302)
        with patch("radio_stream_relay._PinnedHTTPSConnection", RedirectConnection):
            with self.assertRaises(MediaBackendError) as e:
                open_public_mp3_stream(URL_A, resolver=lambda host: "8.8.8.8")
            self.assertEqual(e.exception.code, "STREAM_HTTP")

        class WrongMimeConnection(StubConnection):
            def __init__(self, host, pinned_ip):
                super().__init__(host, pinned_ip)
                self.response = StubResponse(mime="text/html")
        with patch("radio_stream_relay._PinnedHTTPSConnection", WrongMimeConnection):
            with self.assertRaises(MediaBackendError) as e:
                open_public_mp3_stream(URL_A, resolver=lambda host: "8.8.8.8")
            self.assertEqual(e.exception.code, "STREAM_FORMAT")

    def test_loopback_relay_serves_only_registered_tokens_and_closes(self):
        opened = []
        class StubConn:
            def close(self):
                pass
        def opener(uri):
            opened.append(uri)
            return StubConn(), StubResponse(content=b"example mp3 bytes")
        relay = RadioStreamRelay(opener=opener)
        try:
            endpoint = relay.register(URL_A)
            self.assertTrue(endpoint.startswith("http://127.0.0.1:"))
            self.assertNotIn("example.net", endpoint)
            self.assertTrue(relay.owns(endpoint))
            from urllib.request import urlopen
            with urlopen(endpoint, timeout=2) as response:
                self.assertEqual(response.read(), b"example mp3 bytes")
            self.assertEqual(opened, [URL_A])
            with self.assertRaises(Exception):
                urlopen(endpoint + "?redirect=http://127.0.0.1/", timeout=2)
            self.assertFalse(relay.owns(endpoint.replace("127.0.0.1", "localhost")))
        finally:
            relay.close()
        self.assertFalse(relay.owns(endpoint))

    def test_mpd_requires_active_registered_loopback_capability(self):
        backend = MpdBackend()
        with self.assertRaises(MediaBackendError):
            backend.cue({"requiredKind": "mpd-guarded-radio",
                         "uri": "http://127.0.0.1:33000/radio/token"})
        backend.radio_relay = RelayFake()
        endpoint = backend.radio_relay.register(URL_A)
        with patch.object(backend, "command", return_value=["Id: 100"]) as cmd:
            self.assertEqual(backend.cue({
                "requiredKind": "mpd-guarded-radio", "uri": endpoint
            }), "100")
            cmd.assert_called_once_with("addid", endpoint)
        with self.assertRaises(MediaBackendError):
            backend.cue({"requiredKind": "mpd-guarded-radio",
                         "uri": "http://127.0.0.1:9999/private"})

    def test_two_station_switch_load_then_play_without_autoplay(self):
        backend = GuardedFakeMpd()
        relay = RelayFake()
        controller = MediaController(backend=backend, radio_relay=relay)
        catalog = RadioBrowserCatalogSource(
            fetch=lambda params: [station(URL_A, "Jazz Station"),
                                  station(URL_B, "Ambient Station")],
            relay=relay)
        controller.sources["radio-browser"] = catalog
        response = controller.dispatch("search", {"source": "radio-browser",
                                                   "query": ""})
        self.assertEqual(response["browse"]["items"][0]["ref"]["source"], "radio-browser")
        jazz, ambient = (x["ref"] for x in response["browse"]["items"])
        controller.dispatch("select", {"ref": jazz})
        self.assertFalse(any(c[0] == "addid" for c in backend.calls))
        loaded_a = controller.dispatch("load")
        self.assertFalse(loaded_a["autoplay"])
        self.assertEqual(backend.status, "stop")
        self.assertEqual(loaded_a["loaded"]["item"]["title"], "Jazz Station")
        self.assertEqual(loaded_a["loaded"]["ref"], jazz)
        self.assertTrue(controller.loaded["cueUri"].startswith("http://127.0.0.1:"))
        self.assertNotIn(URL_A, controller.loaded["cueUri"])
        controller.dispatch("play")
        self.assertEqual(backend.playing_id, loaded_a["loaded"]["queueId"])

        controller.dispatch("select", {"ref": ambient})
        loaded_b = controller.dispatch("load")
        self.assertEqual(loaded_b["loaded"]["item"]["title"], "Ambient Station")
        self.assertFalse(loaded_b["autoplay"])
        self.assertEqual(backend.playing_id, loaded_a["loaded"]["queueId"],
                         "LOAD must not interrupt first station")
        controller.dispatch("play")
        self.assertEqual(backend.playing_id, loaded_b["loaded"]["queueId"])
        self.assertTrue(controller.snapshot()["session"]["ownedByController"])
        backend.queue_items[-1]["uri"] = "http://127.0.0.1:38000/radio/tampered"
        with self.assertRaises(MediaBackendError):
            controller.dispatch("play")

    def test_without_relay_directory_browsing_stays_catalog_only(self):
        catalog = RadioBrowserCatalogSource(fetch=lambda p: [station(URL_A, "Jazz")])
        ref = catalog.search("")["items"][0]["ref"]
        self.assertFalse(catalog.describe()["playback"]["available"])
        with self.assertRaises(MediaBackendError):
            catalog.prepare(ref)
        self.assertNotIn("url", str(catalog.inspect(ref)))


if __name__ == "__main__":
    unittest.main()
