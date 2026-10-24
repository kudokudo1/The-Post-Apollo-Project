#!/usr/bin/env python3
"""Read-only, sanitized Hi-Fi radio PAUSE/STOP state observer.

Samples the existing controller's 'snapshot' command; never sends transport
commands, opens a radio URL, prints tokens/titles, or changes playback.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from media_controller_cli import send
from media_controller_server import default_socket


VALID_MPD_STATES = frozenset(
    ("playing", "paused", "stopped", "unloaded", "offline", "unavailable"))
VALID_RELAY_STATES = frozenset(
    ("queued", "connecting", "connected", "streaming", "ended",
     "empty", "failed", "unknown"))
VALID_LOADED = frozenset(
    ("radio-browser", "local-mpd", "direct-stream", "youtube"))
VALID_ERROR = frozenset(
    ("BACKEND_OFFLINE", "CONTROLLER_UNAVAILABLE", "BACKEND_PROTOCOL",
     "NO_LOADED_MEDIA", "BACKEND_REJECTED", "UNKNOWN_SOURCE"))


def sanitized_record(response: dict, previous_bytes: int | None = None) -> dict:
    """No URIs, tokens, station titles, queue IDs, raw errors or audio content."""
    result = response.get("result") if response.get("ok") is True else None
    if not isinstance(result, dict):
        result = {}
    session = result.get("session")
    if not isinstance(session, dict):
        session = {}
    loaded = result.get("loaded")
    if not isinstance(loaded, dict):
        loaded = {}
    source = loaded.get("ref")
    if not isinstance(source, dict):
        source = {}
    radio = result.get("radioHealth")
    if not isinstance(radio, dict):
        radio = {}

    state = session.get("state")
    relay_state = radio.get("state")
    source_id = source.get("source")
    raw_bytes = radio.get("bytesReceived")
    byte_count = (raw_bytes if isinstance(raw_bytes, int) and
                  not isinstance(raw_bytes, bool) and raw_bytes >= 0 else None)
    observation = {
        "event": "radio-state",
        "tsMs": round(time.time() * 1000),
        "snapshotOk": response.get("ok") is True,
        "mpdState": state if state in VALID_MPD_STATES else "unknown",
        "controllerOwnsPlayback": session.get("ownedByController") is True,
        "loadedSource": source_id if source_id in VALID_LOADED else "none",
        "relayState": relay_state if relay_state in VALID_RELAY_STATES else "unknown",
        "relayBytesReceived": byte_count,
        "relayBytesDelta": (max(0, byte_count - previous_bytes)
                            if byte_count is not None and previous_bytes is not None
                            else None),
    }
    error = response.get("error")
    if not observation["snapshotOk"] and isinstance(error, dict):
        code = error.get("code")
        observation["errorCode"] = code if code in VALID_ERROR else "unavailable"
    return observation


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", type=int, default=12)
    p.add_argument("--interval", type=float, default=2.0)
    args = p.parse_args(argv)
    if not 1 <= args.samples <= 120:
        p.error("--samples must be between 1 and 120")
    if not 0.5 <= args.interval <= 60:
        p.error("--interval must be 0.5 to 60 seconds")
    path = default_socket()
    previous_bytes = None
    for i in range(args.samples):
        if i:
            time.sleep(args.interval)
        try:
            raw = send(path, "snapshot")
            record = sanitized_record(raw, previous_bytes)
            # Station/queue identity is intentionally not persisted or exposed.
            if record["loadedSource"] != "radio-browser":
                record["relayBytesDelta"] = None
                previous_bytes = None
            else:
                previous_bytes = record["relayBytesReceived"]
        except (OSError, ValueError, RuntimeError) as exc:
            # Never emit exception strings: socket paths or tokens may occur.
            record = {"event": "radio-state", "tsMs": round(time.time() * 1000),
                      "snapshotOk": False, "errorCode": "connection-unavailable"}
            previous_bytes = None
        print(json.dumps(record, separators=(",", ":"), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
