#!/usr/bin/env python3
"""Paired V2 Python vs compact holder PSS in two retained GitW hosts.
CI only; no installed desktop or system-wide claim.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_history_index as index

def process_stat(pid):
    # /proc/PID/stat comm may contain spaces or parentheses.
    fields=(Path("/proc")/str(pid)/"stat").read_text().rsplit(")",1)[1].split()
    return int(fields[1]), int(fields[19])

def descendants(root):
    tree={}
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal(): continue
        pid=int(path.name)
        try: tree[pid]=process_stat(pid)
        except (OSError,ValueError,IndexError): continue
    if root not in tree: raise ValueError("shell exited")
    selected={root:tree[root][1]}
    while True:
        new={pid:start for pid,(parent,start) in tree.items()
             if parent in selected and pid not in selected}
        if not new: return selected
        selected.update(new)

def sample(root,mode,binary):
    expected_helpers=1
    before=descendants(root)
    rows=[]
    for pid,start in sorted(before.items()):
        path=Path("/proc")/str(pid)
        cmd=(path/"cmdline").read_bytes().split(b"\0")
        helper=(Path(os.readlink(path/"exe"))==binary if mode=="compact"
                else any(x.endswith(b"/scripts/git_map_v2_reader_candidate.py") for x in cmd))
        if helper:
            assert Path(os.readlink(path/"exe"))==(binary if mode=="compact" else Path(sys.executable).resolve())
        values={}
        for line in (path/"smaps_rollup").read_text().splitlines():
            key,_,rest=line.partition(":")
            if key in ("Rss","Pss","SwapPss"): values[key]=int(rest.split()[0])
        assert set(values)=={"Rss","Pss","SwapPss"}
        assert process_stat(pid)[1]==start,"process identity changed"
        rows.append(dict(pid=pid,helper=helper,**values))
    assert descendants(root)==before,"process tree changed"
    assert sum(row["helper"] for row in rows)==expected_helpers,rows
    # No transient page/build/witness processes may contaminate retained sample.
    assert len(rows)==1+expected_helpers,rows
    return {"rows":rows,"Pss":sum(row["Pss"] for row in rows),
            "SwapPss":sum(row["SwapPss"] for row in rows)}

def exclusive(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return False
        return True
    finally: os.close(fd)

with tempfile.TemporaryDirectory(prefix="git-map-footprint-") as tmp:
    base=Path(tmp)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"components",scene/"components")
    for folder,names in (
        ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
        ("widgets/git",("GitMapVirtualViewport.qml","GitMapControlHost.qml","GitMapCustodyController.qml","GitMapGenerationLease.qml")),
        ("scripts",("git_map_history_index.py","git_map_index_manager.py","git_map_reader_candidate.py","git_map_isolated_candidate.py","git_map_v2_reader_candidate.py","git_map_compact_holder.c","git_map_v2_manager_candidate.py")),
    ):
        dest=scene/folder
        dest.mkdir(parents=True)
        for name in names: shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapFootprintNative.qml",scene/"smoke.qml")
    fixture=scene/"smoke.qml"
    source=fixture.read_text()
    anchor="GitMapCustodyController { id: pool }"
    assert source.count(anchor)==1
    fixture.write_text(source.replace(anchor,'GitMapCustodyController { id: pool; v2Mode: true; v2Base: Quickshell.env("XDG_CACHE_HOME"); compactHold: Quickshell.env("MAP_COMPACT_HOLDER")==="yes" }'))
    binary=scene/"scripts/git_map_compact_holder"
    subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",str(binary)+".c","-o",str(binary)],check=True)
    repo=base/"repo"
    repo.mkdir()
    def git(*args,**kw):
        return subprocess.run(["git","-C",str(repo),*args],check=True,capture_output=True,**kw)
    git("init","-b","main")
    lines=[]
    for i in range(1,1001):
        lines.extend(["commit refs/heads/main",f"mark :{i}",
                      f"committer Fixture <fixture@example.invalid> {1700000000+i} +0000",
                      "data 1","x"])
        if i>1: lines.append(f"from :{i-1}")
        lines.append("")
    git("fast-import","--quiet",input=("\n".join(lines)+"\n").encode())
    git("reset","--hard","HEAD")
    head=git("rev-parse","HEAD").stdout
    worktree=git("status","--porcelain").stdout
    cache=base/"cache"
    receipt=v2.build(repo,cache)
    assert receipt["manifest"]["total"]==1000,receipt
    directory=Path(receipt["directory"])
    db=directory/v2.NAME
    digest=hashlib.sha256(db.read_bytes()).hexdigest()
    samples={"python":[],"compact":[]}
    for pair,order in enumerate((("python","compact"),("compact","python"),("python","compact"))):
        for mode in order:
            env=os.environ.copy()
            for key in ("HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
                path=base/f"{pair}-{mode}-{key}"
                path.mkdir(mode=0o700)
                env[key]=str(path)
            env.update(XDG_CACHE_HOME=str(cache),QT_QPA_PLATFORM="offscreen",
                       QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
                       QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                       MAP_FOOTPRINT_REPO=str(repo),MAP_FOOTPRINT_MODE="on",
                       MAP_COMPACT_HOLDER="yes" if mode=="compact" else "no")
            # Verify the exact prebuilt snapshot is visible through the same
            # executable and environment as the host, before launching QML.
            lookup=subprocess.run([sys.executable,"-I","-B",
                str(scene/"scripts/git_map_v2_manager_candidate.py"),"--base",str(cache),"lookup",str(repo)],
                env=env,text=True,capture_output=True,timeout=5,check=True)
            assert json.loads(lookup.stdout)==receipt,(lookup.stdout,receipt)
            logfile=base/f"{pair}-{mode}.log"
            with logfile.open("w") as log:
                p=subprocess.Popen(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,
                                   env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    deadline=time.monotonic()+25
                    expected="GIT_MAP_FOOTPRINT_READY "+receipt["manifest"]["snapshot"]
                    while expected not in logfile.read_text():
                        assert "GIT_MAP_FOOTPRINT_FAIL" not in logfile.read_text(),logfile.read_text()
                        assert p.poll() is None,logfile.read_text()
                        assert time.monotonic()<deadline,logfile.read_text()
                        time.sleep(.05)
                    time.sleep(.3)
                    values=[]
                    for _ in range(3):
                        assert not exclusive(directory)
                        values.append(sample(p.pid,mode,binary))
                        time.sleep(.15)
                    print("GIT_MAP_V2_COMPACT_RAW",pair,mode,json.dumps(values),flush=True)
                    samples[mode].append(statistics.median(x["Pss"] for x in values))
                    assert not any(x in logfile.read_text() for x in
                        ("GIT_MAP_FOOTPRINT_FAIL","Binding loop detected","TypeError:","ReferenceError:"))
                finally:
                    try: os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    p.wait(timeout=5)
                    deadline=time.monotonic()+5
                    while not exclusive(directory):
                        assert time.monotonic()<deadline,"owner exit left lock"
                        time.sleep(.02)
    assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
    assert git("rev-parse","HEAD").stdout==head and git("status","--porcelain").stdout==worktree
    print("GIT_MAP_V2_COMPACT_PAIR_MEDIANS_KIB",json.dumps(samples),flush=True)
    print("GIT_MAP_V2_COMPACT_PAIRED_DELTA_KIB",
          json.dumps([b-a for a,b in zip(samples["python"],samples["compact"])]),flush=True)
    assert not (cache/"post-apollo-git-map-v1").exists()
    assert len([p for p in (cache/v2.ROOT_NAME).glob("*/*") if p.is_dir()])==1
    print("GIT_MAP_V2_COMPACT_FOOTPRINT_PASS; no deletion",flush=True)
