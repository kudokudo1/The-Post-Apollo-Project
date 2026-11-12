"""P1.2 real read-only Linux file inspection, no account/network access."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/publisher/PublisherMediaProbe.py"
SPEC = importlib.util.spec_from_file_location("publisher_media_probe_test", SCRIPT)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class PublisherMediaProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "fake-home"
        self.home.mkdir()
        (self.home / "Pictures").mkdir()
        self.patch_home = patch.object(probe.Path, "home", return_value=self.home)
        self.patch_home.start()
        self.addCleanup(self.patch_home.stop)

    def write(self, filename: str, data: bytes) -> Path:
        p = self.home / "Pictures" / filename
        p.write_bytes(data)
        return p

    def test_image_and_video_magic_and_read_only(self):
        cases = {
            "one.png": b"\x89PNG\r\n\x1a\nabc",
            "two.jpeg": b"\xff\xd8\xffsomejpeg",
            "three.webp": b"RIFF\x0c\x00\x00\x00WEBPpayload",
            "four.mp4": b"\x00\x00\x00\x18ftypisompayload",
            "five.webm": b"\x1a\x45\xdf\xa3webm",
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                p = self.write(name, data)
                before = p.read_bytes()
                result = probe.inspect(p.as_uri())
                self.assertTrue(result["ok"], result)
                self.assertEqual(result["sourceUrl"], p.as_uri())
                self.assertEqual(result["sizeBytes"], len(data))
                self.assertEqual(p.read_bytes(), before)
                self.assertTrue(probe.inspect(p.as_uri(), result["stamp"])["ok"])

    def test_source_changes_require_review(self):
        p = self.write("photo.png", b"\x89PNG\r\n\x1a\nalpha")
        saved = probe.inspect(p.as_uri())
        self.assertTrue(saved["ok"])
        p.write_bytes(b"\x89PNG\r\n\x1a\nchanged long content")
        self.assertEqual(probe.inspect(p.as_uri(), saved["stamp"])["reason"],
                         "SOURCE_CHANGED")
        self.assertEqual(probe.inspect(p.as_uri(), "not-a-stamp")["reason"],
                         "INVALID_STAMP")

    def test_refuses_bogus_uris_and_unsupported_types(self):
        p = self.write("photo.png", b"\x89PNG\r\n\x1a\nabc")
        for url in ("https://example.org/photo.png",
                    "file://evil.example/photo.png",
                    "file:../photo.png", p.as_uri() + "?x=1",
                    "file:///../../etc/passwd"):
            with self.subTest(url=url):
                self.assertFalse(probe.inspect(url)["ok"])
        spoofed = self.write("fake.png", b"javascript:alert(1)")
        self.assertEqual(probe.inspect(spoofed.as_uri())["reason"],
                         "MEDIA_SIGNATURE_MISMATCH")
        unsupported = self.write("unsafe.svg", b"<svg></svg>")
        self.assertEqual(probe.inspect(unsupported.as_uri())["reason"],
                         "UNSUPPORTED_MEDIA")
        missing = self.home / "Pictures" / "missing.png"
        self.assertFalse(probe.inspect(missing.as_uri())["ok"])

    def test_refuses_symlinks_hardlinks_hidden_and_nonhome(self):
        original = self.write("real.png", b"\x89PNG\r\n\x1a\nok")
        alias = self.home / "Pictures" / "alias.png"
        alias.symlink_to(original)
        self.assertEqual(probe.inspect(alias.as_uri())["reason"], "SYMLINK_FILE")
        link = self.home / "Pictures" / "hardlink.png"
        os.link(original, link)
        self.assertEqual(probe.inspect(link.as_uri())["reason"], "HARDLINK_SOURCE")
        secret = self.home / ".hidden.png"
        secret.write_bytes(b"\x89PNG\r\n\x1a\nhidden")
        self.assertEqual(probe.inspect(secret.as_uri())["reason"], "HIDDEN_SOURCE")
        outside = Path(self.temp.name) / "outside.png"
        outside.write_bytes(b"\x89PNG\r\n\x1a\nother")
        self.assertEqual(probe.inspect(outside.as_uri())["reason"], "OUTSIDE_HOME")

    def test_refuses_oversized_file_without_reading_whole_body(self):
        p = self.home / "Pictures" / "huge.png"
        with p.open("wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n")
            handle.truncate(probe.IMAGE_LIMIT + 1)
        self.assertEqual(probe.inspect(p.as_uri())["reason"], "MEDIA_SIZE_LIMIT")

    def test_cli_contract_stays_one_json_line(self):
        p = self.write("test%23.png", b"\x89PNG\r\n\x1a\n123")
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        output = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), "inspect", p.as_uri()],
            capture_output=True, text=True, check=True, env=env,
        )
        rows = output.stdout.strip().splitlines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0])["sourceUrl"], p.as_uri())
        self.assertEqual(output.stderr, "")


if __name__ == "__main__":
    unittest.main()
