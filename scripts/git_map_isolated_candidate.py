#!/usr/bin/env python3
"""Disposable v2 namespace admission candidate. No production entrypoint.

Reuse v1 history data layout, but publish only a distinct filename, protocol
marker and salted key under a distinct root. All candidate reads acquire
shared directory custody; no removal, migration, fallback or auto activation.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import uuid

import git_map_history_index as index
import git_map_index_manager as manager
from git_map_reader_candidate import same_directory

ROOT_NAME="post-apollo-git-map-custody-v2"
NAME="history.custody-v2.sqlite3"
PROTOCOL="post-apollo-git-map-custody-v2"
APPLICATION_ID=0x50414332

def key_for(digest):
    if not isinstance(digest,str) or not manager.HEX.fullmatch(digest):
        raise ValueError("invalid roots digest")
    return hashlib.sha256((PROTOCOL+":"+digest).encode("ascii")).hexdigest()

def root_for(base):
    base=Path(base)
    if not base.is_absolute() or base.resolve()!=base:
        raise ValueError("absolute canonical candidate base required")
    return base/ROOT_NAME

def identity(repo):
    repo_id,digest,shallow,_=manager.identity(repo)
    if shallow:
        raise ValueError("shallow history not qualified for candidate v2")
    return repo_id,digest,key_for(digest)

def generation_path(base,repo_id,key):
    if not all(isinstance(x,str) and manager.HEX.fullmatch(x) for x in (repo_id,key)):
        raise ValueError("invalid candidate identity")
    root=root_for(base)
    manager.private_dir(root)
    folder=manager.private_dir(root/repo_id)
    return manager.private_dir(folder/key)

@contextmanager
def read(base,repo_id,key,snapshot=None,*,expected_identity=None,evidence=None,lease_fd=None):
    if snapshot is not None and (not isinstance(snapshot,str) or not index.SNAPSHOT.fullmatch(snapshot)):
        raise ValueError("invalid snapshot")
    path=generation_path(base,repo_id,key)
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        if not same_directory(path,fd) or os.path.lexists(path/index.NAME):
            raise ValueError("mixed or changed candidate generation")
        opened=os.fstat(fd)
        identity=(str(opened.st_dev),str(opened.st_ino))
        if expected_identity is not None and expected_identity!=identity:
            raise ValueError("candidate directory identity changed")
        db=path/NAME
        info=db.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o077 or info.st_nlink!=1):
            raise ValueError("unsafe candidate database")
        conn=sqlite3.connect(db.as_uri()+"?mode=ro&immutable=1",uri=True)
        try:
            conn.row_factory=sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA trusted_schema=OFF")
            if conn.execute("PRAGMA application_id").fetchone()[0]!=APPLICATION_ID:
                raise ValueError("candidate protocol marker missing")
            m=index.manifest_for(conn,snapshot)
            if m["repoId"]!=repo_id or m["shallow"] or key_for(m["rootsDigest"])!=key:
                raise ValueError("candidate manifest identity mismatch")
            if not same_directory(path,fd):
                raise ValueError("candidate directory moved")
            if evidence is not None:
                evidence.update(device=identity[0],inode=identity[1])
            if lease_fd is not None:
                lease_fd.append(fd)
            yield conn,m
        finally: conn.close()
    finally: os.close(fd)

def receipt(base,repo_id,key):
    evidence={}
    with read(base,repo_id,key,evidence=evidence) as (_,m):
        return {"schema":PROTOCOL,"status":"READY","repoId":repo_id,"key":key,
                "directory":str(generation_path(base,repo_id,key)),
                "manifest":m,"reclamationAllowed":False,**evidence}

def lookup(repo,base):
    repo_id,digest,key=identity(repo)
    try: result=receipt(base,repo_id,key)
    except FileNotFoundError:
        # Only a genuinely absent generation is MISSING. A published
        # directory with a missing database is a fault, not a build request.
        try: generation_path(base,repo_id,key)
        except FileNotFoundError:
            result={"schema":PROTOCOL,"status":"MISSING","repoId":repo_id,
                    "key":key,"reclamationAllowed":False}
        else: raise
    if identity(repo)!=(repo_id,digest,key):
        raise ValueError("repository changed during lookup")
    return result

def build(repo,base):
    """Explicit isolated build only; deliberately no CLI or UI wiring."""
    repo_id,digest,key=identity(repo)
    root=root_for(base)
    root.parent.mkdir(parents=True,exist_ok=True)
    manager.private_dir(root,True)
    folder=manager.private_dir(root/repo_id,True)
    lock=os.open(folder/".build.lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1:
            raise ValueError("unsafe build lock")
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if identity(repo)!=(repo_id,digest,key):
            raise ValueError("repository changed before build")
        target=folder/key
        if os.path.lexists(target):
            return lookup(repo,base)
        count=0
        with os.scandir(folder) as items:
            for item in items:
                if item.name==".build.lock":
                    continue
                count+=1
                if count>=manager.MAX_GENERATIONS:
                    return {"schema":PROTOCOL,"status":"CACHE LIMIT","repoId":repo_id,
                            "key":key,"reclamationAllowed":False}
        stage=folder/(".candidate-"+uuid.uuid4().hex)
        m=index.build(repo,stage)
        if m["repoId"]!=repo_id or m["rootsDigest"]!=digest or m["shallow"]:
            raise ValueError("staged identity mismatch")
        # Change the protocol marker only in the unpublished private stage.
        # The legacy filename never exists in a published v2 generation.
        conn=sqlite3.connect(stage/index.NAME)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA application_id="+str(APPLICATION_ID))
            conn.commit()
        finally: conn.close()
        os.rename(stage/index.NAME,stage/NAME)
        with (stage/NAME).open("rb") as file: os.fsync(file.fileno())
        fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)
        if identity(repo)!=(repo_id,digest,key) or os.path.lexists(target):
            raise ValueError("candidate publication refused")
        os.rename(stage,target)
        fd=os.open(folder,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)
        return receipt(base,repo_id,key)
    finally: os.close(lock)
