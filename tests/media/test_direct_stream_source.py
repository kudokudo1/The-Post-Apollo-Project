#!/usr/bin/env python3
"""Direct HTTPS audio source: playback is explicit, browser-free, and fail-closed."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from direct_stream_source import DirectHttpsStreamSource, validate_https_audio_url
from headless_mpd import MediaBackendError, MpdBackend, track_item
from media_controller import MediaController
from media_intent_store import IntentStore
from test_headless_controller import FakeMpd, ref as local_ref


URL = "https://ice5.somafm.com/groovesalad-128-mp3"
REF = {"source": "direct-stream", "kind": "stream", "id": URL}


class StreamFakeMpd(FakeMpd):
    required_kinds = ("mpd-local-track", "mpd-https-stream")

    def queue(self):
        return [track_item({"file": x["uri"], "Id": x["id"]})
                for x in self.queue_items]


class DirectStreamTests(unittest.TestCase):
    def setUp(self):
        self.mpd = StreamFakeMpd()
        self.controller = MediaController(self.mpd)
        self.source = DirectHttpsStreamSource(self.mpd)

    def test_no_library_needed_for_stream_source(self):
        self.assertFalse(self.mpd.queue_items)
        self.assertEqual(self.source.describe()["requirements"], ["mpd-https-stream"])
        self.assertTrue(self.source.describe()["available"])
        self.assertNotIn("search", self.source.describe()["capabilities"])

    def test_inspect_is_pure_and_does_not_start_music(self):
        item = self.source.inspect(REF)
        self.assertEqual(item["ref"], REF)
        self.assertTrue(item["live"])
        self.assertEqual(self.mpd.calls, [])

    def test_select_load_explicit_play(self):
        select = self.controller.request({"version": 1, "op": "select",
                                          "args": {"ref": REF}})
        self.assertTrue(select["ok"], select)
        self.assertIsNone(self.controller.loaded)
        load = self.controller.request({"version": 1, "op": "load"})
        self.assertTrue(load["ok"], load)
        self.assertEqual(self.controller.loaded["ref"], REF)
        self.assertIn(("addid", URL), self.mpd.calls)
        self.assertFalse(any(row[0] == "playid" for row in self.mpd.calls))
        self.assertEqual(self.mpd.status, "stop")
        play = self.controller.request({"version": 1, "op": "play"})
        self.assertTrue(play["ok"], play)
        self.assertEqual(self.mpd.status, "play")
        self.assertTrue(self.controller.snapshot()["session"]["ownedByController"])

    def test_direct_load_preserves_running_local_song_until_play(self):
        self.controller.dispatch("load", {"ref": local_ref(), "autoplay": True})
        self.assertEqual(self.mpd.status, "play")
        old_play_id = self.mpd.playing_id
        self.controller.dispatch("load", {"ref": REF})
        self.assertEqual(self.mpd.playing_id, old_play_id)
        self.assertEqual([row[0] for row in self.mpd.calls].count("playid"), 1)
        # Newly loaded item is not the currently playing item.
        self.assertFalse(self.controller.snapshot()["session"]["ownedByController"])

    def test_existing_youtube_video_is_not_accepted_as_stream(self):
        with self.assertRaises(MediaBackendError):
            self.source.inspect({"source": "direct-stream", "kind": "stream",
                                 "id": "https://www.youtube.com/watch"})
        self.assertFalse(any(row[0] == "addid" for row in self.mpd.calls))

    def test_controller_search_stream_is_cleanly_unsupported(self):
        response = self.controller.request({"version": 1, "op": "search",
                                            "args": {"source": "direct-stream", "query": "x"}})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "UNSUPPORTED")

    def test_queue_source_ref_is_not_local_mpd(self):
        self.mpd.queue_items.append({"id": "100", "uri": URL})
        response = self.controller.dispatch("queue")
        self.assertEqual(response["items"][0]["ref"], REF)

    def test_backend_rejects_unvalidated_unsupported_streams(self):
        backend = MpdBackend()
        backend.command = Mock(return_value=["Id: 401"])
        with self.assertRaises(MediaBackendError):
            backend.cue({"requiredKind": "mpd-https-stream",
                         "uri": "http://127.0.0.1/private"})
        backend.command.assert_not_called()
        self.assertEqual(
            backend.cue({"requiredKind": "mpd-https-stream", "uri": URL}), "401"
        )
        backend.command.assert_called_once_with("addid", URL)

    def test_restart_requires_exact_stream_queue_id_and_url(self):
        with tempfile.TemporaryDirectory() as directory:
            store = IntentStore(Path(directory) / "private" / "intent.json")
            first = MediaController(self.mpd, intent_store=store)
            first.dispatch("select", {"ref": REF})
            first.dispatch("load")
            new = MediaController(self.mpd, intent_store=store)
            self.assertEqual(new.selection, REF)
            self.assertEqual(new.loaded["ref"], REF)
            self.assertIsNone(new.owned_active_id)
            self.mpd.queue_items[0]["uri"] = "https://ice6.somafm.com/groovesalad-128-mp3"
            third = MediaController(self.mpd, intent_store=store)
            self.assertIsNone(third.loaded)
            self.assertIsNone(third.owned_active_id)

    def test_cannot_play_replaced_stream_queue_id(self):
        self.controller.dispatch("load", {"ref": REF})
        self.mpd.queue_items[0]["uri"] = "https://ice6.somafm.com/groovesalad-128-mp3"
        result = self.controller.request({"version": 1, "op": "play"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "LOADED_TRACK_STALE")
        self.assertFalse(any(cmd[0] == "playid" for cmd in self.mpd.calls))

    def test_invalid_public_stream_url_forms(self):
        invalid = [
            "http://ice5.somafm.com/groovesalad-128-mp3",
            "file:///etc/passwd",
            "https://localhost/stream",
            "https://127.0.0.1/stream",
            "https://10.0.0.1/stream",
            "https://host.local/stream",
            "https://device.internal/stream",
            "https://user:pass@radio.example.com/music",
            "https://radio.example.com:8080/stream",
            "https://radio.example.com/stream?token=secret",
            "https://radio.example.com/stream#frag",
            "https://www.youtube.com/audio",
            "https://music.youtube.com/music",
            "https://open.spotify.com/audio",
            "https://radio.example.com/a\nplay",
            "https://singlelabel/stream",
        ]
        for value in invalid:
            with self.subTest(url=value), self.assertRaises(MediaBackendError):
                validate_https_audio_url(value)

    def test_authorized_public_https_is_accepted(self):
        self.assertEqual(validate_https_audio_url(URL), URL)


if __name__ == "__main__":
    unittest.main()
