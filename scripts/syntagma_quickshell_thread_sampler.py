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


def launching_quickshell(proc_root=Path("/proc"), parent=None, uid=None):
    """Resolve only the direct launcher or the fixed timeout wrapper's parent."""
    parent = os.getppid() if parent is None else parent
    uid = os.getuid() if uid is None else uid
    try:
        for depth in range(2):
            entry = proc_root / str(parent)
            if parent <= 1 or entry.stat().st_uid != uid:
                return None
            raw = (entry / "stat").read_text()
            identity = parse_stat_line(raw)
            if identity["name"] == "quickshell":
                return parent
            if depth != 0 or identity["name"] != "timeout":
                return None
            parent = int(raw[raw.rfind(")") + 1:].strip().split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


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


class WorkshopOutputLimit(Exception):
    pass


class WorkshopOutput:
    """ASCII JSONL; enforce the byte cap before writing each complete record."""
    def __init__(self, write=None):
        self.write = write if write is not None else lambda line: print(line, flush=True)
        self.size = 0

    def emit(self, record):
        line = json.dumps(record, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
        size = len(line) + 1
        if self.size + size > 65536:
            raise WorkshopOutputLimit()
        self.write(line)
        self.size += size


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Quickshell PID (default: newest owned process)")
    parser.add_argument("--parent-quickshell", action="store_true", help="Require the launching Quickshell process")
    parser.add_argument("--duration", type=float, default=180,
                        help="Seconds to sample (default 180)")
    parser.add_argument("--interval", type=float, default=0.25,
                        help="Sampling period in seconds (default .25)")
    parser.add_argument("--top", type=int, default=4,
                        help="Ranked entries plus main if outside rank (default 4)")
    parser.add_argument("--workshop", action="store_true", help="Bounded calibrated JSONL receipt")
    parser.add_argument("--workshop-identity", nargs=2, type=int, metavar=("PID","START_TICKS"))
    args = parser.parse_args(argv)
    if args.workshop_identity and (not args.workshop or min(args.workshop_identity)<=0 or args.pid is not None or args.parent_quickshell):
        parser.error("invalid workshop identity")
    if not 0.1 <= args.interval <= 5:
        parser.error("--interval must be between 0.1 and 5 seconds")
    if not 1 <= args.duration <= 1800:
        parser.error("--duration must be between 1 and 1800 seconds")
    if not 1 <= args.top <= 12:
        parser.error("--top must be between 1 and 12")

    if args.workshop:
        interval_ms = round(args.interval * 1000)
        if (int(args.duration) != args.duration or not 1 <= args.duration <= 120
                or interval_ms not in (100, 250, 500, 1000, 2000, 5000)
                or args.interval != interval_ms / 1000
                or interval_ms > args.duration * 1000
                or args.pid is not None or args.parent_quickshell):
            parser.error("invalid workshop calibration")
        limit = (int(args.duration * 1000) + interval_ms - 1) // interval_ms
        if limit > 30 or limit * (args.top + 1) > 150:
            parser.error("workshop report budget")
    proc_root = Path("/proc")
    if args.parent_quickshell and args.pid is not None:
        parser.error("Choose one PID source")
    pid = (launching_quickshell(proc_root) if args.parent_quickshell else
           args.pid if args.pid is not None else
           args.workshop_identity[0] if args.workshop_identity else find_quickshell(proc_root))
    if pid is None:
        print("No same-user Quickshell process found.", file=sys.stderr)
        return 2
    try:
        if (proc_root / str(pid)).stat().st_uid != os.getuid():
            print("Refusing to sample another user's process.", file=sys.stderr)
            return 2
        identity = parse_stat_line((proc_root / str(pid) / "stat").read_text())
        if args.workshop and identity["name"] != "quickshell":
            raise ValueError("not Quickshell")
        proc_start = identity["start"]
        if args.workshop_identity and proc_start != args.workshop_identity[1]:
            raise ValueError("pinned Quickshell replaced")
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
    send = WorkshopOutput().emit if args.workshop else emit
    tag = {"workshopSchema": "post-apollo-thread-calibration-v1", "startTicks": proc_start} if args.workshop else {}
    start_record = {"event": "start", "tsMs": round(time.time() * 1000), "pid": pid,
                    "intervalMs": round(args.interval * 1000),
                    "durationSeconds": args.duration,
                    "note": "CPU percentages are per one logical CPU; no Qt stack traces"}
    if args.workshop:
        start_record.update(tag, topCount=args.top, monotonicMs=round(started*1000))
    send(start_record)
    samples = 0

    try:
        while (sampled_at if args.workshop else time.monotonic()) - started < args.duration:
            time.sleep(min(args.interval, max(0, args.duration - (time.monotonic() - started))) if args.workshop else args.interval)
            now = time.monotonic()
            seconds = now - sampled_at
            sampled_at = now
            try:
                latest_start = parse_stat_line((proc_root / str(pid) / "stat").read_text())["start"]
            except (OSError, ValueError, IndexError):
                latest_start = None
            if latest_start != proc_start:
                send({"event": "stopped", "reason": "quickshell-exited-or-replaced",
                      "tsMs": round(time.time() * 1000), "pid": pid})
                return 1
            current = read_threads(proc_root, pid)
            if not current:
                send({"event": "stopped", "reason": "no-readable-threads",
                      "tsMs": round(time.time() * 1000), "pid": pid})
                return 1
            record = build_sample(previous, current, seconds, hz, pid,
                                  round(time.time() * 1000), args.top)
            add_wchan(record, proc_root, pid)
            if args.workshop:
                # Recheck identity after reading thread counters and wait channels.
                path = proc_root / str(pid)
                latest = parse_stat_line((path / "stat").read_text())
                if (path.stat().st_uid != os.getuid() or latest["name"] != "quickshell"
                        or latest["start"] != proc_start or pid not in current
                        or samples >= limit):
                    return 1
                record["startTicks"] = proc_start
                record["monotonicMs"] = round(sampled_at*1000)
            send(record)
            samples += 1
            previous = current
    except (WorkshopOutputLimit, OSError, ValueError, IndexError):
        return 1
    except KeyboardInterrupt:
        try:
            send({"event": "stopped", "reason": "user-interrupt",
                  "tsMs": round(time.time() * 1000), "pid": pid})
        except WorkshopOutputLimit:
            pass
        return 130
    complete = {"event": "complete", "tsMs": round(time.time() * 1000), "pid": pid}
    if args.workshop:
        complete.update(tag, samples=samples, observedMs=round((sampled_at - started)*1000),
                        monotonicMs=round(sampled_at*1000))
    try:
        send(complete)
    except WorkshopOutputLimit:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
