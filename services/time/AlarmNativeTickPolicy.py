#!/usr/bin/env python3
"""Pure native Clock V2 tick parity with AlarmManagerPolicy.js.

No file access, timers, signaling, audio, network or notification. This
implements the SAME state transition used by the mounted QML scheduler;
it must pass cross-runtime Node/Python differential tests before use.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
import re

MAX_TIME = 8640000000000000
MAX_SAFE = 9007199254740991
MAX_LATE_MS = 2 * 60 * 1000
MAX_RING_MS = 15 * 60 * 1000
EVENTS = frozenset(("none", "fired", "missed", "stopped", "snoozed", "expired"))
SOUND = frozenset(("chime", "soft", "urgent"))
CUSTOM_SOUND = re.compile(r"^user-[0-9a-f]{64}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
DEFAULTS = {
    "favorite": False, "note": "", "lastEventKind": "none",
    "lastEventAtMs": 0, "lastExpectedAtMs": 0, "lastFiredAtMs": 0,
    "lastMissedAtMs": 0, "armedAtMs": 0, "lastProcessedDueMs": 0,
}


def integer(value, lo=0, hi=MAX_TIME):
    return type(value) is int and lo <= value <= hi


def _local_date(raw, empty=False):
    if empty and raw == "":
        return True
    if type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return False
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return False
    return d.year >= 1970 and d.isoformat() == raw


def _text(raw, length):
    return type(raw) is str and len(raw) <= length and not CONTROL.search(raw)


def valid_alarm(a):
    if type(a) is not dict:
        return False
    if not (integer(a.get("id"), 1, MAX_SAFE-1)
            and _text(a.get("name"), 40) and a["name"]
            and ("favorite" not in a or type(a["favorite"]) is bool)
            and ("note" not in a or _text(a["note"], 256))
            and a.get("lastEventKind", "none") in EVENTS
            and all(integer(a.get(k,0)) for k in (
                "lastEventAtMs", "lastExpectedAtMs", "lastFiredAtMs",
                "lastMissedAtMs", "armedAtMs", "lastProcessedDueMs"))):
        return False
    if (not integer(a.get("hour"), 0, 23)
            or not integer(a.get("minute"), 0, 59)
            or a.get("mode") not in ("once", "weekly")):
        return False
    weekdays = a.get("weekdays")
    if (type(weekdays) is not list or len(weekdays) > 7
            or any(not integer(x,0,6) for x in weekdays)
            or len(set(weekdays)) != len(weekdays)
            or (a["mode"] == "weekly" and not weekdays)):
        return False
    if (not _local_date(a.get("date"), empty=a["mode"] == "weekly")
            or not _local_date(a.get("pausedUntilDate"), empty=True)
            or not _local_date(a.get("lastFiredDay"), empty=True)):
        return False
    sound = a.get("soundId")
    if type(sound) is not str or not (
            sound in SOUND or CUSTOM_SOUND.fullmatch(sound)):
        return False
    for flag in ("keepSaved", "enabled", "ringing", "completed",
                 "soundEnabled"):
        if type(a.get(flag)) is not bool:
            return False
    if not integer(a.get("volumePercent"),0,100):
        return False
    for tm in ("ringStartedAtMs", "snoozeUntilMs"):
        if not integer(a.get(tm)):
            return False
    if a["ringing"] and (not a["enabled"] or a["ringStartedAtMs"] <= 0):
        return False
    if a["completed"] and (a["mode"] != "once" or a["enabled"]):
        return False
    return True


def valid_document(doc):
    if (type(doc) is not dict or doc.get("version") != 2
            or not integer(doc.get("nextId"),1,MAX_SAFE-1)
            or type(doc.get("alarms")) is not list
            or len(doc["alarms"]) > 100):
        return False
    seen = set()
    for row in doc["alarms"]:
        if (not valid_alarm(row) or row["id"] in seen
                or row["id"] >= doc["nextId"]):
            return False
        seen.add(row["id"])
    return True


def _day(ms):
    return datetime.fromtimestamp(ms / 1000).date()


def _key(ms):
    return _day(ms).isoformat()


def _at(day, hour, minute):
    return int(datetime(day.year, day.month, day.day,
                        hour, minute).timestamp()*1000)


def _finish_once(a):
    a["ringing"] = False
    a["ringStartedAtMs"] = 0
    a["snoozeUntilMs"] = 0
    a["completed"] = True
    a["enabled"] = False


def _previous_weekly(a, now_ms, pause):
    if (a["mode"] != "weekly" or not a["enabled"]
            or a["completed"] or a["armedAtMs"] == 0
            or a["armedAtMs"] > now_ms):
        return 0
    today = _day(now_ms)
    for back in range(1,8):
        local = today - timedelta(days=back)
        due = _at(local,a["hour"],a["minute"])
        weekday = (datetime.fromtimestamp(due/1000).weekday()+1)%7
        key = local.isoformat()
        if (weekday not in a["weekdays"]
                or (pause and key < pause)
                or due <= a["lastProcessedDueMs"]
                or key == a["lastFiredDay"]
                or due + MAX_LATE_MS < a["armedAtMs"]):
            continue
        return due
    return 0


def tick(doc, now_ms):
    """Same output shape and semantics as QML AlarmManagerPolicy.tick()."""
    unchanged = {"changed": False, "document": doc,
                 "started": [], "expired": [], "missed": []}
    if not valid_document(doc) or not integer(now_ms,1):
        return unchanged
    next_doc = deepcopy(doc)
    for a in next_doc["alarms"]:
        for key,value in DEFAULTS.items():
            a.setdefault(key,value)
    started,expired,missed,removed = [],[],[],[]
    changed = False
    today = _key(now_ms)
    for a in next_doc["alarms"]:
        if not a["enabled"]:
            continue
        if a["mode"] == "weekly" and a["armedAtMs"] == 0:
            a["armedAtMs"] = now_ms
            changed = True
        if a["armedAtMs"] > now_ms and not a["ringing"]:
            continue
        if a["ringing"]:
            if (now_ms >= a["ringStartedAtMs"] and
                    now_ms - a["ringStartedAtMs"] < MAX_RING_MS):
                continue
            if a["mode"] == "once":
                _finish_once(a)
                if not a["keepSaved"]:
                    removed.append(a["id"])
            else:
                a["ringing"] = False
                a["ringStartedAtMs"] = 0
            a["lastEventKind"] = "expired"
            a["lastEventAtMs"] = now_ms
            expired.append(a["id"])
            changed = True
            continue
        if a["snoozeUntilMs"] > 0:
            if now_ms < a["snoozeUntilMs"]:
                continue
            late = now_ms - a["snoozeUntilMs"]
            due = a["snoozeUntilMs"]
            a["snoozeUntilMs"] = 0
            changed = True
            if late > MAX_LATE_MS:
                if a["mode"] == "once":
                    _finish_once(a)
                a["lastEventKind"] = "missed"
                a["lastEventAtMs"] = now_ms
                a["lastMissedAtMs"] = now_ms
                a["lastProcessedDueMs"] = max(a["lastProcessedDueMs"],due)
                missed.append(a["id"])
                continue
            a["ringing"] = True
            a["ringStartedAtMs"] = now_ms
            a["lastEventKind"] = "fired"
            a["lastEventAtMs"] = now_ms
            a["lastFiredAtMs"] = now_ms
            a["lastExpectedAtMs"] = due
            a["lastProcessedDueMs"] = max(a["lastProcessedDueMs"],due)
            started.append(a["id"])
            continue
        pause = a["pausedUntilDate"]
        if pause and today < pause:
            continue
        if pause:
            a["pausedUntilDate"] = ""
            changed = True
        if a["mode"] == "once" and a["date"] < today:
            _finish_once(a)
            due = _at(date.fromisoformat(a["date"]),a["hour"],a["minute"])
            a["lastEventKind"] = "missed"
            a["lastEventAtMs"] = now_ms
            a["lastMissedAtMs"] = now_ms
            a["lastExpectedAtMs"] = due
            a["lastProcessedDueMs"] = due
            missed.append(a["id"])
            changed = True
            continue
        due_key = (
            a["date"] == today if a["mode"] == "once"
            else (datetime.fromtimestamp(now_ms/1000).weekday()+1)%7
                in a["weekdays"]
        )
        if (not due_key or a["lastFiredDay"] == today
                or now_ms < _at(_day(now_ms),a["hour"],a["minute"])):
            previous = _previous_weekly(a,now_ms,pause)
            if previous > 0:
                a["lastProcessedDueMs"] = previous
                a["lastExpectedAtMs"] = previous
                a["lastEventAtMs"] = now_ms
                if now_ms - previous <= MAX_LATE_MS:
                    a["lastFiredDay"] = _key(previous)
                    a["ringing"] = True
                    a["ringStartedAtMs"] = now_ms
                    a["lastEventKind"] = "fired"
                    a["lastFiredAtMs"] = now_ms
                    started.append(a["id"])
                else:
                    a["lastEventKind"] = "missed"
                    a["lastMissedAtMs"] = now_ms
                    missed.append(a["id"])
                changed = True
            continue
        expected = _at(_day(now_ms),a["hour"],a["minute"])
        late = now_ms - expected
        if late > MAX_LATE_MS:
            if a["mode"] == "once":
                _finish_once(a)
            a["lastFiredDay"] = today
            a["lastEventKind"] = "missed"
            a["lastEventAtMs"] = now_ms
            a["lastMissedAtMs"] = now_ms
            a["lastExpectedAtMs"] = expected
            a["lastProcessedDueMs"] = expected
            missed.append(a["id"])
            changed = True
            continue
        a["lastFiredDay"] = today
        a["ringing"] = True
        a["ringStartedAtMs"] = now_ms
        a["lastEventKind"] = "fired"
        a["lastEventAtMs"] = now_ms
        a["lastFiredAtMs"] = now_ms
        a["lastExpectedAtMs"] = expected
        a["lastProcessedDueMs"] = expected
        started.append(a["id"])
        changed = True
    if removed:
        next_doc["alarms"] = [a for a in next_doc["alarms"]
                               if a["id"] not in removed]
    return {"changed": changed, "document": next_doc if changed else doc,
            "started": started, "expired": expired, "missed": missed}
