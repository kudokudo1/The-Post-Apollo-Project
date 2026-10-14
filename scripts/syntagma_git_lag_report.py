#!/usr/bin/env python3
"""Read-only Git/Quickshell timing reporter for one saved log.log session.

No Quickshell IPC, process signals, environment flags, or source edits.
"""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import sys

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}")
STALL = re.compile(r"SYNTAGMA_LAG_PROBE // event-loop interval (\d+)ms")
TOGGLE = re.compile(r"SYNTAGMA_LAG_PROBE // git dock toggle synchronous=(\d+)ms // nowOpen=(true|false)")
KEYWORDS = (
    "SYNTAGMA_LAG_PROBE // event-loop interval",
    "SYNTAGMA_LAG_PROBE // git dock toggle",
    "SYNTAGMA_STARTUP_TRACE // git refresh finished",
    "SYNTAGMA_STARTUP_TRACE // git publish phases",
    "SYNTAGMA_STARTUP_TRACE // git slow refresh callback",
)


def parse(lines):
    entries = []
    for raw in lines:
        if not any(key in raw for key in KEYWORDS):
            continue
        match = STAMP.match(raw)
        if not match:
            continue
        try:
            stamp = datetime.strptime(match.group(), "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            continue
        kind = ("stall" if STALL.search(raw) else
                "toggle" if TOGGLE.search(raw) else
                "refresh" if "git refresh finished" in raw else
                "publish" if "git publish phases" in raw else
                "slow_callback")
        entries.append((stamp, kind, raw.strip()))
    return entries


def log_path(args):
    if args.log:
        return Path(args.log)
    root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "quickshell/by-id"
    if args.session:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.session):
            raise ValueError("Invalid session ID")
        return root / args.session / "log.log"
    paths = list(root.glob("*/log.log"))
    if not paths:
        raise FileNotFoundError("No saved Quickshell log.log found")
    return max(paths, key=lambda p: p.stat().st_mtime)


def render(entries, path, before_s=2.0, after_s=1.0):
    stalls = [(t, raw, int(STALL.search(raw).group(1))) for t, typ, raw in entries if typ == "stall"]
    toggles = [(t, raw, int(TOGGLE.search(raw).group(1))) for t, typ, raw in entries if typ == "toggle"]
    refreshes = [(t, raw) for t, typ, raw in entries if typ == "refresh" and "LIVE QUICKSHELL" in raw]
    print(f"SESSION // {path.parent.name}")
    print(f"Git button toggles: {len(toggles)}; LIVE QUICKSHELL refresh completions: {len(refreshes)}; stalls: {len(stalls)}")
    if stalls:
        print(f"Largest recorded delay: {max(x[2] for x in stalls)}ms")
    if not entries:
        print("No matching diagnostic lines. Ensure both POST_APOLLO diagnostic flags were enabled at launch.")
        return
    if not stalls:
        print("No recorded event-loop gaps >= 350ms in this log.")
    for t, raw, ms in stalls[-12:]:
        print(f"\n--- EVENT-LOOP GAP // {t.strftime('%H:%M:%S.%f')[:-3]} // {ms}ms ---")
        near = [(t2, typ, x) for t2, typ, x in entries if
                t - timedelta(seconds=before_s) <= t2 <= t + timedelta(seconds=after_s)]
        for t2, typ, value in near[-18:]:
            print(f" {t2.strftime('%H:%M:%S.%f')[:-3]} [{typ}] {value.split('WARN qml: ')[-1]}")
    if toggles:
        print("\nToggle synchronous times (last 12):")
        for t, raw, ms in toggles[-12:]:
            m = TOGGLE.search(raw)
            print(f" {t.strftime('%H:%M:%S.%f')[:-3]} {ms}ms nowOpen={m.group(2)}")
    if refreshes:
        print("\nLIVE QUICKSHELL refresh completions (last 10):")
        for t, raw in refreshes[-10:]:
            print(f" {t.strftime('%H:%M:%S.%f')[:-3]} {raw.split('WARN qml: ')[-1]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--session", help="Saved Quickshell by-id session, e.g. 0xls3kmwmt")
    group.add_argument("--log", help="Path to a saved plain-text log.log")
    args = parser.parse_args()
    try:
        path = log_path(args)
        with path.open(encoding="utf-8", errors="replace") as f:
            entries = parse(f)
        render(entries, path)
    except (FileNotFoundError, ValueError, PermissionError, OSError) as exc:
        print(f"Cannot read Quickshell log: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
