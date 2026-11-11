"""Managed Sound Library: import security, persistence and alarm reference gate."""
from pathlib import Path
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/sounds/SoundLibraryHost.py"
UI = (ROOT / "widgets/AlarmManagerPane.qml").read_text()
SERVICE = (ROOT / "services/sounds/SoundLibraryService.qml").read_text()
PICKER = (ROOT / "widgets/AlarmWavImportDialog.qml").read_text()
AUDIO = (ROOT / "services/time/AlarmAudioV2.qml").read_text()
POLICY = (ROOT / "services/time/AlarmManagerPolicy.js").read_text()


def run_host(base, operation, **args):
    cmd = [sys.executable, "-I", "-B", str(HOST),
           "--data-dir", str(base), "--operation", operation]
    for name, value in args.items():
        cmd.extend(["--" + name.replace("_", "-"), str(value)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        obj = json.loads(result.stdout)
    except ValueError:
        raise AssertionError(f"Host emitted invalid JSON: {result!r}")
    assert (result.returncode == 0) == obj["ok"]
    return obj


def make_wav(target, duration=0.5, rate=48000, channels=1, sample_width=2):
    with wave.open(str(target), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(rate)
        w.writeframes(b"\0" * (int(duration * rate) * channels * sample_width))


class SoundLibraryHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.src = self.base / "Source tone.wav"
        make_wav(self.src)

    def test_import_rename_reference_refusal_and_delete(self):
        self.assertEqual(run_host(self.base, "list")["tones"], [])
        imported = run_host(self.base, "import",
                            source=self.src.as_uri(), name="Morning tone")
        self.assertTrue(imported["ok"], imported)
        tone = imported["tones"][0]
        self.assertRegex(tone["id"], r"^user-[0-9a-f]{64}$")
        self.assertEqual(tone["name"], "Morning tone")
        target = Path(tone["url"].removeprefix("file://"))
        self.assertTrue(target.is_file())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(run_host(self.base, "list")["tones"], imported["tones"])
        duplicate = run_host(self.base, "import",
                             source=self.src.as_uri(), name="Ignored second name")
        self.assertTrue(duplicate["ok"])
        self.assertEqual(duplicate["status"], "already-imported")
        self.assertEqual(len(duplicate["tones"]), 1)
        rename = run_host(self.base, "rename", tone_id=tone["id"],
                          name="Travel wake")
        self.assertTrue(rename["ok"])
        self.assertEqual(rename["tones"][0]["name"], "Travel wake")
        # Original can move/disappear; managed copy remains playable.
        self.src.unlink()
        self.assertTrue(target.is_file())
        saved = self.base / "time-alarms-v2.json"
        saved.write_text(json.dumps({"version": 2, "alarms": [
            {"id": 1, "soundId": tone["id"]}]}))
        denied = run_host(self.base, "delete", tone_id=tone["id"])
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["error"], "TONE_ASSIGNED_TO_ALARM")
        self.assertTrue(target.exists())
        saved.write_text(json.dumps({"version": 2, "alarms": [
            {"id": 1, "soundId": "chime"}]}))
        removed = run_host(self.base, "delete", tone_id=tone["id"])
        self.assertTrue(removed["ok"])
        self.assertEqual(removed["tones"], [])
        self.assertFalse(target.exists())

    def test_standard_44100_stereo_25_second_alarm_import(self):
        # A common downloaded sound-effect format: 16-bit stereo 44.1kHz.
        # Previously it failed with UNSUPPORTED_WAV_PCM, even though the
        # 25-second, ~4.4 MB file is well inside the audio-size limit.
        sample = self.base / "mixkit-retro-game-emergency-alarm-1000.wav"
        make_wav(sample, duration=25, rate=44100, channels=2)
        before = sample.read_bytes()
        self.assertGreater(len(before), 4_000_000)
        self.assertLess(len(before), 8 * 1024 * 1024)
        result = run_host(self.base, "import",
                          source=sample.as_uri(),
                          name="mixkit-retro-game-emergency-alarm")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "imported")
        self.assertEqual(len(result["tones"]), 1)
        tone = result["tones"][0]
        self.assertEqual(tone["seconds"], 25.0)
        managed = Path(tone["url"].removeprefix("file://"))
        self.assertEqual(managed.read_bytes(), before)
        with wave.open(str(managed), "rb") as w:
            self.assertEqual(w.getframerate(), 44100)
            self.assertEqual(w.getnchannels(), 2)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getnframes(), 25 * 44100)
        self.assertEqual(sample.read_bytes(), before)
        duplicate = run_host(self.base, "import",
                             source=sample.as_uri(), name="Second name")
        self.assertTrue(duplicate["ok"], duplicate)
        self.assertEqual(duplicate["status"], "already-imported")
        self.assertEqual(len(run_host(self.base, "list")["tones"]), 1)

    def test_reject_non_wav_symlink_wrong_format_and_bad_uri(self):
        for uri in ["https://example.com/steal.wav", "file://remote/share.wav",
                    "file:///tmp/sound.mp3", "data:audio/wav;base64,AAAA"]:
            self.assertFalse(run_host(self.base, "import",
                                      source=uri, name="Denied")["ok"])
        symlink = self.base / "alias.wav"
        symlink.symlink_to(self.src)
        self.assertFalse(run_host(self.base, "import",
                                  source=symlink.as_uri(), name="Denied")["ok"])
        wrong = self.base / "wrong.wav"
        make_wav(wrong, sample_width=1)
        self.assertEqual(run_host(self.base, "import", source=wrong.as_uri(),
                                  name="Denied")["error"], "UNSUPPORTED_WAV_PCM")
        too_long = self.base / "long.wav"
        make_wav(too_long, duration=31)
        self.assertEqual(run_host(self.base, "import", source=too_long.as_uri(),
                                  name="Denied")["error"], "WAV_DURATION_OUT_OF_RANGE")
        too_short = self.base / "short.wav"
        make_wav(too_short, duration=0.05)
        self.assertEqual(run_host(self.base, "import", source=too_short.as_uri(),
                                  name="Denied")["error"], "WAV_DURATION_OUT_OF_RANGE")
        self.assertEqual(run_host(self.base, "list")["tones"], [])

    def test_corrupt_manifest_fails_closed_without_overwrite(self):
        lib = self.base / "sounds-library-v1"
        lib.mkdir()
        index = lib / "index-v1.json"
        index.write_text('{"version":1,"tones":[{"id":"../escape"}]}')
        original = index.read_bytes()
        result = run_host(self.base, "import", source=self.src.as_uri(),
                          name="Blocked")
        self.assertFalse(result["ok"])
        self.assertEqual(index.read_bytes(), original)
        self.assertFalse(any(p.suffix == ".wav" for p in lib.iterdir()))

    def test_source_contracts_and_shared_registry(self):
        self.assertIn("import qs.services.sounds", AUDIO)
        self.assertIn("SoundLibraryService.sourceFor(soundId)", AUDIO)
        self.assertIn("CUSTOM TONE MISSING // CHIME FALLBACK", AUDIO)
        self.assertIn("function validSoundId(id)", POLICY)
        self.assertIn("validSoundId(a.soundId)", POLICY)
        self.assertNotIn('import QtQuick.Dialogs', UI)
        self.assertIn("id: soundImportLoader", UI)
        self.assertIn("active: false", UI)
        self.assertIn('source: "AlarmWavImportDialog.qml"', UI)
        self.assertIn('onLeftClicked: pane.openFilePicker()', UI)
        self.assertIn('FILE PICKER LOADING', UI)
        self.assertIn('FILE PICKER OPEN // SELECT WAV/MP3', UI)
        self.assertIn('status === Loader.Error && active', UI)
        self.assertIn('item.cancelled.connect(', UI)
        self.assertIn('onRejected: pickerHost.cancelled()', PICKER)
        self.assertIn('SOUND LIBRARY // BUSY // RETRY', SERVICE)
        self.assertIn('SOUND LIBRARY // INVALID TONE NAME', SERVICE)
        self.assertIn('ALLOWED_RATES = (24000, 44100, 48000)',
                      HOST.read_text())
        self.assertIn('import QtQuick.Dialogs', PICKER)
        self.assertIn('Sound files (*.wav *.mp3)', PICKER)
        self.assertIn('MP3 audio (*.mp3)', PICKER)
        self.assertIn("pane.openLibrary()", UI)
        self.assertIn("function applyLibraryTone()", UI)
        self.assertIn("function deleteLibraryTone()", UI)
        self.assertIn("model: pane.libraryTones", UI)
        self.assertIn("flickable: pane.soundLibraryOpen ? libraryList : alarmList", UI)
        self.assertIn('Quickshell.shellPath("services/sounds/SoundLibraryHost.py")',
                      SERVICE)
        self.assertNotIn("command: [\"sh\"", SERVICE)
        self.assertNotIn("os.system(", HOST.read_text())


if __name__ == "__main__":
    unittest.main()
