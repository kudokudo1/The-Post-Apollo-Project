#!/usr/bin/env python3
"""Post-Apollo Clock B0: independent, *non-actuating* alarm observer.

The Quickshell AlarmManager remains the sole scheduler/audio/notification
owner. This process only reads its persisted V2 alarm file and reports
potential due/missed events. It cannot ring, modify the file, notify, or
take an ownership lease over Quickshell.

No implicit alarm-file discovery: Quickshell.dataDir is per shell. The
operator or a future authenticated handshake must supply the exact path.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import time

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ALARMS = 100
MAX_LATE_MS = 2 * 60 * 1000
MAX_RING_MS = 15 * 60 * 1000
MAX_TIMESTAMP_MS = 8640000000000000
SUPPORTED_MODES = ("once", "weekly")
OBSERVER_MODE = "READ_ONLY"
VERSION = 1


class Refused(Exception):
    pass


def integer(value, minimum=0, maximum=MAX_TIMESTAMP_MS):
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def local_date(key):
    if not isinstance(key, str) or len(key) != 10:
        raise Refused("INVALID_LOCAL_DATE")
    try:
        value = date.fromisoformat(key)
    except ValueError as exc:
        raise Refused("INVALID_LOCAL_DATE") from exc
    if value.isoformat() != key or value.year < 1970:
        raise Refused("INVALID_LOCAL_DATE")
    return value


def at_local(day, hour, minute):
    # Uses the system's *local* timezone, as Quickshell's JS Date does.
    # The observer never actuates during DST ambiguity; it only reports.
    try:
        return int(datetime(day.year, day.month, day.day, hour, minute).timestamp() * 1000)
    except (OverflowError, OSError, ValueError) as exc:
        raise Refused("INVALID_DUE_TIME") from exc


def snapshot_file(path):
    target = Path(path)
    if not target.is_absolute() or target.name != "time-alarms-v2.json":
        raise Refused("EXPLICIT_V2_ALARM_PATH_REQUIRED")
    fd = None
    try:
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_CLOEXEC", 0))
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or not 0 < st.st_size <= MAX_FILE_BYTES:
            raise Refused("UNSAFE_ALARM_FILE")
        with os.fdopen(fd, "rb", closefd=False) as source:
            raw = source.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise Refused("ALARM_FILE_TOO_LARGE")
    except FileNotFoundError as exc:
        raise Refused("ALARM_FILE_NOT_FOUND") from exc
    except (OSError, PermissionError) as exc:
        raise Refused("ALARM_FILE_UNREADABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise Refused("INVALID_ALARM_JSON") from exc
    validate_snapshot(document)
    return document


def validate_snapshot(doc):
    if not isinstance(doc, dict) or doc.get("version") != 2:
        raise Refused("UNSUPPORTED_ALARM_VERSION")
    rows = doc.get("alarms")
    if not isinstance(rows, list) or len(rows) > MAX_ALARMS:
        raise Refused("INVALID_ALARM_ARRAY")
    if not integer(doc.get("nextId"), 1):
        raise Refused("INVALID_NEXT_ALARM_ID")
    ids = set()
    for a in rows:
        if not isinstance(a, dict):
            raise Refused("INVALID_ALARM")
        identity = a.get("id")
        if not integer(identity, 1, doc["nextId"] - 1) or identity in ids:
            raise Refused("INVALID_ALARM_ID")
        ids.add(identity)
        hour, minute = a.get("hour"), a.get("minute")
        if not integer(hour, 0, 23) or not integer(minute, 0, 59):
            raise Refused("INVALID_ALARM_CLOCK")
        if a.get("mode") not in SUPPORTED_MODES:
            raise Refused("INVALID_ALARM_MODE")
        days = a.get("weekdays")
        if not isinstance(days, list) or any(not integer(d, 0, 6) for d in days) or len(set(days)) != len(days):
            raise Refused("INVALID_WEEKDAYS")
        if a["mode"] == "weekly" and not days:
            raise Refused("MISSING_WEEKDAYS")
        if a["mode"] == "once":
            local_date(a.get("date"))
        pause = a.get("pausedUntilDate", "")
        if pause:
            local_date(pause)
        for field in ("enabled", "ringing", "completed"):
            if not isinstance(a.get(field), bool):
                raise Refused("INVALID_ALARM_STATE")
        for field in ("ringStartedAtMs", "snoozeUntilMs", "armedAtMs", "lastProcessedDueMs"):
            if field in a and not integer(a[field]):
                raise Refused("INVALID_RECOVERY_FIELD")
        last = a.get("lastFiredDay", "")
        if last:
            local_date(last)
        if a["ringing"] and not a["enabled"]:
            raise Refused("INVALID_RINGER_STATE")


def last_weekly_due(a, now_ms):
    today = datetime.fromtimestamp(now_ms / 1000).date()
    for previous_days in range(8):
        day = today - timedelta(days=previous_days)
        # JavaScript Date.getDay(): Sunday=0; Python Monday=0.
        js_weekday = (day.weekday() + 1) % 7
        if js_weekday not in a["weekdays"]:
            continue
        due = at_local(day, a["hour"], a["minute"])
        if due <= now_ms:
            return due, day.isoformat()
    return 0, ""


def next_weekly_due(a, now_ms):
    today = datetime.fromtimestamp(now_ms / 1000).date()
    for days_ahead in range(9):
        day = today + timedelta(days=days_ahead)
        due = at_local(day, a["hour"], a["minute"])
        if ((day.weekday() + 1) % 7) in a["weekdays"] and due > now_ms:
            return due
    return 0


def evaluate_alarm(a, now_ms):
    """A diagnostic classification, NEVER permission for an audio action."""
    result = {"alarmId": a["id"], "phase": "UNKNOWN", "dueAtMs": 0,
              "nextDueMs": 0}
    if not a["enabled"] or a["completed"]:
        result["phase"] = "COMPLETED" if a["completed"] else "DISABLED"
        return result
    if a["ringing"]:
        started = a.get("ringStartedAtMs", 0)
        result["phase"] = "ACTIVE_RING_IN_QUICKSHELL" if started and 0 <= now_ms - started < MAX_RING_MS else "STALE_RING_NEEDS_OWNER_REVIEW"
        result["dueAtMs"] = started
        return result
    snooze = a.get("snoozeUntilMs", 0)
    if snooze:
        result["dueAtMs"] = snooze
        if now_ms < snooze:
            result["phase"] = "SNOOZE_PENDING"
            result["nextDueMs"] = snooze
        elif now_ms - snooze <= MAX_LATE_MS:
            result["phase"] = "SNOOZE_ELIGIBLE_IF_OWNED"
        else:
            result["phase"] = "MISSED_SNOOZE_CANDIDATE"
        return result
    pause = a.get("pausedUntilDate", "")
    today = datetime.fromtimestamp(now_ms / 1000).date()
    if pause and today.isoformat() < pause:
        result["phase"] = "PAUSED"
        return result
    if a["mode"] == "once":
        day = local_date(a["date"])
        due, due_key = at_local(day, a["hour"], a["minute"]), day.isoformat()
        future = 0
    else:
        due, due_key = last_weekly_due(a, now_ms)
        future = next_weekly_due(a, now_ms)
    result["dueAtMs"] = due
    result["nextDueMs"] = future
    if a["mode"] == "once" and due > now_ms:
        result["phase"] = "FUTURE"
        result["nextDueMs"] = due
        return result
    if not due:
        result["phase"] = "FUTURE"
        return result
    if (due_key == a.get("lastFiredDay", "")
            or due <= a.get("lastProcessedDueMs", 0)):
        result["phase"] = "ALREADY_PROCESSED"
        return result
    armed = a.get("armedAtMs", 0)
    if not armed:
        result["phase"] = "UNKNOWN_ARM_TIME"
    elif armed > now_ms or due + MAX_LATE_MS < armed:
        result["phase"] = "BEFORE_ACTUAL_ARMING"
    elif now_ms - due <= MAX_LATE_MS:
        result["phase"] = "ELIGIBLE_IF_OWNED"
    else:
        result["phase"] = "MISSED_CANDIDATE"
    return result


def observe(path, now_ms):
    if not integer(now_ms, 1):
        raise Refused("INVALID_OBSERVATION_TIME")
    doc = snapshot_file(path)
    rows = [evaluate_alarm(a, now_ms) for a in doc["alarms"]]
    rows.sort(key=lambda row: row["alarmId"])
    return {"version": VERSION, "mode": OBSERVER_MODE,
            "actuationEnabled": False, "ownsAlarmFile": False,
            "observedAtMs": now_ms, "state": "READY",
            "alarmCount": len(rows), "alarms": rows}


def observation(path, now_ms):
    try:
        return observe(path, now_ms)
    except Refused as exc:
        return {"version": VERSION, "mode": OBSERVER_MODE,
                "actuationEnabled": False, "ownsAlarmFile": False,
                "observedAtMs": now_ms, "state": "REFUSED",
                "reason": str(exc)}


def observer_lock():
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    base = Path(runtime)
    if not base.is_absolute() or base.is_symlink() or not base.is_dir() or base.stat().st_uid != os.getuid():
        raise Refused("TRUSTED_USER_RUNTIME_REQUIRED")
    directory = base / "post-apollo-alarm-observer"
    if directory.is_symlink():
        raise Refused("UNSAFE_RUNTIME_DIR")
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or (info.st_mode & 0o077):
        raise Refused("UNSAFE_RUNTIME_DIR")
    descriptor = os.open(directory / "observer.lock",
                         os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refused("OBSERVER_ALREADY_RUNNING") from exc
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch", action="store_true")
    parser.add_argument("--alarm-file", required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--at-ms", type=int, default=None)
    args = parser.parse_args(argv)
    if args.at_ms is not None and not args.once:
        parser.error("--at-ms is only allowed with --once")
    if not args.alarm_file or not Path(args.alarm_file).is_absolute():
        parser.error("explicit absolute --alarm-file is required; no guessing")
    if not (1.0 <= args.interval <= 60.0):
        parser.error("--interval must be between 1 and 60 seconds")
    if args.once:
        now = args.at_ms if args.at_ms is not None else int(time.time() * 1000)
        report = observation(args.alarm_file, now)
        print(json.dumps(report, separators=(",", ":"), sort_keys=True))
        return 0 if report["state"] == "READY" else 2
    try:
        descriptor = observer_lock()
    except (Refused, OSError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc) if isinstance(exc, Refused) else "LOCK_ERROR",
                          "mode": OBSERVER_MODE, "actuationEnabled": False}), flush=True)
        return 3
    try:
        previous = None
        last_heartbeat = 0.0
        while True:
            now = int(time.time() * 1000)
            report = observation(args.alarm_file, now)
            # Do not spam journald or log alarm names and notes.
            signature = json.dumps({"state": report["state"],
                                    "reason": report.get("reason", ""),
                                    "alarms": report.get("alarms", [])},
                                   sort_keys=True)
            if signature != previous or time.monotonic() - last_heartbeat >= 60:
                print(json.dumps(report, separators=(",", ":"), sort_keys=True), flush=True)
                previous, last_heartbeat = signature, time.monotonic()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        os.close(descriptor)


if __name__ == "__main__":
    sys.exit(main())
