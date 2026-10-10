#!/usr/bin/env python3
"""Read-only Hi-Fi browser/tab/audio evidence snapshot.

Run: python3 scripts/media/browser_audio_evidence.py
Collects current MPRIS titles, PipeWire sink-input observations, and *already
enabled* Chromium DevTools /json/list targets. It never enables DevTools,
opens a WebSocket, changes playback, or mutes/changes volumes.

The results are observations, not a proven tab-to-PipeWire relationship.
Review tab titles before sharing output; page titles can contain private data.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen


BROWSER_EXECUTABLES = (
    "brave", "chrome", "chromium", "vivaldi", "opera", "microsoft-edge"
)
MAX_CDP_BYTES = 262144


def run_read_only(argv: list[str], timeout: float = 4.0) -> tuple[str, str]:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "", str(exc)
    if result.returncode:
        return "", result.stderr.strip() or "exit " + str(result.returncode)
    return result.stdout.strip(), ""


def debug_port_for_argv(argv: list[str]) -> int | None:
    """Only accept an already-declared port from a recognized browser."""
    if not argv:
        return None
    exe = Path(argv[0]).name.lower()
    if not any(name in exe for name in BROWSER_EXECUTABLES):
        return None
    for index, arg in enumerate(argv):
        value = ""
        if arg.startswith("--remote-debugging-port="):
            value = arg.split("=", 1)[1]
        elif arg == "--remote-debugging-port" and index + 1 < len(argv):
            value = argv[index + 1]
        if value.isascii() and value.isdigit() and 1 <= int(value) <= 65535:
            return int(value)
    return None


def browser_debug_endpoints() -> list[dict]:
    endpoints: dict[int, dict] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
            argv = [x.decode("utf-8", "replace") for x in raw.split(b"\x00") if x]
        except (OSError, ValueError):
            continue
        port = debug_port_for_argv(argv)
        if port is None:
            continue
        observation = endpoints.setdefault(
            port, {"port": port, "processIds": [], "executables": []}
        )
        observation["processIds"].append(int(entry.name))
        executable = Path(argv[0]).name
        if executable not in observation["executables"]:
            observation["executables"].append(executable)
    return [endpoints[port] for port in sorted(endpoints)]


def sanitize_devtools_targets(payload: object) -> list[dict]:
    """Expose page titles and origin, never complete URLs or WebSockets."""
    if not isinstance(payload, list):
        return []
    results = []
    for target in payload:
        if not isinstance(target, dict):
            continue
        kind = str(target.get("type") or "").lower()
        if kind not in ("page", "webview"):
            continue
        target_url = str(target.get("url") or "")
        origin = urlsplit(target_url).hostname or ""
        results.append({
            "provider": "DEVTOOLS",
            "targetId": str(target.get("id") or ""),
            "title": str(target.get("title") or ""),
            "urlHost": origin,
            "type": kind
        })
    return results


def devtools_probe(endpoint: dict) -> dict:
    result = dict(endpoint)
    result["targets"] = []
    result["error"] = ""
    try:
        # Strict loopback endpoint; only ports declared by browser processes.
        with urlopen(
            "http://127.0.0.1:%d/json/list" % endpoint["port"],
            timeout=0.8
        ) as response:
            data = response.read(MAX_CDP_BYTES + 1)
        if len(data) > MAX_CDP_BYTES:
            raise ValueError("DevTools response exceeds snapshot limit")
        result["targets"] = sanitize_devtools_targets(json.loads(data))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    return result


def mpris_snapshot() -> dict:
    names, error = run_read_only(["playerctl", "-l"])
    result = {"players": [], "error": error}
    for player in names.splitlines():
        player = player.strip()
        if not player:
            continue
        title, title_error = run_read_only(
            ["playerctl", "-p", player, "metadata", "--format", "{{title}}"]
        )
        status, status_error = run_read_only(
            ["playerctl", "-p", player, "status"]
        )
        result["players"].append({
            "player": player,
            "trackTitle": title,
            "status": status,
            "error": title_error or status_error
        })
    return result


def pipewire_snapshot() -> dict:
    raw, error = run_read_only(["pactl", "-f", "json", "list", "sink-inputs"])
    result: dict = {"sinkInputs": [], "error": error}
    if error:
        return result
    try:
        records = json.loads(raw)
        if not isinstance(records, list):
            raise ValueError("Expected an array of sink-inputs")
        for item in records:
            if not isinstance(item, dict):
                continue
            props = item.get("properties") or {}
            result["sinkInputs"].append({
                "index": item.get("index"),
                "muted": bool(item.get("mute", False)),
                "processId": props.get("application.process.id"),
                "processBinary": props.get("application.process.binary"),
                "applicationName": props.get("application.name"),
                "applicationId": props.get("application.id"),
                "mediaName": props.get("media.name")
            })
    except (ValueError, TypeError) as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    return result


def main() -> int:
    endpoints = browser_debug_endpoints()
    snapshot = {
        "schema": "hi-fi-media-identity-observations-v0",
        "warning": (
            "Evidence only; titles may be private. No automatic tab-to-audio "
            "mapping is proven by this snapshot."
        ),
        "mpris": mpris_snapshot(),
        "pipewire": pipewire_snapshot(),
        "browserDevtools": [devtools_probe(e) for e in endpoints],
        "devtoolsNote": (
            "No recognized browser process advertises an existing DevTools "
            "port; none was enabled or requested."
            if not endpoints else
            "Only already-enabled loopback DevTools endpoints were queried."
        ),
        "atSpiNote": (
            "AT-SPI was not queried by this one-shot probe; use Team 5's "
            "TabSurfaceProvider to capture accessibility-based tabs."
        )
    }
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
