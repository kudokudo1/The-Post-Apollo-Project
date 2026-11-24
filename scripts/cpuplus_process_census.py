#!/usr/bin/env python3
"""Bounded same-user process census. Read-only Linux procfs, JSONL stdout.

RSS is not PSS and cannot be summed into unique physical RAM. Kernel storage
I/O counters are not database transaction counts. Short-lived processes may
escape both snapshots. Names are comm labels, not trusted application identity.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

SCHEMA = "post-apollo-process-census-v1"
MAX_PIDS = 8192
TOP = 6
FOCUS_LIMIT = 8
FOCUS = {"quickshell", "sway", "swaypx", "kitty", "devexp", "post-apollo-sway"}


def parse_stat(text, page_size):
    left, right = text.find("("), text.rfind(")")
    if left < 1 or right <= left:
        raise ValueError("bad stat")
    pid = int(text[:left].strip())
    fields = text[right + 1:].split()
    if len(fields) < 22:
        raise ValueError("short stat")
    item = {"pid": pid, "name": text[left + 1:right][:64],
            "ticks": int(fields[11]) + int(fields[12]),
            "threads": int(fields[17]), "startTicks": int(fields[19]),
            "rssKiB": int(fields[21]) * page_size // 1024}
    if pid <= 0 or any(item[k] < 0 for k in ("ticks", "threads", "startTicks", "rssKiB")):
        raise ValueError("invalid stat")
    return item


def parse_io(text):
    values = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key in ("read_bytes", "write_bytes"):
            if key in values or not value.strip().isascii() or not value.strip().isdecimal():
                raise ValueError("invalid io")
            values[key] = int(value.strip())
    if len(values) != 2:
        raise ValueError("incomplete io")
    return values


def read_process(path, uid, page_size):
    if path.stat().st_uid != uid:
        return None
    before = parse_stat((path / "stat").read_text(errors="replace"), page_size)
    try:
        io = parse_io((path / "io").read_text())
    except (OSError, ValueError):
        io = None
    after = parse_stat((path / "stat").read_text(errors="replace"), page_size)
    if (after["pid"] != int(path.name) or before["pid"] != after["pid"]
            or before["startTicks"] != after["startTicks"]
            or before["ticks"] > after["ticks"] or path.stat().st_uid != uid):
        return None
    after["io"] = io
    after["observedNs"] = time.monotonic_ns()
    return after


def snapshot(root, uid, page_size, own_pid):
    rows = {}
    skipped = 0
    examined = 0
    truncated = False
    # Stop enumeration at the cap; do not imply the truncated set is exhaustive.
    with os.scandir(root) as entries:
        for entry in entries:
            if not entry.name.isascii() or not entry.name.isdecimal():
                continue
            if examined >= MAX_PIDS:
                truncated = True
                break
            examined += 1
            if int(entry.name) == own_pid:
                continue
            try:
                row = read_process(Path(entry.path), uid, page_size)
            except (OSError, ValueError, IndexError):
                skipped += 1
                continue
            if row is not None:
                rows[row["pid"]] = row
    return rows, {"examinedPidEntries": examined, "unreadableOrExited": skipped,
                  "truncated": truncated}


def delta_rate(old, new, seconds):
    if old is None or new is None or new < old or seconds <= 0:
        return None
    return round((new - old) / seconds, 1)


def compare(previous, current, hz):
    rows = []
    for pid, after in current.items():
        before = previous.get(pid)
        same = before is not None and before["startTicks"] == after["startTicks"]
        row = {key: after[key] for key in
               ("pid", "name", "startTicks", "rssKiB", "threads")}
        row.update(cpuPct=None, readBps=None, writeBps=None)
        if same:
            elapsed = (after["observedNs"] - before["observedNs"]) / 1e9
            rate = delta_rate(before["ticks"], after["ticks"], elapsed)
            if rate is not None:
                row["cpuPct"] = round(100 * rate / hz, 1)
            if before["io"] is not None and after["io"] is not None:
                row["readBps"] = delta_rate(before["io"]["read_bytes"],
                                            after["io"]["read_bytes"], elapsed)
                row["writeBps"] = delta_rate(before["io"]["write_bytes"],
                                             after["io"]["write_bytes"], elapsed)
        rows.append(row)
    return rows


def select_rows(rows):
    # Deduplicated top CPU, RSS, read and write rankings plus a bounded
    # named-process subset. Missing counters are not treated as measured zero.
    selected = {}
    for key in ("cpuPct", "rssKiB", "readBps", "writeBps"):
        ranked = sorted((row for row in rows if row[key] is not None),
                        key=lambda row: (-row[key], row["pid"]))[:TOP]
        for row in ranked:
            selected[row["pid"]] = row
    focus = sorted((row for row in rows if row["name"].lower() in FOCUS),
                   key=lambda row: (-row["rssKiB"], row["pid"]))
    for row in focus[:FOCUS_LIMIT]:
        selected[row["pid"]] = row
    return sorted(selected.values(), key=lambda row: row["pid"]), len(focus)


def emit(data):
    print(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
          flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args(argv)
    # At most six intervals; fixed production button uses three.
    if not (1 <= args.duration <= 60 and 1 <= args.interval <= args.duration
            and (args.duration + args.interval - 1) // args.interval <= 6):
        parser.error("duration 1..60 seconds, at most six intervals")
    root = Path("/proc")
    uid, page, hz = os.getuid(), os.sysconf("SC_PAGE_SIZE"), os.sysconf("SC_CLK_TCK")
    count = 0
    try:
        previous, previous_coverage = snapshot(root, uid, page, os.getpid())
        if not previous:
            raise ValueError("no observable processes")
        deadline = time.monotonic() + args.duration
        while count < 6:
            remaining = deadline - time.monotonic()
            if remaining <= 0 and count:
                break
            time.sleep(max(0, min(args.interval, remaining)))
            current, coverage = snapshot(root, uid, page, os.getpid())
            if not current:
                raise ValueError("no observable processes")
            rows = compare(previous, current, hz)
            selected, focus_count = select_rows(rows)
            count += 1
            emit({"schema": SCHEMA, "event": "census", "sequence": count,
                  "tsMs": round(time.time() * 1000), "scope": "same-user",
                  "observed": len(rows), "cpuMeasured": sum(r["cpuPct"] is not None for r in rows),
                  "ioMeasured": sum(r["readBps"] is not None and r["writeBps"] is not None for r in rows),
                  "coverage": coverage, "previousCoverage": previous_coverage,
                  "focusMatches": focus_count, "rows": selected})
            previous, previous_coverage = current, coverage
            if time.monotonic() >= deadline:
                break
    except (OSError, ValueError, IndexError):
        emit({"schema": SCHEMA, "event": "stopped", "samples": count,
              "reason": "observation-unavailable"})
        return 1
    except KeyboardInterrupt:
        emit({"schema": SCHEMA, "event": "stopped", "samples": count,
              "reason": "user-interrupt"})
        return 130
    emit({"schema": SCHEMA, "event": "complete", "samples": count})
    return 0


if __name__ == "__main__":
    sys.exit(main())
