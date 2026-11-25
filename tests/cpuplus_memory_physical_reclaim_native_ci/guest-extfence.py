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

def publish_archive_and_fence(guard, module):
    # Run the exact unrouted candidate in the explicitly marked offline guest.
    # Do not substitute its paths, lock, observations, reader or writer.
    raw = guard.protected_bytes(WRITER)
    require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() ==
            WRITER_PIN, "writer changed")
    import types
    writer = types.ModuleType("native_custody_writer")
    exec(compile(raw, str(WRITER), "exec", dont_inherit=True), writer.__dict__)
    result = writer.prepare_candidate()
    require(result == {"state":"PREPARED_REVIEW_REQUIRED","can_execute":False,"can_clear":False},
            "writer receipt mismatch")
    archive = guard.protected_bytes(ARCHIVE)
    bundle = json.loads(archive)
    records = [guard.protected_bytes(guard.EXT / name).hex() for name in guard.RECORD_NAMES[:2]]
    require(bundle["state"] == "ARCHIVE_CUSTODY" and bundle["candidate_blob"] == PIN
            and bundle["boot_id"] == guard.boot_id() and bundle["records_hex"] == records
            and bundle["identity"] == [list(row) for row in module.extension_identity()]
            and bundle["can_execute"] is False and bundle["can_clear"] is False,
            "actual archive binding mismatch")
    archive_sha = hashlib.sha256(archive).hexdigest()
    prepared = canonical_bytes({"version":1,"state":"PREPARED","archive_sha256":archive_sha,
                  "boot_id":bundle["boot_id"],"can_execute":False,"can_clear":False})
    fence_identity(guard, prepared)
    print("CPU_MEM_EXTFENCE_PASS // EXACT_WRITER_ARCHIVE_AND_PREPARED", flush=True)
    return archive_sha, prepared

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
    require(guard.history() == history and [guard.digest_file(p) for p in paths] == records
            and guard.digest_file(ARCHIVE) == archive_sha, "fenced invocation altered records")
    witness = {"boot":guard.boot_id(),"identity":identities,"fence":fence_identity(guard, prepared),
               "history":history,"records":records,"swap":signature(guard),
               "archive":archive_sha,"prepared":prepared.decode("ascii")}
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
    prepared = witness["prepared"].encode("ascii")
    archive = guard.protected_bytes(ARCHIVE)
    require(hashlib.sha256(archive).hexdigest() == witness["archive"], "archive changed across reboot")
    bundle = json.loads(archive)
    require(bundle["boot_id"] == witness["boot"] and bundle["candidate_blob"] == PIN
            and bundle["can_execute"] is False and bundle["records_hex"] ==
            [guard.protected_bytes(guard.EXT / name).hex() for name in guard.RECORD_NAMES[:2]],
            "archived original record mismatch")
    require(prepared == canonical_bytes({"version":1,"state":"PREPARED",
            "archive_sha256":witness["archive"],"boot_id":witness["boot"],
            "can_execute":False,"can_clear":False}), "prepared binding mismatch")
    actual = {"identity":[guard.identity(guard.BASE)[1:],guard.identity(guard.EXTRA)[1:]],
              "fence_inode":fence_identity(guard, prepared)[1],"swap":signature(guard)}
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
    verify_refusal(guard, prepared)
    require(guard.digest_file(ARCHIVE) == witness["archive"], "archive changed during refusals")
    print("CPU_MEM_EXTFENCE_PASS // REAL_ARCHIVE_AND_PREPARED_RETAINED", flush=True)
    require(guard.history()==witness["history"]
            and [guard.digest_file(guard.EXT / name) for name in guard.RECORD_NAMES[:2]]
            == witness["records"] and signature(guard)==witness["swap"],
            "reboot or refusal changed recovery evidence")
    print("CPU_MEM_EXTFENCE_PASS // NEW_BOOT_EXTERNAL_FENCE_AND_RECORDS_RETAINED_NO_REPLAY",flush=True)

def physical_trial(guard):
    # ONLY a fresh independent allocation in this offline CI guest.
    # Never touch managed base/extension, recovery archive or fence.
    require(guard.protected_bytes(Path("/etc/postapollo-memory-native-physical-reclaim-ci-only")).strip()
            == b"DISPOSABLE_CPU_MEMORY_PHYSICAL_RECLAIM_V1", "physical fixture marker absent")
    witness = json.loads(guard.protected_bytes(WITNESS))
    require(guard.boot_id() != witness["boot"], "reboot prerequisite absent")
    trial = Path("/var/lib/postapollo-memory-ci-reclaim-only")
    path = trial / "swapfile"
    receipt = Path("/var/lib/postapollo-memory-ci-reclaim-result.json")
    require(not os.path.lexists(trial) and not os.path.lexists(receipt), "trial already exists")
    guard.verify_swap(False)
    before = signature(guard)
    history = guard.history()
    records = [guard.digest_file(guard.EXT / name) for name in guard.RECORD_NAMES[:2]]
    identities = [guard.identity(guard.BASE),guard.identity(guard.EXTRA)]
    custody = [guard.digest_file(ARCHIVE),guard.digest_file(PREPARED)]
    fence = fence_identity(guard,witness["prepared"].encode("ascii"))
    parent = trial.parent
    module = load_candidate(guard)
    mount, fs = module.mount_info()
    require(fs == "btrfs" and mount in ("/", "/var", "/var/lib"),
            "trusted Btrfs mount unavailable")
    require(os.stat(mount).st_dev == parent.stat().st_dev,
            "trial parent differs from filesystem mount")
    btrfs = "/usr/bin/btrfs"
    def command(*args):
        import subprocess
        try:
            return guard.command(btrfs,*map(str,args)).strip()
        except subprocess.CalledProcessError as exc:
            print("CPU_MEM_EXTFENCE_DIAG // " + json.dumps({
                "command":list(exc.cmd),"returncode":exc.returncode,
                "stderr":str(exc.stderr)[:1000]},sort_keys=True),flush=True)
            raise RuntimeError("fixture Btrfs command failed") from exc
    def rootid(target):
        value = command("inspect-internal","rootid",target)
        require(re.fullmatch(r"[1-9][0-9]*",value) is not None,"root ID unverified")
        return int(value)
    def usage():
        command("filesystem","sync",mount)
        output = command("filesystem","usage","--raw",mount)
        totals = re.findall(r"(?m)^\s*Used:\s*(\d+)\s*$",output)
        require(len(totals)==1,"Btrfs used bytes unavailable")
        v=os.statvfs(parent)
        return {"used":int(totals[0]),"available":v.f_bavail*v.f_frsize}
    def unchanged():
        require(signature(guard)==before and guard.history()==history
                and [guard.identity(guard.BASE),guard.identity(guard.EXTRA)]==identities
                and [guard.digest_file(guard.EXT / n) for n in guard.RECORD_NAMES[:2]]==records
                and [guard.digest_file(ARCHIVE),guard.digest_file(PREPARED)]==custody
                and fence_identity(guard,witness["prepared"].encode("ascii"))==fence,
                "managed swap or custody changed")
    def inactive(identity):
        require(str(path) not in guard.rows(),"trial is active")
        for name,(kind,*_) in guard.rows().items():
            if kind=="file":
                s=os.stat(name)
                require((s.st_dev,s.st_ino)!=identity,"active swap alias")
    require(re.findall(r"Total devices\s+(\d+)\b",command("filesystem","show","--raw",mount))==["1"],
            "not single-device Btrfs")
    baseline=usage()
    print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps({"mount":mount,"baseline":baseline},sort_keys=True),flush=True)
    command("subvolume","create",trial)
    trial.chmod(0o700)
    command("filesystem","mkswapfile","--size","1G",path)
    path.chmod(0o600)
    command("inspect-internal","map-swapfile",path)
    root=rootid(trial)
    require(rootid(path)==root and rootid(parent)!=root and rootid(guard.BASE)!=root
            and rootid(guard.EXTRA)!=root,"trial root identity mismatch")
    fd=os.open(trial,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        d=os.fstat(fd)
        s=os.stat("swapfile",dir_fd=fd,follow_symlinks=False)
        identity=(s.st_dev,s.st_ino)
        require(stat.S_ISDIR(d.st_mode) and d.st_uid==0 and d.st_ino==256
                and not d.st_mode&0o077 and stat.S_ISREG(s.st_mode) and s.st_uid==0
                and s.st_nlink==1 and not s.st_mode&0o077 and s.st_size==guard.GIB
                and s.st_blocks*512>=guard.GIB//2
                and set(os.listdir(fd))=={"swapfile"},"trial allocation unverified")
        allocated=usage()
        print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps({"allocated":allocated},sort_keys=True),flush=True)
        require(allocated["used"]-baseline["used"]>=guard.GIB//2
                and baseline["available"]-allocated["available"]>=guard.GIB//2,
                "physical allocation accounting insufficient")
        unchanged()
        inactive(identity)
        now=os.stat("swapfile",dir_fd=fd,follow_symlinks=False)
        named=trial.lstat()
        require((now.st_dev,now.st_ino,now.st_size,now.st_nlink)==
                (s.st_dev,s.st_ino,s.st_size,s.st_nlink)
                and (named.st_dev,named.st_ino)==(d.st_dev,d.st_ino)
                and rootid(trial)==root,"trial identity changed")
        # The only file deletion is the fixed never-activated CI allocation.
        os.unlink("swapfile",dir_fd=fd)
        os.fsync(fd)
        # A fresh directory description is needed for Btrfs enumeration.
        fresh=os.open(trial,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            f=os.fstat(fresh)
            require((f.st_dev,f.st_ino)==(d.st_dev,d.st_ino) and not os.listdir(fresh),
                    "trial not empty or replaced")
            require(not os.path.lexists(path) and rootid(trial)==root,"trial identity lost")
        finally:
            os.close(fresh)
        unchanged()
        inactive(identity)
    finally:
        os.close(fd)
    require((trial.lstat().st_dev,trial.lstat().st_ino)==(d.st_dev,d.st_ino)
            and rootid(trial)==root and not list(trial.iterdir()),"empty trial replaced")
    command("subvolume","delete","--commit-after",trial)
    command("subvolume","sync",mount,root)
    released=usage()
    print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps({"released":released},sort_keys=True),flush=True)
    require(not os.path.lexists(trial),"trial directory retained")
    require(allocated["used"]-released["used"]>=guard.GIB//2
            and released["available"]-allocated["available"]>=guard.GIB//2,
            "actual physical release not verified")
    unchanged()
    data={"version":1,"state":"DISPOSABLE_PHYSICAL_RELEASE_VERIFIED","boot":guard.boot_id(),
          "subvolume":root,"allocated_file_bytes":s.st_size,"baseline":baseline,
          "allocated":allocated,"released":released,"can_execute":False,"can_clear":False}
    write_once(guard,receipt,canonical_bytes(data))
    print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps(data,sort_keys=True),flush=True)
    print("CPU_MEM_EXTFENCE_PASS // DISPOSABLE_PHYSICAL_RELEASE_VERIFIED",flush=True)

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
        physical_trial(guard)
    else:
        raise RuntimeError("invalid phase")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        print("CPU_MEM_EXTFENCE_FAIL // "+type(exc).__name__+": "+str(exc),flush=True)
        raise SystemExit(2)
