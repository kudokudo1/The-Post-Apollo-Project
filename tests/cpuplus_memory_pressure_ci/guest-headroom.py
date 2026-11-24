#!/usr/bin/python3 -I
"""Disposable guest-only real headroom refusal fixture. Never run on a workstation."""
import importlib.machinery
import importlib.util
import json
import mmap
import os
from pathlib import Path
import stat
import time

GIB_KIB = 1024 ** 2
STEP = 64 * 1024 ** 2
MAX_ALLOC = 2 * 1024 ** 3
# For the existing 6 GiB guest: keep a generous independent floor.
FLOOR_KIB = 3 * GIB_KIB
MARGIN_KIB = 256 * 1024
DEADLINE_SECONDS = 35
RECOVERY = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
PRESSURE_MARKER = Path("/etc/postapollo-memory-native-headroom-ci-only")

def require(value, message):
    if not value:
        raise RuntimeError(message)

def load_recovery():
    # Refuse before importing any fixture module outside its dedicated guest.
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader = importlib.machinery.SourceFileLoader("cpu_memory_fault_guard", str(RECOVERY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.guard()
    require(module.protected_bytes(PRESSURE_MARKER).strip() == b"DISPOSABLE_CPU_MEMORY_HEADROOM_V1",
            "headroom fixture marker absent")
    return module

def memory():
    fields = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, _, tail = line.partition(":")
        if key in ("MemTotal", "MemAvailable"):
            value, unit = tail.split()
            require(unit == "kB" and key not in fields, "invalid memory observation")
            fields[key] = int(value)
    total, available = fields["MemTotal"], fields["MemAvailable"]
    require(5 * GIB_KIB <= total <= 7 * GIB_KIB and 0 <= available <= total,
            "unexpected guest RAM geometry")
    return total, available

def allocate_chunk():
    region = mmap.mmap(-1, STEP, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
                       prot=mmap.PROT_READ | mmap.PROT_WRITE)
    try:
        # Fault real anonymous pages in, without mlock, swap manipulation,
        # kernel policy changes, or global pressure on the host.
        for offset in range(0, STEP, mmap.PAGESIZE):
            region[offset] = 1
        return region
    except BaseException:
        region.close()
        raise

def hold_headroom(sample, allocate, regions, *, now=time.monotonic, pause=time.sleep):
    """Bounded workload; caller owns region cleanup even on a failed sample."""
    started = now()
    while True:
        total, available = sample()
        required = max(4 * GIB_KIB, (total + 3) // 4)
        require(available >= FLOOR_KIB, "independent guest RAM floor breached")
        if available <= required - MARGIN_KIB:
            return available, required
        require(now() - started < DEADLINE_SECONDS, "headroom target deadline")
        require((len(regions) + 1) * STEP <= MAX_ALLOC, "headroom target not reached within cap")
        require(available - STEP // 1024 >= FLOOR_KIB, "next allocation would breach floor")
        regions.append(allocate())
        pause(0.10)

def stable_swap(guard):
    return {path: (kind, size, priority)
            for path, (kind, size, used, priority) in guard.rows().items()}

def records_absent(guard):
    return not any(os.path.lexists(guard.EXT / name) for name in guard.RECORD_NAMES) and not os.path.lexists(guard.PENDING)

def preflight(guard):
    result = guard.helper("reduction-preflight", "4")
    require(result.returncode == 0, "advisory command failed")
    return json.loads(result.stdout)

def run():
    guard = load_recovery()
    guard.verify_swap(True)
    require(records_absent(guard), "requires unfenced active extension")
    original = stable_swap(guard)
    original_ids = [guard.identity(guard.BASE), guard.identity(guard.EXTRA)]
    original_history = guard.history()
    first = preflight(guard)
    require(first["state"] == "READY_ADVISORY", "initial reduction not ready")
    regions = []
    try:
        available, required = hold_headroom(memory, allocate_chunk, regions)
        print("CPU_MEM_HEADROOM_STAGE // allocatedMiB=" + str(len(regions)*STEP//1024**2)
              + " availableKiB=" + str(available) + " requiredKiB=" + str(required), flush=True)
        blocked = preflight(guard)
        evidence = blocked.get("evidence", {})
        require(blocked.get("state") == "WAITING" and blocked.get("code") == "RAM_HEADROOM",
                "expected real RAM_HEADROOM blocker")
        require(FLOOR_KIB <= evidence["availableKiB"] <= evidence["requiredRamKiB"] - MARGIN_KIB,
                "fresh refusal margin not established")
        require(evidence["extensionUsedKiB"] == 0, "extension occupancy confounds headroom test")
        # This explicitly exercises the privileged refusal in the disposable
        # guest. A racing workload is still possible; any unexpected mutation
        # is a failing test, not something to retry or automatically undo.
        result = guard.helper("withdraw-authorized", "4")
        require(result.returncode == 2, "privileged headroom refusal not observed")
        prefix = "REDUCTION BLOCKED: "
        lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
        require(len(lines) == 1, "missing privileged blocker receipt")
        receipt = json.loads(lines[0][len(prefix):])
        require(receipt["state"] == "WAITING" and receipt["code"] == "RAM_HEADROOM",
                "unexpected privileged blocker")
        require(receipt["evidence"]["availableKiB"] < receipt["evidence"]["requiredRamKiB"],
                "headroom evidence mismatch")
        guard.verify_swap(True)
        require(stable_swap(guard) == original and records_absent(guard),
                "refusal changed swap or published operation intent")
        require([guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == original_ids
                and guard.history() == original_history, "refusal changed files or history")
        print("CPU_MEM_HEADROOM_PASS // ADVISORY_AND_PRIVILEGED_REFUSAL_NO_MUTATION", flush=True)
    finally:
        for region in reversed(regions):
            region.close()
    # Only advisory rechecks after releasing fixture-owned anonymous memory.
    # No automatic privileged retry.
    deadline = time.monotonic() + 20
    while True:
        restored = preflight(guard)
        if restored.get("state") == "READY_ADVISORY":
            break
        require(time.monotonic() < deadline, "headroom did not recover")
        time.sleep(1)
    guard.verify_swap(True)
    require(stable_swap(guard) == original and records_absent(guard)
            and guard.history() == original_history, "unexpected post-release mutation")
    print("CPU_MEM_HEADROOM_PASS // READY_ADVISORY_AFTER_RELEASE_NO_REPLAY", flush=True)

if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print("CPU_MEM_HEADROOM_FAIL // " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(2)
