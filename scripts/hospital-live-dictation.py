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
import time
import wave
from pathlib import Path

# The script is both directly executable and imported by offline test fixtures.
# Keep its sibling session module importable in either context.
SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import hospital_whisper_session

RATE = 16000
FRAME_BYTES = 2
READ_BYTES = RATE * FRAME_BYTES // 10
CHUNK_SECONDS = 4
MAX_SECONDS = 90
MIN_TAIL_SECONDS = 1
MAX_QUEUE = 2
MODEL_GUARD = Path(__file__).with_name("hospital-whisper-sandbox.py")
OVERLAP_BYTES = RATE * FRAME_BYTES * 3 // 4  # 750 ms of preceding speech
# Require 300ms of PCM and two 100ms speech windows before prewarming.
# Early model loading must not happen on idle/silent microphone capture.
WARMUP_MIN_BYTES = RATE * FRAME_BYTES * 3 // 10
# Optional pause-aware partials only after the existing persistent model is
# loaded. Never schedule clips shorter than 1.2s; 2s remains the maximum.
PAUSE_MIN_BYTES = RATE * FRAME_BYTES * 6 // 5
TOKENS = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
PLACEHOLDER = re.compile(
    r"\[\s*(?:BLANK_AUDIO|NO_SPEECH|SILENCE|MUSIC|NO_AUDIO)\s*\]",
    re.IGNORECASE,
)
TIMESTAMP = re.compile(r"^\s*\[\d\d:\d\d:\d\d(?:\.\d+)?\s*-->\s*"
                       r"\d\d:\d\d:\d\d(?:\.\d+)?\]\s*")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Only non-content latency codes ever leave the Python process.
TIMING_FIELDS = frozenset(("AUDIO_READY", "MODEL_STARTUP", "QUEUE_WAIT",
                           "INFERENCE", "FIRST_TEXT"))


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


def quiet_pcm_frame(pcm: bytes, threshold: float = 500.0) -> bool:
    """Only 100ms-frame energy, never samples, leaves this Python process."""
    if len(pcm) < FRAME_BYTES:
        return False
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) - len(pcm) % FRAME_BYTES])
    if sys.byteorder != "little":
        samples.byteswap()
    return (sum(int(v) * int(v) for v in samples) / max(1, len(samples))
            < threshold * threshold)


def clear_pause_at_end(pcm: bytes, *, minimum_ms: int = 400,
                       threshold: float = 350.0) -> bool:
    """Require sustained low energy before dropping prior-window overlap.

    Check every 100ms frame in the trailing window. A single speech-like
    frame keeps the previous overlap to protect cut-off words. No captured
    samples, frame levels, or voice-derived details are logged.
    """
    frame_bytes = RATE * FRAME_BYTES // 10
    required = frame_bytes * max(4, min(6, (minimum_ms + 99) // 100))
    if len(pcm) < required:
        return False
    ending = pcm[-required:]
    return all(
        quiet_pcm_frame(ending[pos:pos + frame_bytes], threshold)
        for pos in range(0, required, frame_bytes)
    )


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


def trim_repeated_prefix(previous: str, current: str) -> str:
    """Remove exact repeated words caused by a small overlapping PCM window.

    Require at least two matching words to avoid deleting a deliberate "I",
    "yes", or repeated single-word answer.
    """
    before = [m.group().casefold() for m in TOKENS.finditer(previous)]
    spans = list(TOKENS.finditer(current))
    after = [m.group().casefold() for m in spans]
    for size in range(min(8, len(before), len(after)), 1, -1):
        if before[-size:] == after[:size]:
            return current[spans[size - 1].end():].lstrip(" ,.;:!?’'—-")
    return current


def packet(kind: str, *, text: str = "", detail: str = "") -> str:
    return json.dumps({"kind": kind, "text": text, "detail": detail},
                      ensure_ascii=False, separators=(",", ":"))


def timing_packet(metric: str, milliseconds: int) -> str:
    """No text/audio, filenames, tokens, device identifiers or process IDs."""
    if metric not in TIMING_FIELDS or type(milliseconds) is not int:
        raise ValueError("INVALID TIMING RECEIPT")
    return json.dumps({"kind": "timing", "detail": metric,
                       "ms": max(0, min(45000, milliseconds))},
                      separators=(",", ":"))


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
         silence_ms: int = 2200, min_speech_ms: int = 250,
         pilot_one_chunk: bool = False,
         pilot_live_chunks: int = 0, prefer_persistent: bool = False,
         speech_pause_ms: int = 0) -> int:
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

    started_at = time.monotonic()  # session-relative, never wall-clock logging
    stopping = threading.Event()
    cancelled = threading.Event()
    clips = queue.Queue(maxsize=MAX_QUEUE)
    send_lock = threading.Lock()
    capture_done = threading.Event()
    model_warmup_requested = threading.Event()
    persistent_model_ready = threading.Event()
    recognition_idle = threading.Event()
    recognition_idle.set()  # no extra requests while the model is occupied
    recognition_done = threading.Event()
    stopping_error = threading.Event()
    # Single owner-reason receipt for STOP vs internal safety shutdown.
    # Codes are bounded constants, never speech/text or device details.
    capture_reason = ["CAPTURE_SOURCE_ENDED"]
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

    def send_timing(metric: str, start_at: float):
        # Only allow elapsed milliseconds in fixed named slots; do not export
        # raw monotonic timestamps, voice contents or microphone metadata.
        if cancelled.is_set():
            return
        ms = round(max(0.0, time.monotonic() - start_at) * 1000)
        with send_lock:
            print(timing_packet(metric, ms), flush=True)

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
                    capture_reason[0] = "CAPTURE_USER_STOP"
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
        accepted_chunks = 0
        backpressure_reported = False
        quiet_run_ms = 0
        # A pause triggers early submission only if the same guarded model
        # is already ready and at least 1.2s of audio is accumulated. The
        # legacy CLI path and first 1.4s chunk retain their normal cadence.
        pause_gap_ms = (max(400, min(650, speech_pause_ms))
                        if speech_pause_ms > 0 else 0)
        # The follow-up trial restores incremental text while retaining a
        # ceiling on total model launches, capture duration and queue depth.
        live_chunk_ceiling = max(0, min(8, int(pilot_live_chunks)))
        limit = RATE * FRAME_BYTES * (
            6 if pilot_one_chunk else 25 if live_chunk_ceiling else MAX_SECONDS)
        heard_speech = False
        speech_ms = 0
        quiet_ms = 0

        def enqueue(raw):
            nonlocal first_chunk_reported, accepted_chunks, backpressure_reported
            if not raw or not is_speech(raw) or stopping_error.is_set():
                return False
            if live_chunk_ceiling and accepted_chunks >= live_chunk_ceiling:
                return False
            try:
                clips.put((raw, time.monotonic()), timeout=0.1)
                accepted_chunks += 1
                if (live_chunk_ceiling >= 3
                        and accepted_chunks == live_chunk_ceiling - 1):
                    send("stage", detail="CAPTURE_LIMIT_NEAR")
                if not first_chunk_reported:
                    first_chunk_reported = True
                    send("stage", detail="FIRST_AUDIO_QUEUED")
                    send_timing("AUDIO_READY", started_at)
                return True
            except queue.Full:
                if live_chunk_ceiling:
                    # Keep recording and deliver the first model result while
                    # the mic is still open. Drop ONLY this unqueued chunk;
                    # never spawn concurrent Whisper workers or enlarge queue.
                    if not backpressure_reported:
                        backpressure_reported = True
                        send("stage", detail="MODEL_BACKPRESSURE")
                    return False
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
                if (prefer_persistent and pilot_live_chunks > 0
                        and not pilot_one_chunk
                        and not model_warmup_requested.is_set()
                        and len(pending) >= WARMUP_MIN_BYTES
                        and is_speech(bytes(pending))):
                    # Same single guarded worker, no new queue slot. Start its
                    # model concurrently with capture rather than serially
                    # AFTER the opening 1.4-second chunk.
                    model_warmup_requested.set()
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
                # Natural sentence gaps can be sent sooner than the fixed
                # 2-second batch, but only on the already loaded AF_UNIX
                # backend. Do not emit very short fragments or extra jobs.
                if (pause_gap_ms and first_chunk_sent
                        and persistent_model_ready.is_set()):
                    frame_ms = round(len(data) * 1000 / (RATE * FRAME_BYTES))
                    quiet_run_ms = (quiet_run_ms + frame_ms
                                    if quiet_pcm_frame(data) else 0)
                else:
                    quiet_run_ms = 0
                next_size = target if first_chunk_sent else first_target
                full_chunk = len(pending) >= next_size
                pause_chunk = (not full_chunk and first_chunk_sent
                               and persistent_model_ready.is_set()
                               and pause_gap_ms > 0
                               and recognition_idle.is_set()
                               and clips.empty()
                               and len(pending) >= PAUSE_MIN_BYTES
                               and quiet_run_ms >= pause_gap_ms)
                if full_chunk or pause_chunk:
                    take_size = next_size if full_chunk else len(pending)
                    sent = enqueue(bytes(pending[:take_size]))
                    del pending[:take_size]
                    first_chunk_sent = first_chunk_sent or sent
                    quiet_run_ms = 0
                    if pause_chunk and sent:
                        send("stage", detail="PAUSE_CHUNK_READY")
                    if (pilot_one_chunk and sent) or (
                            live_chunk_ceiling
                            and accepted_chunks >= live_chunk_ceiling):
                        # One active model, bounded queued clips, and a hard
                        # ceiling on model launches per live trial.
                        capture_reason[0] = "CAPTURE_CHUNK_LIMIT"
                        stopping.set()
                        halt_child()
                        break
                if vad and heard_speech and quiet_ms >= max(300, silence_ms):
                    capture_reason[0] = "CAPTURE_SILENCE_LIMIT"
                    stopping.set()
                    halt_child()
                    break
                if received >= limit:
                    capture_reason[0] = "CAPTURE_DURATION_LIMIT"
                    stopping.set()
                    halt_child()
                    break
        finally:
            # Short spoken endings must not disappear when the operator
            # presses STOP before the next 1.4/2s chunk threshold.
            # Preserve the one-chunk legacy pilot's strict no-tail behavior.
            # Bounded streaming may consume its *remaining* model budget.
            if (not pilot_one_chunk
                    and (not live_chunk_ceiling
                         or accepted_chunks < live_chunk_ceiling)
                    and not cancelled.is_set()
                    and is_speech(bytes(pending))):
                tail = bytes(pending)
                minimum = RATE * FRAME_BYTES * MIN_TAIL_SECONDS
                if len(tail) < minimum:
                    tail += bytes(minimum - len(tail))
                enqueue(tail)
            capture_done.set()
            send("stage", detail=capture_reason[0])
            send("stage", detail="CAPTURE_STOPPED")
            # Sentinel eventually enters after the finite queued chunks.
            while not cancelled.is_set() and not recognition_done.is_set():
                try:
                    clips.put(None, timeout=0.2)
                    break
                except queue.Full:
                    continue

    def recognize():
        nonlocal first_text_ready
        session = None
        attempted_session = False
        previous_text = ""
        previous_pcm_tail = b""
        previous_chunk_ended_quietly = False
        def start_persistent_once(*, early: bool = False):
            nonlocal session, attempted_session
            if attempted_session or cancelled.is_set() or not prefer_persistent:
                return
            attempted_session = True
            # Only the one existing recognition thread calls this function.
            # No separate loader or concurrent Whisper model can be spawned.
            # An incompatible server still falls back to the guarded CLI.
            if not hospital_whisper_session.server_available(stt_helper):
                send("stage", detail="MODEL_SESSION_UNAVAILABLE")
                return
            if early:
                send("stage", detail="MODEL_EARLY_START")
            send("stage", detail="MODEL_SESSION_STARTING")
            candidate = hospital_whisper_session.WhisperSession(stt_helper)
            try:
                model_loading_at = time.monotonic()
                candidate.start(cancelled=cancelled)
                send_timing("MODEL_STARTUP", model_loading_at)
                session = candidate
                model_started(session.process)
                persistent_model_ready.set()
                send("stage", detail="MODEL_SESSION_READY")
            except (OSError, ValueError, RuntimeError,
                    subprocess.SubprocessError):
                candidate.close()
                send("stage", detail="MODEL_SESSION_UNAVAILABLE")

        try:
            while not cancelled.is_set():
                try:
                    item = clips.get(timeout=0.1)
                except queue.Empty:
                    if capture_done.is_set():
                        break
                    if model_warmup_requested.is_set() and not attempted_session:
                        start_persistent_once(early=True)
                    continue
                if item is None:
                    break
                chunk, enqueued_at = item
                send_timing("QUEUE_WAIT", enqueued_at)
                start_persistent_once()
                if cancelled.is_set():
                    break
                try:
                    recognition_idle.clear()
                    decoding_at = time.monotonic()
                    if session is None:
                        phrase = transcribe_chunk(stt_helper, chunk,
                                                  on_start=model_started,
                                                  on_end=model_ended)
                    else:
                        # A 750-ms overlap gives the decoder continuity at
                        # word boundaries. Prior recognized text is sent only
                        # to the private model over its AF_UNIX socket.
                        # The previous 750ms is useful across a word cut,
                        # but re-decoding it after a verified quiet boundary
                        # wastes CPU and may repeat the previous phrase.
                        # Keep overlap for all continuous/uncertain speech.
                        overlap = previous_pcm_tail
                        if (speech_pause_ms > 0 and previous_chunk_ended_quietly
                                and overlap):
                            overlap = b""
                            send("stage", detail="SILENT_OVERLAP_SKIPPED")
                        raw = session.transcribe(overlap + chunk,
                                                 prompt=previous_text[-160:])
                        cleaned = clean_transcript(raw)
                        phrase = trim_repeated_prefix(previous_text, cleaned)
                        previous_pcm_tail = chunk[-OVERLAP_BYTES:]
                        previous_chunk_ended_quietly = (
                            speech_pause_ms > 0 and clear_pause_at_end(chunk)
                        )
                        if phrase:
                            previous_text = (previous_text + " " + phrase)[-300:]
                    send_timing("INFERENCE", decoding_at)
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                    # No fallback after a server request fails: that could
                    # introduce a *second* model during a stressed session.
                    send("stage", detail=(
                        "MODEL_TIMEOUT" if isinstance(error, subprocess.TimeoutExpired)
                        else "MODEL_FAILURE"))
                    stopping_error.set()
                    send("error", detail="LOCAL WHISPER CHUNK FAILED")
                    stopping.set()
                    halt_child()
                    break
                finally:
                    recognition_idle.set()
                if phrase:
                    if not first_text_ready:
                        first_text_ready = True
                        send("stage", detail="FIRST_TEXT_READY")
                        send_timing("FIRST_TEXT", started_at)
                    send("partial", text=phrase)
        finally:
            if session is not None:
                tracked = session.process
                session.close()
                if tracked is not None:
                    model_ended(tracked)
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
    parser.add_argument("--pilot-one-chunk", action="store_true",
                        help="capture only the first speech chunk and run Whisper once")
    parser.add_argument("--pilot-live-chunks", type=int, default=0,
                        help="bounded incremental trial: max 1-8 model chunks")
    parser.add_argument("--prefer-persistent", action="store_true",
                        help="prefer one private AF_UNIX Whisper model session")
    parser.add_argument("--speech-pause-ms", type=int, default=0,
                        help="optional 400-650ms pause flush on persistent model only")
    parser.add_argument("--vad", action="store_true")
    parser.add_argument("--threshold", type=int, default=600)
    parser.add_argument("--silence-ms", type=int, default=2200)
    parser.add_argument("--min-speech-ms", type=int, default=250)
    args = parser.parse_args()
    return live(args.stt_helper, chunk_seconds=args.chunk_seconds,
                first_chunk_ms=args.first_chunk_ms, vad=args.vad, threshold=args.threshold,
                silence_ms=args.silence_ms, min_speech_ms=args.min_speech_ms,
                pilot_one_chunk=args.pilot_one_chunk,
                pilot_live_chunks=args.pilot_live_chunks,
                prefer_persistent=args.prefer_persistent,
                speech_pause_ms=args.speech_pause_ms)


if __name__ == "__main__":
    raise SystemExit(main())
