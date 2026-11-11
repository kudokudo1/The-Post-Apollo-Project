#!/usr/bin/env python3
"""Fake-only persistent Whisper integration and boundary regression checks.

No live microphone, genuine speech model, persistent audio or TCP listener.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/hospital-live-dictation.py"
HELPER = ROOT / "scripts/hospital-reception-stt.sh"
SPEC = importlib.util.spec_from_file_location("hospital_quality_live", SCRIPT)
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)


def packet_from_pipe(process, selector, pending, timeout=0.4):
    while b"\n" not in pending:
        if not selector.select(timeout=timeout):
            return None
        block = os.read(process.stdout.fileno(), 65536)
        if not block:
            return None
        pending.extend(block)
    line, _, remainder = pending.partition(b"\n")
    pending[:] = remainder
    return json.loads(line.decode("utf-8"))


def build_fake_runtime(root: Path):
    fakebin = root / "bin"
    fakebin.mkdir()
    recorder = fakebin / "pw-record"
    recorder.write_text(textwrap.dedent(r"""
        #!/usr/bin/env python3
        import sys, time
        sample=(1700).to_bytes(2, "little", signed=True)
        for _ in range(125):
            sys.stdout.buffer.write(sample * 1600)
            sys.stdout.buffer.flush()
            time.sleep(0.025)
        time.sleep(12)
    """).lstrip())
    recorder.chmod(0o700)
    model = root / "ggml-base.en.bin"
    model.write_bytes(b"model-placeholder-not-an-actual-model")
    cli = fakebin / "whisper-cli"
    cli.write_text(
        "#!/usr/bin/env bash\n"
        'printf "one CLI call\\n" >> "$TEST_CLI_CALLS"\n'
        'printf "CLI fallback.\\n"\n'
    )
    cli.chmod(0o700)
    server = fakebin / "whisper-server"
    server.write_text(textwrap.dedent(r"""
        #!/usr/bin/env python3
        import json, os, pathlib, socketserver, sys
        from http.server import BaseHTTPRequestHandler
        if "--help" in sys.argv:
            print("--host unix socket path ending .sock")
            sys.exit(0)
        path = sys.argv[sys.argv.index("--host") + 1]
        assert path.startswith("/") and path.endswith(".sock")
        with open(os.environ["TEST_SERVER_STARTS"], "a") as file:
            file.write("start\n")
        pathlib.Path(os.environ["TEST_SERVER_PID"]).write_text(str(os.getpid()))

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                assert self.path == "/inference"
                data = self.rfile.read(int(self.headers["Content-Length"]))
                assert b'name="file"' in data
                assert b"speech.wav" in data and b"RIFF" in data
                count = pathlib.Path(os.environ["TEST_SERVER_REQUESTS"])
                with count.open("a") as file:
                    file.write(str(len(data)) + "\n")
                index = len(count.read_text().splitlines())
                text = ("Turn left at the" if index == 1
                        else "at the next light" if index == 2
                        else "next light and stop")
                body = json.dumps({"text": text}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        class Server(socketserver.UnixStreamServer):
            allow_reuse_address = True

        with Server(path, Handler) as service:
            service.serve_forever()
    """).lstrip())
    server.chmod(0o700)
    starts = root / "server-starts"
    requests = root / "server-requests"
    pid = root / "server-pid"
    cli_calls = root / "cli-calls"
    env = dict(os.environ,
               PATH=str(fakebin) + ":" + os.environ["PATH"],
               POST_APOLLO_STT_SERVER_BIN=str(server),
               POST_APOLLO_STT_BIN=str(cli),
               POST_APOLLO_STT_MODEL=str(model),
               TEST_SERVER_STARTS=str(starts),
               TEST_SERVER_REQUESTS=str(requests),
               TEST_SERVER_PID=str(pid),
               TEST_CLI_CALLS=str(cli_calls))
    return env, starts, requests, pid, cli_calls


class PersistentWhisperTests(unittest.TestCase):
    def test_overlap_removes_only_matching_multitoken_boundary(self):
        self.assertEqual(
            live.trim_repeated_prefix("Turn left at the", "at the next light"),
            "next light")
        self.assertEqual(
            live.trim_repeated_prefix("at the next light",
                                      "next light and stop"),
            "and stop")
        self.assertEqual(live.trim_repeated_prefix("I", "I agree"), "I agree")
        self.assertEqual(
            live.trim_repeated_prefix("red green", "red blue"), "red blue")

    def test_capability_profile_is_readonly_and_identifies_selected_model(self):
        with tempfile.TemporaryDirectory(prefix="hospital-whisper-profile-") as tmp:
            env, starts, _, _, cli_calls = build_fake_runtime(Path(tmp))
            status = subprocess.run(["bash", str(HELPER), "--profile"], env=env,
                                    capture_output=True, text=True, timeout=3)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("MODEL // ggml-base.en.bin", status.stdout)
            self.assertIn("SESSION // AVAILABLE", status.stdout)
            self.assertFalse(starts.exists())
            self.assertFalse(cli_calls.exists())

    def test_guarded_session_reuses_one_model_before_stop(self):
        with tempfile.TemporaryDirectory(prefix="hospital-whisper-reuse-") as tmp:
            env, starts, requests, pid_file, cli_calls = build_fake_runtime(
                Path(tmp))
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), str(HELPER),
                 "--chunk-seconds", "2", "--first-chunk-ms", "1400",
                 "--pilot-live-chunks", "6", "--prefer-persistent"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
            pending = bytearray()
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                seen = set()
                spoken = []
                deadline = time.monotonic() + 16
                while time.monotonic() < deadline and len(spoken) < 2:
                    entry = packet_from_pipe(process, selector, pending)
                    if entry is None:
                        continue
                    if entry["kind"] == "stage":
                        seen.add(entry["detail"])
                    elif entry["kind"] == "partial":
                        spoken.append(entry["text"])
                        self.assertIsNone(
                            process.poll(), "Text should arrive before STOP")
                    elif entry["kind"] == "error":
                        self.fail(str(entry))
                self.assertEqual(spoken,
                                 ["Turn left at the", "next light"], seen)
                self.assertIn("MODEL_SESSION_READY", seen)
                self.assertNotIn("MODEL_SESSION_UNAVAILABLE", seen)
                self.assertNotIn("CAPTURE_STOPPED", seen)
                self.assertEqual(starts.read_text().splitlines(), ["start"])
                self.assertGreaterEqual(len(requests.read_text().splitlines()), 2)
                self.assertFalse(cli_calls.exists(),
                                 "One model session must replace repeated CLI")

                process.stdin.write("STOP\n")
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=12)
                self.assertEqual(process.returncode, 0)
                self.assertEqual(starts.read_text().splitlines(), ["start"])
                pid = int(pid_file.read_text())
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=4)
                selector.close()

    def test_missing_session_falls_back_to_guarded_cli(self):
        with tempfile.TemporaryDirectory(prefix="hospital-whisper-fallback-") as tmp:
            env, starts, _, _, cli_calls = build_fake_runtime(Path(tmp))
            env["POST_APOLLO_STT_SERVER_BIN"] = str(Path(tmp) / "no-server")
            run = subprocess.run(
                [sys.executable, str(SCRIPT), str(HELPER),
                 "--pilot-one-chunk", "--first-chunk-ms", "1400",
                 "--prefer-persistent"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                env=env, timeout=12)
            self.assertEqual(run.returncode, 0, run.stderr)
            records = [json.loads(line) for line in run.stdout.splitlines()]
            self.assertIn("MODEL_SESSION_UNAVAILABLE",
                          [r["detail"] for r in records if r["kind"] == "stage"])
            self.assertEqual(
                [r["text"] for r in records if r["kind"] == "partial"],
                ["CLI fallback."])
            self.assertFalse(starts.exists())
            self.assertEqual(cli_calls.read_text().splitlines(), ["one CLI call"])

    def test_no_tcp_or_unbounded_native_worker(self):
        source = (ROOT / "scripts/hospital_whisper_session.py").read_text()
        guard = (ROOT / "scripts/hospital-whisper-sandbox.py").read_text()
        helper = HELPER.read_text()
        qml = (ROOT / "services/hospital/HospitalLiveDictationService.qml").read_text()
        host = (ROOT / "widgets/HospitalW.qml").read_text()
        self.assertIn("socket.AF_UNIX", source)
        self.assertNotIn("socket.AF_INET", source)
        self.assertIn("MAX_RESPONSE_BYTES = 65536", source)
        self.assertIn("MAX_SESSION_CPU_SECONDS = 48", guard)
        self.assertIn("MAX_VIRTUAL_BYTES = 3 * 1024 * 1024 * 1024", guard)
        self.assertIn("not os.path.lexists(resource_path)", guard)
        self.assertIn('exec "$server" -m "$model" --host "$socket_path"', helper)
        self.assertIn("-ng -t 2 -p 1", helper)
        self.assertIn("property bool safetyHold: true", qml)
        self.assertIn("preferPersistentModel: true", host)
        self.assertIn("pilotLiveChunks: 6", host)


if __name__ == "__main__":
    unittest.main(verbosity=2)
