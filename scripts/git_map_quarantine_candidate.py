"""Disposable explicit V2 quarantine. No deletion or production entrypoint."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import sqlite3
import stat

import git_map_history_index as index
import git_map_index_manager as manager
import git_map_isolated_candidate as v2
from git_map_reader_candidate import same_directory

@contextmanager
def locked_folder(repo,base):
    if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
        raise ValueError("disposable qualification only")
    ident=v2.identity(repo)
    folder=manager.private_dir(manager.private_dir(v2.root_for(base))/ident[0])
    fd=os.open(folder/".build.lock",os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_nlink!=1:
            raise ValueError("unsafe build lock")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if v2.identity(repo)!=ident:
            raise ValueError("repository changed")
        yield ident,folder
    finally: os.close(fd)

def validate(path,fd,repo_id,key,snapshot,expected):
    s=os.fstat(fd)
    if not same_directory(path,fd) or (str(s.st_dev),str(s.st_ino))!=expected:
        raise ValueError("generation identity changed")
    if set(os.listdir(fd))!={v2.NAME}:
        raise ValueError("unexpected generation contents")
    db=path/v2.NAME
    info=db.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_nlink!=1:
        raise ValueError("unsafe database")
    conn=sqlite3.connect(db.as_uri()+"?mode=ro&immutable=1",uri=True)
    try:
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        if conn.execute("PRAGMA application_id").fetchone()[0]!=v2.APPLICATION_ID:
            raise ValueError("wrong database protocol")
        m=index.manifest_for(conn,snapshot)
        if m["repoId"]!=repo_id or m["shallow"] or v2.key_for(m["rootsDigest"])!=key:
            raise ValueError("wrong generation manifest")
    finally: conn.close()
    if not same_directory(path,fd) or db.lstat()!=info:
        # Ignore atime changes by comparing identity and immutable metadata below.
        now=db.lstat()
        if not same_directory(path,fd) or (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns)!=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns):
            raise ValueError("generation changed")

def move(repo,base,key,snapshot,device,inode,*,restore=False):
    """Explicit reversible rename; caller must supply previously observed identity.
    An interrupted rename is discoverable by deterministic quarantine name.
    No auto recovery or deletion, no claims against noncooperating same-UID writers.
    """
    if not isinstance(key,str) or not manager.HEX.fullmatch(key):
        raise ValueError("invalid key")
    if not isinstance(snapshot,str) or not index.SNAPSHOT.fullmatch(snapshot):
        raise ValueError("invalid snapshot")
    expected=(device,inode)
    if not all(isinstance(x,str) and x.isascii() and x.isdecimal() and len(x)<=20 for x in expected):
        raise ValueError("invalid identity")
    with locked_folder(repo,base) as (ident,folder):
        repo_id,_,current=ident
        if not restore:
            if key==current or v2.lookup(repo,base)["status"]!="READY":
                raise ValueError("current or unavailable generation")
        live=folder/key
        retired=folder/(".retired-"+key)
        source,target=(retired,live) if restore else (live,retired)
        fd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            validate(source,fd,repo_id,key,snapshot,expected)
            if os.path.lexists(target) or v2.identity(repo)!=ident:
                raise ValueError("destination exists or repository changed")
            # Cooperating publishers share the build lock; readers share the
            # original generation inode. No recursive removal, no overwrite.
            os.rename(source,target)
            parent=os.open(folder,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try: os.fsync(parent)
            finally: os.close(parent)
            if not same_directory(target,fd):
                raise ValueError("rename disposition unknown; inspect quarantine")
            return {"status":"RESTORED" if restore else "QUARANTINED",
                    "repoId":repo_id,"key":key,"snapshot":snapshot,"device":device,
                    "inode":inode,"directory":str(target),"reclamationAllowed":False}
        finally: os.close(fd)
