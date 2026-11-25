#!/usr/bin/env python3
"""Explicitly reuse/build a private derived Git-map cache. Never mutate Git."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import uuid

# -I intentionally excludes the script directory from sys.path.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import git_map_history_index as index

SCHEMA="post-apollo-git-map-cache-v1"
# V2 retains its original conservative qualification bound. V1 has no
# safe reclamation authority; bounded append-only headroom restores history
# for active repositories without modifying or removing existing generations.
MAX_GENERATIONS=8
V1_MAX_GENERATIONS=64
MAX_INVENTORY_ENTRIES=64
CANDIDATE=re.compile(r"\.candidate-[0-9a-f]{32}")
HEX=re.compile(r"[0-9a-f]{64}")


def private_dir(path,create=False):
    if create:
        path.mkdir(mode=0o700,exist_ok=True)
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError("unsafe cache directory")
    return path


def cache_root():
    raw=os.environ.get("XDG_CACHE_HOME","")
    base=Path(raw) if raw and Path(raw).is_absolute() else Path.home()/".cache"
    return base/"post-apollo-git-map-v1"


def identity(repo):
    repo=Path(repo).resolve(strict=True)
    common=index.git_output(repo,"rev-parse","--path-format=absolute","--git-common-dir").strip()
    repo_id=hashlib.sha256(common).hexdigest()
    roots=index.roots_for(repo)
    roots_digest=hashlib.sha256("\n".join(roots).encode("ascii")).hexdigest()
    shallow=index.shallow_for(repo)
    boundary=""
    if shallow:
        # A deepen can change history with unchanged tips and shallow=true.
        raw=index.git_output(repo,"rev-parse","--path-format=absolute","--git-path","shallow").strip()
        path=Path(os.fsdecode(raw))
        if not path.is_absolute():
            raise ValueError("invalid shallow path")
        with path.open("rb") as stream:
            data=stream.read(2_000_001)
        if len(data)>2_000_000:
            raise ValueError("shallow boundary exceeds bound")
        boundary=hashlib.sha256(data).hexdigest()
    key=hashlib.sha256((roots_digest+":"+str(shallow)+":"+boundary).encode("ascii")).hexdigest()
    return repo_id,roots_digest,shallow,key


def receipt(path,ident,status):
    repo_id,roots_digest,shallow,key=ident
    result={"schema":SCHEMA,"status":status,"repoId":repo_id,"key":key}
    if status=="READY":
        private_dir(path)
        with index.open_index(path) as conn:
            m=index.manifest_for(conn)
        conn.close()
        if (m.get("repoId")!=repo_id or m.get("rootsDigest")!=roots_digest
                or m.get("shallow") is not shallow or type(m.get("maxLane")) is not int
                or not 0<=m["maxLane"]<index.MAX_LANES):
            raise ValueError("index identity mismatch")
        result.update(directory=str(path),manifest=m)
    return result


def lookup(repo,root):
    ident=identity(repo)
    folder=root/ident[0]
    target=folder/ident[3]
    for path in (root,folder,target):
        try:
            private_dir(path)
        except FileNotFoundError:
            return receipt(target,ident,"MISSING")
    result=receipt(target,ident,"READY")
    if identity(repo)!=ident:
        raise ValueError("repository changed during lookup")
    return result


def build(repo,root):
    # Only BUILD can create cache directories or start a history traversal.
    ident=identity(repo)
    root.parent.mkdir(parents=True,exist_ok=True)
    private_dir(root,True)
    folder=private_dir(root/ident[0],True)
    lock=os.open(folder/".build.lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(lock)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o077 or info.st_nlink!=1):
            raise ValueError("unsafe cache lock")
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if identity(repo)!=ident:
            raise ValueError("repository changed before build")
        target=folder/ident[3]
        try:
            private_dir(target)
        except FileNotFoundError:
            pass
        else:
            return receipt(target,ident,"READY")
        count=0
        with os.scandir(folder) as entries:
            for item in entries:
                if item.name==".build.lock":
                    continue
                count+=1
                if count>=V1_MAX_GENERATIONS:
                    return receipt(target,ident,"CACHE LIMIT")
        stage=folder/(".candidate-"+uuid.uuid4().hex)
        m=index.build(repo,stage)
        if (identity(repo)!=ident or m.get("repoId")!=ident[0]
                or m.get("rootsDigest")!=ident[1] or m.get("shallow") is not ident[2]):
            raise ValueError("repository changed during build")
        # Cooperating writers share the lock. Completed index is published
        # as a new directory; no previously published index is overwritten.
        if os.path.lexists(target):
            raise ValueError("cache target already exists")
        os.rename(stage,target)
        fd=os.open(folder,os.O_DIRECTORY|os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return receipt(target,ident,"READY")
    finally:
        os.close(lock)



def inventory(repo,root):
    """Bounded observation of derived generation files; never authorize removal."""
    ident=identity(repo)
    repo_id,roots_digest,shallow,key=ident
    folder=root/repo_id
    result={"schema":"post-apollo-git-map-inventory-v1","repoId":repo_id,
            "currentKey":key,"generationLimit":V1_MAX_GENERATIONS,
            "entries":[],"observedSlots":0,"truncated":False,
            "observedDatabaseBytes":0,"readerProtection":"NOT ESTABLISHED",
            "reclamationAllowed":False}
    for path in (root,folder):
        try:
            private_dir(path)
        except FileNotFoundError:
            if identity(repo)!=ident:
                raise ValueError("repository changed during inventory")
            return result
    # This observation does not acquire a lock, create files, or recurse.
    # Concurrent builds may move entries; missing or unsafe metadata is
    # reported conservatively, never interpreted as evidence of inactivity.
    with os.scandir(folder) as items:
        for item in items:
            if item.name==".build.lock":
                continue
            if result["observedSlots"]>=MAX_INVENTORY_ENTRIES:
                result["truncated"]=True
                break
            result["observedSlots"]+=1
            name=item.name
            published=HEX.fullmatch(name) is not None
            staging=CANDIDATE.fullmatch(name) is not None
            entry={"key":name if published or staging else None,
                   "state":"UNKNOWN ENTRY","databaseBytes":None,
                   "readerStatus":"UNKNOWN","reclamationAllowed":False}
            result["entries"].append(entry)
            if not (published or staging):
                continue
            path=folder/name
            try:
                private_dir(path)
                db=path/index.NAME
                if staging:
                    # A staged file may be partial, including SQLite journal
                    # state. Never open or count it as a published index.
                    entry["state"]="STAGING"
                    try:
                        db.lstat()
                    except FileNotFoundError:
                        db=path/".building.sqlite3"
                info=db.lstat()
                if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                        or info.st_mode&0o077 or info.st_nlink!=1):
                    raise ValueError("unsafe generation database")
                entry["databaseBytes"]=info.st_size
                result["observedDatabaseBytes"]+=info.st_size
                if staging:
                    continue
                conn=index.open_index(path)
                try:
                    m=index.manifest_for(conn)
                finally:
                    conn.close()
                if (m.get("repoId")!=repo_id or not isinstance(m.get("rootsDigest"),str)
                        or not HEX.fullmatch(m["rootsDigest"])
                        or type(m.get("shallow")) is not bool
                        or type(m.get("maxLane")) is not int
                        or not 0<=m["maxLane"]<index.MAX_LANES):
                    raise ValueError("generation identity mismatch")
                # For non-shallow generations the directory key can be
                # independently reconstructed. Old shallow keys include a
                # boundary digest not stored in v1 manifests.
                if not m["shallow"]:
                    expected=hashlib.sha256((m["rootsDigest"]+":False:").encode("ascii")).hexdigest()
                    if expected!=name:
                        raise ValueError("generation key mismatch")
                if name==key and (m["rootsDigest"]!=roots_digest or m["shallow"] is not shallow):
                    raise ValueError("current generation mismatch")
                entry.update(state=("CURRENT" if name==key else
                                    "HISTORICAL" if not m["shallow"] else "HISTORICAL SHALLOW UNVERIFIED"),
                             snapshot=m["snapshot"],commits=m["total"])
            except FileNotFoundError:
                entry["state"]="INCOMPLETE OR MOVED"
            except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):
                entry["state"]="UNSAFE OR INVALID"
    if identity(repo)!=ident:
        raise ValueError("repository changed during inventory")
    result["entries"].sort(key=lambda entry:(entry["key"] is None,entry["key"] or ""))
    return result


def main(argv=None):
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("lookup","build","inventory"))
    p.add_argument("repo",type=Path)
    args=p.parse_args(argv)
    try:
        if not args.repo.is_absolute():
            raise ValueError("absolute repository required")
        result={"lookup":lookup,"build":build,"inventory":inventory}[args.action](args.repo,cache_root())
        print(json.dumps(result,ensure_ascii=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error,subprocess.SubprocessError):
        print("Git map cache unavailable; existing Git history preserved.",file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
