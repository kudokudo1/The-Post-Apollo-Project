"""Uninstalled read-only observer. No CLI, authorization or mutation path.

Trusted integration must supply the exact helper loaded by #2798's verified
loader and establish this module's integrity. The helper dependency is not
a public caller interface. The observation never authorizes an effect.
"""
import fcntl
import os
from pathlib import Path
import re
import stat
import subprocess
from contextlib import contextmanager
from observation import classify, result, NAMES, LIMIT

PARENT=Path("/var/lib")
EXT=PARENT/"post-apollo-memory-extension"
BASE=PARENT/"post-apollo-memory-swap"/"swapfile"
ARCHIVE=PARENT/"post-apollo-memory-reclaim-archive.json"
FENCE=PARENT/"post-apollo-memory-reclaim"
LOCK=Path("/run/post-apollo-memory.lock")

class Unverified(RuntimeError):
    pass

def require(ok):
    if not ok:
        raise Unverified("protected observation unavailable")

def metadata(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def trusted(s,private=False,kind=stat.S_ISDIR):
    require(kind(s.st_mode) and s.st_uid==0 and not s.st_mode & (0o077 if private else 0o022))
    if kind is stat.S_ISREG:
        require(s.st_nlink==1)

def named(fd,name):
    try:
        return os.stat(name,dir_fd=fd,follow_symlinks=False)
    except FileNotFoundError:
        return None

@contextmanager
def child_dir(fd,name):
    before=named(fd,name)
    require(before is not None)
    trusted(before,private=True)
    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
    try:
        actual=os.fstat(child)
        trusted(actual,private=True)
        require(metadata(actual)==metadata(before))
        yield child
        final=named(fd,name)
        require(final is not None and metadata(final)==metadata(actual)
                and metadata(os.fstat(child))==metadata(actual))
    finally:
        os.close(child)

def raw_record(fd,name,limit):
    before=named(fd,name)
    if before is None:
        return None,None
    trusted(before,private=True,kind=stat.S_ISREG)
    require(0<before.st_size<=limit)
    item=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=fd)
    try:
        actual=os.fstat(item)
        trusted(actual,private=True,kind=stat.S_ISREG)
        require(metadata(actual)==metadata(before))
        with os.fdopen(item,"rb",closefd=False) as stream:
            data=stream.read(limit+1)
        final=named(fd,name)
        require(len(data)==actual.st_size and final is not None
                and metadata(os.fstat(item))==metadata(actual)==metadata(final))
        return data,metadata(actual)
    finally:
        os.close(item)

@contextmanager
def shared_existing_lock():
    """Never create, chmod, remove or unlock a lock belonging to another actor."""
    require(os.geteuid()==0)
    trusted(LOCK.parent.lstat())
    fd=os.open(LOCK,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        actual=os.fstat(fd)
        trusted(actual,private=True,kind=stat.S_ISREG)
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        require(metadata(LOCK.lstat())==metadata(actual))
        yield
        require(metadata(LOCK.lstat())==metadata(os.fstat(fd))==metadata(actual))
    finally:
        os.close(fd)

def capture(helper,fd):
    boot=helper.current_boot_id()
    archive,archive_id=raw_record(fd,ARCHIVE.name,LIMIT)
    fence_info=named(fd,FENCE.name)
    extension_info=named(fd,EXT.name)
    args={"archive_presence":"ABSENT" if archive is None else "PRESENT",
          "archive_raw":archive,"fence_presence":"ABSENT" if fence_info is None else "PRESENT",
          "fence_names":None,"prepared_raw":None,"boot_id":boot,
          "extension_presence":"ABSENT" if extension_info is None else "PRESENT"}
    ids=[archive_id,None if fence_info is None else metadata(fence_info),
         None if extension_info is None else metadata(extension_info)]
    if fence_info is not None:
        with child_dir(fd,FENCE.name) as child:
            names=sorted(os.listdir(child))
            args["fence_names"]=names
            if "prepared.json" in names:
                args["prepared_raw"],marker_id=raw_record(child,"prepared.json",16384)
                require(marker_id is not None)
                ids.append(marker_id)
    if extension_info is not None:
        with child_dir(fd,EXT.name) as child:
            names=sorted(os.listdir(child))
            args["directory_names"]=names
            if set(names)==NAMES:
                identity=helper.extension_identity()
                st=os.fstat(child)
                require((st.st_dev,st.st_ino)==tuple(identity[2][:2]))
                records=[raw_record(child,name,16384) for name in ("withdrawal.json","withdrawal-result.json")]
                require(all(meta is not None for _,meta in records))
                ids.extend(meta for _,meta in records)
                args["records_raw"]=[raw for raw,_ in records]
                args["identity"]=[list(row) for row in identity]
                mount,fs=helper.mount_info()
                require(fs=="btrfs" and re.findall(r"Total devices\s+(\d+)\b",
                    helper.run("/usr/bin/btrfs","filesystem","show","--raw",mount))==["1"])
                def rootid(path):
                    value=helper.run("/usr/bin/btrfs","inspect-internal","rootid",str(path)).strip()
                    require(re.fullmatch(r"[1-9][0-9]*",value) is not None)
                    return int(value)
                root=rootid(EXT)
                require(rootid(EXT/"swapfile")==root and rootid(BASE)!=root and rootid(PARENT)!=root)
                args["subvolume_id"]=root
                helper.check_extension_boot_policy()
                snapshot=helper.read_reduction_snapshot()
                for path,row in snapshot["rows"].items():
                    if row["kind"]=="file":
                        item=os.stat(path)
                        require(stat.S_ISREG(item.st_mode)
                                and (item.st_dev,item.st_ino)!=tuple(identity[3][:2]))
                args["snapshot"]={"rows":snapshot["rows"]}
    require(helper.current_boot_id()==boot)
    return args,ids

def stable(args):
    # Occupancy is deliberately not treated as swap configuration identity.
    value=dict(args)
    if value.get("snapshot") is not None:
        value["snapshot"]={p:[r["kind"],r["sizeKiB"],r["priority"]]
                           for p,r in value["snapshot"]["rows"].items()}
    return value

def inspect_candidate(helper):
    """Internal read-only seam; not a production command or a trust decision."""
    try:
        require((helper.PARENT,helper.EXT_DIRECTORY,helper.SWAPFILE,helper.RECLAIM_ARCHIVE,
                 helper.RECLAIM_FENCE,helper.LOCK)==(PARENT,EXT,BASE,ARCHIVE,FENCE,LOCK))
        with shared_existing_lock():
            helper.secure_parent()
            fd=os.open(PARENT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:
                actual=os.fstat(fd)
                trusted(actual)
                first,ids=capture(helper,fd)
                second,ids2=capture(helper,fd)
                require(stable(first)==stable(second) and ids==ids2)
                require(metadata(PARENT.lstat())==metadata(os.fstat(fd))==metadata(actual))
                observed=classify(helper,**second)
            finally:
                os.close(fd)
        return observed
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RuntimeError,subprocess.SubprocessError):
        return result("PROTECTED_OBSERVATION_UNVERIFIED")
