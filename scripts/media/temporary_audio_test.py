#!/usr/bin/env python3
"""Explicit, temporary PipeWire sink-input A/B probe for the Hi-Fi test bench.

THIS IS NOT A TAB ISOLATION IMPLEMENTATION. A browser sink input can contain
audio from several tabs. The experiment deliberately exposes that limitation.
Called only from an armed UI test; saves and attempts to restore the value.
"""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import time


class ProbeInterrupted(Exception):
    pass


def on_signal(signum, frame):
    raise ProbeInterrupted("interrupted by signal " + str(signum))


def pactl(*args: str) -> str:
    result = subprocess.run(
        ["pactl", *args], capture_output=True, text=True, timeout=5
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "pactl failed")
    return result.stdout


def snapshot(index: int) -> dict | None:
    records = json.loads(pactl("-f", "json", "list", "sink-inputs"))
    return next((s for s in records if int(s.get("index", -1)) == index), None)


def fingerprint_matches(record: dict | None, pid: str, binary: str) -> bool:
    if not record or (not pid and not binary):
        return False
    props = record.get("properties") or {}
    if pid and str(props.get("application.process.id", "")) != pid:
        return False
    if binary and str(props.get("application.process.binary", "")) != binary:
        return False
    return True


def main() -> int:
    if len(sys.argv) != 5:
        print("ERROR: expected index, mute|volume, expected PID, expected binary")
        return 2

    index_text, action, pid, binary = sys.argv[1:]
    if not index_text.isdigit() or action not in ("mute", "volume"):
        print("ERROR: invalid stream or action")
        return 2

    index = int(index_text)
    changed = False
    saved = None
    saved_channels = []
    saved_muted = False
    outcome = "NO CHANGE"

    try:
        saved = snapshot(index)
        if not fingerprint_matches(saved, pid, binary):
            raise RuntimeError("target changed or identity unavailable — no change made")

        saved_muted = bool(saved.get("mute", False))
        channel_objects = list((saved.get("volume") or {}).values())
        saved_channels = [int(channel["value"]) for channel in channel_objects]
        if action == "volume" and not saved_channels:
            raise RuntimeError("volume channels unavailable")

        if action == "mute":
            if saved_muted:
                raise RuntimeError("stream already muted; choose an audible stream")
            pactl("set-sink-input-mute", str(index), "1")
        else:
            # Keep original channel balance. Never raise the user's current level.
            attenuated = [str(max(0, value // 2)) for value in saved_channels]
            pactl("set-sink-input-volume", str(index), *attenuated)
        changed = True

        # Both user-comparison tabs should be audibly playing during this window.
        time.sleep(3)
        outcome = "3-SECOND " + action.upper() + " TEST FINISHED"

    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError,
            subprocess.TimeoutExpired, OSError, ProbeInterrupted) as exc:
        outcome = "ERROR: " + str(exc)

    finally:
        if changed:
            try:
                # Do not restore a stream index that now belongs to another process.
                current = snapshot(index)
                if not fingerprint_matches(current, pid, binary):
                    outcome += " | NOT RESTORED: stream identity changed"
                elif action == "mute":
                    pactl("set-sink-input-mute", str(index), "1" if saved_muted else "0")
                    outcome += " | RESTORED"
                else:
                    pactl("set-sink-input-volume", str(index),
                          *(str(value) for value in saved_channels))
                    outcome += " | RESTORED"
            except Exception as exc:
                outcome += " | RESTORE FAILED: " + str(exc)

    print(outcome, flush=True)
    return 0 if "RESTORED" in outcome and "NOT RESTORED" not in outcome else 1


if __name__ == "__main__":
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    sys.exit(main())
