#!/usr/bin/env python3
import argparse
import array
import math
import os
import signal
import subprocess
import sys
import time
import wave


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path")
    parser.add_argument("--threshold", type=int, default=600)
    parser.add_argument("--silence-ms", type=int, default=2200)
    parser.add_argument("--min-speech-ms", type=int, default=250)
    parser.add_argument("--max-seconds", type=int, default=90)
    return parser.parse_args()


def chunk_rms(data):
    if not data:
        return 0.0

    samples = array.array("h")
    samples.frombytes(data)

    if sys.byteorder != "little":
        samples.byteswap()

    if not samples:
        return 0.0

    total = 0
    for sample in samples:
        total += sample * sample

    return math.sqrt(total / len(samples))


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.audio_path) or ".", exist_ok=True)

    command = [
        "pw-record",
        "--raw",
        "--rate=16000",
        "--channels=1",
        "--format=s16",
        "-"
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=None
    )

    stopping = False

    def stop_child(signum=None, frame=None):
        nonlocal stopping
        stopping = True

        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)

    sample_rate = 16000
    frames_per_chunk = 1600
    bytes_per_chunk = frames_per_chunk * 2
    chunk_ms = int((frames_per_chunk / sample_rate) * 1000)

    heard_speech = False
    speech_ms = 0
    silence_ms = 0
    automatic_reason = ""
    started = time.monotonic()

    try:
        with wave.open(args.audio_path, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)

            while not stopping:
                if process.stdout is None:
                    break

                data = process.stdout.read(bytes_per_chunk)

                if not data:
                    break

                output.writeframesraw(data)
                rms = chunk_rms(data)

                if rms >= args.threshold:
                    speech_ms += chunk_ms
                    silence_ms = 0

                    if speech_ms >= args.min_speech_ms:
                        heard_speech = True
                elif heard_speech:
                    silence_ms += chunk_ms
                else:
                    speech_ms = 0

                if (
                    heard_speech
                    and silence_ms >= args.silence_ms
                ):
                    automatic_reason = "VAD_STOP"
                    break

                if (
                    args.max_seconds > 0
                    and time.monotonic() - started
                    >= args.max_seconds
                ):
                    automatic_reason = "VAD_MAX"
                    break
    finally:
        stop_child()

        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass

            process.wait(timeout=2.0)

    if automatic_reason:
        print(automatic_reason, file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
