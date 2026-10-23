#!/usr/bin/env python3
"""TimeW: elapsed duration between two explicitly zoned civil date-times.

CLI: python3 -B -I TimeDifference.py START_ZONE START_DATE START_HH:MM
                                    END_ZONE END_DATE END_HH:MM
Each instant is resolved with system IANA zoneinfo. Skipped clock times are
rejected and repeated DST hours yield explicit alternative pairings.
No filesystem writes, network calls, system clock changes or subprocesses.
"""
from datetime import datetime, timezone
import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ZONE_RE = re.compile(r"^(?:UTC|[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+)+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def error(status):
    return {"status": status, "options": []}


def resolve(zone, date, clock):
    if (not isinstance(zone, str) or not isinstance(date, str)
            or not isinstance(clock, str)
            or not ZONE_RE.fullmatch(zone) or not DATE_RE.fullmatch(date)
            or not TIME_RE.fullmatch(clock)):
        return "INVALID_INPUT", []
    try:
        naive = datetime.strptime(date + " " + clock, "%Y-%m-%d %H:%M")
        if not 1900 <= naive.year <= 2100:
            return "UNSUPPORTED_YEAR", []
        location = ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError):
        return "ZONE_OR_DATE_UNAVAILABLE", []

    instants = {}
    for fold in (0, 1):
        local = naive.replace(tzinfo=location, fold=fold)
        utc = local.astimezone(timezone.utc)
        roundtrip = utc.astimezone(location)
        if roundtrip.replace(tzinfo=None) != naive:
            continue
        instants[utc.isoformat()] = (utc, roundtrip)
    if not instants:
        return "NONEXISTENT_LOCAL_TIME", []
    return "READY", [instants[key] for key in sorted(instants)]


def difference(start_zone, start_date, start_time,
               end_zone, end_date, end_time):
    start_status, starts = resolve(start_zone, start_date, start_time)
    if start_status != "READY":
        return error("START_" + start_status)
    end_status, ends = resolve(end_zone, end_date, end_time)
    if end_status != "READY":
        return error("END_" + end_status)

    choices = []
    # At most two folds per endpoint -> four concrete elapsed durations.
    for start_utc, start_local in starts:
        for end_utc, end_local in ends:
            total_seconds = int((end_utc - start_utc).total_seconds())
            # Civil inputs have minute resolution. Seconds remain zero.
            total_minutes = total_seconds // 60
            absolute = abs(total_minutes)
            choices.append({
                "start": start_local.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
                "end": end_local.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
                "start_utc": start_utc.isoformat(),
                "end_utc": end_utc.isoformat(),
                "total_minutes": total_minutes,
                "sign": "-" if total_minutes < 0 else "+",
                "days": absolute // 1440,
                "hours": absolute % 1440 // 60,
                "minutes": absolute % 60,
            })
    return {
        "status": "AMBIGUOUS_LOCAL_TIME" if len(choices) > 1 else "READY",
        "start_zone": start_zone,
        "end_zone": end_zone,
        "ambiguous_start": len(starts) > 1,
        "ambiguous_end": len(ends) > 1,
        "options": choices,
    }


def main():
    result = difference(*sys.argv[1:]) if len(sys.argv) == 7 else error("INVALID_ARGUMENTS")
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))


if __name__ == "__main__":
    main()
