#!/usr/bin/python3 -I
"""Disposable native fence qualification, not a production marker writer."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys

PIN = "5f6e6d800dcf41c1f0f7330fdb248dfd2177104f"
MARKER = Path("/etc/postapollo-memory-native-extfence-ci-only")
GUARD = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
FENCE = Path("/var/lib/post-apollo-memory-reclaim")
WITNESS = Path("/var/lib/postapollo-memory-native-extfence-witness.json")
COMMANDS = (("add","4"),("add-authorized","4"),("persist-authorized",),
            ("expand-authorized","8"),("withdraw-authorized","4"),
            ("reactivate-authorized","8"),("archive-cycle-authorized",),
            ("inspect-recovery-authorized",))

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def guarded():
    require(os.geteuid() == 0 and Path("/run/ostree-booted").is_file(),
            "not a root Silverblue guest")
    loader = importlib.machinery.SourceFileLoader("extfence_guard", str(GUARD))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    guard = importlib.util.module_from_spec(spec)
    loader.exec_module(guard)
    require(guard.protected_bytes(MARKER).strip() ==
            b"DISPOSABLE_CPU_MEMORY_EXTFENCE_V1", "fence fixture marker absent")
    guard.PIN = PIN
    guard.guard()
    return guard

def sync_parent():
    fd = os.open(FENCE.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def signature(guard):
    return {p: [k,s,pr] for p,(k,s,u,pr) in guard.rows().items()}

def fence_identity():
    info = FENCE.lstat()
    require(info.st_uid == 0 and info.st_mode & 0o777 == 0o700
            and FENCE.is_dir() and not FENCE.is_symlink() and not list(FENCE.iterdir()),
            "fixture fence identity mismatch")
    return [info.st_dev,info.st_ino]

def verify_refusal(guard):
    before = signature(guard)
    original = fence_identity()
    for args in COMMANDS:
        result = guard.helper(*args)
        prefix = "REDUCTION RECOVERY: "
        records = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
        require(result.returncode == 3 and len(records) == 1
                and json.loads(records[0][len(prefix):])["code"] == "RECLAIM_RECOVERY_REQUIRED",
                "entrypoint not fenced: " + args[0])
        require(signature(guard) == before and fence_identity() == original,
                "fenced invocation changed kernel or fence")
    print("CPU_MEM_EXTFENCE_STAGE // EIGHT_PROTECTED_ENTRYPOINTS_REFUSED", flush=True)

def fresh(guard):
    require(not any(os.path.lexists(p) for p in (FENCE,WITNESS,guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "not fresh guest")
    FENCE.mkdir(mode=0o700)
    sync_parent()
    original = fence_identity()
    verify_refusal(guard)
    require(not any(os.path.lexists(p) for p in (guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "managed path created despite fence")
    # Only fixture-created empty marker is removed, before managed swap
    # exists. This is NOT an authorized production clearance path.
    require(fence_identity() == original, "fixture marker replaced")
    FENCE.rmdir()
    sync_parent()
    print("CPU_MEM_EXTFENCE_PASS // ABSENT_EXTENSION_ALL_ENTRYPOINTS_BLOCKED", flush=True)

def prepare(guard):
    guard.verify_swap(True)
    history = guard.history()
    require(len(history) == 2 and not os.path.lexists(FENCE)
            and not os.path.lexists(WITNESS), "normal-cycle evidence missing")
    guard.withdraw()
    paths = [guard.EXT / name for name in guard.RECORD_NAMES[:2]]
    records = [guard.digest_file(p) for p in paths]
    identities = [guard.identity(guard.BASE),guard.identity(guard.EXTRA)]
    FENCE.mkdir(mode=0o700)
    sync_parent()
    verify_refusal(guard)
    require(guard.history() == history and [guard.digest_file(p) for p in paths] == records,
            "fenced invocation altered records")
    witness = {"boot":guard.boot_id(),"identity":identities,"fence":fence_identity(),
               "history":history,"records":records,"swap":signature(guard)}
    fd = os.open(WITNESS,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"w") as stream:
        json.dump(witness,stream,sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    sync_parent()
    print("CPU_MEM_EXTFENCE_PASS // FENCE_AND_WITHDRAWAL_WITNESS_DURABLE",flush=True)

def after_reboot(guard):
    witness=json.loads(guard.protected_bytes(WITNESS))
    require(guard.boot_id()!=witness["boot"],"new kernel boot not observed")
    guard.verify_swap(False)
    actual = {"identity":[guard.identity(guard.BASE)[1:],guard.identity(guard.EXTRA)[1:]],
              "fence_inode":fence_identity()[1],"swap":signature(guard)}
    expected = {"identity":[row[1:] for row in witness["identity"]],
                "fence_inode":witness["fence"][1],"swap":witness["swap"]}
    # Dedicated offline guest only. Report fixed fixture metadata, not swap
    # contents. Do not drop unrelated swap rows or accept changed identities.
    for key in ("identity","fence_inode","swap"):
        if actual[key]!=expected[key]:
            print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps(
                  {"field":key,"expected":expected[key],"actual":actual[key]},sort_keys=True),flush=True)
    require(actual["identity"]==expected["identity"],"managed file inode or size changed after reboot")
    require(actual["fence_inode"]==expected["fence_inode"],"external fence inode changed after reboot")
    require(actual["swap"]==expected["swap"],"active swap composition changed after reboot")
    verify_refusal(guard)
    require(guard.history()==witness["history"]
            and [guard.digest_file(guard.EXT / name) for name in guard.RECORD_NAMES[:2]]
            == witness["records"] and signature(guard)==witness["swap"],
            "reboot or refusal changed recovery evidence")
    print("CPU_MEM_EXTFENCE_PASS // NEW_BOOT_EXTERNAL_FENCE_AND_RECORDS_RETAINED_NO_REPLAY",flush=True)

def main():
    guard=guarded()
    require(len(sys.argv)==2,"phase required")
    if sys.argv[1]=="guard":
        print("CPU_MEM_EXTFENCE_STAGE // EXACT_CANDIDATE "+PIN,flush=True)
    elif sys.argv[1]=="fresh":
        fresh(guard)
    elif sys.argv[1]=="prepare":
        prepare(guard)
    elif sys.argv[1]=="after-reboot":
        after_reboot(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        print("CPU_MEM_EXTFENCE_FAIL // "+type(exc).__name__+": "+str(exc),flush=True)
        raise SystemExit(2)
