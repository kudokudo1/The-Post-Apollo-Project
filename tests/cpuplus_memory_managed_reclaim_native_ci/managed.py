"""CI-only derivative of exact #2798 writer 95af2225.
Only a new offline, disposable Silverblue guest may execute this combined
reclamation trial. No production install, caller, replay or clearance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types

PIN = "9dfd8331445ecf60d3a37ea630d08b1f3f6789a2"
PARENT = Path("/var/lib")
BASE = PARENT / "post-apollo-memory-swap" / "swapfile"
EXT = PARENT / "post-apollo-memory-extension"
EXTRA = EXT / "swapfile"
ARCHIVE = PARENT / "post-apollo-memory-reclaim-archive.json"
FENCE = PARENT / "post-apollo-memory-reclaim"
NAMES = {"swapfile", "withdrawal.json", "withdrawal-result.json"}
LIMIT = 131072

class CustodyRefused(RuntimeError):
    pass

def require(ok, code):
    if not ok:
        raise CustodyRefused(code)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def strict_object(data):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, "DUPLICATE_RECORD_KEY")
            result[k] = v
        return result
    value = json.loads(data, object_pairs_hook=unique)
    require(type(value) is dict, "INVALID_RECORD")
    return value

def absent(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    return False

def secure_dir(fd, private=False):
    s = os.fstat(fd)
    require(stat.S_ISDIR(s.st_mode) and s.st_uid == 0
            and not s.st_mode & (0o077 if private else 0o022), "UNTRUSTED_DIRECTORY")
    return (s.st_dev, s.st_ino)

def directory(path):
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)

def read(fd, name, limit=LIMIT, sync=False, private=True):
    item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    try:
        s = os.fstat(item)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & (0o077 if private else 0o022)
                and s.st_nlink == 1 and 0 < s.st_size <= limit, "UNTRUSTED_RECORD")
        with os.fdopen(item, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        t = os.fstat(item)
        require(len(raw) == s.st_size and
                (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns) ==
                (t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns), "RECORD_CHANGED")
        if sync:
            os.fsync(item)
        return raw
    finally:
        os.close(item)

def write_once(fd, name, data):
    require(0 < len(data) <= LIMIT, "RECORD_SIZE")
    item = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                   0o600, dir_fd=fd)
    try:
        with os.fdopen(item, "wb", closefd=False) as stream:
            require(stream.write(data) == len(data), "SHORT_WRITE")
            stream.flush()
        os.fsync(item)
    finally:
        os.close(item)
    os.fsync(fd)
    require(read(fd, name) == data, "PUBLICATION_READBACK")

def load_verified_helper():
    # Fixed installed path, never accept a caller module or arbitrary source.
    require(os.geteuid() == 0, "ROOT_REQUIRED")
    path = Path("/usr/local/sbin/post-apollo-memory-add-swap")
    # Resolve the fixed install path, then verify all canonical ancestors.
    # Installer custody must independently establish the canonical path
    # (including Silverblue's /usr/local mapping) before any real integration.
    resolved = path.resolve(strict=True)
    for ancestor in reversed(resolved.parents):
        fd = directory(ancestor)
        try:
            secure_dir(fd)
        finally:
            os.close(fd)
    parent = directory(resolved.parent)
    try:
        secure_dir(parent)
        raw = read(parent, resolved.name, limit=262144, private=False)
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(blob == PIN, "HELPER_BLOB_MISMATCH")
    finally:
        os.close(parent)
    # Execute exactly the captured, hash-verified bytes, never reopen the
    # source or trust a caller-provided module. Fixed trusted release/installer
    # and candidate's own integrity remain separate prerequisites.
    helper = types.ModuleType("postapollo_verified_memory_helper")
    helper.__file__ = str(path)
    exec(compile(raw,str(path),"exec",dont_inherit=True),helper.__dict__)
    require((helper.PARENT,helper.SWAPFILE,helper.EXT_DIRECTORY,helper.EXT_FILE,
             helper.RECLAIM_FENCE,helper.RECLAIM_ARCHIVE) ==
            (PARENT,BASE,EXT,EXTRA,FENCE,ARCHIVE),"FIXED_PATH_MISMATCH")
    helper.secure_parent()
    return helper

def observe(helper, fd, extfd):
    require(helper._mutation_fd is not None, "HELPER_LOCK_REQUIRED")
    helper.check_external_reclaim_fence()
    return observe_locked(helper,fd,extfd)

def observe_locked(helper,fd,extfd):
    require(helper._mutation_fd is not None, "HELPER_LOCK_REQUIRED")
    helper.check_extension_boot_policy()
    boot = helper.current_boot_id()
    identity = helper.extension_identity()
    require(secure_dir(extfd, private=True) == tuple(identity[2][:2])
            and set(os.listdir(extfd)) == NAMES, "EXTENSION_IDENTITY_OR_CONTENTS")
    mount, fs = helper.mount_info()
    require(fs == "btrfs" and re.findall(r"Total devices\s+(\d+)\b",
            helper.run("/usr/bin/btrfs","filesystem","show","--raw",mount)) == ["1"],
            "UNSUPPORTED_BTRFS")
    def rootid(path):
        value = helper.run("/usr/bin/btrfs","inspect-internal","rootid",str(path)).strip()
        require(re.fullmatch(r"[1-9][0-9]*",value) is not None, "ROOTID_UNVERIFIED")
        return int(value)
    root = rootid(EXT)
    require(identity[2][1] == 256 and rootid(EXTRA) == root and rootid(BASE) != root
            and rootid(PARENT) != root, "SUBVOLUME_MISMATCH")
    snapshot = helper.read_reduction_snapshot()
    for path, row in snapshot["rows"].items():
        if row["kind"] == "file":
            s = os.stat(path)
            require(stat.S_ISREG(s.st_mode) and (s.st_dev,s.st_ino) != tuple(identity[3][:2]),
                    "ACTIVE_FILE_ALIAS")
    raw = [read(extfd,name,16384) for name in ("withdrawal.json","withdrawal-result.json")]
    intent, outcome = [strict_object(item) for item in raw]
    witness = helper.withdrawal_boot_witness(intent,outcome,identity,snapshot,boot)
    require(witness == {"version":1,"boot_id":boot,
            "withdrawal_digest":digest(canonical([intent,outcome])[:-1])}, "WITHDRAWAL_UNVERIFIED")
    require(helper.current_boot_id() == boot and helper.extension_identity() == identity
            and [read(extfd,name,16384) for name in ("withdrawal.json","withdrawal-result.json")] == raw
            and set(os.listdir(extfd)) == NAMES, "OBSERVATION_CHANGED")
    require(secure_dir(fd) == (PARENT.lstat().st_dev,PARENT.lstat().st_ino), "PARENT_CHANGED")
    return {"version":1,"state":"ARCHIVE_CUSTODY","candidate_blob":PIN,
            "boot_id":boot,"identity":[list(row) for row in identity],"subvolume_id":root,
            "records_hex":[item.hex() for item in raw],"withdrawal_witness":witness,
            "swap":{p:[v["kind"],v["sizeKiB"],v["priority"]] for p,v in snapshot["rows"].items()},
            "can_execute":False,"can_clear":False}

RESULT = PARENT / "postapollo-memory-ci-managed-reclaim-result.json"

def fixture_guard(helper):
    require(os.geteuid()==0 and Path("/run/ostree-booted").is_file(),"NOT_DISPOSABLE_GUEST")
    for name,expected in (
        ("postapollo-memory-ci-only",b"DISPOSABLE_CPU_MEMORY_NATIVE_V1"),
        ("postapollo-memory-native-fault-ci-only",b"DISPOSABLE_CPU_MEMORY_FAULT_V1"),
        ("postapollo-memory-native-protected-custody-ci-only",b"DISPOSABLE_CPU_MEMORY_PROTECTED_CUSTODY_V1"),
        ("postapollo-memory-native-managed-reclaim-ci-only",b"DISPOSABLE_CPU_MEMORY_MANAGED_RECLAIM_V1")):
        d=directory(Path("/etc"))
        try:
            secure_dir(d)
            require(read(d,name,128).strip()==expected,"MISSING_DISPOSABLE_MARKER")
        finally:
            os.close(d)
    require(helper.run("/usr/bin/systemd-detect-virt","--vm").strip() in ("kvm","qemu")
            and helper.run("/usr/sbin/getenforce").strip()=="Enforcing","NOT_ISOLATED_ENFORCING_GUEST")

def reclaim_locked(helper,fd,extfd,child,evidence,archive,marker,fence_identity):
    """Run only in the original writer lock, after durable PREPARED."""
    fixture_guard(helper)
    require(helper._mutation_fd is not None,"HELPER_LOCK_REQUIRED")
    boot=evidence["boot_id"]
    old=evidence["identity"]
    root=evidence["subvolume_id"]
    mount,fs=helper.mount_info()
    require(fs=="btrfs" and old[3][2]==4*helper.GIB,"FIXTURE_CAPACITY_OR_MOUNT")
    require(absent(fd,RESULT.name),"FIXTURE_RESULT_EXISTS")
    def command(*args):
        return helper.run("/usr/bin/btrfs",*map(str,args)).strip()
    def rootid(path):
        value=command("inspect-internal","rootid",path)
        require(re.fullmatch(r"[1-9][0-9]*",value) is not None,"ROOTID_UNVERIFIED")
        return int(value)
    def usage():
        command("filesystem","sync",mount)
        values=re.findall(r"(?m)^\s*Used:\s*(\d+)\s*$",command("filesystem","usage","--raw",mount))
        require(len(values)==1,"PHYSICAL_ACCOUNTING_UNVERIFIED")
        v=os.statvfs(PARENT)
        return {"used":int(values[0]),"available":v.f_bavail*v.f_frsize}
    def history():
        # Read-only history custody; fixed qualified fixture has exactly two cycles.
        path=PARENT/"post-apollo-memory-history"
        d=directory(path)
        try:
            secure_dir(d,private=True)
            names=sorted(os.listdir(d))
            require(len(names)==2 and all(re.fullmatch(r"cycle-[a-f0-9]{64}\.json",n) for n in names),
                    "FIXTURE_HISTORY_UNVERIFIED")
            return {n:digest(read(d,n)) for n in names}
        finally:
            os.close(d)
    old_history=history()
    def common():
        require(helper._mutation_fd is not None and helper.current_boot_id()==boot,
                "LOCK_OR_BOOT_CHANGED")
        helper.secure_parent()
        helper.trusted_swap_file()
        helper.check_extension_boot_policy()
        for path,row in zip((BASE.parent,BASE),old[:2]):
            s=path.lstat()
            require([s.st_dev,s.st_ino,s.st_size if path==BASE else 0]==row,"BASE_CHANGED")
        require(rootid(BASE)!=root and rootid(PARENT)!=root,"BASE_ROOT_CHANGED")
        require(secure_dir(fd)==(PARENT.lstat().st_dev,PARENT.lstat().st_ino),"PARENT_CHANGED")
        f=os.stat(FENCE.name,dir_fd=fd,follow_symlinks=False)
        require((f.st_dev,f.st_ino)==fence_identity==secure_dir(child,private=True)
                and read(child,"prepared.json")==marker and read(fd,ARCHIVE.name)==archive,
                "CUSTODY_CHANGED")
        snap=helper.read_reduction_snapshot()
        require({p:[r["kind"],r["sizeKiB"],r["priority"]] for p,r in snap["rows"].items()}
                ==evidence["swap"],"ACTIVE_SWAP_CHANGED")
        for path,row in snap["rows"].items():
            if row["kind"]=="file":
                s=os.stat(path)
                require((s.st_dev,s.st_ino)!=tuple(old[3][:2]),"ACTIVE_FILE_ALIAS")
        require(history()==old_history,"HISTORY_CHANGED")
    def names_now():
        d=os.open(EXT.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
        try:
            require(secure_dir(d,private=True)==tuple(old[2][:2]),"EXTENSION_REPLACED")
            return set(os.listdir(d))
        finally:
            os.close(d)
    def extension(expected_names):
        named=os.stat(EXT.name,dir_fd=fd,follow_symlinks=False)
        require((named.st_dev,named.st_ino)==tuple(old[2][:2])
                ==secure_dir(extfd,private=True) and rootid(EXT)==root
                and names_now()==expected_names,"EXTENSION_CHANGED")
    common()
    require(observe_locked(helper,fd,extfd)==evidence,"POST_PREPARED_OBSERVATION_CHANGED")
    before=usage()
    common()
    require(observe_locked(helper,fd,extfd)==evidence,"PRE_EFFECT_OBSERVATION_CHANGED")
    remaining=set(NAMES)
    for name,record in zip(("withdrawal.json","withdrawal-result.json"),evidence["records_hex"]):
        require(read(extfd,name,16384)==bytes.fromhex(record),"WITHDRAWAL_RECORD_CHANGED")
    s=os.stat("swapfile",dir_fd=extfd,follow_symlinks=False)
    require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and not s.st_mode&0o077
            and [s.st_dev,s.st_ino,s.st_size]==old[3] and s.st_blocks*512>=s.st_size//2,
            "FILE_IDENTITY_OR_ALLOCATION_CHANGED")
    extension(remaining)
    # Fixed inactive extension only. Archive and PREPARED remain outside it.
    os.unlink("swapfile",dir_fd=extfd)
    os.fsync(extfd)
    remaining.remove("swapfile")
    for name,record in zip(("withdrawal.json","withdrawal-result.json"),evidence["records_hex"]):
        common()
        extension(remaining)
        require(read(extfd,name,16384)==bytes.fromhex(record),"WITHDRAWAL_RECORD_CHANGED")
        os.unlink(name,dir_fd=extfd)
        os.fsync(extfd)
        remaining.remove(name)
    common()
    extension(set())
    return before,root,common

def finish_locked(helper,fd,child,evidence,archive,marker,trial):
    before,root,common=trial
    common()
    mount,fs=helper.mount_info()
    require(fs=="btrfs","MOUNT_CHANGED")
    d=os.open(EXT.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
    try:
        require(secure_dir(d,private=True)==tuple(evidence["identity"][2][:2])
                and not os.listdir(d),"EMPTY_EXTENSION_REPLACED")
        require(helper.run("/usr/bin/btrfs","inspect-internal","rootid",str(EXT)).strip()==str(root),
                "EXTENSION_ROOT_CHANGED")
    finally:
        os.close(d)
    common()
    named=os.stat(EXT.name,dir_fd=fd,follow_symlinks=False)
    require((named.st_dev,named.st_ino)==tuple(evidence["identity"][2][:2]),"EXTENSION_REPLACED")
    helper.run("/usr/bin/btrfs","subvolume","delete","--commit-after",str(EXT))
    helper.run("/usr/bin/btrfs","subvolume","sync",mount,str(root))
    helper.run("/usr/bin/btrfs","filesystem","sync",mount)
    values=re.findall(r"(?m)^\s*Used:\s*(\d+)\s*$",helper.run("/usr/bin/btrfs","filesystem","usage","--raw",mount))
    require(len(values)==1,"PHYSICAL_ACCOUNTING_UNVERIFIED")
    v=os.statvfs(PARENT)
    after={"used":int(values[0]),"available":v.f_bavail*v.f_frsize}
    print("CPU_MEM_EXTFENCE_DIAG // "+json.dumps({"before":before,"after":after},sort_keys=True),flush=True)
    require(absent(fd,EXT.name) and before["used"]-after["used"]>=2*helper.GIB
            and after["available"]-before["available"]>=2*helper.GIB,"PHYSICAL_RELEASE_UNVERIFIED")
    common()
    result={"version":1,"state":"DISPOSABLE_MANAGED_RELEASE_VERIFIED","boot_id":evidence["boot_id"],
            "archive_sha256":digest(archive),"prepared_sha256":digest(marker),
            "subvolume_id":root,"file_bytes":evidence["identity"][3][2],"before":before,"after":after,
            "can_execute":False,"can_clear":False}
    write_once(fd,RESULT.name,canonical(result))
    common()
    return result

def prepare_candidate():
    """Unrouted candidate. Do not install/invoke until separate review.

    Archive presence now fences all subsequent common-lock admissions, even
    without PREPARED. The original writer retains its already-acquired lock
    while reobserving and publishing the separate fence. Never reuse or clear.
    """
    helper = load_verified_helper()
    fixture_guard(helper)
    with helper.mutation_lock(inspection=True):
        fd = directory(PARENT)
        try:
            secure_dir(fd)
            require(absent(fd,ARCHIVE.name) and absent(fd,FENCE.name), "EXISTING_CUSTODY")
            extfd = directory(EXT)
            try:
                evidence = observe(helper,fd,extfd)
                archive = canonical(evidence)
                write_once(fd,ARCHIVE.name,archive)
                require(read(fd,ARCHIVE.name,sync=True) == archive,"ARCHIVE_CHANGED")
                os.fsync(fd)
                require(observe(helper,fd,extfd) == evidence
                        and read(fd,ARCHIVE.name) == archive, "EVIDENCE_CHANGED")
                # Fence existence alone blocks current protected helper paths.
                os.mkdir(FENCE.name,0o700,dir_fd=fd)
                os.fsync(fd)
                child = os.open(FENCE.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,
                                dir_fd=fd)
                try:
                    original = secure_dir(child,private=True)
                    marker = canonical({"version":1,"state":"PREPARED",
                        "archive_sha256":digest(archive),"boot_id":evidence["boot_id"],
                        "can_execute":False,"can_clear":False})
                    write_once(child,"prepared.json",marker)
                    s = os.stat(FENCE.name,dir_fd=fd,follow_symlinks=False)
                    # Keep every original post-publication predicate. Report
                    # the exact failing boundary, not sensitive record bytes.
                    actual = (s.st_dev, s.st_ino)
                    require(actual == original,
                            "FENCE_IDENTITY_CHANGED expected=%r actual=%r" % (original, actual))
                    # Btrfs can limit readdir to entries present when a directory
                    # was opened (btrfs_file_private.last_index). The write fd
                    # was opened before PREPARED existed. Open a fresh directory
                    # description AFTER durable publication, through the same
                    # retained parent, and verify it is still the original inode.
                    fresh = os.open(FENCE.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,
                                    dir_fd=fd)
                    try:
                        require(secure_dir(fresh,private=True) == original,
                                "FENCE_REOPEN_IDENTITY_CHANGED")
                        names = set(os.listdir(fresh))
                        require(names == {"prepared.json"},
                                "FENCE_CONTENTS_CHANGED count=%d prepared=%s" %
                                (len(names), "prepared.json" in names))
                        require(read(child,"prepared.json") == marker and
                                read(fresh,"prepared.json") == marker,
                                "PREPARED_READBACK_CHANGED")
                        require(read(fd,ARCHIVE.name) == archive, "ARCHIVE_READBACK_CHANGED")
                        final = os.stat(FENCE.name,dir_fd=fd,follow_symlinks=False)
                        require((final.st_dev,final.st_ino) == original and
                                secure_dir(child,private=True) == original and
                                secure_dir(fresh,private=True) == original,
                                "FENCE_FINAL_IDENTITY_CHANGED")
                    finally:
                        os.close(fresh)
                    trial=reclaim_locked(helper,fd,extfd,child,evidence,archive,marker,original)
                    os.close(extfd)
                    extfd=None
                    return finish_locked(helper,fd,child,evidence,archive,marker,trial)
                finally:
                    os.close(child)
            finally:
                if extfd is not None:
                    os.close(extfd)
        finally:
            os.close(fd)
