#!/usr/bin/env python3
"""Opt-in, offline-only streaming recognizer proof. Not linked to Hospital UI.

Reads *only* 16kHz, mono, signed 16-bit PCM from standard input and emits
replaceable hypotheses and committed results on standard output. Does not
open a microphone, submit a Hospital form, install packages/models, connect
to the network, or retain audio/transcripts in files.

A small local Vosk model and the vosk Python package are optional external
prerequisites. Production Hospital remains on its existing Whisper engine.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

SAMPLE_RATE = 16000
FRAME_BYTES = 2
FRAME_MS = 100
READ_BYTES = SAMPLE_RATE * FRAME_BYTES * FRAME_MS // 1000
MAX_AUDIO_SECONDS = 25
MAX_WALL_SECONDS = 45
MAX_AUDIO_BYTES = SAMPLE_RATE * FRAME_BYTES * MAX_AUDIO_SECONDS
MAX_TEXT_CHARS = 4000
MAX_PACKET_CHARS = 8192
MAX_EMISSIONS = 300
MAX_VIRTUAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_CPU_SECONDS = 12
MAX_CORES = 2
PLACEHOLDER = re.compile(r"^\[\s*(?:BLANK_AUDIO|NO_SPEECH|SILENCE|MUSIC)\s*\]$", re.I)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _text_result(raw: str, key: str) -> str:
    """Parse the selected backend field, never trusting a model's JSON."""
    if not isinstance(raw, str) or len(raw) > MAX_PACKET_CHARS:
        raise ValueError("INVALID STREAMING RESULT")
    try:
        record = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("INVALID STREAMING RESULT") from exc
    if not isinstance(record, dict) or not isinstance(record.get(key), str):
        raise ValueError("INVALID STREAMING RESULT")
    value = record[key]
    if CONTROL.search(value) or len(value) > MAX_TEXT_CHARS:
        raise ValueError("INVALID STREAMING TEXT")
    value = " ".join(value.split())
    return "" if PLACEHOLDER.fullmatch(value) else value


class HypothesisReducer:
    """Only a final decoder result may become a committed text segment.

    Repeated/changed hypotheses replace a separate preview; clients must
    never append them to the editable Room/Job form. A commit clears preview.
    """
    def __init__(self):
        self.revision = 0
        self.provisional = ""
        self.committed_chars = 0

    def _event(self, kind: str, text: str) -> dict:
        if self.revision >= MAX_EMISSIONS:
            raise ValueError("STREAMING EVENT LIMIT")
        self.revision += 1
        return {"kind": kind, "text": text, "revision": self.revision,
                "clear_provisional": kind == "commit"}

    def hypothesis(self, raw: str) -> list[dict]:
        text = _text_result(raw, "partial")
        if text == self.provisional:
            return []
        self.provisional = text
        return [self._event("hypothesis", text)]

    def commit(self, raw: str) -> list[dict]:
        text = _text_result(raw, "text")
        had_preview = bool(self.provisional)
        self.provisional = ""
        if not text:
            return [self._event("hypothesis", "")] if had_preview else []
        if self.committed_chars + len(text) > MAX_TEXT_CHARS:
            raise ValueError("STREAMING TEXT LIMIT")
        self.committed_chars += len(text)
        return [self._event("commit", text)]


def process_pcm(stream, recognizer, emit, *, max_bytes: int = MAX_AUDIO_BYTES):
    """One recognizer, finite raw PCM, no device access or parallel model."""
    if not 0 < max_bytes <= MAX_AUDIO_BYTES or max_bytes % FRAME_BYTES:
        raise ValueError("INVALID STREAMING CAP")
    reducer = HypothesisReducer()
    read_bytes = 0
    first_hypothesis_ms = -1
    first_commit_ms = -1
    started_at = time.monotonic()

    def forward(events):
        nonlocal first_hypothesis_ms, first_commit_ms
        for event in events:
            elapsed = min(45000, int((time.monotonic() - started_at) * 1000))
            if event["kind"] == "hypothesis" and event["text"] and first_hypothesis_ms < 0:
                first_hypothesis_ms = elapsed
            if event["kind"] == "commit" and first_commit_ms < 0:
                first_commit_ms = elapsed
            emit(event)

    hit_limit = False
    while read_bytes < max_bytes:
        chunk = stream.read(min(READ_BYTES, max_bytes - read_bytes))
        if not chunk:
            break
        if not isinstance(chunk, bytes) or len(chunk) % FRAME_BYTES:
            raise ValueError("INVALID PCM FRAME")
        read_bytes += len(chunk)
        if recognizer.AcceptWaveform(chunk):
            forward(reducer.commit(recognizer.Result()))
        else:
            forward(reducer.hypothesis(recognizer.PartialResult()))
    else:
        hit_limit = True

    # Vosk's FinalResult is the only valid source for trailing committed words.
    forward(reducer.commit(recognizer.FinalResult()))
    if hit_limit:
        emit({"kind": "status", "code": "CAPTURE_DURATION_LIMIT"})
    emit({"kind": "metrics", "first_hypothesis_ms": first_hypothesis_ms,
          "first_commit_ms": first_commit_ms, "pcm_bytes": read_bytes})
    emit({"kind": "done"})
    return read_bytes


def _clamp_limit(which: int, requested: int) -> None:
    soft, hard = resource.getrlimit(which)
    if soft != resource.RLIM_INFINITY:
        requested = min(requested, soft)
    if hard != resource.RLIM_INFINITY:
        requested = min(requested, hard)
    resource.setrlimit(which, (requested, requested))


def apply_limits() -> None:
    """Fail closed: never load a native model without Linux resource limits."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("LINUX REQUIRED")
    _clamp_limit(resource.RLIMIT_AS, MAX_VIRTUAL_BYTES)
    _clamp_limit(resource.RLIMIT_CPU, MAX_CPU_SECONDS)
    _clamp_limit(resource.RLIMIT_CORE, 0)
    os.nice(10)
    allowed = sorted(os.sched_getaffinity(0))
    if not allowed:
        raise RuntimeError("CPU UNAVAILABLE")
    os.sched_setaffinity(0, set(allowed[:MAX_CORES]))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "2"


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline streaming model proof; no live mic")
    parser.add_argument("--offline-probe", action="store_true")
    parser.add_argument("--model-dir", default="")
    args = parser.parse_args()
    if not args.offline_probe or not args.model_dir:
        print('{"kind":"status","code":"PROBE_DISABLED"}', flush=True)
        return 64
    if not Path(args.model_dir).is_dir() or sys.stdin.isatty():
        print('{"kind":"status","code":"MODEL_OR_PCM_UNAVAILABLE"}', flush=True)
        return 66
    try:
        apply_limits()
        # SIGALRM's default action terminates even a stalled native model or
        # blocked stdin read. CPU time alone cannot bound those stalls.
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.alarm(MAX_WALL_SECONDS)
        # Lazy optional dependency; normal Hospital never loads this package.
        import vosk
        vosk.SetLogLevel(-1)
        model = vosk.Model(args.model_dir)
        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        def emit(event):
            print(json.dumps(event, ensure_ascii=False, separators=(",", ":")),
                  flush=True)
        process_pcm(sys.stdin.buffer, recognizer, emit)
        return 0
    except (ImportError, OSError, RuntimeError, ValueError, MemoryError):
        # No raw exception, file path, audio, word, or model details in errors.
        print('{"kind":"status","code":"OFFLINE_PROBE_FAILED"}', flush=True)
        return 70
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
