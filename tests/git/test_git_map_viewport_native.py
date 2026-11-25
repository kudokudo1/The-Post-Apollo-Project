#!/usr/bin/env python3
"""Disposable offscreen Quickshell; real page subprocess, synthetic index."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_history_index as index

def build(directory,count,offset,snapshot,repo):
    directory.mkdir(mode=0o700)
    db=directory/index.NAME
    def rows():
        for i in range(count):
            sha=format(offset+i+1,"040x")
            parents=[format(offset+i+2,"040x")] if i+1<count else []
            yield sha,parents,i,"Fixture","Commit "+str(i)
    with sqlite3.connect(db) as conn:
        manifest=index.fill(conn,rows(),snapshot=snapshot,repo_id=repo,
                            roots_digest="c"*64,shallow=False)
    conn.close()
    db.chmod(0o600)
    return manifest

with tempfile.TemporaryDirectory(prefix="git-map-native-") as temporary:
    base=Path(temporary)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"components",scene/"components")
    for folder,files in (
        ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
        ("widgets/git",("GitMapVirtualViewport.qml",)),
    ):
        dest=scene/folder
        dest.mkdir(parents=True)
        for name in files:
            shutil.copy2(ROOT/folder/name,dest/name)
    scripts=scene/"scripts"
    scripts.mkdir()
    shutil.copy2(ROOT/"scripts/git_map_history_index.py",scripts/"real_index.py")
    # A test-only wrapper induces real asynchronous delays and one error.
    # The production helper is otherwise invoked unchanged, using runpy
    # because the bridge runs Python in isolated mode.
    (scripts/"git_map_history_index.py").write_text(
        'import os, pathlib, runpy, sys, time\n'
        'start=int(sys.argv[4]); directory=pathlib.Path(sys.argv[2])\n'
        'if directory.name=="index-a" and start==0: time.sleep(0.8)\n'
        'if directory.name=="index-a" and start==99968:\n'
        '    marker=directory/"fixture-failed-once"\n'
        '    if not marker.exists(): marker.touch(); sys.exit(2)\n'
        'if directory.name=="index-a" and start==49920: time.sleep(0.5)\n'
        'runpy.run_path(str(pathlib.Path(__file__).with_name("real_index.py")),run_name="__main__")\n'
    )
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapVirtualViewportNative.qml",scene/"smoke.qml")
    a=build(base/"index-a",100000,0,"a"*32,"b"*64)
    b=build(base/"index-b",257,200000,"d"*32,"e"*64)
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
               MAP_FIXTURE_A=json.dumps(a),MAP_FIXTURE_B=json.dumps(b),
               MAP_FIXTURE_DIR_A=str(base/"index-a"),MAP_FIXTURE_DIR_B=str(base/"index-b"))
    result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=35)
    print(result.stdout)
    if result.returncode or "GIT_MAP_NATIVE_PASS" not in result.stdout or "GIT_MAP_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native Git map fixture failed")
