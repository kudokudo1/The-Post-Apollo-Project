#!/usr/bin/env python3
"""Shared local Hospital live dictation, never a form submit.

PipeWire raw 16 kHz PCM is captured continuously while a separate thread runs
the already installed whisper-cli helper against short, isolated WAV chunks.
One JSON line per accepted phrase arrives before STOP, unlike the old
record-then-transcribe flow. Latency depends on local model inference.

No network, database writes, user document access, or persistent audio storage.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path

RATE = 16000
FRAME_BYTES = 2
READ_BYTES = RATE * FRAME_BYTES // 10
CHUNK_SECONDS = 4
MAX_SECONDS = 90
MIN_TAIL_SECONDS = 1
MAX_QUEUE = 2
MODEL_GUARD = Path(__file__).with_name("hospital-whisper-sandbox.py")
PLACEHOLDER = re.compile(
    r"\[\s*(?:BLANK_AUDIO|NO_SPEECH|SILENCE|MUSIC|NO_AUDIO)\s*\]",
    re.IGNORECASE,
)
TIMESTAMP = re.compile(r"^\s*\[\d\d:\d\d:\d\d(?:\.\d+)?\s*-->\s*"
                       r"\d\d:\d\d:\d\d(?:\.\d+)?\]\s*")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def is_speech(pcm: bytes, threshold: float = 500.0) -> bool:
    """Gate silent chunks before Whisper can hallucinate [BLANK_AUDIO]."""
    if len(pcm) < FRAME_BYTES:
        return False
    count = 0
    window = RATE * FRAME_BYTES // 10
    for offset in range(0, len(pcm) - window + 1, window):
        segment = array.array("h")
        segment.frombytes(pcm[offset:offset + window])
        if sys.byteorder != "little":
            segment.byteswap()
        rms = math.sqrt(sum(int(x) * int(x) for x in segment) /
                        max(1, len(segment)))
        if rms >= threshold:
            count += 1
            if count >= 2:
                return True
    return False


def clean_transcript(value: str) -> str:
    if not isinstance(value, str):
        return ""
    chunks = []
    for line in value.splitlines():
        line = TIMESTAMP.sub("", line.strip())
        line = PLACEHOLDER.sub("", line).strip()
        if not line or line.startswith("###") or line == "[Start speaking]":
            continue
        chunks.append(line)
    text = " ".join(chunks)
    text = re.sub(r"\s+", " ", text).strip()
    if CONTROL.search(text):
        return ""
    return text[:4000]


def packet(kind: str, *, text: str = "", detail: str = "") -> str:
    return json.dumps({"kind": kind, "text": text, "detail": detail},
                      ensure_ascii=False, separators=(",", ":"))


def transcribe_chunk(stt_helper: str, audio: bytes, *,
                     on_start=None, on_end=None) -> str:
    if not is_speech(audio):
        return ""
    # Keep a handle to the actual Whisper process: a cancelled voice session
    # must not leave a model consuming memory/CPU after Python stops.
    with tempfile.TemporaryDirectory(prefix="hospital-live-chunk-") as folder:
        wav = Path(folder) / "speech.wav"
        with wave.open(str(wav), "wb") as dest:
            dest.setnchannels(1)
            dest.setsampwidth(FRAME_BYTES)
            dest.setframerate(RATE)
            dest.writeframes(audio)
        # The recorder has active threads: never use Popen(preexec_fn=...).
        # A dedicated Python child applies per-model Linux limits *before*
        # exec. On guard failure inference refuses rather than running raw.
        process = subprocess.Popen(
            [sys.executable, str(MODEL_GUARD), stt_helper, str(wav)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True)
        try:
            if on_start is not None:
                on_start(process)
            output, _ = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            # Kill the whole model process group, not just its entry-point.
            # This also covers future helper scripts that fork children.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        finally:
            if on_end is not None:
                on_end(process)
    if process.returncode != 0:
        raise RuntimeError("LOCAL WHISPER CHUNK FAILED")
    return clean_transcript(output)


def live(stt_helper: str, *, chunk_seconds: int = CHUNK_SECONDS,
         first_chunk_ms: int = 1400, vad: bool = False, threshold: int = 600,
         silence_ms: int = 2200, min_speech_ms: int = 250) -> int:
    if not Path(stt_helper).is_file():
        print(packet("error", detail="LOCAL WHISPER HELPER UNAVAILABLE"),
              flush=True)
        return 2
    try:
        subprocess.run(["bash", stt_helper, "--check"], check=True,
                       capture_output=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        print(packet("error", detail="LOCAL WHISPER MODEL UNAVAILABLE"),
              flush=True)
        return 2

    stopping = threading.Event()
    cancelled = threading.Event()
    clips = queue.Queue(maxsize=MAX_QUEUE)
    send_lock = threading.Lock()
    capture_done = threading.Event()
    recognition_done = threading.Event()
    stopping_error = threading.Event()
    recorder = None
    model_lock = threading.Lock()
    active_model = None
    first_model_started = False
    first_model_ended = False
    first_text_ready = False

    def halt_model():
        with model_lock:
            current = active_model
        if current is not None and current.poll() is None:
            try:
                # The bash helper execs whisper-cli; session leadership also
                # protects against future helper subprocesses.
                os.killpg(current.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            # A model ignoring SIGTERM must not outlive its dictation
            # session and keep consuming the user's PC resources.
            def force_stop():
                if current.poll() is None:
                    try:
                        os.killpg(current.pid, signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
            threading.Timer(1.0, force_stop).start()

    def model_started(process):
        nonlocal active_model, first_model_started
        with model_lock:
            active_model = process
        if not first_model_started:
            first_model_started = True
            send("stage", detail="FIRST_MODEL_STARTED")
        if cancelled.is_set():
            halt_model()

    def model_ended(process):
        nonlocal active_model, first_model_ended
        with model_lock:
            if active_model is process:
                active_model = None
        if not first_model_ended:
            first_model_ended = True
            send("stage", detail="FIRST_MODEL_ENDED")

    def send(kind, text="", detail=""):
        if cancelled.is_set():
            return
        with send_lock:
            print(packet(kind, text=text, detail=detail), flush=True)

    def halt_child():
        if recorder is not None and recorder.poll() is None:
            try:
                recorder.terminate()
            except (ProcessLookupError, OSError):
                pass

    def sigterm(*_unused):
        cancelled.set()
        stopping.set()
        halt_model()
        halt_child()

    signal.signal(signal.SIGTERM, sigterm)
    signal.signal(signal.SIGINT, sigterm)

    try:
        recorder = subprocess.Popen(
            ["pw-record", "--raw", "--rate=16000", "--channels=1",
             "--format=s16", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        send("error", detail="PIPEWIRE RECORDING UNAVAILABLE")
        return 3
    # Stage-only receipts, never audio, transcript contents, device names or
    # process identifiers. QML publishes at most a handful per recording.
    send("stage", detail="RECORDER_STARTED")

    def read_commands():
        try:
            for line in sys.stdin:
                command = line.strip().upper()
                if command == "CANCEL":
                    cancelled.set()
                    stopping.set()
                    halt_model()
                    halt_child()
                    break
                if command == "STOP":
                    stopping.set()
                    halt_child()
                    break
        except (OSError, ValueError):
            pass

    def capture():
        pending = bytearray()
        received = 0
        # Shorter phrases can be shown sooner without changing Manage's default.
        # Send the opening speech segment sooner. Subsequent segments use the
        # normal cadence so a slow local model cannot spawn a new inference
        # for every word; the recognition queue remains bounded.
        target = RATE * FRAME_BYTES * max(2, min(4, chunk_seconds))
        first_target = RATE * FRAME_BYTES * max(
            1000, min(1000 * max(2, min(4, chunk_seconds)), first_chunk_ms)) // 1000
        first_chunk_sent = False
        first_chunk_reported = False
        limit = RATE * FRAME_BYTES * MAX_SECONDS
        heard_speech = False
        speech_ms = 0
        quiet_ms = 0

        def enqueue(raw):
            nonlocal first_chunk_reported
            if not raw or not is_speech(raw) or stopping_error.is_set():
                return False
            try:
                clips.put(raw, timeout=0.1)
                if not first_chunk_reported:
                    first_chunk_reported = True
                    send("stage", detail="FIRST_AUDIO_QUEUED")
                return True
            except queue.Full:
                stopping_error.set()
                send("error", detail="LOCAL MODEL TOO SLOW // DICTATION STOPPED")
                stopping.set()
                halt_child()
                return False

        try:
            while not stopping.is_set() and not cancelled.is_set():
                data = recorder.stdout.read(READ_BYTES) if recorder.stdout else b""
                if not data:
                    break
                pending.extend(data)
                received += len(data)
                if vad:
                    samples = array.array("h")
                    samples.frombytes(data[:len(data) - len(data) % 2])
                    if sys.byteorder != "little":
                        samples.byteswap()
                    rms = math.sqrt(sum(int(x) * int(x) for x in samples)
                                    / max(1, len(samples)))
                    frame_ms = round(len(data) * 1000 / (RATE * FRAME_BYTES))
                    if rms >= max(1, threshold):
                        speech_ms += frame_ms
                        quiet_ms = 0
                        if speech_ms >= max(100, min_speech_ms):
                            heard_speech = True
                    elif heard_speech:
                        quiet_ms += frame_ms
                    else:
                        speech_ms = 0
                next_size = target if first_chunk_sent else first_target
                if len(pending) >= next_size:
                    sent = enqueue(bytes(pending[:next_size]))
                    del pending[:next_size]
                    first_chunk_sent = first_chunk_sent or sent
                if (vad and heard_speech and quiet_ms >= max(300, silence_ms)) \
                        or received >= limit:
                    stopping.set()
                    halt_child()
                    break
        finally:
            # Short spoken endings used to disappear (<1s was discarded).
            # Gate on speech first, then pad a final subsecond clip to 1s so
            # Whisper can recognize it after an explicit STOP.
            if not cancelled.is_set() and is_speech(bytes(pending)):
                tail = bytes(pending)
                minimum = RATE * FRAME_BYTES * MIN_TAIL_SECONDS
                if len(tail) < minimum:
                    tail += bytes(minimum - len(tail))
                enqueue(tail)
            capture_done.set()
            # Sentinel eventually enters after the finite queued chunks.
            while not cancelled.is_set() and not recognition_done.is_set():
                try:
                    clips.put(None, timeout=0.2)
                    break
                except queue.Full:
                    continue

    def recognize():
        while not cancelled.is_set():
            try:
                chunk = clips.get(timeout=0.2)
            except queue.Empty:
                if capture_done.is_set():
                    break
                continue
            if chunk is None:
                break
            try:
                phrase = transcribe_chunk(stt_helper, chunk,
                                          on_start=model_started,
                                          on_end=model_ended)
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                # Distinguish slow/stalled inference from other model failures
                # without exposing stderr, audio, identifiers or recognized text.
                send("stage", detail=(
                    "MODEL_TIMEOUT" if isinstance(error, subprocess.TimeoutExpired)
                    else "MODEL_FAILURE"))
                stopping_error.set()
                send("error", detail="LOCAL WHISPER CHUNK FAILED")
                stopping.set()
                halt_child()
                break
            if phrase:
                nonlocal first_text_ready
                if not first_text_ready:
                    first_text_ready = True
                    send("stage", detail="FIRST_TEXT_READY")
                send("partial", text=phrase)
        recognition_done.set()
        if not cancelled.is_set() and not stopping_error.is_set():
            send("stage", detail="RECORDING_COMPLETED")
            send("done")

    command_thread = threading.Thread(target=read_commands, daemon=True)
    capture_thread = threading.Thread(target=capture, daemon=True)
    recognition_thread = threading.Thread(target=recognize, daemon=True)
    command_thread.start()
    recognition_thread.start()
    capture_thread.start()
    send("ready")
    recognition_thread.join()
    stopping.set()
    halt_model()
    halt_child()
    capture_thread.join(timeout=3)
    try:
        recorder.wait(timeout=2)
    except subprocess.TimeoutExpired:
        recorder.kill()
        recorder.wait(timeout=2)
    return 0 if not cancelled.is_set() else 130


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stt_helper")
    parser.add_argument("--chunk-seconds", type=int, default=CHUNK_SECONDS)
    parser.add_argument("--first-chunk-ms", type=int, default=1400)
    parser.add_argument("--vad", action="store_true")
    parser.add_argument("--threshold", type=int, default=600)
    parser.add_argument("--silence-ms", type=int, default=2200)
    parser.add_argument("--min-speech-ms", type=int, default=250)
    args = parser.parse_args()
    return live(args.stt_helper, chunk_seconds=args.chunk_seconds,
                first_chunk_ms=args.first_chunk_ms, vad=args.vad, threshold=args.threshold,
                silence_ms=args.silence_ms, min_speech_ms=args.min_speech_ms)


if __name__ == "__main__":
    raise SystemExit(main())
