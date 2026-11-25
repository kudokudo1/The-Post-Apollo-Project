#!/usr/bin/python3 -I
"""Disposable native fence qualification, not a production marker writer."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
from pathlib import Path
import sys

PIN = "9dfd8331445ecf60d3a37ea630d08b1f3f6789a2"
MARKER = Path("/etc/postapollo-memory-native-extfence-ci-only")
GUARD = Path("/usr/local/libexec/postapollo-memory-ci-fault.py")
FENCE = Path("/var/lib/post-apollo-memory-reclaim")
WITNESS = Path("/var/lib/postapollo-memory-native-extfence-witness.json")
ARCHIVE = Path("/var/lib/post-apollo-memory-reclaim-archive.json")
WRITER = Path("/usr/local/libexec/postapollo-memory-ci-custody.py")
WRITER_PIN = "95af22255db13baa829a68c7a9b90b25c50a6bdd"
PREPARED = FENCE / "prepared.json"
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
    require(guard.protected_bytes(Path("/etc/postapollo-memory-native-protected-custody-ci-only")).strip() ==
            b"DISPOSABLE_CPU_MEMORY_PROTECTED_CUSTODY_V1", "custody fixture marker absent")
    raw = guard.protected_bytes(WRITER)
    require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
            WRITER_PIN, "writer blob mismatch")
    require(guard.protected_bytes(Path("/usr/local/sbin/post-apollo-memory-add-swap")) ==
            guard.protected_bytes(guard.HELPER), "installed helper bytes mismatch")
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

def fence_identity(guard, prepared=None):
    info = FENCE.lstat()
    require(info.st_uid == 0 and info.st_mode & 0o777 == 0o700
            and stat.S_ISDIR(info.st_mode), "fixture fence identity mismatch")
    names = {p.name for p in FENCE.iterdir()}
    require(names == (set() if prepared is None else {PREPARED.name}),
            "fixture fence contents mismatch")
    if prepared is not None:
        require(guard.protected_bytes(PREPARED) == prepared, "prepared record changed")
    return [info.st_dev,info.st_ino]

def verify_refusal(guard, prepared=None):
    before = signature(guard)
    original = fence_identity(guard, prepared)
    for args in COMMANDS:
        result = guard.helper(*args)
        prefix = "REDUCTION RECOVERY: "
        records = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
        require(result.returncode == 3 and len(records) == 1
                and json.loads(records[0][len(prefix):])["code"] == "RECLAIM_RECOVERY_REQUIRED",
                "entrypoint not fenced: " + args[0])
        require(signature(guard) == before and fence_identity(guard, prepared) == original,
                "fenced invocation changed kernel or fence")
    print("CPU_MEM_EXTFENCE_STAGE // EIGHT_PROTECTED_ENTRYPOINTS_REFUSED", flush=True)

def fresh(guard):
    require(not any(os.path.lexists(p) for p in (FENCE,WITNESS,ARCHIVE,guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "not fresh guest")
    # Test archive-only admission before any managed allocation. Only this
    # fixture-created partial leaf is removed, not any real custody evidence.
    partial = b"{"
    write_once(guard, ARCHIVE, partial)
    before = signature(guard)
    for args in COMMANDS:
        result = guard.helper(*args)
        records = [line for line in result.stdout.splitlines()
                   if line.startswith("REDUCTION RECOVERY: ")]
        require(result.returncode == 3 and len(records) == 1 and
                json.loads(records[0].split(": ", 1)[1])["code"] == "RECLAIM_RECOVERY_REQUIRED",
                "archive-only admission not fenced: " + args[0])
        require(signature(guard) == before and guard.protected_bytes(ARCHIVE) == partial
                and not os.path.lexists(FENCE), "archive-only refusal mutated state")
    require(not any(os.path.lexists(p) for p in (guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "managed path created despite archive-only fence")
    ARCHIVE.unlink()
    sync_parent()
    print("CPU_MEM_EXTFENCE_PASS // ARCHIVE_ONLY_EIGHT_ENTRYPOINTS_REFUSED", flush=True)
    FENCE.mkdir(mode=0o700)
    sync_parent()
    original = fence_identity(guard)
    verify_refusal(guard)
    require(not any(os.path.lexists(p) for p in (guard.BASE.parent,guard.EXT,guard.HISTORY)),
            "managed path created despite fence")
    # Only fixture-created empty marker is removed, before managed swap
    # exists. This is NOT an authorized production clearance path.
    require(fence_identity(guard) == original, "fixture marker replaced")
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

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"

def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def write_once(guard, path, data):
    require(type(data) is bytes and 0 < len(data) <= 131072, "fixture record size")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        require(stream.write(data) == len(data), "fixture short write")
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(path.parent)
    require(guard.protected_bytes(path) == data, "fixture record readback mismatch")

RESULT = Path("/var/lib/postapollo-memory-ci-managed-reclaim-result.json")
MANAGED = Path("/usr/local/libexec/postapollo-memory-ci-managed.py")
MANAGED_PIN = "60df42d1d9948ead331542c24225b559c2e227a6"

def publish_archive_and_fence(guard,module):
    import types
    import signal
    require(guard.protected_bytes(Path("/etc/postapollo-memory-native-managed-interrupt-ci-only")).strip()
            == b"DISPOSABLE_CPU_MEMORY_MANAGED_INTERRUPT_V1","interrupt fixture marker absent")
    raw=guard.protected_bytes(MANAGED)
    require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==MANAGED_PIN,
            "managed fixture blob mismatch")
    combined=types.ModuleType("managed_reclaim_fixture")
    exec(compile(raw,str(MANAGED),"exec",dont_inherit=True),combined.__dict__)
    identity=[list(row) for row in module.extension_identity()]
    records=[guard.protected_bytes(guard.EXT/name).hex() for name in guard.RECORD_NAMES[:2]]
    class FaultOS:
        # Module-local proxy: preserve actual os calls, interrupt only the child
        # after the fixed inactive extension's unlink AND actual successful fsync.
        def __init__(self):
            self.pending=None
        def __getattr__(self,name):
            return getattr(os,name)
        def unlink(self,name,*,dir_fd):
            require(name=="swapfile" and self.pending is None,
                    "unexpected unlink before interruption")
            st=os.fstat(dir_fd)
            require((st.st_dev,st.st_ino)==tuple(identity[2][:2]),
                    "fault target identity mismatch")
            os.unlink(name,dir_fd=dir_fd)
            self.pending=dir_fd
        def fsync(self,fd):
            os.fsync(fd)
            if self.pending is not None:
                require(fd==self.pending and not os.path.lexists(guard.EXTRA),
                        "unexpected post-unlink synchronization")
                print("CPU_MEM_EXTFENCE_STAGE // ACTUAL_UNLINK_AND_FSYNC_BEFORE_SIGKILL",flush=True)
                os.kill(os.getpid(),signal.SIGKILL)
                raise RuntimeError("SIGKILL did not terminate child")
    child=os.fork()
    if child==0:
        try:
            combined.os=FaultOS()
            combined.prepare_candidate()
        except BaseException as exc:
            print("CPU_MEM_EXTFENCE_FAIL // interruption child "+repr(exc),flush=True)
            os._exit(2)
        os._exit(3)
    got,status=os.waitpid(child,0)
    require(got==child and os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL,
            "interruption child did not terminate by SIGKILL")
    archive=guard.protected_bytes(ARCHIVE)
    bundle=json.loads(archive)
    prepared=guard.protected_bytes(PREPARED)
    require(bundle["identity"]==identity and bundle["records_hex"]==records
            and bundle["boot_id"]==guard.boot_id()
            and bundle["can_execute"] is False and bundle["can_clear"] is False
            and prepared==canonical_bytes({"version":1,"state":"PREPARED",
                "archive_sha256":hashlib.sha256(archive).hexdigest(),"boot_id":guard.boot_id(),
                "can_execute":False,"can_clear":False}),"interrupted custody binding mismatch")
    require(not os.path.lexists(guard.EXTRA) and not os.path.lexists(RESULT)
            and {p.name for p in guard.EXT.iterdir()}==set(guard.RECORD_NAMES[:2])
            and [guard.protected_bytes(guard.EXT/name).hex() for name in guard.RECORD_NAMES[:2]]==records,
            "interruption boundary not observed")
    st=guard.EXT.lstat()
    require((st.st_dev,st.st_ino)==tuple(identity[2][:2]),"partial subvolume replaced")
    fence_identity(guard,prepared)
    print("CPU_MEM_EXTFENCE_PASS // SIGKILL_PARTIAL_RELEASE_NO_SUCCESS_RECEIPT",flush=True)
    return guard.digest_file(ARCHIVE),prepared

def prepare(guard):
    guard.verify_swap(True)
    history = guard.history()
    require(len(history) == 2 and not os.path.lexists(FENCE)
            and not os.path.lexists(WITNESS) and not os.path.lexists(ARCHIVE),
            "normal-cycle evidence missing")
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
    archive_sha, prepared = publish_archive_and_fence(guard, module)
    verify_refusal(guard, prepared)
    require(guard.history() == history and not os.path.lexists(guard.EXTRA)
            and not os.path.lexists(RESULT)
            and [guard.digest_file(p) for p in paths]==records
            and guard.digest_file(ARCHIVE)==archive_sha
            and guard.identity(guard.BASE)==identities[0], "interrupted release changed preserved evidence")
    witness = {"boot":guard.boot_id(),"identity":identities,"fence":fence_identity(guard, prepared),
               "history":history,"records":records,"swap":signature(guard),
               "archive":archive_sha,"prepared":prepared.decode("ascii"),
               "ext_inode":guard.EXT.lstat().st_ino,"result_absent":True}
    fd = os.open(WITNESS,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"w") as stream:
        json.dump(witness,stream,sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    sync_parent()
    print("CPU_MEM_EXTFENCE_PASS // FENCE_AND_WITHDRAWAL_WITNESS_DURABLE",flush=True)

def after_reboot(guard):
    witness=json.loads(guard.protected_bytes(WITNESS))
    require(guard.boot_id()!=witness["boot"] and witness["result_absent"] is True,
            "new kernel boot or incomplete state not observed")
    prepared=witness["prepared"].encode("ascii")
    def unchanged():
        require(not os.path.lexists(guard.EXTRA) and not os.path.lexists(RESULT)
                and guard.EXT.lstat().st_ino==witness["ext_inode"]
                and {p.name for p in guard.EXT.iterdir()}==set(guard.RECORD_NAMES[:2])
                and [guard.digest_file(guard.EXT/name) for name in guard.RECORD_NAMES[:2]]==witness["records"]
                and signature(guard)==witness["swap"]
                and guard.identity(guard.BASE)[1:]==witness["identity"][0][1:]
                and fence_identity(guard,prepared)[1]==witness["fence"][1]
                and guard.digest_file(ARCHIVE)==witness["archive"] and guard.history()==witness["history"],
                "interrupted recovery evidence changed after reboot")
    unchanged()
    bundle=json.loads(guard.protected_bytes(ARCHIVE))
    require(bundle["boot_id"]==witness["boot"] and bundle["can_execute"] is False
            and bundle["can_clear"] is False
            and [hashlib.sha256(bytes.fromhex(v)).hexdigest() for v in bundle["records_hex"]]==witness["records"],
            "archive lost interrupted withdrawal records")
    verify_refusal(guard,prepared)
    unchanged()
    print("CPU_MEM_EXTFENCE_PASS // INTERRUPTED_RELEASE_REBOOT_RETAINED_NO_REPLAY",flush=True)

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
