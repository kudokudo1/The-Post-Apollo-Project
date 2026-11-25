#!/usr/bin/env python3
"""Exercise an unmodified, pinned pre-lock GitW reader in disposable caches."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2

PIN="489423080aadedeb2a389ebff14b2a8360d812ca"
BLOBS={"git_map_history_index.py":"32b5c8e3bd3dad9a3c627868fc854879277f7f2a",
       "git_map_index_manager.py":"989eed6edd6d0076b869a1811d20d3a1ceb1333b"}

def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),"-c","user.name=Fixture",
        "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)

def fingerprint(root):
    return {str(p.relative_to(root)):(p.stat().st_ino,hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob("*") if p.is_file()}

def main():
    if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
        raise SystemExit("Disposable CI only")
    historical=Path(sys.argv[1]).resolve(strict=True)
    assert git(historical,"rev-parse","HEAD").decode().strip()==PIN
    scripts=historical/"scripts"
    for name,expected in BLOBS.items():
        data=(scripts/name).read_bytes()
        assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==expected,name
    with tempfile.TemporaryDirectory(prefix="gitw-frozen-reader-") as tmp:
        base=Path(tmp).resolve()
        repo=base/"repo"
        repo.mkdir()
        cache=base/"cache"
        cache.mkdir(mode=0o700)
        home=base/"home"
        home.mkdir(mode=0o700)
        env=dict(os.environ,HOME=str(home),XDG_CACHE_HOME=str(cache))
        def old(script,*args):
            return subprocess.run([sys.executable,"-I","-B",str(scripts/script),*map(str,args)],
                env=env,capture_output=True,text=True,timeout=15)
        def accepted(p):
            assert p.returncode==0,p.stderr
            return json.loads(p.stdout)
        git(repo,"init","-b","main")
        git(repo,"commit","--allow-empty","-m","first")
        git(repo,"commit","--allow-empty","-m","second")
        head=git(repo,"rev-parse","HEAD").decode().strip()
        status=git(repo,"status","--porcelain")
        new=v2.build(repo,cache)
        assert new["status"]=="READY" and new["reclamationAllowed"] is False
        new_dir=Path(new["directory"])
        new_before=fingerprint(new_dir)
        manager="git_map_index_manager.py"
        reader="git_map_history_index.py"
        assert accepted(old(manager,"lookup",repo))["status"]=="MISSING"
        assert not (cache/"post-apollo-git-map-v1").exists()
        legacy=accepted(old(manager,"build",repo))
        old_dir=Path(legacy["directory"])
        assert old_dir!=new_dir and legacy["key"]!=new["key"]
        assert accepted(old(manager,"lookup",repo))==legacy
        before=fingerprint(cache)
        for directory,manifest,should_read in ((old_dir,legacy["manifest"],True),
                                                  (new_dir,new["manifest"],False)):
            snap=manifest["snapshot"]
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                for action,args in (("info",()),("page",(snap,"0")),
                    ("locate",(snap,head)),("search",(snap,"first","0"))):
                    p=old(reader,action,directory,*args)
                    if should_read:
                        result=accepted(p)
                        assert result["snapshot"]==snap
                        if action=="page": assert len(result["rows"])==2
                        if action=="locate": assert result["sha"]==head and result["ordinal"]==0
                        if action=="search": assert result["match"]["ordinal"]==1
                    else:
                        assert p.returncode==1 and not p.stdout,(action,p.stdout,p.stderr)
                if should_read:
                    print("GIT_MAP_FROZEN_V1_UNLOCKED_READER_PASS",flush=True)
                else:
                    print("GIT_MAP_FROZEN_V2_DIRECT_REFUSAL_PASS",flush=True)
            finally:
                os.close(fd)
        assert fingerprint(cache)==before
        assert fingerprint(new_dir)==new_before
        assert not (new_dir/"history.sqlite3").exists()
        assert git(repo,"rev-parse","HEAD").decode().strip()==head
        assert git(repo,"status","--porcelain")==status
        with v2.read(cache,new["repoId"],new["key"],new["manifest"]["snapshot"],
                     expected_identity=(new["device"],new["inode"])) as (conn,m):
            assert m["total"]==2
        print("GIT_MAP_FROZEN_COMPATIBILITY_PASS",flush=True)

if __name__=="__main__":
    main()
