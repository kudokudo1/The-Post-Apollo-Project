#!/usr/bin/env python3
"""Private, session-scoped local whisper-server backend for Hospital dictation.

No TCP listener, durable audio, browser access, remote calls or auto-submits.
A single native model is loaded once through the existing Linux resource guard.
This module is optional: callers retain the guarded whisper-cli fallback.
"""
from __future__ import annotations

import http.client
import io
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import wave

RATE = 16000
MODEL_GUARD = Path(__file__).with_name("hospital-whisper-sandbox.py")
MAX_RESPONSE_BYTES = 65536
MAX_PROMPT_CHARS = 160


class SessionUnavailable(RuntimeError):
    pass


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, *, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
        except BaseException:
            sock.close()
            raise
        self.sock = sock


def server_available(stt_helper: str) -> bool:
    """Read-only executable/model preflight. Never starts model inference."""
    try:
        return subprocess.run(
            ["bash", stt_helper, "--session-check"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=3, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def wav_bytes(pcm: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm)
    return out.getvalue()


def multipart_audio(pcm: bytes, prompt: str) -> tuple[bytes, str]:
    boundary = "hospital-" + uuid.uuid4().hex
    data = wav_bytes(pcm)
    # Form-data is assembled in memory; bytes never reach persistent storage.
    fields = [
        ("response_format", "json"),
        ("language", "en"),
        ("temperature", "0.0"),
    ]
    if prompt:
        fields.append(("prompt", prompt[-MAX_PROMPT_CHARS:]))
    body = bytearray()
    for key, value in fields:
        body.extend(("--" + boundary + "\r\nContent-Disposition: form-data; name=\""
                     + key + "\"\r\n\r\n" + str(value) + "\r\n").encode("utf-8"))
    body.extend(("--" + boundary + "\r\nContent-Disposition: form-data; "
                 "name=\"file\"; filename=\"speech.wav\"\r\n"
                 "Content-Type: audio/wav\r\n\r\n").encode("ascii"))
    body.extend(data)
    body.extend(("\r\n--" + boundary + "--\r\n").encode("ascii"))
    return bytes(body), "multipart/form-data; boundary=" + boundary


class WhisperSession:
    """One bounded whisper-server model per active Hospital mic session."""

    def __init__(self, stt_helper: str):
        self.helper = stt_helper
        self.process: subprocess.Popen | None = None
        self._private: tempfile.TemporaryDirectory | None = None
        self.path = ""

    def start(self, *, cancelled=None, timeout: float = 12.0):
        if self.process is not None:
            raise RuntimeError("WHISPER SESSION ALREADY STARTED")
        self._private = tempfile.TemporaryDirectory(prefix="hospital-whisper-")
        # mkdtemp is 0700; assert it rather than risk a readable UDS.
        os.chmod(self._private.name, 0o700)
        self.path = str(Path(self._private.name) / "voice.sock")
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(MODEL_GUARD), "--session",
                 self.helper, self.path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            until = time.monotonic() + timeout
            while time.monotonic() < until:
                if cancelled is not None and cancelled.is_set():
                    raise SessionUnavailable("WHISPER SESSION CANCELLED")
                if self.process.poll() is not None:
                    raise SessionUnavailable("WHISPER SERVER EXITED")
                try:
                    if stat.S_ISSOCK(os.stat(self.path).st_mode):
                        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as check:
                            check.settimeout(0.3)
                            check.connect(self.path)
                        return
                except (OSError, ValueError):
                    pass
                time.sleep(0.05)
            raise SessionUnavailable("WHISPER SERVER READY TIMEOUT")
        except BaseException:
            self.close()
            raise

    def transcribe(self, pcm: bytes, *, prompt: str = "", timeout: float = 13.0) -> str:
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("WHISPER SERVER NOT RUNNING")
        payload, content_type = multipart_audio(pcm, prompt)
        conn = _UnixConnection(self.path, timeout=timeout)
        try:
            conn.request("POST", "/inference", body=payload, headers={
                "Content-Type": content_type,
                "Content-Length": str(len(payload)),
                "Connection": "close",
            })
            response = conn.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("WHISPER SESSION INFERENCE FAILED")
            value = json.loads(raw)
            if not isinstance(value, dict) or not isinstance(value.get("text"), str):
                raise RuntimeError("WHISPER SESSION INVALID RESPONSE")
            return value["text"]
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise RuntimeError("WHISPER SESSION REQUEST FAILED") from exc
        finally:
            conn.close()

    def close(self):
        process = self.process
        self.process = None
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        pass
                    process.wait(timeout=2)
            else:
                process.wait()
        if self._private is not None:
            self._private.cleanup()
            self._private = None
        self.path = ""
