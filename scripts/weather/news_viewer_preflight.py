#!/usr/bin/env python3
"""Read-only V0 preflight for Weather Station NEWS's future isolated viewer.

NO browser launch. NO compositor IPC. NO network requests, profile writes,
runtime mutations, QtWebEngine imports, or arbitrary URL execution. This helper
returns one small JSON record for a deliberate CHECK ENGINE action.

A real browser process is disallowed until Stage Director owns and verifies
viewport clipping, stacking, focus and CLOSE semantics on the actual display.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit

SCHEMA = 1
ROLE = "post-apollo-weather-news"
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
CHANNEL_ID = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")
SOURCE_ID = re.compile(r"[a-z0-9_-]{2,40}\Z")
BROWSER_CANDIDATES = (
    "brave-browser", "brave-browser-stable", "chromium",
    "chromium-browser", "google-chrome-stable", "google-chrome",
    "microsoft-edge-stable", "microsoft-edge",
)


def trusted_https(value: str) -> bool:
    if not isinstance(value, str) or not (0 < len(value) < 2048):
        return False
    if any(x in value for x in ("\\", "\n", "\r", "\t", " ", "<", ">")):
        return False
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.username is not None or parsed.password is not None or parsed.port is not None:
        return False
    if parsed.fragment:
        return False
    return re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname) is not None


def sources() -> dict[str, dict[str, str]]:
    file = Path(__file__).with_name("news_viewer_allowlist.json")
    registry = json.loads(file.read_text(encoding="utf-8"))
    if registry.get("schema") != SCHEMA:
        raise ValueError("SOURCE REGISTRY VERSION MISMATCH")
    out: dict[str, dict[str, str]] = {}
    for item in registry.get("sources", []):
        sid, url = item["id"], item["url"]
        if (not SOURCE_ID.fullmatch(sid) or not trusted_https(url)
                or sid in out):
            raise ValueError("SOURCE REGISTRY INVALID")
        out[sid] = {"url": url, "section": item["section"]}
    return out


def resolved_target(kind: str, ident: str) -> dict[str, str] | None:
    """Resolve only a registered source or strictly typed public YouTube ID."""
    if kind == "source":
        matched = sources().get(ident) if SOURCE_ID.fullmatch(ident) else None
        if matched is None:
            return None
        return {"kind": "catalog", "id": ident,
                "url": matched["url"], "section": matched["section"]}
    if kind == "youtube-video" and VIDEO_ID.fullmatch(ident):
        return {"kind": kind, "id": ident,
                "url": "https://www.youtube.com/watch?v=" + ident,
                "section": "CREATORS"}
    if kind == "youtube-channel" and CHANNEL_ID.fullmatch(ident):
        return {"kind": kind, "id": ident,
                "url": "https://www.youtube.com/channel/" + ident,
                "section": "CREATORS"}
    return None


def inspect_browser() -> dict:
    found = []
    for name in BROWSER_CANDIDATES:
        path = shutil.which(name)
        if path:
            found.append({"program": name, "path": path})
    return {"available": bool(found),
            "preferred": found[0]["program"] if found else "",
            "candidates": found}


def report(target: dict[str, str] | None = None) -> dict:
    browser = inspect_browser()
    return {
        "schema": SCHEMA,
        "role": ROLE,
        "state": "BLOCKED_VIEWPORT_UNAVAILABLE",
        "renderer": "EXTERNAL_BROWSER_PROCESS",
        "browser": browser,
        "target": target,
        "stage_director": {
            "clip_verified": False,
            "input_routing_verified": False,
            "lifecycle_verified": False,
        },
        "can_launch": False,
        "can_play": False,
        "muted": True,
        "message": ("BROWSER CANDIDATE FOUND // STAGE DIRECTOR NOT CONNECTED"
                    if browser["available"]
                    else "NO HOST BROWSER FOUND // STAGE DIRECTOR NOT CONNECTED"),
    }


def main(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect", help="read-only browser capability")
    plan = commands.add_parser("plan", help="read-only source-target validation")
    plan.add_argument("--kind", choices=("source", "youtube-channel", "youtube-video"),
                      required=True)
    plan.add_argument("--id", required=True)
    parsed = parser.parse_args(args)

    target = None
    if parsed.command == "plan":
        target = resolved_target(parsed.kind, parsed.id)
        if target is None:
            print(json.dumps({
                "schema": SCHEMA,
                "state": "INVALID_TARGET",
                "can_launch": False,
                "message": "SOURCE NOT REGISTERED OR INVALID IDENTIFIER",
            }))
            return 2

    print(json.dumps(report(target), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
