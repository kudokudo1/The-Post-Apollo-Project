#!/usr/bin/env python3
"""Compare actual retained V2 holder processes; not whole-desktop RAM."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2

def main():
    assert os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")=="CI_DISPOSABLE_ONLY"
    with tempfile.TemporaryDirectory(prefix="gitw-compact-") as tmp:
        base=Path(tmp).resolve()
        scripts=base/"scripts"
        scripts.mkdir()
        for name in ("git_map_history_index.py","git_map_index_manager.py","git_map_reader_candidate.py",
                     "git_map_isolated_candidate.py","git_map_v2_reader_candidate.py","git_map_compact_holder.c"):
            shutil.copy2(ROOT/"scripts"/name,scripts/name)
        binary=scripts/"git_map_compact_holder"
        subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                        str(binary)+".c","-o",str(binary)],check=True)
        repo=base/"repo"
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(["git","-C",str(repo),"-c","user.name=Fixture",
                "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
        git("init","-b","main")
        git("commit","--allow-empty","-m","first")
        git("commit","--allow-empty","-m","second")
        head=git("rev-parse","HEAD")
        status=git("status","--porcelain")
        cache=base/"cache"
        receipt=v2.build(repo,cache)
        directory=Path(receipt["directory"])
        db=directory/v2.NAME
        digest=hashlib.sha256(db.read_bytes()).hexdigest()
        prefix=[sys.executable,"-I","-B",str(scripts/"git_map_v2_reader_candidate.py"),
                "--base",str(cache),"--device",receipt["device"],"--inode",receipt["inode"]]
        identity=[receipt["repoId"],receipt["key"],receipt["manifest"]["snapshot"]]
        expected={"schema":"post-apollo-git-map-reader-v2-candidate","status":"HELD",
                  "repoId":identity[0],"key":identity[1],"snapshot":identity[2],
                  "reclamationAllowed":False,"device":receipt["device"],"inode":receipt["inode"]}
        def argv(mode):
            return prefix+(["--compact-hold"] if mode=="compact" else [])+["hold"]+identity
        def exclusive(path=directory):
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: return False
                return True
            finally: os.close(fd)
        def stop(p):
            if p.poll() is None: p.kill()
            p.wait(timeout=5)
            for stream in (p.stdin,p.stdout,p.stderr):
                if stream and not stream.closed: stream.close()
        def start(mode):
            p=subprocess.Popen(argv(mode),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,text=True)
            try:
                assert select.select([p.stdout],[],[],5)[0],"receipt timeout"
                assert json.loads(p.stdout.readline())==expected
                assert not exclusive()
                exe=Path("/proc")/str(p.pid)/"exe"
                assert exe.resolve()==(binary if mode=="compact" else Path(sys.executable).resolve())
                return p
            except BaseException:
                stop(p)
                raise
        def sample(p):
            proc=Path("/proc")/str(p.pid)
            def identity():
                return (proc/"stat").read_text().rsplit(")",1)[1].split()[19]
            stamp=identity()
            values={}
            for line in (proc/"smaps_rollup").read_text().splitlines():
                key,_,rest=line.partition(":")
                if key in ("Pss","Rss","SwapPss"): values[key]=int(rest.split()[0])
            assert set(values)=={"Pss","Rss","SwapPss"} and identity()==stamp
            return values
        samples={"python":[],"compact":[]}
        for pair,order in enumerate((("python","compact"),("compact","python"),("python","compact"))):
            for mode in order:
                p=start(mode)
                try:
                    finite=subprocess.run(prefix+["page"]+identity+["0"],capture_output=True,
                                          text=True,check=True,timeout=5)
                    assert json.loads(finite.stdout)["result"]["total"]==2
                    values=[]
                    for _ in range(3):
                        assert not exclusive()
                        values.append(sample(p))
                        time.sleep(.05)
                    print("GIT_MAP_COMPACT_RAW",pair,mode,json.dumps(values),flush=True)
                    samples[mode].append(statistics.median(x["Pss"] for x in values))
                    p.stdin.close()
                    assert p.wait(timeout=5)==0
                    assert exclusive()
                finally: stop(p)
        # Missing executable must fail without publishing HELD or leaving lock.
        hidden=binary.with_suffix(".hidden")
        binary.rename(hidden)
        result=subprocess.run(argv("compact"),input="",capture_output=True,text=True,timeout=5)
        assert (result.returncode,result.stdout)==(1,"") and exclusive()
        hidden.rename(binary)
        # Non-pipe input, wrong inode and conflicting lock must fail closed.
        result=subprocess.run(argv("compact"),stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
        assert (result.returncode,result.stdout)==(1,"") and exclusive()
        wrong=argv("compact")
        wrong[wrong.index("--inode")+1]=str(int(receipt["inode"])+1)
        result=subprocess.run(wrong,input="",capture_output=True,text=True,timeout=5)
        assert (result.returncode,result.stdout)==(1,"") and exclusive()
        fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=subprocess.run(argv("compact"),input="",capture_output=True,text=True,timeout=5)
            assert (result.returncode,result.stdout)==(1,"")
        finally: os.close(fd)
        # Two separate open file descriptions: one death must not unlock both.
        a=start("compact")
        try:
            b=start("compact")
            try:
                a.kill()
                a.wait(timeout=5)
                assert not exclusive()
                b.stdin.write("x")
                b.stdin.flush()
                assert b.wait(timeout=5)==1
                assert exclusive()
            finally: stop(b)
        finally: stop(a)
        assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
        assert git("rev-parse","HEAD")==head and git("status","--porcelain")==status
        delta=[b-a for a,b in zip(samples["python"],samples["compact"])]
        print("GIT_MAP_COMPACT_PAIR_MEDIANS_KIB",json.dumps(samples),flush=True)
        print("GIT_MAP_COMPACT_DELTA_KIB",json.dumps(delta),flush=True)
        assert statistics.median(delta)<0,delta
        print("GIT_MAP_COMPACT_HOLDER_PASS",flush=True)

if __name__=="__main__":
    main()
