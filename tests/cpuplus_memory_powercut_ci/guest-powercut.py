#!/usr/bin/python3 -I
"""Abrupt guest termination after durable archive fence; disposable CI only."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

PIN = "6bac8be7b1de6883f480a95944d6ba1130852270"
RECOVERY = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
MARKER = Path("/etc/postapollo-memory-native-powercut-ci-only")
WITNESS = Path("/var/lib/postapollo-memory-native-powercut-witness.json")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_POWERCUT_STAGE // " + message, flush=True)

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    guard = load("powercut_guard", RECOVERY)
    require(guard.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_POWERCUT_V1", "powercut marker absent")
    guard.PIN = PIN
    guard.guard()
    return guard

def digest(records):
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()

def signature(guard):
    return {path: [kind, size, priority]
            for path, (kind, size, used, priority) in guard.rows().items()}

def write_witness(data):
    fd = os.open(WITNESS, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        json.dump(data, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(WITNESS.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def verify_pending(guard, witness):
    pending = json.loads(guard.protected_bytes(guard.PENDING))
    require(pending == {"version":1, "state":"ARCHIVE_PENDING", "digest":witness["digest"]},
            "pending marker changed")
    history = guard.history()
    name = "cycle-" + witness["digest"] + ".json"
    require(set(history) == set(witness["history"]) | {name}
            and all(history.get(k) == v for k, v in witness["history"].items()),
            "history missing, changed or duplicated")
    bundle = json.loads(guard.protected_bytes(guard.HISTORY / name))
    require(bundle["records"] == witness["records"] and bundle["digest"] == witness["digest"],
            "archive content changed")
    require(all(guard.digest_file(guard.EXT / name) == value
                for name, value in witness["journal"].items()),
            "journal retired prematurely or changed")
    return history

def prepare(guard):
    require(not os.path.lexists(WITNESS), "existing powercut witness")
    guard.verify_swap(True)
    old = guard.history()
    require(len(old) == 2, "two normal cycles required")
    require(not any(os.path.lexists(guard.EXT / n) for n in guard.RECORD_NAMES)
            and not os.path.lexists(guard.PENDING), "prior journal exists")
    guard.withdraw()
    guard.success("reactivate-authorized", "8", prefix="VERIFIED REACTIVATION: ")
    guard.verify_swap(True)
    records = [json.loads(guard.protected_bytes(guard.EXT / n)) for n in guard.RECORD_NAMES]
    witness = {"version":1, "candidate":PIN, "bootId":guard.boot_id(),
               "identity":[guard.identity(guard.BASE), guard.identity(guard.EXTRA)],
               "swap":signature(guard), "history":old, "records":records,
               "digest":digest(records),
               "journal":{n:guard.digest_file(guard.EXT / n) for n in guard.RECORD_NAMES}}
    # Persist the independent expected state BEFORE the archive fault.
    write_witness(witness)
    helper = load("powercut_candidate", guard.HELPER)
    original = helper.sync_archive
    def stop_after_sync(path):
        result = original(path)
        if path == guard.PENDING:
            verify_pending(guard, witness)
            require(signature(guard) == witness["swap"]
                    and [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == witness["identity"],
                    "pre-cut swap or identity changed")
            # The actual candidate just completed file+directory fsync.
            # Do not request guest poweroff or return to retirement.
            stage("CUT_READY_PENDING_SYNCED_BEFORE_RETIREMENT")
            os.kill(os.getpid(), signal.SIGSTOP)
            raise RuntimeError("cut boundary unexpectedly resumed")
        return result
    helper.sync_archive = stop_after_sync
    helper.archive_cycle_authorized()
    raise RuntimeError("cut boundary not reached")

def after_cut(guard):
    witness = json.loads(guard.protected_bytes(WITNESS))
    require(witness["version"] == 1 and witness["candidate"] == PIN
            and witness["bootId"] != guard.boot_id(), "different boot not established")
    guard.verify_swap(False)
    current = [guard.identity(guard.BASE), guard.identity(guard.EXTRA)]
    # Device numbers can legitimately differ across boots; verify inode/size.
    require([r[1:] for r in current] == [r[1:] for r in witness["identity"]],
            "managed inode or size changed")
    expected = dict(witness["swap"])
    expected.pop(str(guard.EXTRA))
    require(signature(guard) == expected, "unexpected post-cut active swap composition")
    retained = verify_pending(guard, witness)
    guard.fence()
    observed = guard.success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
    require(observed["code"] == "ARCHIVE_PENDING" and observed["mutationAllowed"] is False
            and observed["recordCleared"] is False, "pending fence lost")
    require(verify_pending(guard, witness) == retained and signature(guard) == expected,
            "inspection or refusal changed state")
    print("CPU_MEM_POWERCUT_PASS // REAL_NEW_BOOT_PENDING_AND_JOURNALS_RETAINED", flush=True)
    print("CPU_MEM_POWERCUT_PASS // BASE_ACTIVE_EXTENSION_INACTIVE_NO_REPLAY", flush=True)
    # Do not attempt archive resume on an inactive extension or clear the
    # marker. Current recovery contract is deliberately fail closed.

def main():
    guard = guarded()
    require(len(sys.argv) == 2, "phase required")
    if sys.argv[1] == "guard":
        stage("EXACT_CANDIDATE " + PIN)
    elif sys.argv[1] == "prepare":
        prepare(guard)
    elif sys.argv[1] == "after-cut":
        after_cut(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("CPU_MEM_POWERCUT_FAIL // " + type(exc).__name__ + ": " + str(exc), flush=True)
        raise SystemExit(2)
