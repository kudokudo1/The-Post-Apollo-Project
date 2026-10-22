#!/usr/bin/env python3
"""TimeW: read-only civil-time conversion using the host's IANA tzdata.

CLI: python3 -B -I TimeZoneConverter.py FROM_ZONE TO_ZONE YYYY-MM-DD HH:MM
No shell, network, clock mutation, persistence, or process spawning.
Emits one JSON object. Missing hours are rejected; repeated hours return two
explicit possibilities rather than silently assuming a DST fold.
"""
from datetime import datetime, timezone
import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ZONE_RE = re.compile(r"^(?:UTC|[A-Za-z][A-Za-z0-9._+-]*(?:/[A-Za-z0-9._+-]+)+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def unavailable(status):
    return {"status": status, "options": []}


def convert(source, destination, date, clock):
    if not all(isinstance(v, str) for v in (source, destination, date, clock)):
        return unavailable("INVALID_INPUT")
    if (not ZONE_RE.fullmatch(source) or not ZONE_RE.fullmatch(destination)
            or not DATE_RE.fullmatch(date) or not TIME_RE.fullmatch(clock)):
        return unavailable("INVALID_INPUT")
    try:
        naive = datetime.strptime(date + " " + clock, "%Y-%m-%d %H:%M")
        if not 1900 <= naive.year <= 2100:
            return unavailable("UNSUPPORTED_YEAR")
        from_zone = ZoneInfo(source)
        to_zone = ZoneInfo(destination)
    except (ValueError, ZoneInfoNotFoundError):
        return unavailable("ZONE_OR_DATE_UNAVAILABLE")

    options = []
    seen = set()
    for fold in (0, 1):
        local = naive.replace(tzinfo=from_zone, fold=fold)
        instant = local.astimezone(timezone.utc)
        # A local hour during spring-forward may be syntactically valid but
        # have no corresponding instant. Roundtrip both ways before accepting.
        back = instant.astimezone(from_zone)
        if back.replace(tzinfo=None) != naive:
            continue
        stamp = instant.isoformat()
        if stamp in seen:
            continue
        seen.add(stamp)
        target = instant.astimezone(to_zone)
        options.append({
            "utc": stamp,
            "source": back.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
            "destination": target.strftime("%Y-%m-%d %H:%M:%S %Z (%z)"),
            "source_offset": back.strftime("%z"),
            "destination_offset": target.strftime("%z"),
        })
    options.sort(key=lambda item: item["utc"])
    if not options:
        return unavailable("NONEXISTENT_LOCAL_TIME")
    return {
        "status": "AMBIGUOUS_LOCAL_TIME" if len(options) > 1 else "READY",
        "source_zone": source,
        "destination_zone": destination,
        "options": options,
    }


def main():
    if len(sys.argv) != 5:
        print(json.dumps(unavailable("INVALID_ARGUMENTS")))
        return
    result = convert(*sys.argv[1:])
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))


if __name__ == "__main__":
    main()
