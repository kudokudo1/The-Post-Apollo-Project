#!/usr/bin/env python3
"""Observe known Post-Apollo storage metadata, never file contents.

Counts sampled changes in size, mtime or inode, NOT write syscalls,
transactions, bytes written, or writer identity. No directory traversal.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import time

SCHEMA = "post-apollo-storage-observation-v1"
# Fixed source-derived catalog. IDs, not paths, appear in reports.
TARGETS = (
    ("notifications.history", "qs", "notifications-history.json"),
    ("notifications.favorites", "qs", "notification-favorites.json"),
    ("notifications.policies", "qs", "notification-policies.json"),
    ("notifications.scroll", "qs", "notification-scroll-settings.json"),
    ("weather.cache", "qs", "weather-last-known-v1.json"),
    ("weather.history", "qs", "weather-live-history-v1.json"),
    ("weather.events", "qs", "weather-event-archive-v1.json"),
    ("weather.places", "qs", "weather-place-last-known-v1.json"),
    ("weather.dossier", "qs", "weather-dossier-archive-v1.json"),
    ("hub.layout", "qs", "apollo-hub-layout.json"),
    ("hub.notes", "qs", "apollo-hub-notes-v1.json"),
    ("hub.todo", "qs", "apollo-hub-todo-v1.json"),
    ("social.identities", "qs", "social-identities-v1.json"),
    ("git.journal", "shell", "git-operation-journal.json"),
    ("git.delta", "shell", "git-operation-journal-delta.json"),
    ("forest.preferences", "xdg", "post-apollo/forest/ui-preferences/model-preferences-v1.json"),
    ("finance.manual", "xdg", "post-apollo/finance/banking-manual/manual-session.json"),
    ("company.hubs", "xdg", "post-apollo/company/hubs-v1.json"),
)


def xdg_data():
    value = os.environ.get("XDG_DATA_HOME", "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / ".local/share"


def observe(path, uid):
    # lstat does not open the object or follow its final symlink. Parent
    # directory resolution follows the user's ordinary configured paths.
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ("absent", None)
    except OSError:
        return ("unavailable", None)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != uid:
        return ("unavailable", None)
    return ("present", (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))


def begin(id_, observation):
    state, value = observation
    return {"id": id_, "initialState": state, "finalState": state,
            "initialBytes": value[2] if value else None,
            "finalBytes": value[2] if value else None,
            "changedIntervals": 0, "replacementIntervals": 0,
            "unavailableIntervals": 0, "comparableIntervals": 0}


def advance(row, before, after):
    old_state, old = before
    state, value = after
    row["finalState"] = state
    row["finalBytes"] = value[2] if value else None
    if "unavailable" in (old_state, state):
        row["unavailableIntervals"] += 1
        return
    row["comparableIntervals"] += 1
    if before != after:
        row["changedIntervals"] += 1
        if old and value and old[:2] != value[:2]:
            row["replacementIntervals"] += 1


def emit(record):
    print(json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--shell-dir", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--workshop", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_dir.is_absolute() or not args.shell_dir.is_absolute():
        parser.error("absolute configured roots required")
    if not 1 <= args.duration <= 30:
        parser.error("duration 1..30 seconds")
    if args.workshop:
        from syntagma_quickshell_thread_sampler import WorkshopOutput, WorkshopOutputLimit
        send = WorkshopOutput().emit
        output_errors = (WorkshopOutputLimit,)
    else:
        send = emit
        output_errors = ()
    roots = {"qs": args.data_dir, "shell": args.shell_dir, "xdg": xdg_data()}
    targets = [(key, roots[root] / rel) for key, root, rel in TARGETS]
    uid = os.getuid()
    previous = {key: observe(path, uid) for key, path in targets}
    rows = {key: begin(key, previous[key]) for key, path in targets}
    start = time.monotonic()
    samples = 0
    try:
        for tick in range(1, args.duration + 1):
            time.sleep(max(0, start + tick - time.monotonic()))
            for key, path in targets:
                current = observe(path, uid)
                advance(rows[key], previous[key], current)
                previous[key] = current
            if tick % 10 == 0 or tick == args.duration:
                samples += 1
                now = time.monotonic()
                elapsed_ms = round((now - start) * 1000)
                timeline = {"monotonicMs": round(now*1000)} if args.workshop else {}
                send({**timeline, "schema": SCHEMA, "event": "storage", "sequence": samples,
                      "intervals": tick, "elapsedMs": elapsed_ms,
                      "rows": list(rows.values())})
    except output_errors:
        return 1
    except KeyboardInterrupt:
        try:
            send({"schema": SCHEMA, "event": "stopped", "samples": samples})
        except output_errors:
            pass
        return 130
    end = {"schema": SCHEMA, "event": "complete", "samples": samples}
    if args.workshop:
        end.update(workshopSchema="post-apollo-observer-calibration-v1",
                   calibration={"kind":"storage","durationSeconds":args.duration},
                   observedMs=elapsed_ms, monotonicMs=round(now*1000),
                   startedMonotonicMs=round(start*1000))
    try:
        send(end)
    except output_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
