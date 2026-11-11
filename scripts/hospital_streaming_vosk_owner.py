#!/usr/bin/env python3
"""Held Hospital Vosk trial: one PipeWire owner, one resource-limited decoder.

The existing HospitalLiveDictationService owns this subprocess *instead of*
Whisper when its explicit, default-off streaming gate is enabled. No files,
network, model downloads, credentials, or Hospital actions. The child model
uses the separately bounded hospital_streaming_vosk_probe.py stdin interface.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import selectors
import signal
import subprocess
import sys
import threading
import time

RATE = 16000
FRAME = RATE * 2 // 10
PCM_BUDGET = RATE * 2 * 25
WALL_BUDGET = 45
MODEL_FINISH_SECONDS = 5
WRITE_BUDGET_SECONDS = 0.8
MAX_OUTPUT_LINE = 8192
MODEL_SCRIPT = Path(__file__).with_name("hospital_streaming_vosk_probe.py")
RECORDER_COMMAND = ("pw-record", "--raw", "--rate=16000",
                    "--channels=1", "--format=s16", "-")
MODEL_ERRORS = frozenset(("OFFLINE_PROBE_FAILED", "MODEL_OR_PCM_UNAVAILABLE",
                          "PROBE_DISABLED", "CAPTURE_DURATION_LIMIT"))


def packet(kind: str, **values):
    return json.dumps({"kind": kind, **values}, separators=(",", ":"),
                      ensure_ascii=False)


def safe_decoder_packet(record):
    """No arbitrary child data or diagnostic content reaches the QML host."""
    if not isinstance(record, dict):
        return False
    kind = record.get("kind")
    if kind in ("hypothesis", "commit"):
        return (set(record) == {"kind", "text", "revision", "clear_provisional"}
                and type(record["text"]) is str
                and len(record["text"]) <= 4000
                and type(record["revision"]) is int
                and 1 <= record["revision"] <= 300
                and type(record["clear_provisional"]) is bool
                and record["clear_provisional"] == (kind == "commit"))
    if kind == "done":
        return set(record) == {"kind"}
    if kind == "metrics":
        return (set(record) == {"kind", "first_hypothesis_ms",
                               "first_commit_ms", "pcm_bytes"}
                and all(type(record[n]) is int for n in
                        ("first_hypothesis_ms", "first_commit_ms", "pcm_bytes"))
                and -1 <= record["first_hypothesis_ms"] <= 45000
                and -1 <= record["first_commit_ms"] <= 45000
                and 0 <= record["pcm_bytes"] <= PCM_BUDGET)
    if kind == "status":
        return set(record) == {"kind", "code"} and record["code"] in MODEL_ERRORS
    return False


def terminate_group(process):
    if process is None:
        return
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
        try:
            process.wait(timeout=0.4)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass


def write_pcm(fd: int, data: bytes, *, cancelled: threading.Event,
              stopping: threading.Event) -> bool:
    """Never block indefinitely if model loads slowly or stops reading."""
    view = memoryview(data)
    deadline = time.monotonic() + WRITE_BUDGET_SECONDS
    while view:
        if cancelled.is_set() or stopping.is_set() or time.monotonic() >= deadline:
            return False
        _, writable, _ = select.select([], [fd], [], 0.1)
        if not writable:
            continue
        try:
            size = os.write(fd, view)
        except (BlockingIOError, InterruptedError):
            continue
        except (BrokenPipeError, OSError):
            return False
        if size <= 0:
            return False
        view = view[size:]
    return True


def run_trial(model_dir: str, *, recorder_command=None, decoder_command=None,
              commands=None, output=None) -> int:
    """Own exactly one recorder and one Vosk decoder until *both* exit.

    Injectable commands are only a Python test seam, never CLI flags. The
    desktop path passes the pinned recorder and decoder commands.
    """
    if not model_dir or not Path(model_dir).is_dir():
        return 66
    recorder_command = (RECORDER_COMMAND if recorder_command is None
                        else recorder_command)
    decoder_command = ([sys.executable, str(MODEL_SCRIPT), "--offline-probe",
                        "--model-dir", model_dir]
                       if decoder_command is None else decoder_command)
    commands = sys.stdin.buffer if commands is None else commands
    output = sys.stdout if output is None else output
    stop = threading.Event()
    cancelled = threading.Event()
    failed = threading.Event()
    finished = threading.Event()
    stdout_lock = threading.Lock()
    recorder = None
    decoder = None
    old_term = None
    old_int = None

    def emit(kind, **payload):
        if cancelled.is_set():
            return
        with stdout_lock:
            output.write(packet(kind, **payload) + "\n")
            output.flush()

    def signal_cancel(*_):
        cancelled.set()
        stop.set()

    def controls():
        try:
            while not cancelled.is_set() and not stop.is_set():
                line = commands.readline()
                if not line:
                    break
                if line.strip().upper() == b"CANCEL":
                    cancelled.set()
                    stop.set()
                    break
                if line.strip().upper() == b"STOP":
                    stop.set()
                    break
        except (OSError, ValueError):
            cancelled.set()
            stop.set()

    def read_decoder():
        count = 0
        try:
            for line in decoder.stdout:
                count += 1
                if count > 310 or len(line) > MAX_OUTPUT_LINE:
                    failed.set()
                    break
                try:
                    row = json.loads(line.decode("utf-8"))
                except (UnicodeError, ValueError):
                    failed.set()
                    break
                if not safe_decoder_packet(row):
                    failed.set()
                    break
                if row["kind"] == "status" and row["code"] != "CAPTURE_DURATION_LIMIT":
                    failed.set()
                    break
                if row["kind"] == "done":
                    finished.set()
                if not cancelled.is_set():
                    emit(row["kind"], **{k: v for k, v in row.items()
                                        if k != "kind"})
        except (OSError, ValueError):
            failed.set()

    # For production QML the parent is a single host-owned Process. An
    # unexpected parent exit must also tear down both descendants.
    owner_pid = os.getppid()
    main_thread = threading.current_thread() is threading.main_thread()
    try:
        if main_thread:
            old_term = signal.signal(signal.SIGTERM, signal_cancel)
            old_int = signal.signal(signal.SIGINT, signal_cancel)
        # Spawn the guarded model once. It loads no native library until the
        # sandboxed decoder has applied its limits and 45s alarm.
        decoder = subprocess.Popen(decoder_command, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True, bufsize=0)
        os.set_blocking(decoder.stdin.fileno(), False)
        recorder = subprocess.Popen(recorder_command, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, start_new_session=True,
                                    bufsize=0)
        threading.Thread(target=controls, daemon=True).start()
        reader = threading.Thread(target=read_decoder, daemon=True)
        reader.start()
        emit("stage", detail="STREAM_RECORDER_STARTED")
        observed = 0
        captured = bytearray()
        started = time.monotonic()
        stop_reason = "CAPTURE_SOURCE_ENDED"
        with selectors.DefaultSelector() as selector:
            selector.register(recorder.stdout, selectors.EVENT_READ)
            while not stop.is_set() and not cancelled.is_set() and not failed.is_set():
                if os.getppid() != owner_pid:
                    cancelled.set()
                    break
                if time.monotonic() - started >= WALL_BUDGET:
                    stop_reason = "CAPTURE_DURATION_LIMIT"
                    stop.set()
                    break
                if observed >= PCM_BUDGET:
                    stop_reason = "CAPTURE_DURATION_LIMIT"
                    stop.set()
                    break
                if decoder.poll() is not None:
                    failed.set()
                    break
                if not selector.select(timeout=0.1):
                    continue
                chunk = os.read(recorder.stdout.fileno(),
                                min(FRAME, PCM_BUDGET - observed))
                if not chunk:
                    break
                if len(chunk) % 2:
                    failed.set()
                    break
                observed += len(chunk)
                captured.extend(chunk)
                while len(captured) >= FRAME and not stop.is_set():
                    pcm = bytes(captured[:FRAME])
                    del captured[:FRAME]
                    if not write_pcm(decoder.stdin.fileno(), pcm,
                                     cancelled=cancelled, stopping=stop):
                        failed.set()
                        break
                if failed.is_set():
                    break
        if stop.is_set() and not cancelled.is_set() and stop_reason == "CAPTURE_SOURCE_ENDED":
            stop_reason = "CAPTURE_USER_STOP"
        if not cancelled.is_set() and not failed.is_set() and captured:
            if len(captured) % 2:
                failed.set()
            elif not write_pcm(decoder.stdin.fileno(), bytes(captured),
                               cancelled=cancelled, stopping=threading.Event()):
                failed.set()
        if not cancelled.is_set():
            emit("stage", detail=stop_reason)
            emit("stage", detail="CAPTURE_STOPPED")
        if decoder.stdin and not decoder.stdin.closed:
            decoder.stdin.close()  # EOF forces Vosk FinalResult.
        if not cancelled.is_set() and not failed.is_set():
            reader.join(timeout=MODEL_FINISH_SECONDS)
            if reader.is_alive() or not finished.is_set():
                failed.set()
        if not cancelled.is_set() and not failed.is_set():
            decoder.wait(timeout=1)
            if decoder.returncode != 0:
                failed.set()
        if failed.is_set() and not cancelled.is_set():
            emit("error", detail="STREAMING_TRIAL_FAILED")
        return (130 if cancelled.is_set() else
                70 if failed.is_set() else 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        if not cancelled.is_set():
            emit("error", detail="STREAMING_TRIAL_UNAVAILABLE")
        return 70
    finally:
        stop.set()
        terminate_group(recorder)
        terminate_group(decoder)
        if main_thread:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGINT, old_int)


def main() -> int:
    parser = argparse.ArgumentParser(description="Held Hospital Vosk mic owner")
    parser.add_argument("--streaming-trial", action="store_true")
    parser.add_argument("--model-dir", default="")
    args = parser.parse_args()
    if not args.streaming_trial:
        print(packet("error", detail="STREAMING_TRIAL_HOLD"), flush=True)
        return 64
    return run_trial(args.model_dir)


if __name__ == "__main__":
    raise SystemExit(main())
