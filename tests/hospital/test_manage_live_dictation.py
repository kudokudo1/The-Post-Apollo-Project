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


def next_json_packet(process, selector, pending: bytearray, *, timeout: float):
    """Read multiple JSON lines from a pipe without TextIO read-ahead races.

    Extra stage receipts can arrive in the same kernel read as a transcript.
    Selecting on the file descriptor before every TextIO.readline() would
    hide already buffered complete lines and produce false timeouts.
    """
    while b"\n" not in pending:
        if not selector.select(timeout=timeout):
            return None
        part = os.read(process.stdout.fileno(), 65536)
        if not part:
            return None
        pending.extend(part)
    raw, _, remaining = pending.partition(b"\n")
    pending[:] = remaining
    return json.loads(raw.decode("utf-8"))


class LiveDictationTests(unittest.TestCase):
    def test_bounded_incremental_multiple_partials_before_stop(self):
        # The microphone MUST remain active while successive guarded model
        # chunks deliver text. No real audio device or Whisper is used.
        with tempfile.TemporaryDirectory(prefix="hospital-incremental-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1500).to_bytes(2,'little',signed=True)\n"
                "for _ in range(100):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.035)\n"
                "time.sleep(10)\n"
            )
            recorder.chmod(0o700)
            count = root / "model-calls"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "$1" == "--check" ]]; then exit 0; fi\n'
                'printf "run\\n" >> "$HOSPITAL_MODEL_CALLS"\n'
                'printf "Incremental phrase.\\n"\n'
            )
            helper.chmod(0o700)
            env = dict(os.environ,
                       PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_MODEL_CALLS=str(count))
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-live-chunks", "6"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            selector = selectors.DefaultSelector()
            pending = bytearray()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                chunks = []
                stages = []
                deadline = time.monotonic() + 9
                while time.monotonic() < deadline and len(chunks) < 2:
                    event = next_json_packet(process, selector, pending,
                                             timeout=0.3)
                    if event is None:
                        continue
                    if event["kind"] == "stage":
                        stages.append(event["detail"])
                    elif event["kind"] == "partial":
                        chunks.append(event["text"])
                        self.assertIsNone(process.poll(),
                                          "Live text must arrive BEFORE STOP")
                    elif event["kind"] == "error":
                        self.fail(str(event))
                self.assertEqual(chunks,
                                 ["Incremental phrase.", "Incremental phrase."])
                self.assertIn("FIRST_TEXT_READY", stages)
                self.assertNotIn("CAPTURE_STOPPED", stages,
                                 "Second phrase must arrive with mic still open")
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=12)
                self.assertEqual(process.returncode, 0)
                self.assertGreaterEqual(len(count.read_text().splitlines()), 2)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                selector.close()

    def test_slow_whisper_does_not_force_stop_before_first_partial(self):
        # In the bounded trial, queue overflow reports lost audio instead of
        # turning a slow local model into hidden stop-then-transcribe behavior.
        with tempfile.TemporaryDirectory(prefix="hospital-stream-lag-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1500).to_bytes(2,'little',signed=True)\n"
                "for _ in range(120):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.002)\n"
                "time.sleep(10)\n"
            )
            recorder.chmod(0o700)
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "$1" == "--check" ]]; then exit 0; fi\n'
                "sleep 0.8\n"
                'printf "Slow but live.\\n"\n'
            )
            helper.chmod(0o700)
            env = dict(os.environ, PATH=str(fakebin) + ":" + os.environ["PATH"])
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-live-chunks", "6"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            selector = selectors.DefaultSelector()
            pending = bytearray()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                seen = set()
                first_text = False
                deadline = time.monotonic() + 9
                while time.monotonic() < deadline and not (
                        first_text and "MODEL_BACKPRESSURE" in seen):
                    event = next_json_packet(process, selector, pending,
                                             timeout=0.3)
                    if event is None:
                        continue
                    if event["kind"] == "stage":
                        seen.add(event["detail"])
                    elif event["kind"] == "partial":
                        self.assertEqual(event["text"], "Slow but live.")
                        first_text = True
                        self.assertIsNone(process.poll())
                    elif event["kind"] == "error":
                        self.fail(str(event))
                self.assertTrue(first_text, "No early phrase despite queued speech")
                self.assertIn("MODEL_BACKPRESSURE", seen)
                self.assertNotIn("CAPTURE_STOPPED", seen,
                                 "Queue lag must not secretly stop the mic")
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=12)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                selector.close()

    def test_bounded_live_short_stop_flushes_tail_without_exceeding_budget(self):
        # A phrase shorter than 1.4s has no partial yet. STOP must still
        # submit that small local audio tail through one guarded worker.
        with tempfile.TemporaryDirectory(prefix="hospital-stream-tail-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1600).to_bytes(2,'little',signed=True)\n"
                "for _ in range(4):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.015)\n"
                "time.sleep(10)\n"
            )
            recorder.chmod(0o700)
            count = root / "model-calls"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "$1" == "--check" ]]; then exit 0; fi\n'
                'printf "run\\n" >> "$HOSPITAL_MODEL_CALLS"\n'
                'printf "Short final phrase.\\n"\n'
            )
            helper.chmod(0o700)
            env = dict(os.environ,
                       PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_MODEL_CALLS=str(count))
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-live-chunks", "6"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            try:
                time.sleep(0.3)
                self.assertIsNone(process.poll())
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=10)
                self.assertEqual(process.returncode, 0)
                rows = [json.loads(line) for line in
                        process.stdout.read().splitlines()]
                self.assertEqual([row["text"] for row in rows
                                  if row["kind"] == "partial"],
                                 ["Short final phrase."])
                self.assertEqual(count.read_text().splitlines(), ["run"])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)

    def test_bounded_live_autostops_after_six_model_chunks(self):
        with tempfile.TemporaryDirectory(prefix="hospital-stream-cap-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1600).to_bytes(2,'little',signed=True)\n"
                "for _ in range(150):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.035)\n"
                "time.sleep(10)\n"
            )
            recorder.chmod(0o700)
            counter = root / "model-calls"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "$1" == "--check" ]]; then exit 0; fi\n'
                'printf "run\\n" >> "$HOSPITAL_MODEL_CALLS"\n'
                'printf "Guarded chunk.\\n"\n'
            )
            helper.chmod(0o700)
            env = dict(os.environ,
                       PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_MODEL_CALLS=str(counter))
            run = subprocess.run(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-live-chunks", "6"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                env=env, timeout=12)
            self.assertEqual(run.returncode, 0, run.stderr)
            rows = [json.loads(line) for line in run.stdout.splitlines()]
            stages = [p["detail"] for p in rows if p["kind"] == "stage"]
            self.assertIn("CAPTURE_STOPPED", stages)
            self.assertIn("RECORDING_COMPLETED", stages)
            self.assertEqual(sum(p["kind"] == "partial" for p in rows), 6)
            self.assertEqual(counter.read_text().splitlines(), ["run"] * 6,
                             "No model launch beyond six permitted chunks")

    def test_pilot_live_one_chunk_and_no_second_whisper_launch(self):
        # The authorized live trial is simulated with fake pw-record + model.
        # No host mic, actual Whisper, auth credentials or desktop processes.
        with tempfile.TemporaryDirectory(prefix="hospital-pilot-once-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1500).to_bytes(2,'little',signed=True)\n"
                "for _ in range(80):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.004)\n"
                "time.sleep(15)\n"
            )
            recorder.chmod(0o700)
            count_path = root / "model-calls"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then exit 0; fi\n"
                "printf 'run\\n' >> \"$HOSPITAL_PILOT_MODEL_CALLS\"\n"
                "printf 'One guarded phrase.\\n'\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ,
                       PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_PILOT_MODEL_CALLS=str(count_path))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-one-chunk"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            packets = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([p["text"] for p in packets
                              if p["kind"] == "partial"],
                             ["One guarded phrase."])
            stages = [p["detail"] for p in packets if p["kind"] == "stage"]
            for code in ("RECORDER_STARTED", "FIRST_AUDIO_QUEUED",
                         "FIRST_MODEL_STARTED", "FIRST_MODEL_ENDED",
                         "FIRST_TEXT_READY", "RECORDING_COMPLETED"):
                self.assertIn(code, stages)
            self.assertEqual(sum(p["kind"] == "done" for p in packets), 1)
            self.assertEqual(count_path.read_text().splitlines(), ["run"],
                             "Pilot must NEVER start a second model process")

    def test_pilot_silence_auto_stops_without_loading_model(self):
        with tempfile.TemporaryDirectory(prefix="hospital-pilot-silence-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "for _ in range(80):\n"
                " sys.stdout.buffer.write(b'\\x00'*3200)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.004)\n"
                "time.sleep(15)\n"
            )
            recorder.chmod(0o700)
            count_path = root / "model-calls"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then exit 0; fi\n"
                "printf 'run\\n' >> \"$HOSPITAL_PILOT_MODEL_CALLS\"\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ,
                       PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_PILOT_MODEL_CALLS=str(count_path))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(helper),
                 "--first-chunk-ms", "1400", "--pilot-one-chunk"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            packets = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertFalse(any(p["kind"] == "partial" for p in packets))
            self.assertEqual(sum(p["kind"] == "done" for p in packets), 1)
            self.assertFalse(count_path.exists(), "Silence must never load Whisper")

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
        with mock.patch.object(live.subprocess, "Popen") as popen:
            self.assertEqual(live.transcribe_chunk("never-called", pcm(0, 4)), "")
            popen.assert_not_called()
            child = popen.return_value
            child.returncode = 0
            child.communicate.return_value = ("[BLANK_AUDIO]\nWork on Finance.", "")
            self.assertEqual(live.transcribe_chunk("local-stt.sh", pcm(1300, 4)),
                             "Work on Finance.")
            command = popen.call_args.args[0]
            self.assertEqual(command[:2], [sys.executable, str(live.MODEL_GUARD)])
            self.assertEqual(command[2], "local-stt.sh")
            self.assertEqual(child.communicate.call_args.kwargs["timeout"], 15)
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            self.assertFalse(Path(command[3]).exists(),
                             "Temporary WAV must be removed at completion")


    def test_model_guard_caps_cpu_address_space_priority_and_affinity(self):
        # Uses a harmless Python observer, not actual Whisper or microphone.
        with tempfile.TemporaryDirectory(prefix="hospital-model-guard-") as folder:
            folder_path = Path(folder)
            audio = folder_path / "audio.wav"
            audio.write_bytes(b"not-real-audio")
            fake = folder_path / "limits.sh"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "python3 - <<'PY'\n"
                "import json,os,resource\n"
                "print(json.dumps({'address':resource.getrlimit(resource.RLIMIT_AS)[0],"
                "'cpu':resource.getrlimit(resource.RLIMIT_CPU)[0],"
                "'core':resource.getrlimit(resource.RLIMIT_CORE)[0],"
                "'affinity':len(os.sched_getaffinity(0)),"
                "'nice':os.nice(0),"
                "'safe':os.environ.get('POST_APOLLO_STT_SAFE_MODE'),"
                "'omp':os.environ.get('OMP_NUM_THREADS')}))\n"
                "PY\n"
            )
            result = subprocess.run(
                [sys.executable, str(live.MODEL_GUARD), str(fake), str(audio)],
                capture_output=True, text=True, timeout=6)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertGreater(data["address"], 0)
            self.assertLessEqual(data["address"], 3 * 1024**3)
            self.assertLessEqual(data["cpu"], 12)
            self.assertEqual(data["core"], 0)
            self.assertLessEqual(data["affinity"], 2)
            self.assertGreaterEqual(data["nice"], 10)
            self.assertEqual(data["safe"], "1")
            self.assertEqual(data["omp"], "2")

    def test_model_guard_fails_closed_on_missing_helper(self):
        with tempfile.TemporaryDirectory(prefix="hospital-guard-refusal-") as folder:
            wav = Path(folder) / "sound.wav"
            wav.write_bytes(b"not-real-audio")
            result = subprocess.run(
                [sys.executable, str(live.MODEL_GUARD),
                 str(Path(folder) / "missing-helper.sh"), str(wav)],
                capture_output=True, text=True, timeout=6)
            self.assertEqual(result.returncode, 66)

    def test_safe_mode_whisper_args_are_opt_in_to_guarded_live_calls(self):
        # The legacy single-file STT call must not silently inherit live flags.
        with tempfile.TemporaryDirectory(prefix="hospital-safe-args-") as folder:
            root = Path(folder)
            wav = root / "speech.wav"
            wav.write_bytes(b"test")
            model = root / "tiny-model.bin"
            model.write_bytes(b"test")
            backend = root / "fake-whisper-cli"
            backend.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n")
            backend.chmod(0o700)
            helper = ROOT / "scripts" / "hospital-reception-stt.sh"
            env = dict(os.environ, POST_APOLLO_STT_MODEL=str(model),
                       POST_APOLLO_STT_BIN=str(backend))
            legacy = subprocess.run(
                ["bash", str(helper), str(wav)], env=env,
                capture_output=True, text=True, timeout=6)
            self.assertEqual(legacy.returncode, 0, legacy.stderr)
            self.assertNotIn("-ng", legacy.stdout.splitlines())
            live_call = subprocess.run(
                [sys.executable, str(live.MODEL_GUARD),
                 str(helper), str(wav)], env=env,
                capture_output=True, text=True, timeout=6)
            self.assertEqual(live_call.returncode, 0, live_call.stderr)
            args = live_call.stdout.splitlines()
            self.assertIn("-ng", args)
            self.assertIn("-t", args)
            self.assertEqual(args[args.index("-t") + 1], "2")

    def test_protocol_no_submit_or_permissions(self):
        result = json.loads(live.packet("partial", text="new spoken words"))
        self.assertEqual(result, {"kind": "partial", "text": "new spoken words",
                                  "detail": ""})
        self.assertNotIn("submit", json.dumps(result))
        self.assertNotIn("authority", json.dumps(result))

    def test_opening_words_arrive_without_waiting_for_stop(self):
        # The fake recorder emits 1.5s of speech, then stays open but silent.
        # A 2-second-only capture would withhold its first partial forever.
        with tempfile.TemporaryDirectory(prefix="hospital-early-voice-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1400).to_bytes(2,'little',signed=True)\n"
                "for _ in range(15):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.02)\n"
                "time.sleep(15)\n"
            )
            recorder.chmod(0o700)
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then exit 0; fi\n"
                "printf 'First words while listening.\\n'\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ, PATH=str(fakebin) + ":" + os.environ["PATH"])
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                partial = None
                stage_codes = []
                pending = bytearray()
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    event = next_json_packet(process, selector, pending, timeout=0.5)
                    if event is None:
                        continue
                    if event["kind"] == "stage":
                        self.assertEqual(event["text"], "")
                        self.assertRegex(event["detail"], r"^[A-Z_]+$")
                        stage_codes.append(event["detail"])
                        continue
                    if event["kind"] == "partial":
                        partial = event["text"]
                        self.assertIsNone(process.poll(), "Mic must remain open")
                        break
                    if event["kind"] == "error":
                        self.fail(str(event))
                self.assertEqual(partial, "First words while listening.")
                self.assertTrue({
                    "RECORDER_STARTED", "FIRST_AUDIO_QUEUED",
                    "FIRST_MODEL_STARTED", "FIRST_MODEL_ENDED",
                    "FIRST_TEXT_READY",
                }.issubset(set(stage_codes)), stage_codes)
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=18)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                selector.close()

    def test_short_final_speech_is_flushed_after_stop(self):
        # Two chunks: 1.4s initial speech, then 0.4s tail. Previously the
        # remaining subsecond tail was silently thrown away on STOP.
        with tempfile.TemporaryDirectory(prefix="hospital-tail-voice-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1500).to_bytes(2,'little',signed=True)\n"
                "for _ in range(18):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.008)\n"
                "time.sleep(15)\n"
            )
            recorder.chmod(0o700)
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then exit 0; fi\n"
                "printf 'Recognized.\\n'\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ, PATH=str(fakebin) + ":" + os.environ["PATH"])
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            try:
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                first = None
                pending = bytearray()
                deadline = time.monotonic() + 7
                while time.monotonic() < deadline:
                    data = next_json_packet(process, selector, pending, timeout=0.4)
                    if data is None:
                        continue
                    if data["kind"] == "partial":
                        first = data["text"]
                        break
                    if data["kind"] == "error":
                        self.fail(str(data))
                self.assertEqual(first, "Recognized.")
                time.sleep(0.2)
                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=8)
                remaining = [
                    json.loads(line)
                    for line in (pending.decode("utf-8")
                                 + process.stdout.read()).splitlines()
                ]
                second = [row["text"] for row in remaining
                          if row["kind"] == "partial"]
                self.assertEqual(second, ["Recognized."],
                                 "Subsecond final phrase must not vanish")
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                selector.close()

    def test_cancel_reaps_owned_whisper_model(self):
        # A stuck fake model records its real PID; CANCEL must end both it
        # and the Python/PipeWire owner without waiting for a 15s timeout.
        with tempfile.TemporaryDirectory(prefix="hospital-cancel-voice-") as folder:
            root = Path(folder)
            fakebin = root / "bin"
            fakebin.mkdir()
            recorder = fakebin / "pw-record"
            recorder.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "speech=(1300).to_bytes(2,'little',signed=True)\n"
                "for _ in range(16):\n"
                " sys.stdout.buffer.write(speech*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.008)\n"
                "time.sleep(30)\n"
            )
            recorder.chmod(0o700)
            pid_file = root / "whisper-pid"
            helper = root / "whisper.sh"
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == '--check' ]]; then exit 0; fi\n"
                "printf '%s' \"$BASHPID\" > \"$HOSPITAL_MODEL_PID_FILE\"\n"
                "exec sleep 30\n"
            )
            helper.chmod(0o700)
            env = dict(os.environ, PATH=str(fakebin) + ":" + os.environ["PATH"],
                       HOSPITAL_MODEL_PID_FILE=str(pid_file))
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(helper),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            try:
                deadline = time.monotonic() + 7
                model_pid = None
                while time.monotonic() < deadline:
                    # The fixture PID file may exist before its write closes.
                    # Do not race the shell completing its PID file write.
                    value = pid_file.read_text().strip() if pid_file.exists() else ""
                    if value.isdigit():
                        model_pid = int(value)
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(model_pid, "Fake Whisper must start")
                process.stdin.write("CANCEL\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=7)
                self.assertEqual(process.returncode, 130)
                with self.assertRaises(ProcessLookupError):
                    os.kill(model_pid, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)

    def test_real_stdout_stream_and_stop_with_fake_audio(self):
        # Test 2-second Reception/Intercom cadence with fake local audio.
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
                "for _ in range(500):\n"
                " sys.stdout.buffer.write(x*1600)\n"
                " sys.stdout.buffer.flush()\n"
                " time.sleep(0.008)\n"
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
                [sys.executable, str(SCRIPT), str(helper), "--chunk-seconds", "2"],
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
