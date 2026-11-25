#!/usr/bin/env python3
"""Actual native Process stdin lifetime, two readers and crash release."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_index_manager as manager

def locked(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return True
        return False
    finally: os.close(fd)

with tempfile.TemporaryDirectory(prefix="git-map-native-custody-") as tmp:
    base=Path(tmp)
    repo=base/"repo"
    repo.mkdir()
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL,text=True).strip()
    git("init","-b","main")
    git("commit","--allow-empty","-m","first")
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    cache=Path(env["XDG_CACHE_HOME"])/"post-apollo-git-map-v1"
    old=manager.build(repo,cache)
    git("commit","--allow-empty","-m","second")
    new=manager.build(repo,cache)
    paths=[Path(v["directory"]) for v in (old,new)]
    digests=[hashlib.sha256((p/manager.index.NAME).read_bytes()).hexdigest() for p in paths]
    head=git("rev-parse","HEAD")
    scene=base/"scene"
    scene.mkdir()
    (scene/"scripts").mkdir()
    for name in ("git_map_reader_candidate.py","git_map_index_manager.py","git_map_history_index.py"):
        shutil.copy2(ROOT/"scripts"/name,scene/"scripts"/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapReaderCustodyNative.qml",scene/"smoke.qml")
    shutil.copy2(ROOT/"tests/git/fixtures/git_map_reader_lock_probe.py",scene/"probe.py")
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
        QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
        CUSTODY_OLD=json.dumps(old),CUSTODY_NEW=json.dumps(new))
    for mode in ("graceful","crash"):
        env["CUSTODY_MODE"]=mode
        logfile=base/(mode+".log")
        with logfile.open("w") as log:
            p=subprocess.Popen(["qs","-p",str(scene/"smoke.qml"),"--no-color"],
                cwd=scene,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                if mode=="graceful":
                    assert p.wait(timeout=30)==0
                    assert "GIT_MAP_CUSTODY_NATIVE_PASS" in logfile.read_text()
                else:
                    deadline=time.monotonic()+15
                    while "GIT_MAP_CUSTODY_CRASH_READY" not in logfile.read_text():
                        assert p.poll() is None,"owner exited before crash witness"
                        assert time.monotonic()<deadline,"crash witness timeout"
                        time.sleep(.02)
                    assert all(locked(path) for path in paths),"locks not held at owner death"
                    p.kill()
                    assert p.wait(timeout=5)==-signal.SIGKILL
                deadline=time.monotonic()+5
                while any(locked(path) for path in paths):
                    assert time.monotonic()<deadline,"reader lock survived owner exit"
                    time.sleep(.02)
                print(logfile.read_text())
                raw=logfile.read_text()
                assert not any(x in raw for x in ("GIT_MAP_CUSTODY_FAIL","TypeError:","ReferenceError:","Binding loop detected"))
                assert raw.count("CUSTODY_HELPER_MEMORY") >= 4
                print("GIT_MAP_CUSTODY_OWNER_RELEASE_PASS",mode,flush=True)
            finally:
                # Scope cleanup to this disposable native fixture only.
                try: os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                p.wait(timeout=5)
    assert [hashlib.sha256((p/manager.index.NAME).read_bytes()).hexdigest() for p in paths]==digests
    assert git("rev-parse","HEAD")==head and git("status","--porcelain")==""
    print("GIT_MAP_CUSTODY_NATIVE_ALL_PASS; original generations and Git unchanged")
