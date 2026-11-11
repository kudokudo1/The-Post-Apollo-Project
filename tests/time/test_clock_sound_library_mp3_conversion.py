"""Actual MP3 -> bounded PCM WAV Sound Library import and failure regression."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/sounds/SoundLibraryHost.py"
UI = (ROOT / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
PICKER = (ROOT / "widgets/AlarmWavImportDialog.qml").read_text(encoding="utf-8")
QML = (ROOT / "services/sounds/SoundLibraryService.qml").read_text(encoding="utf-8")


def call_host(base, operation, env=None, **args):
    cmd = [sys.executable, "-I", "-B", str(HOST),
           "--data-dir", str(base), "--operation", operation]
    for name, value in args.items():
        cmd.extend(["--" + name.replace("_", "-"), str(value)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    data = json.loads(result.stdout)
    assert (result.returncode == 0) == data["ok"], (cmd, data, result.stderr)
    return data


def create_wav(path, seconds=0.7):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\0\0" * int(seconds * 48000))


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required for real MP3 conversion tests")
class MP3SoundLibraryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.source_wav = self.base / "Original.wav"
        self.mp3 = self.base / "My alarm tone.mp3"
        create_wav(self.source_wav)
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(self.source_wav), "-codec:a", "libmp3lame", "-b:a",
            "128k", str(self.mp3),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)

    def test_real_mp3_import_stores_pcm_wav_and_preserves_original(self):
        result = call_host(self.base, "import",
                           source=self.mp3.as_uri(), name="Wake up")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "imported")
        self.assertEqual(len(result["tones"]), 1)
        tone = result["tones"][0]
        self.assertRegex(tone["id"], r"^user-[a-f0-9]{64}$")
        target = Path(tone["url"].removeprefix("file://"))
        self.assertEqual(target.parent.name, "sounds-library-v1")
        self.assertTrue(target.name.endswith(".wav"))
        self.assertTrue(self.mp3.exists())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        with wave.open(str(target), "rb") as w:
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 48000)
            self.assertEqual(w.getcomptype(), "NONE")
            self.assertTrue(0.2 <= w.getnframes() / w.getframerate() <= 30)
        self.assertEqual(call_host(self.base, "list")["tones"], result["tones"])
        again = call_host(self.base, "import", source=self.mp3.as_uri(), name="Duplicate")
        self.assertTrue(again["ok"])
        self.assertEqual(again["status"], "already-imported")
        self.assertEqual(len(again["tones"]), 1)
        self.assertFalse(any(p.name.startswith(".mp3-decode-")
                             for p in target.parent.iterdir()))
        self.mp3.unlink()
        self.assertTrue(target.is_file())
        # A real saved alarm prevents deletion just as it does for WAV imports.
        (self.base / "time-alarms-v2.json").write_text(json.dumps({
            "version": 2, "alarms": [{"id": 1, "soundId": tone["id"]}]
        }))
        refused = call_host(self.base, "delete", tone_id=tone["id"])
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["error"], "TONE_ASSIGNED_TO_ALARM")
        self.assertTrue(target.is_file())

    def test_corrupt_and_symlinked_mp3_do_not_change_library(self):
        bad = self.base / "corrupt.mp3"
        bad.write_bytes(os.urandom(600))
        self.assertEqual(call_host(self.base, "import",
                                  source=bad.as_uri(), name="Bad")["error"],
                         "MP3_CONVERSION_FAILED")
        fake = self.base / "fake.mp3"
        shutil.copyfile(self.source_wav, fake)
        self.assertEqual(call_host(self.base, "import",
                                  source=fake.as_uri(), name="Wrong data")["error"],
                         "MP3_CONVERSION_FAILED")
        linked = self.base / "link.mp3"
        linked.symlink_to(self.mp3)
        self.assertFalse(call_host(self.base, "import",
                                   source=linked.as_uri(), name="Link")["ok"])
        huge = self.base / "huge.mp3"
        with huge.open("wb") as out:
            out.truncate(16 * 1024 * 1024 + 1)
        self.assertEqual(call_host(self.base, "import",
                                  source=huge.as_uri(), name="Too big")["error"],
                         "INVALID_MP3_SIZE")
        self.assertEqual(call_host(self.base, "list")["tones"], [])
        store = self.base / "sounds-library-v1"
        self.assertFalse(any(p.name.startswith(".mp3-decode-")
                             for p in store.iterdir()))

    def test_long_mp3_refused_instead_of_truncated_silently(self):
        long_mp3 = self.base / "too long.mp3"
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
            "-t", "31.5", "-c:a", "libmp3lame", "-b:a", "64k", str(long_mp3)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)
        refused = call_host(self.base, "import",
                            source=long_mp3.as_uri(), name="Too long")
        self.assertFalse(refused["ok"])
        self.assertIn(refused["error"],
                      ("WAV_DURATION_OUT_OF_RANGE", "INVALID_WAV_SIZE"))
        self.assertEqual(call_host(self.base, "list")["tones"], [])

    def test_missing_converter_is_a_clear_error_but_wav_still_imports(self):
        # sys.executable is an absolute path. Only the decoder lookup uses
        # PATH, with no shell or implicit package installation.
        env = dict(os.environ, PATH=str(self.base / "no-such-path"))
        no_ffmpeg = call_host(self.base, "import", env=env,
                              source=self.mp3.as_uri(), name="Unavailable")
        self.assertFalse(no_ffmpeg["ok"])
        self.assertEqual(no_ffmpeg["error"], "MP3_CONVERTER_UNAVAILABLE")
        wav = call_host(self.base, "import", env=env,
                        source=self.source_wav.as_uri(), name="WAV still works")
        self.assertTrue(wav["ok"])

    def test_ui_and_decoder_boundary(self):
        host = HOST.read_text(encoding="utf-8")
        self.assertIn('"-protocol_whitelist", "pipe"', host)
        self.assertIn('"-f", "mp3", "-i", "pipe:0"', host)
        self.assertIn('"pcm_s16le"', host)
        self.assertIn('timeout=CONVERSION_TIMEOUT_SECONDS', host)
        self.assertNotIn("shell=True", host)
        self.assertIn("subprocess.run(", host)
        self.assertIn("source.suffix.lower() == \".wav\"", host)
        self.assertIn("def import_audio(root, args):", host)
        self.assertIn("function importAudio(fileUrl, displayName)", QML)
        self.assertIn("SoundLibraryService.importAudio(", UI)
        self.assertIn("name.replace(/\\.(wav|mp3)$/i", UI)
        self.assertIn("+ WAV/MP3", UI)
        self.assertIn("Sound files (*.wav *.mp3)", PICKER)
        self.assertIn("MP3 audio (*.mp3)", PICKER)


if __name__ == "__main__":
    unittest.main()
