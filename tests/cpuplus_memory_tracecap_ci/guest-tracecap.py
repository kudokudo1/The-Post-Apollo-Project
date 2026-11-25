#!/usr/bin/python3 -I
"""Read-only trace capability discovery in an isolated guest. No tracing setup."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys

PIN = "6bac8be7b1de6883f480a95944d6ba1130852270"
ROOT = Path("/sys/kernel/tracing")
MARKER = Path("/etc/postapollo-memory-native-tracecap-ci-only")
GUARD = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader = importlib.machinery.SourceFileLoader("tracecap_guard", str(GUARD))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    guard = importlib.util.module_from_spec(spec)
    loader.exec_module(guard)
    require(guard.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_TRACECAP_V1", "trace capability marker absent")
    guard.PIN = PIN
    guard.guard()
    require(platform.machine() == "x86_64", "unsupported architecture")
    return guard

def bounded(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "bounded read exceeded")
    return raw.decode("ascii", errors="strict")

def event_fields(root, relative, required):
    try:
        raw = bounded(root / "events" / relative / "format", 65536)
        names = set(re.findall(r"^\s*field:[^;]*\b([A-Za-z_][A-Za-z_0-9]*)\s*(?:\[[^\]]*\])?;", raw, re.M))
        return {"readable": True, "required": sorted(required),
                "present": sorted(required & names), "complete": required <= names}
    except (OSError, ValueError, RuntimeError):
        return {"readable": False, "required": sorted(required),
                "present": [], "complete": False}

def inspect(guard):
    before = {p: (kind, size, priority) for p, (kind, size, used, priority) in guard.rows().items()}
    boot = guard.boot_id()
    blockers = []
    result = {"kernel": platform.release(), "architecture": platform.machine(),
              "tracefs": False, "clock": [], "function_exact": False,
              "kprobe_event_control_exists": False, "instances_exists": False,
              "events": {}, "collector_qualified": False}
    try:
        result["tracefs"] = guard.command("/usr/bin/findmnt", "-n", "-o", "FSTYPE",
                                          "-T", str(ROOT)).strip() == "tracefs"
    except (OSError, RuntimeError, ValueError):
        pass
    except Exception as exc:
        # CalledProcessError indicates missing mount; do not mount or change it.
        import subprocess
        if not isinstance(exc, subprocess.CalledProcessError):
            raise
    if not result["tracefs"]:
        blockers.append("TRACEFS_NOT_MOUNTED")
    else:
        try:
            clocks = bounded(ROOT / "trace_clock", 4096)
            result["clock"] = sorted(set(clocks.replace("[", "").replace("]", "").split()) &
                                     {"global", "mono", "mono_raw", "boot"})
        except (OSError, ValueError, RuntimeError):
            pass
        if not result["clock"]:
            blockers.append("COMMON_CLOCK_UNVERIFIED")
        try:
            functions = bounded(ROOT / "available_filter_functions", 16 * 1024 * 1024)
            result["function_exact"] = any(line.split()[:1] == ["try_to_unuse"]
                                           for line in functions.splitlines())
        except (OSError, ValueError, RuntimeError):
            pass
        if not result["function_exact"]:
            blockers.append("EXACT_UNUSE_FUNCTION_UNAVAILABLE")
        result["kprobe_event_control_exists"] = (ROOT / "kprobe_events").is_file()
        result["instances_exists"] = (ROOT / "instances").is_dir()
        if not result["kprobe_event_control_exists"]:
            blockers.append("KPROBE_CONTROL_MISSING")
        if not result["instances_exists"]:
            blockers.append("TRACE_INSTANCE_CONTROL_MISSING")
        for name, fields in (("syscalls/sys_enter_swapoff", {"common_pid", "__syscall_nr"}),
                             ("syscalls/sys_exit_swapoff", {"common_pid", "__syscall_nr", "ret"}),
                             ("signal/signal_generate", {"common_pid", "sig", "pid", "result"})):
            result["events"][name] = event_fields(ROOT, name, fields)
            if not result["events"][name]["complete"]:
                blockers.append("EVENT_SCHEMA_UNAVAILABLE:" + name)
    require(guard.boot_id() == boot and
            {p: (kind, size, priority) for p, (kind, size, used, priority) in guard.rows().items()} == before,
            "boot or swap configuration changed during read-only probe")
    require(not os.path.lexists(guard.EXT) and not os.path.lexists(guard.BASE.parent),
            "managed swap paths unexpectedly exist")
    result["blockers"] = blockers
    result["state"] = "BLOCKED" if blockers else "DISCOVERY_ONLY"
    # Do not infer dynamic probe registration, signal delivery, trace loss,
    # real kernel-function interruption or recovery from file existence.
    print("CPU_MEM_TRACECAP_STAGE // " + json.dumps(result, sort_keys=True), flush=True)
    print("CPU_MEM_TRACECAP_PASS // READ_ONLY_CAPABILITY_DISCOVERY_COMPLETE", flush=True)
    print("CPU_MEM_TRACECAP_STAGE // NO_MANAGED_SWAP_MUTATION_NO_TRACE_SETUP", flush=True)

def main():
    guard = guarded()
    require(len(sys.argv) == 2, "phase required")
    if sys.argv[1] == "guard":
        print("CPU_MEM_TRACECAP_STAGE // EXACT_CANDIDATE " + PIN, flush=True)
    elif sys.argv[1] == "run":
        inspect(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print("CPU_MEM_TRACECAP_FAIL // " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(2)
