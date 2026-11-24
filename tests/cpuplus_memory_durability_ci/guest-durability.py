#!/usr/bin/python3 -I
"""Candidate-specific native archive interruption fixture; isolated CI only."""
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
MARKER = Path("/etc/postapollo-memory-native-durability-ci-only")
BOUNDARIES = ("publication-before-file-sync", "resume-after-pending-sync", "first-retirement")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def stage(message):
    print("CPU_MEM_DURABILITY_STAGE // " + message, flush=True)

def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    guard = load("durability_guard", RECOVERY)
    require(guard.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_DURABILITY_V1", "durability marker absent")
    # Use the existing guard with exactly this separately reviewed candidate,
    # never a caller-supplied hash or a mutable checkout.
    guard.PIN = PIN
    guard.guard()
    return guard

def signature(guard):
    return {path: (kind, size, priority)
            for path, (kind, size, used, priority) in guard.rows().items()}

def crash(guard, boundary):
    require(boundary in BOUNDARIES, "unknown fault boundary")
    helper = load("durability_candidate", guard.HELPER)
    def die():
        stage("SIGKILL_AT " + boundary)
        os.kill(os.getpid(), signal.SIGKILL)
    if boundary == BOUNDARIES[0]:
        original = os.fsync
        def interrupted(fd):
            # Real file write and stream.flush already happened. Stop before
            # the actual file fsync, not after an invented journal write.
            info = os.fstat(fd)
            try:
                pending = guard.PENDING.lstat()
            except FileNotFoundError:
                pending = None
            if pending is not None and (info.st_dev, info.st_ino) == (pending.st_dev, pending.st_ino):
                require(json.loads(guard.protected_bytes(guard.PENDING))["state"] ==
                        "ARCHIVE_PENDING", "publication not observed")
                die()
            return original(fd)
        os.fsync = interrupted
    elif boundary == BOUNDARIES[1]:
        original = helper.sync_archive
        def interrupted(path):
            result = original(path)
            if path == guard.PENDING:
                # Candidate's actual protected file+parent sync returned.
                die()
            return result
        helper.sync_archive = interrupted
    else:
        original = Path.unlink
        def interrupted(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path == guard.EXT / guard.RECORD_NAMES[0]:
                die()
            return result
        Path.unlink = interrupted
    helper.archive_cycle_authorized()
    raise RuntimeError("expected fault boundary not reached")

def spawn(boundary):
    stage("SPAWN " + boundary)
    reply = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                            "crash", boundary], stdin=subprocess.DEVNULL)
    require(reply.returncode == -signal.SIGKILL, "fault child did not die by SIGKILL")

def prepare(guard):
    require(not os.path.lexists(guard.WITNESS), "fixture already prepared")
    guard.verify_swap(True)
    previous = guard.history()
    require(len(previous) == 2, "two archived normal cycles required")
    require(not any(os.path.lexists(guard.EXT / n) for n in guard.RECORD_NAMES)
            and not os.path.lexists(guard.PENDING), "unexpected preexisting journal")
    ids = [guard.identity(guard.BASE), guard.identity(guard.EXTRA)]
    original = signature(guard)
    guard.withdraw()
    guard.success("reactivate-authorized", "8", prefix="VERIFIED REACTIVATION: ")
    guard.verify_swap(True)
    originals = {name: guard.digest_file(guard.EXT / name) for name in guard.RECORD_NAMES}
    pending_bytes = None
    archived = None
    for index, boundary in enumerate(BOUNDARIES):
        spawn(boundary)
        guard.verify_swap(True)
        require(signature(guard) == original and
                [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == ids,
                "archive interruption changed swap or files")
        current = guard.protected_bytes(guard.PENDING)
        pending = json.loads(current)
        require(pending["state"] == "ARCHIVE_PENDING", "missing pending fence")
        history = guard.history()
        require(len(history) == 3 and all(history.get(k) == v for k, v in previous.items()),
                "archive history lost or duplicated")
        archive = guard.HISTORY / ("cycle-" + pending["digest"] + ".json")
        bundle = json.loads(guard.protected_bytes(archive))
        require(bundle["digest"] == pending["digest"], "archive binding mismatch")
        # Compare archived record content to the actual pre-crash journal
        # bytes semantically (canonical encoding need not equal live bytes).
        require(len(bundle["records"]) == 4, "archive incomplete")
        if index == 0:
            pending_bytes, archived = current, history
            require(all(json.loads(guard.protected_bytes(guard.EXT / name)) == record
                        for name, record in zip(guard.RECORD_NAMES, bundle["records"])),
                    "archive does not bind original records")
        else:
            require(current == pending_bytes and history == archived,
                    "same-cycle archive or fence changed")
        for i, name in enumerate(guard.RECORD_NAMES):
            if index == 2 and i == 0:
                require(not os.path.lexists(guard.EXT / name), "first retirement missing")
            else:
                require(guard.digest_file(guard.EXT / name) == originals[name],
                        "live record changed or retired prematurely")
        guard.fence()
        observed = guard.success("inspect-recovery-authorized", prefix="RECOVERY INSPECTION: ")
        require(observed["code"] == "ARCHIVE_PENDING" and observed["mutationAllowed"] is False
                and observed["recordCleared"] is False, "recovery incorrectly cleared")
        print("CPU_MEM_DURABILITY_PASS // " + boundary, flush=True)
    guard.success("archive-cycle-authorized", prefix="VERIFIED CYCLE ARCHIVE: ")
    guard.verify_swap(True)
    require(signature(guard) == original and guard.history() == archived and
            [guard.identity(guard.BASE), guard.identity(guard.EXTRA)] == ids and
            not os.path.lexists(guard.PENDING) and
            not any(os.path.lexists(guard.EXT / name) for name in guard.RECORD_NAMES),
            "explicit resume did not preserve exact archive and swap state")
    print("CPU_MEM_DURABILITY_PASS // EXPLICIT_RESUME_ONE_ARCHIVE_NO_SWAP_REPLAY", flush=True)
    # Leave a verified inactive extension for the existing clean-reboot check.
    guard.withdraw()
    guard.fence()
    witness = {"version":1, "bootId":guard.boot_id(), "identity":ids,
               "history":archived, "withdrawal":{name:guard.digest_file(guard.EXT / name)
                                                  for name in guard.RECORD_NAMES[:2]}}
    fd = os.open(guard.WITNESS, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(witness, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(guard.WITNESS.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    print("CPU_MEM_DURABILITY_PASS // REBOOT_WITNESS_DURABLE", flush=True)

def main():
    guard = guarded()
    require(len(sys.argv) >= 2, "phase required")
    phase = sys.argv[1]
    if phase == "crash" and len(sys.argv) == 3:
        crash(guard, sys.argv[2])
    elif phase == "guard" and len(sys.argv) == 2:
        stage("EXACT_CANDIDATE " + PIN)
    elif phase == "prepare" and len(sys.argv) == 2:
        prepare(guard)
    elif phase == "after-reboot" and len(sys.argv) == 2:
        guard.after_reboot()
    else:
        raise RuntimeError("invalid phase")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("CPU_MEM_DURABILITY_FAIL // " + type(error).__name__ + ": " + str(error), flush=True)
        raise SystemExit(2)
