#!/usr/bin/env python3
"""No-hardware tests for Hi-Fi controller v0 and its MPD wire boundary."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import socketserver
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "media"))

from headless_mpd import MpdBackend, MediaBackendError, mpd_quote, parse_records
from media_controller import MediaController
from media_controller_server import HiFiServer, prepare_directory


class FakeMpd:
    id = "mpd"
    required_kind = "mpd-local-track"

    def __init__(self):
        self.available = True
        self.calls = []
        self.entries = {"music/one.ogg": "First", "music/two.ogg": "Second"}
        self.queue_items = []
        self.playing_id = None
        self.status = "stop"

    def command(self, command, *args):
        self.calls.append((command, *args))
        if not self.available:
            raise MediaBackendError("BACKEND_OFFLINE", "No MPD")
        if command == "search":
            needle = args[1].lower()
            lines = []
            for path, title in self.entries.items():
                if needle in title.lower() or needle in path.lower():
                    lines.extend(["file: " + path, "Title: " + title])
            return lines
        if command == "lsinfo":
            uri = args[0]
            return ["file: " + uri, "Title: " + self.entries[uri]] if uri in self.entries else []
        if command == "status":
            return ["state: " + self.status, "playlistlength: " + str(len(self.queue_items))]
        if command == "currentsong":
            item = next((x for x in self.queue_items if x["id"] == self.playing_id), None)
            return (["file: " + item["uri"], "Id: " + item["id"]]
                    if item else [])
        if command == "playlistinfo":
            result = []
            for pos, item in enumerate(self.queue_items):
                result.extend(["file: " + item["uri"], "Id: " + item["id"],
                               "Pos: " + str(pos)])
            return result
        if command == "addid":
            ident = str(len(self.queue_items) + 100)
            self.queue_items.append({"id": ident, "uri": args[0]})
            return ["Id: " + ident]
        if command == "playid":
            self.playing_id = args[0]
            self.status = "play"
            return []
        if command == "pause":
            self.status = "pause"
            return []
        if command == "stop":
            self.status = "stop"
            return []
        if command == "seekcur":
            return []
        if command == "next" or command == "previous":
            return []
        if command == "deleteid":
            self.queue_items = [x for x in self.queue_items if x["id"] != args[0]]
            return []
        raise AssertionError("Unexpected MPD command: " + command)

    def probe(self):
        return {"id": self.id, "available": self.available,
                "reason": "" if self.available else "No MPD", "capabilities": ["cue"]}

    def observe(self):
        song = next((x for x in self.queue_items if x["id"] == self.playing_id), None)
        return {"backend": "mpd", "state": self.status, "observed": True,
                "current": {"queueId": song["id"]} if song else None}

    def queue(self):
        return [{"queueId": x["id"], "ref": {"source": "local-mpd",
                 "kind": "track", "id": x["uri"]}} for x in self.queue_items]

    def cue(self, prepared):
        return self.command("addid", prepared["uri"])[0].split(": ", 1)[1]

    def play_id(self, song_id):
        self.command("playid", song_id)

    def transport(self, op, seconds=None):
        return self.command("seekcur" if op == "seek_relative" else op,
                            *([f"{seconds:+d}"] if seconds is not None else
                              ["1"] if op == "pause" else []))

    def remove(self, song_id):
        self.command("deleteid", song_id)


def ref(uri="music/one.ogg"):
    return {"source": "local-mpd", "kind": "track", "id": uri}


class HiFiControllerTests(unittest.TestCase):
    def setUp(self):
        self.mpd = FakeMpd()
        self.c = MediaController(self.mpd)

    def test_search_does_not_select_load_or_play(self):
        response = self.c.request({"version": 1, "op": "search", "args":
                                   {"source": "local-mpd", "query": "first"}})
        self.assertTrue(response["ok"], response)
        self.assertEqual(len(response["result"]["browse"]["items"]), 1)
        self.assertIsNone(self.c.selection)
        self.assertIsNone(self.c.loaded)
        self.assertFalse(any(cmd[0] in ("addid", "playid") for cmd in self.mpd.calls))

    def test_select_and_load_do_not_autoplay(self):
        self.assertTrue(self.c.request({"version": 1, "op": "select",
                                        "args": {"ref": ref()}})["ok"])
        self.assertEqual(self.c.selection, ref())
        self.assertIsNone(self.c.loaded)
        self.assertTrue(self.c.request({"version": 1, "op": "load"})["ok"])
        self.assertEqual(self.c.loaded["queueId"], "100")
        self.assertEqual(self.mpd.status, "stop")
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))
        self.assertTrue(self.c.request({"version": 1, "op": "play"})["ok"])
        self.assertEqual(self.mpd.status, "play")
        self.assertTrue(self.c.snapshot()["session"]["ownedByController"])

    def test_browse_another_track_preserves_loaded_session(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        old_loaded = self.c.loaded.copy()
        self.c.dispatch("search", {"query": "second"})
        self.c.dispatch("select", {"ref": ref("music/two.ogg")})
        self.assertEqual(self.c.loaded, old_loaded)
        self.assertTrue(self.c.snapshot()["session"]["ownedByController"])
        self.assertEqual(self.mpd.status, "play")

    def test_loading_b_preserves_playing_a_control_until_play(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        first_id = self.c.owned_active_id
        self.c.dispatch("select", {"ref": ref("music/two.ogg")})
        self.c.dispatch("load")
        self.assertEqual(self.c.owned_active_id, first_id)
        self.assertTrue(self.c.snapshot()["session"]["ownedByController"])
        self.assertEqual(self.mpd.playing_id, first_id)
        self.assertTrue(self.c.request({"version": 1, "op": "pause"})["ok"])
        self.assertEqual(self.mpd.status, "pause")
        self.c.dispatch("play")
        self.assertEqual(self.mpd.playing_id, self.c.loaded["queueId"])
        self.assertNotEqual(self.c.owned_active_id, first_id)

    def test_failed_switch_keeps_old_owned_queue(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        original = self.c.owned_active.copy()
        self.c.dispatch("load", {"ref": ref("music/two.ogg")})
        original_playid = self.mpd.play_id
        def refused(song_id):
            raise MediaBackendError("BACKEND_REJECTED", "station unavailable")
        self.mpd.play_id = refused
        try:
            failure = self.c.request({"version": 1, "op": "play"})
            self.assertFalse(failure["ok"])
            self.assertEqual(self.c.owned_active, original)
            self.assertTrue(self.c.snapshot()["session"]["ownedByController"])
            self.assertTrue(self.c.request({"version": 1, "op": "pause"})["ok"])
        finally:
            self.mpd.play_id = original_playid

    def test_external_queue_replacement_never_gains_ownership(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        self.c.dispatch("load", {"ref": ref("music/two.ogg")})
        self.mpd.queue_items[0]["uri"] = "music/two.ogg"
        denied = self.c.request({"version": 1, "op": "pause"})
        self.assertEqual(denied["error"]["code"], "OWNED_TRACK_STALE")

    def test_playid_success_without_matching_observation_does_not_transfer(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        former = self.c.owned_active_id
        self.c.dispatch("load", {"ref": ref("music/two.ogg")})
        original_playid = self.mpd.play_id
        self.mpd.play_id = lambda song_id: None
        try:
            failure = self.c.request({"version": 1, "op": "play"})
            self.assertEqual(failure["error"]["code"], "PLAY_NOT_CONFIRMED")
            self.assertEqual(self.c.owned_active_id, former)
        finally:
            self.mpd.play_id = original_playid

    def test_queue_add_does_not_replace_loaded_track(self):
        self.c.dispatch("load", {"ref": ref()})
        loaded = self.c.loaded.copy()
        self.c.dispatch("queue_add", {"ref": ref("music/two.ogg")})
        self.assertEqual(self.c.loaded, loaded)
        self.assertEqual(len(self.c.dispatch("queue")["items"]), 2)
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))

    def test_external_playback_change_blocks_transport(self):
        self.c.dispatch("load", {"ref": ref(), "autoplay": True})
        self.mpd.queue_items.append({"id": "900", "uri": "music/two.ogg"})
        self.mpd.playing_id = "900"
        response = self.c.request({"version": 1, "op": "pause"})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "PLAYBACK_CHANGED_EXTERNALLY")
        self.assertFalse(any(c[0] == "pause" for c in self.mpd.calls))

    def test_queue_remove_rejects_unowned_current_song(self):
        self.mpd.queue_items = [{"id": "900", "uri": "music/two.ogg"}]
        self.mpd.playing_id = "900"
        self.mpd.status = "play"
        response = self.c.request({"version": 1, "op": "queue_remove",
                                   "args": {"queueId": "900"}})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "ACTIVE_TRACK")
        self.assertFalse(any(c[0] == "deleteid" for c in self.mpd.calls))

    def test_direct_dispatch_without_arguments(self):
        self.assertEqual(self.c.dispatch("queue"), {"items": []})
        self.assertEqual(self.c.dispatch("sources")["sources"][0]["id"], "local-mpd")

    def test_no_loaded_media_rejects_play(self):
        response = self.c.request({"version": 1, "op": "play"})
        self.assertEqual(response["error"]["code"], "NO_LOADED_MEDIA")

    def test_source_unavailable_still_reports_health(self):
        self.mpd.available = False
        health = self.c.request({"version": 1, "op": "health"})
        self.assertTrue(health["ok"])
        self.assertFalse(health["result"]["backend"]["available"])
        self.assertFalse(self.c.request({"version": 1, "op": "load",
                                         "args": {"ref": ref()}})["ok"])

    def test_missing_track_or_foreign_source_fails_closed(self):
        self.assertEqual(self.c.request({"version": 1, "op": "select",
                         "args": {"ref": ref("missing")}})["error"]["code"], "NOT_FOUND")
        self.assertEqual(self.c.request({"version": 1, "op": "select",
                         "args": {"ref": {"source": "unknown-future-provider", "kind": "track",
                                           "id": "abc"}}})["error"]["code"], "UNKNOWN_SOURCE")

    def test_no_unverified_player_volume(self):
        r = self.c.request({"version": 1, "op": "set_player_volume",
                            "args": {"percent": 70}})
        self.assertEqual(r["error"]["code"], "UNAVAILABLE")
        self.assertFalse(any(c[0] == "volume" for c in self.mpd.calls))

    def test_autoplay_must_be_explicit_boolean(self):
        response = self.c.request({"version": 1, "op": "load",
                                   "args": {"ref": ref(), "autoplay": "true"}})
        self.assertFalse(response["ok"])
        self.assertFalse(any(c[0] in ("addid", "playid") for c in self.mpd.calls))

    def test_seeking_requires_controller_ownership(self):
        self.c.dispatch("load", {"ref": ref()})
        denied = self.c.request({"version": 1, "op": "seek_relative",
                                 "args": {"seconds": 5}})
        self.assertEqual(denied["error"]["code"], "NO_OWNED_PLAYBACK")
        self.c.dispatch("play")
        self.assertTrue(self.c.request({"version": 1, "op": "seek_relative",
                                       "args": {"seconds": -5}})["ok"])
        self.assertIn(("seekcur", "-5"), self.mpd.calls)

    def test_malformed_request_and_no_mutation(self):
        self.assertFalse(self.c.request({"version": 0, "op": "play"})["ok"])
        self.assertFalse(self.c.request({"version": 1, "op": "go-wild"})["ok"])
        self.assertFalse(self.c.request(None)["ok"])
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))


class MpdWireTests(unittest.TestCase):
    def test_quote_escapes_and_rejects_newlines(self):
        self.assertEqual(mpd_quote('song "quoted" \\ old'), '"song \\"quoted\\" \\\\ old"')
        with self.assertRaises(MediaBackendError):
            mpd_quote("track\nplay")
        with self.assertRaises(MediaBackendError):
            mpd_quote("track\rplay")

    def test_record_parser_keeps_individual_tracks(self):
        self.assertEqual(parse_records(["file: x", "Title: X", "file: y", "Title: Y"]),
                         [{"file": "x", "Title": "X"}, {"file": "y", "Title": "Y"}])

    def test_real_socket_wire_uses_single_escaped_command(self):
        received = []
        class MPDHandler(socketserver.StreamRequestHandler):
            def handle(self):
                self.wfile.write(b"OK MPD 0.23.8\n")
                self.wfile.flush()
                received.append(self.rfile.readline().decode("utf-8"))
                self.wfile.write(b"Id: 3\nOK\n")
                self.wfile.flush()
        with socketserver.TCPServer(("127.0.0.1", 0), MPDHandler) as srv:
            thread = threading.Thread(target=srv.handle_request)
            thread.start()
            backend = MpdBackend("127.0.0.1", srv.server_address[1])
            self.assertEqual(backend.command("addid", 'music/"one".ogg'), ["Id: 3"])
            thread.join(timeout=3)
        self.assertEqual(received, ['addid "music/\\"one\\".ogg"\n'])


class SocketApiTests(unittest.TestCase):
    def test_private_unix_protocol_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "controller.sock"
            prepare_directory(path)
            server = HiFiServer(str(path), MediaController(FakeMpd()))
            try:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                with socket.socket(socket.AF_UNIX) as client:
                    client.connect(str(path))
                    client.sendall(b'{"version":1,"op":"sources","args":{}}\n')
                    raw = client.recv(32768)
                response = json.loads(raw)
                self.assertTrue(response["ok"])
                self.assertEqual(response["result"]["sources"][0]["id"], "local-mpd")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
