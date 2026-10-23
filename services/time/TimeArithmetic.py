#!/usr/bin/env python3
"""TimeW CALC: manually add/subtract elapsed durations across IANA zones.

CLI: python3 -B -I TimeArithmetic.py ZONE DATE HH:MM OP DAYS HOURS MINUTES
OP: add | subtract. Days are 24h elapsed, not calendar-day operations.
Read-only, no shell, network, timers, or system clock updates.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
import re
import sys

ZONE_RE = re.compile(r"^(?:UTC|[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+)+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLOCK_RE = re.compile(r"^\d{2}:\d{2}$")
COUNT_RE = re.compile(r"^\d{1,4}$")


def error(status):
    return {"status": status, "options": []}


def arithmetic(zone, date, clock, operation, days, hours, minutes):
    inputs = (zone, date, clock, operation, days, hours, minutes)
    if not all(isinstance(value, str) for value in inputs):
        return error("INVALID_INPUT")
    if (not ZONE_RE.fullmatch(zone) or not DATE_RE.fullmatch(date)
            or not CLOCK_RE.fullmatch(clock)
            or operation not in ("add", "subtract")
            or not all(COUNT_RE.fullmatch(value) for value in (days, hours, minutes))):
        return error("INVALID_INPUT")
    d, h, m = int(days), int(hours), int(minutes)
    if d > 3650 or h > 999 or m > 59:
        return error("DURATION_OUT_OF_RANGE")
    try:
        naive = datetime.strptime(date + " " + clock, "%Y-%m-%d %H:%M")
        if not 1900 <= naive.year <= 2100:
            return error("UNSUPPORTED_YEAR")
        location = ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError):
        return error("ZONE_OR_DATE_UNAVAILABLE")

    duration = timedelta(days=d, hours=h, minutes=m)
    if operation == "subtract":
        duration = -duration
    options = []
    seen = set()
    for fold in (0, 1):
        local = naive.replace(tzinfo=location, fold=fold)
        utc = local.astimezone(timezone.utc)
        original = utc.astimezone(location)
        # Reject a skipped local time, including a DST spring-forward gap.
        if original.replace(tzinfo=None) != naive:
            continue
        stamp = utc.isoformat()
        if stamp in seen:
            continue
        seen.add(stamp)
        try:
            shifted = (utc + duration).astimezone(location)
        except (OverflowError, ValueError):
            return error("RESULT_OUT_OF_RANGE")
        if not 1900 <= shifted.year <= 2100:
            return error("RESULT_OUT_OF_RANGE")
        options.append({
            "utc": stamp,
            "source": original.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
            "result": shifted.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
        })
    options.sort(key=lambda entry: entry["utc"])
    if not options:
        return error("NONEXISTENT_LOCAL_TIME")
    return {
        "status": "AMBIGUOUS_LOCAL_TIME" if len(options) > 1 else "READY",
        "zone": zone,
        "operation": operation,
        "elapsed_minutes": int(duration.total_seconds() // 60),
        "options": options,
    }


def main():
    result = arithmetic(*sys.argv[1:]) if len(sys.argv) == 8 else error("INVALID_ARGUMENTS")
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))


if __name__ == "__main__":
    main()
