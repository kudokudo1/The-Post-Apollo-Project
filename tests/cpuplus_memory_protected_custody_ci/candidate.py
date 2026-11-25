"""Uninstalled protected custody writer candidate, no CLI or caller.

No deletion, release/clearance, replay, swap commands, or authorization. Future
trusted integration must verify the installed helper and retire legacy entrypoints.
The candidate is source-only; do not invoke on a workstation.
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

def prepare_candidate():
    """Unrouted candidate. Do not install/invoke until separate review.

    Archive presence now fences all subsequent common-lock admissions, even
    without PREPARED. The original writer retains its already-acquired lock
    while reobserving and publishing the separate fence. Never reuse or clear.
    """
    helper = load_verified_helper()
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
                finally:
                    os.close(child)
                return {"state":"PREPARED_REVIEW_REQUIRED","can_execute":False,"can_clear":False}
            finally:
                os.close(extfd)
        finally:
            os.close(fd)
