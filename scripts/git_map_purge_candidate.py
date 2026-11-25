"""Disposable V2 purge candidate; explicit confirmation and recovery only."""
import fcntl
import os
import re

import git_map_history_index as index
import git_map_index_manager as manager
import git_map_isolated_candidate as v2
import git_map_quarantine_candidate as q
from git_map_reader_candidate import same_directory

def purge(repo,base,key,snapshot,device,inode,*,confirmation,recover=False):
    if confirmation!="PURGE" or type(recover) is not bool:
        raise ValueError("explicit purge confirmation required")
    if not isinstance(key,str) or not manager.HEX.fullmatch(key):
        raise ValueError("invalid generation key")
    if not isinstance(snapshot,str) or not index.SNAPSHOT.fullmatch(snapshot):
        raise ValueError("invalid snapshot")
    expected=(device,inode)
    if not all(isinstance(x,str) and re.fullmatch(r"0|[1-9][0-9]{0,19}",x) for x in expected):
        raise ValueError("invalid generation identity")
    with q.locked_folder(repo,base) as (ident,folder):
        repo_id,_,current=ident
        retired=folder/(".retired-"+key)
        pending=folder/(".purging-"+key+"-"+snapshot+"-"+device+"-"+inode)
        live=folder/key
        def still_obsolete():
            if (key==current or os.path.lexists(live) or v2.identity(repo)!=ident
                    or v2.lookup(repo,base)["status"]!="READY"):
                raise ValueError("current, rebuilt or unavailable generation")
        still_obsolete()
        # Refuse ambiguous transactions for the same generation.
        matches=list(folder.glob(".purging-"+key+"-*"))
        if recover:
            if os.path.lexists(retired) or matches!=[pending]:
                raise ValueError("no unique matching interrupted purge; inspect")
            source=pending
        else:
            if matches:
                raise ValueError("interrupted purge requires explicit recovery")
            source=retired
        parent=os.open(folder,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            fd=os.open(source.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                def named(path):
                    st=os.fstat(fd)
                    if not same_directory(folder,parent) or not same_directory(path,fd) or (str(st.st_dev),str(st.st_ino))!=expected:
                        raise ValueError("purge identity changed")
                named(source)
                entries=set(os.listdir(fd))
                if entries=={v2.NAME}:
                    q.validate(source,fd,repo_id,key,snapshot,expected)
                elif not recover or entries:
                    raise ValueError("unexpected purge contents")
                if not recover:
                    still_obsolete()
                    named(source)
                    if os.path.lexists(pending):
                        raise ValueError("purge destination exists")
                    os.rename(source.name,pending.name,src_dir_fd=parent,dst_dir_fd=parent)
                    os.fsync(parent)
                named(pending)
                still_obsolete()
                if set(os.listdir(fd))!=entries:
                    raise ValueError("purge contents changed")
                if entries:
                    q.validate(pending,fd,repo_id,key,snapshot,expected)
                    still_obsolete()
                    named(pending)
                    # Only the single validated derived SQLite file; never recurse.
                    os.unlink(v2.NAME,dir_fd=fd)
                os.fsync(fd)
                named(pending)
                if os.listdir(fd):
                    raise ValueError("purge directory not empty")
                still_obsolete()
                os.rmdir(pending.name,dir_fd=parent)
                os.fsync(parent)
                return {"status":"PURGED","repoId":repo_id,"key":key,
                        "snapshot":snapshot,"device":device,"inode":inode,
                        "reclamationAllowed":False}
            finally: os.close(fd)
        finally: os.close(parent)
