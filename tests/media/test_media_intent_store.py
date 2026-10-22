#!/usr/bin/env python3
"""Fail-closed persistence and recovery tests for Hi-Fi intent (no live MPD)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "media"))
from media_intent_store import IntentStore
from media_controller import MediaController
from test_headless_controller import FakeMpd, ref


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "media" / "controller-intent-v1.json"
        self.store = IntentStore(self.path)
        self.mpd = FakeMpd()
        self.c = MediaController(self.mpd, intent_store=self.store)

    def test_no_file_until_a_real_intent(self):
        self.assertFalse(self.path.exists())
        self.c.dispatch("search", {"query": "first"})
        self.assertFalse(self.path.exists())

    def test_restart_restores_loaded_queue_without_seizing_playback(self):
        self.c.dispatch("select", {"ref": ref()})
        # Direct controller invocation is the same boundary used by socket requests.
        self.c.dispatch("load", {"autoplay": True})
        self.assertTrue(self.path.exists())
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        assert self.mpd.status == "play"
        self.mpd.calls.clear()
        restarted = MediaController(self.mpd, intent_store=self.store)
        self.assertEqual(restarted.selection, ref())
        self.assertEqual(restarted.loaded["queueId"], "100")
        self.assertEqual(restarted.loaded["ref"], ref())
        self.assertIsNone(restarted.owned_active_id)
        self.assertFalse(restarted.snapshot()["session"]["ownedByController"])
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))
        denied = restarted.request({"version": 1, "op": "pause"})
        self.assertEqual(denied["error"]["code"], "NO_OWNED_PLAYBACK")

    def test_restart_rejects_reassigned_queue_id_even_if_it_is_playing(self):
        self.c.dispatch("load", {"ref": ref()})
        # Fake replaces entry with identical ID but another file.
        self.mpd.queue_items[0]["uri"] = "music/two.ogg"
        restarted = MediaController(self.mpd, intent_store=self.store)
        self.assertIsNone(restarted.loaded)
        self.assertIsNone(restarted.active_backend)
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))

    def test_play_validates_queue_id_and_file_against_external_change(self):
        self.c.dispatch("load", {"ref": ref()})
        self.mpd.queue_items[0]["uri"] = "music/two.ogg"
        response = self.c.request({"version": 1, "op": "play"})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "LOADED_TRACK_STALE")
        self.assertIsNone(self.c.loaded)
        self.assertFalse(any(c[0] == "playid" for c in self.mpd.calls))
        self.assertIsNone(self.store.load().get("loaded"))

    def test_selection_persists_separately_from_loaded_track(self):
        self.c.dispatch("select", {"ref": ref()})
        restarted = MediaController(self.mpd, intent_store=self.store)
        self.assertEqual(restarted.selection, ref())
        self.assertIsNone(restarted.loaded)

    def test_offline_mpd_never_adopts_loaded_state(self):
        self.c.dispatch("load", {"ref": ref()})
        class OfflineFake(FakeMpd):
            def queue(self):
                from headless_mpd import MediaBackendError
                raise MediaBackendError("BACKEND_OFFLINE", "not running")
        restored = MediaController(OfflineFake(), intent_store=self.store)
        self.assertIsNone(restored.loaded)
        self.assertIsNone(restored.owned_active_id)

    def test_unrecognized_format_is_not_accepted(self):
        self.path.parent.mkdir(mode=0o700)
        self.path.write_text(json.dumps({"version": 89, "selection": ref()}))
        self.path.chmod(0o600)
        self.assertEqual(self.store.load(), {})

    def test_permissive_file_is_rejected(self):
        self.path.parent.mkdir(mode=0o700)
        self.path.write_text(json.dumps({"version": 1, "selection": ref()}))
        self.path.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.store.load()

    def test_symlink_file_refused_without_modifying_target(self):
        self.path.parent.mkdir(mode=0o700)
        target = Path(self.temp.name) / "victim.json"
        target.write_text("victim")
        self.path.symlink_to(target)
        with self.assertRaises(OSError):
            self.store.load()
        self.assertEqual(target.read_text(), "victim")

    def test_invalid_state_does_not_block_browsing(self):
        self.path.parent.mkdir(mode=0o700)
        self.path.write_bytes(b"{invalid-json")
        recovering = MediaController(self.mpd, intent_store=self.store)
        self.assertEqual(recovering.persistence_error, "STATE_LOAD_FAILED")
        response = recovering.request({"version": 1, "op": "search",
                                      "args": {"query": "first"}})
        self.assertTrue(response["ok"])

    def test_radio_directory_uuid_selection_survives_restart_without_loading(self):
        import uuid
        ref = {"source": "radio-browser", "kind": "station",
               "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "https://example.com/station"))}
        self.store.save(ref, None)
        self.assertEqual(self.store.load().get("selection"), ref)
        self.assertIsNone(self.store.load().get("loaded"))
        restarted = MediaController(self.mpd, intent_store=self.store)
        self.assertEqual(restarted.selection, ref)
        self.assertIsNone(restarted.loaded)
        self.assertIsNone(restarted.owned_active_id)
        self.assertFalse(any(call[0] in ("addid", "playid") for call in self.mpd.calls))
        for bad in ("not-a-uuid", "ABCDEF", ref["id"].upper()):
            with self.assertRaises(ValueError):
                self.store.save({**ref, "id": bad}, None)

    def test_no_credentials_or_browse_query_written(self):
        self.c.dispatch("search", {"source": "local-mpd", "query": "private-query"})
        self.c.dispatch("select", {"ref": ref()})
        raw = self.path.read_text()
        self.assertNotIn("private-query", raw)
        self.assertNotIn("YOUTUBE_API_KEY", raw)
        self.assertEqual(self.store.load()["selection"], ref())


if __name__ == "__main__":
    unittest.main()
