#!/usr/bin/env python3
"""Synthetic safety/evidence checks; never connects to a live controller."""
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MEDIA = ROOT / "scripts" / "media"
sys.path.insert(0, str(MEDIA))
spec = importlib.util.spec_from_file_location("media_pause_state_probe",
                                               MEDIA / "media_pause_state_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeSafetyTest(unittest.TestCase):
    def test_sanitizes_radio_and_session_metadata(self):
        response = {
            "ok": True,
            "result": {
                "session": {"state": "pause not verified", "ownedByController": True,
                            "current": {"title": "PRIVATE TITLE",
                                        "uri": "https://secret.example/stream"}},
                "loaded": {"ref": {"source": "radio-browser", "id": "https://secret.example"},
                           "queueId": "private-id", "cueUri": "http://127.0.0.1/radio/token"},
                "radioHealth": {"state": "streaming", "bytesReceived": 1729,
                                "errorCode": "SECRET_PRIVATE_ERROR"},
            }
        }
        result = probe.sanitized_record(response, previous_bytes=1700)
        self.assertEqual(result["mpdState"], "unknown")
        self.assertEqual(result["loadedSource"], "radio-browser")
        self.assertEqual(result["relayBytesDelta"], 29)
        self.assertEqual(result["relayState"], "streaming")
        self.assertTrue(result["controllerOwnsPlayback"])
        import json
        rendered = json.dumps(result)
        for secret in ("PRIVATE TITLE", "secret.example", "token",
                       "queueId", "SECRET_PRIVATE_ERROR", "private-id"):
            self.assertNotIn(secret, rendered)

    def test_handles_empty_or_malformed_responses(self):
        result = probe.sanitized_record({"ok": False, "error": {"code": "TOKEN_TOO_PRIVATE"}})
        self.assertFalse(result["snapshotOk"])
        self.assertEqual(result["errorCode"], "unavailable")
        self.assertEqual(result["loadedSource"], "none")
        self.assertIsNone(result["relayBytesDelta"])
        state = probe.sanitized_record({
            "ok": True,
            "result": {"session": {"state": "paused", "ownedByController": False},
                       "radioHealth": {"state": "ended", "bytesReceived": "leaked"},
                       "loaded": {"ref": {"source": "radio-browser"}}}
        })
        self.assertEqual(state["mpdState"], "paused")
        self.assertIsNone(state["relayBytesReceived"])

    def test_no_transport_or_network_mutation_paths(self):
        source = (MEDIA / "media_pause_state_probe.py").read_text()
        self.assertIn('send(path, "snapshot")', source)
        for forbidden in ('send(path, "play")', 'send(path, "pause")',
                          'send(path, "stop")', 'subprocess.', 'requests.',
                          'os.kill(', 'pactl', 'mpc pause', 'mpc stop'):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
