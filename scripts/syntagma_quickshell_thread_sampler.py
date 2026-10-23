#!/usr/bin/env python3
"""Read-only, out-of-process Quickshell thread sampler for UI-freeze diagnosis.

Emits JSON Lines to stdout; no ptrace, signals, performance packages, or
Quickshell modifications. Capture a separate Quickshell lag log with 'qs log'.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time


def parse_stat_line(line):
    """Parse /proc/PID[/task/TID]/stat, whose '(comm)' may contain spaces."""
    left = line.find("(")
    right = line.rfind(")")
    if left < 0 or right <= left:
        raise ValueError("missing stat command")
    fields = line[right + 1:].strip().split()
    if len(fields) < 20:
        raise ValueError("short proc stat")
    return {
        "name": line[left + 1:right],
        "state": fields[0],       # field 3
        "ticks": int(fields[11]) + int(fields[12]),  # utime + stime, 14/15
        "start": int(fields[19]), # field 22, stable process identity
    }


def find_quickshell(proc_root=Path("/proc"), uid=None):
    """Choose the newest same-user Quickshell, not an unrelated user's shell."""
    if uid is None:
        uid = os.getuid()
    found = []
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            if (entry / "comm").read_text().strip() != "quickshell":
                continue
            stamp = parse_stat_line((entry / "stat").read_text())["start"]
            found.append((stamp, int(entry.name)))
        except (OSError, ValueError, IndexError):
            continue
    return max(found)[1] if found else None


def read_threads(proc_root, pid):
    """Snapshot thread CPU ticks and state; omit threads exiting mid-scan."""
    task_dir = proc_root / str(pid) / "task"
    result = {}
    try:
        entries = list(task_dir.iterdir())
    except OSError:
        return result
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            result[int(entry.name)] = parse_stat_line((entry / "stat").read_text())
        except (OSError, ValueError, IndexError):
            continue
    return result


def build_sample(previous, current, seconds, hertz, pid, ts_ms, top_count=4):
    """Thread CPU percentage is per ONE logical core (100% = one core)."""
    active = []
    for tid, item in current.items():
        before = previous.get(tid)
        same_thread = before is not None and before["start"] == item["start"]
        delta = max(0, item["ticks"] - before["ticks"]) if same_thread else 0
        cpu = round(100.0 * delta / (hertz * seconds), 1) if seconds > 0 else 0.0
        active.append({
            "tid": tid, "name": item["name"], "state": item["state"],
            "cpuPct": cpu,
        })
    active.sort(key=lambda x: (-x["cpuPct"], x["tid"]))
    main = next((x for x in active if x["tid"] == pid), None)
    selected = active[:top_count]
    if main is not None and not any(x["tid"] == pid for x in selected):
        selected.append(main)
    return {
        "event": "threads", "tsMs": ts_ms, "pid": pid,
        "sampleIntervalMs": round(seconds * 1000),
        "totalCpuPct": round(sum(x["cpuPct"] for x in active), 1),
        "threadCount": len(active), "main": main, "top": selected,
    }


def add_wchan(sample, proc_root, pid):
    """wchan is advisory and may be unavailable or masked by procfs policy."""
    for item in sample["top"]:
        try:
            item["wchan"] = (proc_root / str(pid) / "task" /
                             str(item["tid"]) / "wchan").read_text().strip()
        except OSError:
            item["wchan"] = "unavailable"


def emit(record):
    print(json.dumps(record, separators=(",", ":"), sort_keys=True), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Quickshell PID (default: newest owned process)")
    parser.add_argument("--duration", type=float, default=180,
                        help="Seconds to sample (default 180)")
    parser.add_argument("--interval", type=float, default=0.25,
                        help="Sampling period in seconds (default .25)")
    parser.add_argument("--top", type=int, default=4,
                        help="Non-main thread entries to retain (default 4)")
    args = parser.parse_args(argv)
    if not 0.1 <= args.interval <= 5:
        parser.error("--interval must be between 0.1 and 5 seconds")
    if not 1 <= args.duration <= 1800:
        parser.error("--duration must be between 1 and 1800 seconds")
    if not 1 <= args.top <= 12:
        parser.error("--top must be between 1 and 12")

    proc_root = Path("/proc")
    pid = args.pid if args.pid is not None else find_quickshell(proc_root)
    if pid is None:
        print("No same-user Quickshell process found.", file=sys.stderr)
        return 2
    try:
        if (proc_root / str(pid)).stat().st_uid != os.getuid():
            print("Refusing to sample another user's process.", file=sys.stderr)
            return 2
        proc_start = parse_stat_line((proc_root / str(pid) / "stat").read_text())["start"]
    except (OSError, ValueError, IndexError):
        print("Quickshell PID disappeared or cannot be inspected.", file=sys.stderr)
        return 2

    hz = os.sysconf("SC_CLK_TCK")
    previous = read_threads(proc_root, pid)
    if not previous:
        print("Cannot read Quickshell thread stats.", file=sys.stderr)
        return 2
    started = time.monotonic()
    sampled_at = started
    emit({"event": "start", "tsMs": round(time.time() * 1000), "pid": pid,
          "intervalMs": round(args.interval * 1000),
          "durationSeconds": args.duration,
          "note": "CPU percentages are per one logical CPU; no Qt stack traces"})

    try:
        while time.monotonic() - started < args.duration:
            time.sleep(args.interval)
            now = time.monotonic()
            seconds = now - sampled_at
            sampled_at = now
            try:
                latest_start = parse_stat_line((proc_root / str(pid) / "stat").read_text())["start"]
            except (OSError, ValueError, IndexError):
                latest_start = None
            if latest_start != proc_start:
                emit({"event": "stopped", "reason": "quickshell-exited-or-replaced",
                      "tsMs": round(time.time() * 1000), "pid": pid})
                return 1
            current = read_threads(proc_root, pid)
            if not current:
                emit({"event": "stopped", "reason": "no-readable-threads",
                      "tsMs": round(time.time() * 1000), "pid": pid})
                return 1
            record = build_sample(previous, current, seconds, hz, pid,
                                  round(time.time() * 1000), args.top)
            add_wchan(record, proc_root, pid)
            emit(record)
            previous = current
    except KeyboardInterrupt:
        emit({"event": "stopped", "reason": "user-interrupt",
              "tsMs": round(time.time() * 1000), "pid": pid})
        return 130
    emit({"event": "complete", "tsMs": round(time.time() * 1000),
          "pid": pid})
    return 0


if __name__ == "__main__":
    sys.exit(main())
