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
MAX_GENERATIONS=8
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
                if count>=MAX_GENERATIONS:
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


def main(argv=None):
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("lookup","build"))
    p.add_argument("repo",type=Path)
    args=p.parse_args(argv)
    try:
        if not args.repo.is_absolute():
            raise ValueError("absolute repository required")
        result=(lookup if args.action=="lookup" else build)(args.repo,cache_root())
        print(json.dumps(result,ensure_ascii=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error,subprocess.SubprocessError):
        print("Git map cache unavailable; existing Git history preserved.",file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
