#!/usr/bin/env python3
"""Offline safety contract for independent NEWS viewer V0 preflight."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/weather/news_viewer_preflight.py"
SPEC = importlib.util.spec_from_file_location("news_viewer_preflight", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class PreflightTests(unittest.TestCase):
    def test_allowlist_registered_destinations(self):
        approved = MOD.sources()
        self.assertEqual(len(approved), 18)
        self.assertEqual(approved["cspan"]["section"], "CONGRESS")
        self.assertEqual(approved["cspan"]["url"], "https://www.c-span.org/")
        for sid, info in approved.items():
            self.assertTrue(MOD.SOURCE_ID.fullmatch(sid))
            self.assertTrue(MOD.trusted_https(info["url"]))
            self.assertEqual(MOD.resolved_target("source", sid)["url"], info["url"])

    def test_unknown_target_rejected(self):
        for kind, ident in [
            ("source", "../../etc/passwd"),
            ("source", "cspan;sh -c evil"),
            ("source", "https://evil.example/"),
            ("source", "unknown-network"),
            ("youtube-channel", "UCfake"),
            ("youtube-video", "../abc123456"),
            ("youtube-video", "https://example.org/"),
        ]:
            self.assertIsNone(MOD.resolved_target(kind, ident), (kind, ident))

    def test_youtube_id_only(self):
        video_id = "abcDEF012_-"
        channel_id = "UC" + "Z" * 22
        self.assertEqual(MOD.resolved_target("youtube-video", video_id)["url"],
                         "https://www.youtube.com/watch?v=" + video_id)
        self.assertEqual(MOD.resolved_target("youtube-channel", channel_id)["url"],
                         "https://www.youtube.com/channel/" + channel_id)

    def test_inspect_browser_does_not_run(self):
        with patch.object(MOD.shutil, "which", return_value=None) as which:
            result = MOD.report()
            self.assertFalse(result["browser"]["available"])
            self.assertEqual(result["state"], "BLOCKED_VIEWPORT_UNAVAILABLE")
            self.assertFalse(result["can_launch"])
            self.assertFalse(result["can_play"])
            self.assertTrue(result["muted"])
            self.assertIsNone(result["target"])
            self.assertFalse(result["stage_director"]["clip_verified"])
            self.assertEqual(which.call_count, len(MOD.BROWSER_CANDIDATES))
        with patch.object(MOD.shutil, "which", side_effect=lambda n: "/usr/bin/" + n if n == "chromium" else None):
            result = MOD.report()
            self.assertTrue(result["browser"]["available"])
            self.assertEqual(result["browser"]["preferred"], "chromium")
            self.assertFalse(result["can_launch"])

    def test_cli_inspect_is_read_only_json(self):
        with patch.object(MOD.shutil, "which", return_value=None):
            out = io.StringIO()
            with redirect_stdout(out):
                code = MOD.main(["inspect"])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.getvalue())["can_launch"])

    def test_cli_plan_never_authorizes_launch(self):
        with patch.object(MOD.shutil, "which", return_value="/usr/bin/chromium"):
            out = io.StringIO()
            with redirect_stdout(out):
                code = MOD.main(["plan", "--kind", "source", "--id", "house"])
            self.assertEqual(code, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["target"]["url"], "https://live.house.gov/")
            self.assertFalse(result["can_launch"])
            self.assertEqual(result["role"], "post-apollo-weather-news")

    def test_cli_invalid_target_hard_stop(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = MOD.main(["plan", "--kind", "source", "--id", "not-registered"])
        self.assertEqual(code, 2)
        result = json.loads(out.getvalue())
        self.assertEqual(result["state"], "INVALID_TARGET")
        self.assertFalse(result["can_launch"])

    def test_no_side_effects_in_preflight_module(self):
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in ["subprocess", "Popen(", "os.system(", "urlopen(",
                          "requests.", "socket.", "swaymsg", "startDetached",
                          "QtWebEngine", "os.exec", "shutil.copy"]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
