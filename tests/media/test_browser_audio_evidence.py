#!/usr/bin/env python3
"""Pure regression tests for the read-only Hi-Fi browser evidence collector.

Run: python3 -m unittest discover -s tests/media -p 'test_browser_audio_evidence.py'
No PipeWire, MPRIS, browser, or DevTools session is required.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "media" / "browser_audio_evidence.py"
SPEC = importlib.util.spec_from_file_location("browser_audio_evidence", SOURCE)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class BrowserAudioEvidenceTests(unittest.TestCase):
    def test_existing_brave_devtools_endpoint(self):
        argv = [
            "/opt/brave.com/brave/brave",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=9222",
        ]
        self.assertEqual(PROBE.debug_port_for_argv(argv), 9222)

    def test_existing_chromium_space_separated_port(self):
        argv = ["chromium", "--remote-debugging-port", "9224"]
        self.assertEqual(PROBE.debug_port_for_argv(argv), 9224)

    def test_reject_unrelated_process_using_same_switch(self):
        self.assertIsNone(PROBE.debug_port_for_argv(
            ["fake-local-daemon", "--remote-debugging-port=9222"]
        ))

    def test_absent_or_invalid_port_is_not_invented(self):
        self.assertIsNone(PROBE.debug_port_for_argv(["brave", "https://youtube.com"]))
        self.assertIsNone(PROBE.debug_port_for_argv(
            ["brave", "--remote-debugging-port=0"]
        ))
        self.assertIsNone(PROBE.debug_port_for_argv(
            ["brave", "--remote-debugging-port=65536"]
        ))
        self.assertIsNone(PROBE.debug_port_for_argv(
            ["brave", "--remote-debugging-port=wrong"]
        ))

    def test_devtools_sanitization_drops_full_url_and_websocket(self):
        payload = [
            {
                "type": "page",
                "id": "tab-A",
                "title": "Music Video",
                "url": "https://www.youtube.com/watch?v=secret-token",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/secret"
            },
            {
                "type": "service_worker",
                "id": "worker-A",
                "title": "Background",
                "url": "https://example.org/private"
            }
        ]
        rows = PROBE.sanitize_devtools_targets(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["targetId"], "tab-A")
        self.assertEqual(rows[0]["title"], "Music Video")
        self.assertEqual(rows[0]["urlHost"], "www.youtube.com")
        self.assertNotIn("url", rows[0])
        self.assertNotIn("webSocketDebuggerUrl", rows[0])

    def test_malformed_devtools_payload_returns_no_rows(self):
        self.assertEqual(PROBE.sanitize_devtools_targets(None), [])
        self.assertEqual(PROBE.sanitize_devtools_targets({"error": 1}), [])


if __name__ == "__main__":
    unittest.main()
