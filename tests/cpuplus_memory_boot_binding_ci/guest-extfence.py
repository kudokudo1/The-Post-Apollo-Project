#!/usr/bin/python3 -I
"""Disposable native fence qualification, not a production marker writer."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys

PIN = "8082bac43e3d8a0f506348e0ecee2e063d34935b"
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
    require(guard.protected_bytes(Path("/etc/postapollo-memory-native-boot-binding-ci-only")).strip() ==
            b"DISPOSABLE_CPU_MEMORY_BOOT_BINDING_V1", "boot binding fixture marker absent")
    guard.PIN = PIN
    guard.guard()
    # Pin only the disposable guest's boot-generated ZRAM capacity. Do not
    # normalize away changes in the complete /proc/swaps signature.
    config = Path("/etc/systemd/zram-generator.conf.d/99-postapollo-boot-binding-ci.conf")
    require(guard.protected_bytes(config) == b"[zram0]\nzram-size = 4096\nswap-priority = 100\n",
            "fixture ZRAM configuration mismatch")
    require(int(Path("/sys/block/zram0/disksize").read_text()) == 4 * guard.GIB,
            "fixture ZRAM disk capacity mismatch")
    row = guard.rows().get("/dev/zram0")
    require(row is not None and row[0] == "partition" and row[3] == 100
            and row[1] == 4 * guard.GIB // 1024 - os.sysconf("SC_PAGE_SIZE") // 1024,
            "fixture ZRAM swap capacity or priority mismatch")
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

def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()

def load_candidate(guard):
    # Guard verified exact installed bytes, root-only markers and offline VM.
    loader = importlib.machinery.SourceFileLoader("boot_bound_candidate", str(guard.HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

def check_pair(intent, outcome, boot):
    require(intent["state"] == "PREPARED" and outcome["state"] == "VERIFIED",
            "expected durable withdrawal pair")
    require(intent["bootBinding"] == {"version": 1, "bootId": boot}
            and outcome["bootBinding"] == {"version": 1, "bootId": boot,
                                          "intentDigest": canonical_digest(intent)},
            "independent boot or full intent digest mismatch")

def prepare(guard):
    guard.verify_swap(True)
    history = guard.history()
    require(len(history) == 2 and not os.path.lexists(FENCE)
            and not os.path.lexists(WITNESS), "normal-cycle evidence missing")
    module = load_candidate(guard)
    boot = guard.boot_id()
    # Both real normal cycles have already completed and archived.
    # Archived evidence is not a current inactive withdrawal witness.
    with module.mutation_lock(inspection=True):
        for name in history:
            bundle = json.loads(guard.protected_bytes(guard.HISTORY / name))
            intent, outcome = bundle["records"][:2]
            check_pair(intent, outcome, boot)
            require(module.withdrawal_boot_witness(intent, outcome, module.extension_identity(),
                    module.read_reduction_snapshot(), boot) is None,
                    "active archived extension incorrectly qualifies")
    print("CPU_MEM_EXTFENCE_PASS // BOUND_ARCHIVED_CYCLES_ACTIVE_REFUSED", flush=True)
    ready = guard.helper("reduction-preflight", "4")
    require(ready.returncode == 0 and json.loads(ready.stdout)["state"] == "READY_ADVISORY",
            "native withdrawal preflight not ready")
    receipt = guard.success("withdraw-authorized", "4", prefix="VERIFIED REDUCTION: ")
    require(set(receipt) == {"version", "state", "targetGiB", "sizeKiB", "basePriority",
            "extensionActive", "fileRetained", "timeNs"} and receipt["state"] == "VERIFIED"
            and receipt["extensionActive"] is False and receipt["fileRetained"] is True,
            "public stdout schema changed")
    guard.verify_swap(False)
    paths = [guard.EXT / name for name in guard.RECORD_NAMES[:2]]
    with module.mutation_lock(inspection=True):
        intent, outcome = [json.loads(guard.protected_bytes(p)) for p in paths]
        check_pair(intent, outcome, boot)
        require({k:v for k,v in outcome.items() if k != "bootBinding"} == receipt,
                "public receipt differs from durable outcome")
        identity = module.extension_identity()
        snapshot = module.read_reduction_snapshot()
        require(module.current_boot_id() == boot == guard.boot_id(), "boot observation changed")
        expected = {"version": 1, "boot_id": boot,
                    "withdrawal_digest": canonical_digest([intent, outcome])}
        require(module.withdrawal_boot_witness(intent, outcome, identity, snapshot, boot) == expected,
                "actual same-boot inactive witness missing")
        legacy_intent = {k:v for k,v in intent.items() if k != "bootBinding"}
        legacy_outcome = {k:v for k,v in outcome.items() if k != "bootBinding"}
        require(module.classify_recovery(legacy_intent, legacy_outcome, identity, snapshot)["code"]
                == "RECORDED_VERIFIED_INACTIVE"
                and module.withdrawal_boot_witness(legacy_intent, legacy_outcome, identity, snapshot, boot) is None,
                "legacy observation became authorizing witness")
        bad = dict(outcome, bootBinding=dict(outcome["bootBinding"], intentDigest="0"*64))
        require(module.withdrawal_boot_witness(intent, bad, identity, snapshot, boot) is None,
                "malformed intent binding qualified")
    print("CPU_MEM_EXTFENCE_PASS // SAME_BOOT_INACTIVE_WITNESS_AND_PUBLIC_RECEIPT", flush=True)
    print("CPU_MEM_EXTFENCE_PASS // LEGACY_AND_MALFORMED_WITNESS_REFUSED", flush=True)
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
    module = load_candidate(guard)
    intent, outcome = [json.loads(guard.protected_bytes(guard.EXT / name))
                       for name in guard.RECORD_NAMES[:2]]
    check_pair(intent, outcome, witness["boot"])
    current_boot = guard.boot_id()
    require(module.current_boot_id() == current_boot, "independent boot observation disagrees")
    # Pure non-authorizing negative check. The external fence remains present;
    # never bypass it to acquire the helper's protected mutation lock.
    require(module.withdrawal_boot_witness(intent, outcome, module.extension_identity(),
            module.read_reduction_snapshot(), current_boot) is None,
            "prior boot witness accepted")
    print("CPU_MEM_EXTFENCE_PASS // PRIOR_BOOT_WITNESS_REFUSED", flush=True)
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
        print("CPU_MEM_EXTFENCE_PASS // FIXED_GUEST_ZRAM_4GIB", flush=True)
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
