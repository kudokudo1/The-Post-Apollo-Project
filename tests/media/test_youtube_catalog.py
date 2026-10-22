#!/usr/bin/env python3
"""Official YouTube catalog adapter regression tests: all requests fake-only."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from headless_mpd import MediaBackendError
from youtube_catalog import YouTubeCatalogSource
from media_controller import MediaController
from test_headless_controller import FakeMpd, ref


VIDEO_ID = "AbCdEf12345"
PLAYLIST_ID = "PL0123456789"
YOUTUBE_REF = {"source": "youtube", "kind": "video", "id": VIDEO_ID}
PLAYLIST_REF = {"source": "youtube", "kind": "playlist", "id": PLAYLIST_ID}


class FakeCatalog:
    def __init__(self):
        self.requests = []

    def __call__(self, resource, params):
        self.requests.append((resource, params))
        if resource == "search":
            return {"items": [{"id": {"videoId": VIDEO_ID},
                     "snippet": {"title": "Test track", "channelTitle": "Artist"}}],
                    "nextPageToken": "PAGE2"}
        if resource == "videos":
            return {"items": [{"id": VIDEO_ID,
                     "snippet": {"title": "Test track", "channelTitle": "Artist"}}]}
        if resource == "playlistItems":
            return {"items": [{"contentDetails": {"videoId": VIDEO_ID},
                     "snippet": {"title": "Test track"}}]}
        raise AssertionError("Invalid endpoint")


class YouTubeCatalogTests(unittest.TestCase):
    def setUp(self):
        self.fetch = FakeCatalog()
        self.youtube = YouTubeCatalogSource(api_key="test-only", fetch=self.fetch)

    def test_no_key_disables_discovery(self):
        source = YouTubeCatalogSource(api_key="", fetch=self.fetch)
        self.assertFalse(source.describe()["available"])
        with self.assertRaises(MediaBackendError) as captured:
            source.search("music")
        self.assertEqual(captured.exception.code, "SOURCE_NOT_CONFIGURED")
        self.assertEqual(self.fetch.requests, [])

    def test_search_is_catalog_only_and_pageable(self):
        result = self.youtube.search("monster", cursor="PAGE1")
        self.assertEqual(result["items"][0]["ref"], YOUTUBE_REF)
        self.assertEqual(result["nextCursor"], "PAGE2")
        self.assertFalse(result["items"][0]["playback"]["available"])
        resource, params = self.fetch.requests[-1]
        self.assertEqual(resource, "search")
        self.assertEqual(params["type"], "video")
        self.assertEqual(params["pageToken"], "PAGE1")
        self.assertNotIn("key", params)

    def test_inspect_exact_id_only(self):
        item = self.youtube.inspect(YOUTUBE_REF)
        self.assertEqual(item["title"], "Test track")
        with self.assertRaises(MediaBackendError):
            self.youtube.inspect({"source": "youtube", "kind": "video", "id": "bad"})
        with self.assertRaises(MediaBackendError):
            self.youtube.inspect({"source": "local-mpd", "kind": "track", "id": VIDEO_ID})

    def test_playlist_browse_is_not_playback(self):
        result = self.youtube.list(PLAYLIST_REF, cursor="NEXTPAGE")
        self.assertEqual(result["items"][0]["ref"], YOUTUBE_REF)
        resource, params = self.fetch.requests[-1]
        self.assertEqual(resource, "playlistItems")
        self.assertEqual(params["playlistId"], PLAYLIST_ID)
        self.assertEqual(params["pageToken"], "NEXTPAGE")

    def test_fail_closed_invalid_cursor_and_playlist(self):
        with self.assertRaises(MediaBackendError):
            self.youtube.search("song", cursor="\\nsecret")
        with self.assertRaises(MediaBackendError):
            self.youtube.list({"source": "youtube", "kind": "playlist", "id": "../../bad"})
        self.assertFalse(self.fetch.requests)

    def test_prepare_always_rejects_without_network_or_play(self):
        with self.assertRaises(MediaBackendError) as captured:
            self.youtube.prepare(YOUTUBE_REF)
        self.assertEqual(captured.exception.code, "PLAYBACK_UNAVAILABLE")
        self.assertEqual(self.fetch.requests, [])

    def test_malformed_provider_payload_fails(self):
        bad = YouTubeCatalogSource(api_key="test-only", fetch=lambda r, p: {"items": "bad"})
        with self.assertRaises(MediaBackendError) as captured:
            bad.search("music")
        self.assertEqual(captured.exception.code, "SOURCE_PROTOCOL")


class ControllerCatalogTests(unittest.TestCase):
    def setUp(self):
        self.mpd = FakeMpd()
        self.controller = MediaController(self.mpd)
        self.fetch = FakeCatalog()
        self.controller.sources["youtube"] = YouTubeCatalogSource(api_key="test-only",
                                                                   fetch=self.fetch)

    def test_local_playback_unaffected_by_youtube_browsing(self):
        self.controller.dispatch("load", {"ref": ref(), "autoplay": True})
        loaded_before = self.controller.loaded.copy()
        self.controller.dispatch("search", {"source": "youtube", "query": "monster"})
        self.controller.dispatch("select", {"ref": YOUTUBE_REF})
        self.controller.dispatch("list", {"source": "youtube", "collection": PLAYLIST_REF})
        self.assertEqual(self.controller.loaded, loaded_before)
        self.assertEqual(self.mpd.status, "play")
        self.assertTrue(self.controller.snapshot()["session"]["ownedByController"])
        self.assertEqual([x[0] for x in self.mpd.calls].count("playid"), 1)

    def test_youtube_load_fails_and_does_not_touch_mpd(self):
        self.controller.dispatch("select", {"ref": YOUTUBE_REF})
        before = self.mpd.calls[:]
        result = self.controller.request({"version": 1, "op": "load"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "PLAYBACK_UNAVAILABLE")
        self.assertEqual(self.mpd.calls, before)
        self.assertIsNone(self.controller.loaded)

    def test_source_availability_independent_of_local(self):
        info = self.controller.dispatch("sources")
        self.assertEqual({i["id"] for i in info["sources"]}, {"youtube", "local-mpd", "direct-stream", "radio-browser"})
        self.assertEqual(self.controller.dispatch("health")["backend"]["id"], "mpd")

    def test_local_search_cursor_denied(self):
        result = self.controller.request({"version": 1, "op": "search",
                   "args": {"source": "local-mpd", "query": "first", "cursor": "NEXT"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "PAGINATION_UNSUPPORTED")

    def test_list_mpds_unsupported(self):
        result = self.controller.request({"version": 1, "op": "list",
                   "args": {"source": "local-mpd", "collection": PLAYLIST_REF}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
