#!/usr/bin/python3 -I
"""Real occupied-extension refusal, fresh isolated CI VM only."""
import importlib.machinery
import importlib.util
import json
import mmap
import os
import platform
import sys
from pathlib import Path
import re
import stat
import time

GIB = 1024 ** 3
KIB = 1024
WORKLOAD = 128 * 1024 ** 2
MARKER = Path("/etc/postapollo-memory-native-occupied-ci-only")
RECOVERY = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_OCCUPIED_STAGE // " + message, flush=True)

def load_guard():
    # Existing exact helper identity, root, Silverblue, VM, SELinux and Btrfs
    # checks remain mandatory. Never import or provision on a workstation.
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader = importlib.machinery.SourceFileLoader("occupied_guard", str(RECOVERY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.guard()
    require(module.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_OCCUPIED_V1", "occupied fixture marker absent")
    return module

def pageout_advice(*, platform_name, machine, exported, supports_madvise):
    # Linux x86-64 UAPI asm-generic/mman-common.h defines MADV_PAGEOUT
    # as 21. CPython may omit the named constant at build time while still
    # accepting that integer through mmap.madvise(). Never substitute
    # MADV_DONTNEED (which would discard pages instead of testing swap).
    require(platform_name == "linux" and machine == "x86_64",
            "unsupported MADV_PAGEOUT ABI")
    require(supports_madvise, "Python mmap.madvise unavailable")
    require(exported is None or type(exported) is int and exported == 21,
            "unexpected MADV_PAGEOUT constant")
    return 21

def memory_available():
    fields = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, _, tail = line.partition(":")
        if key in ("MemTotal", "MemAvailable"):
            value, unit = tail.split()
            require(unit == "kB" and key not in fields, "invalid RAM observation")
            fields[key] = int(value) * KIB
    require(5 * GIB <= fields["MemTotal"] <= 7 * GIB, "unexpected guest geometry")
    return fields["MemAvailable"]

def evidence_absent(guard):
    return (not os.path.lexists(guard.HISTORY)
            and not any(os.path.lexists(guard.EXT / name)
                        for name in guard.RECORD_NAMES)
            and not os.path.lexists(guard.PENDING))

def create_fixture_swap(guard, path, priority):
    # This is deliberately not a production expansion API. Fresh guest
    # setup creates the extension before the base to avoid filling higher
    # priority devices or disabling any existing swap.
    require(path in (guard.BASE, guard.EXTRA), "unexpected fixture path")
    require((path == guard.BASE and priority == 10)
            or (path == guard.EXTRA and priority == 9), "unexpected priority")
    require(not os.path.lexists(path.parent), "fixture directory already exists")
    vfs = os.statvfs("/var/lib")
    require(vfs.f_bavail * vfs.f_frsize >= 36 * GIB, "insufficient guest disk reserve")
    guard.command("/usr/bin/btrfs", "subvolume", "create", str(path.parent))
    path.parent.chmod(0o700)
    guard.command("/usr/bin/btrfs", "filesystem", "mkswapfile",
                  "--size", "4G", str(path))
    path.chmod(0o600)
    guard.command("/usr/bin/btrfs", "inspect-internal", "map-swapfile", str(path))
    guard.command("/usr/sbin/swapon", "--priority", str(priority), "--", str(path))
    row = guard.rows().get(str(path))
    require(row is not None and row[0] == "file" and row[3] == priority
            and 0 <= 4 * GIB // KIB - row[1] <= 1024, "fixture activation not observed")

def identities(guard):
    result = []
    for path in (guard.BASE.parent, guard.BASE, guard.EXTRA.parent, guard.EXTRA):
        info = path.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o077
                and (stat.S_ISDIR(info.st_mode) if path in (guard.BASE.parent, guard.EXTRA.parent)
                     else stat.S_ISREG(info.st_mode) and info.st_nlink == 1),
                "unexpected fixture identity")
        result.append((info.st_dev, info.st_ino,
                       info.st_size if stat.S_ISREG(info.st_mode) else 0))
    return result

def swap_signature(guard):
    return {path: (row[0], row[1], row[3]) for path, row in guard.rows().items()}

def occupied_evidence(result):
    require(result.get("state") == "WAITING" and result.get("code") == "EXTENSION_OCCUPIED",
            "wrong blocker")
    e = result["evidence"]
    require(type(e["extensionUsedKiB"]) is int and e["extensionUsedKiB"] > 0,
            "actual extension occupancy missing")
    # Distinguish occupancy from the independent RAM/base reserve checks.
    require(e["availableKiB"] >= e["requiredRamKiB"]
            and e["baseFreeKiB"] >= e["requiredBaseFreeKiB"],
            "headroom confounds occupancy")
    return e

def advisory(guard):
    reply = guard.helper("reduction-preflight", "4")
    require(reply.returncode == 0, "advisory command failed")
    return json.loads(reply.stdout)

def run():
    guard = load_guard()
    require(not guard.rows(), "fresh guest must have zero existing swap devices")
    require(not any(os.path.lexists(p) for p in
                    (guard.BASE.parent, guard.EXT, guard.HISTORY)),
            "managed state already exists")
    for path in (Path("/"), Path("/var"), Path("/var/lib")):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o022, "untrusted fixture parent")
    mount = guard.command("/usr/bin/findmnt", "-n", "-o", "TARGET", "-T", "/var/lib").strip()
    require(mount in ("/", "/var", "/var/lib"), "unexpected guest mount")
    require(re.search(r"\bTotal devices\s+1\b",
                      guard.command("/usr/bin/btrfs", "filesystem", "show", "--raw", mount)),
            "single-device Btrfs required")
    advice = pageout_advice(platform_name=sys.platform, machine=platform.machine(),
                            exported=getattr(mmap, "MADV_PAGEOUT", None),
                            supports_madvise=callable(getattr(mmap.mmap, "madvise", None)))
    stage("LINUX_PAGEOUT_ADVICE=" + str(advice))
    require(memory_available() >= 4 * GIB + WORKLOAD, "insufficient fixture RAM")
    os.umask(0o077)
    create_fixture_swap(guard, guard.EXTRA, 9)
    rows = guard.rows()
    require(set(rows) == {str(guard.EXTRA)} and rows[str(guard.EXTRA)][2] == 0,
            "extension must initially be sole empty swap")
    stage("EXTENSION_ONLY_ACTIVE")
    # At most 128 MiB of private anonymous pages, no mlock or global
    # swappiness change. Request real pageout and observe the kernel, rather
    # than assume MADV_PAGEOUT succeeded. No pressure escalation or OOM.
    region = mmap.mmap(-1, WORKLOAD, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
                       prot=mmap.PROT_READ | mmap.PROT_WRITE)
    try:
        for offset in range(0, WORKLOAD, mmap.PAGESIZE):
            region[offset] = 1
        for attempt in range(4):
            require(memory_available() >= 4 * GIB, "fixture RAM floor breached")
            region.madvise(advice)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                observed = guard.rows()
                require(set(observed) == {str(guard.EXTRA)}, "unexpected active swap")
                if observed[str(guard.EXTRA)][2] > 0:
                    break
                time.sleep(0.2)
            if guard.rows()[str(guard.EXTRA)][2] > 0:
                break
        require(guard.rows()[str(guard.EXTRA)][2] > 0, "real extension pageout not observed")
        # Do not touch the mapping again until close; preserve occupied slots.
        create_fixture_swap(guard, guard.BASE, 10)
        rows = guard.rows()
        require(set(rows) == {str(guard.BASE), str(guard.EXTRA)}
                and rows[str(guard.EXTRA)][2] > 0, "occupied extension lost during base setup")
        original = swap_signature(guard)
        original_ids = identities(guard)
        require(evidence_absent(guard), "unexpected prior journal")
        e = occupied_evidence(advisory(guard))
        stage("KERNEL_OCCUPIED_KIB=" + str(e["extensionUsedKiB"]))
        result = guard.helper("withdraw-authorized", "4")
        require(result.returncode == 2, "privileged occupied refusal not observed")
        prefix = "REDUCTION BLOCKED: "
        lines = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
        require(len(lines) == 1, "missing privileged blocker receipt")
        e = occupied_evidence(json.loads(lines[0][len(prefix):]))
        require(guard.rows()[str(guard.EXTRA)][2] > 0
                and swap_signature(guard) == original
                and identities(guard) == original_ids and evidence_absent(guard),
                "refusal changed active swap, identities, or journal")
        print("CPU_MEM_OCCUPIED_PASS // ACTUAL_OCCUPIED_ADVISORY_AND_PRIVILEGED_REFUSAL", flush=True)
    finally:
        # Release only this fixture's mapping; never issue swapoff or a
        # compensating privileged mutation, including on failure.
        region.close()
    deadline = time.monotonic() + 30
    while True:
        rows = guard.rows()
        require(swap_signature(guard) == original and identities(guard) == original_ids
                and evidence_absent(guard), "unexpected post-release mutation")
        if rows[str(guard.EXTRA)][2] == 0 and advisory(guard).get("state") == "READY_ADVISORY":
            break
        require(time.monotonic() < deadline, "extension did not drain to advisory readiness")
        time.sleep(1)
    print("CPU_MEM_OCCUPIED_PASS // RELEASED_PAGES_ADVISORY_READY_NO_REPLAY", flush=True)

if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        print("CPU_MEM_OCCUPIED_FAIL // " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(2)
