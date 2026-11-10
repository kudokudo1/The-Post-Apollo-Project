#!/usr/bin/env python3
"""Offline tests for local chunked partial Whisper dictation, no real mic/model."""
import array
import importlib.util
import json
import math
import os
from pathlib import Path
import selectors
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "hospital-live-dictation.py"
SPEC = importlib.util.spec_from_file_location("hospital_live_dictation", SCRIPT)
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)


def pcm(value, seconds=1):
    wave = array.array("h", [value] * (live.RATE * seconds))
    if sys.byteorder != "little":
        wave.byteswap()
    return wave.tobytes()


class LiveDictationTests(unittest.TestCase):
    def test_no_audio_no_model_inference(self):
        self.assertFalse(live.is_speech(pcm(0, 5)))
        self.assertFalse(live.is_speech(pcm(25, 5)))
        self.assertTrue(live.is_speech(pcm(1000, 1)))
        self.assertFalse(live.is_speech(pcm(1000, 1)[:100]))

    def test_blank_audio_and_placeholder_suppression(self):
        for value in ("[BLANK_AUDIO]", "[ blank_audio ]",
                      "[NO_SPEECH]", "[SILENCE]", "[NO_AUDIO]", "",
                      "[MUSIC]", " \n[BLANK_AUDIO]\n"):
            self.assertEqual(live.clean_transcript(value), "")
        self.assertEqual(live.clean_transcript(
            "[BLANK_AUDIO]\n Hello operator.\n [NO_SPEECH]"), "Hello operator.")
        self.assertEqual(live.clean_transcript(
            "[00:00:00.000 --> 00:00:01.000] Hello there."), "Hello there.")
        self.assertEqual(live.clean_transcript("Hi \x00"), "")

    def test_chunk_calls_local_whisper_only_for_speech(self):
        with mock.patch.object(live.subprocess, "run") as run:
            self.assertEqual(live.transcribe_chunk("never-called", pcm(0, 4)), "")
            run.assert_not_called()
            run.return_value.returncode = 0
            run.return_value.stdout = "[BLANK_AUDIO]\nWork on Finance."
            self.assertEqual(live.transcribe_chunk("local-stt.sh", pcm(1300, 4)),
                             "Work on Finance.")
            command = run.call_args.args[0]
            self.assertEqual(command[:2], ["bash", "local-stt.sh"])
            self.assertEqual(run.call_args.kwargs["timeout"], 25)
            self.assertEqual(run.call_args.kwargs["check"], False)
            self.assertFalse(Path(command[2]).exists(),
                             "Temporary WAV must be removed at completion")

    def test_protocol_no_submit_or_permissions(self):
        result = json.loads(live.packet("partial", text="new spoken words"))
        self.assertEqual(result, {"kind": "partial", "text": "new spoken words",
                                  "detail": ""})
        self.assertNotIn("submit", json.dumps(result))
        self.assertNotIn("authority", json.dumps(result))

    def test_real_stdout_stream_and_stop_with_fake_audio(self):
        # Truly test the child process while injecting throwaway fake pw-record
        # and fake local whisper helper. No actual microphone or service.
        with tempfile.TemporaryDirectory(prefix="hospital-live-fixture-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_recorder = fakebin / "pw-record"
            fake_recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "x=(1300).to_bytes(2,'little',signed=True)\n"
                "for _ in range(120):\n"
                " sys.stdout.buffer.write(x*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.004)\n"
            )
            fake_recorder.chmod(0o700)
            helper = root / "local-whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then echo READY; exit 0; fi\n"
                "printf 'Finance widget.\\n'\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ, PATH=str(fakebin) + ":" + os.environ["PATH"])
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            try:
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                seen_partial = False
                deadline = time.monotonic() + 14
                while time.monotonic() < deadline:
                    if not selector.select(timeout=0.5):
                        continue
                    packet = json.loads(process.stdout.readline())
                    if packet["kind"] == "partial":
                        self.assertEqual(packet["text"], "Finance widget.")
                        seen_partial = True
                        # Record should still be running when partial arrives.
                        self.assertIsNone(process.poll())
                        break
                    if packet["kind"] == "error":
                        self.fail(str(packet))
                self.assertTrue(seen_partial, "Must emit text BEFORE pressing STOP")
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=18)
                output = process.stdout.read()
                self.assertNotIn("BLANK_AUDIO", output)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                selector.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
