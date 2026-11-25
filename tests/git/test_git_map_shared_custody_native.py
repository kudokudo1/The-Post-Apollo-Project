#!/usr/bin/env python3
import os
import fcntl
import time
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="git-map-shared-custody-") as tmp:
    base=Path(tmp)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"components",scene/"components")
    for folder,names in (
        ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
        ("widgets/git",("GitMapVirtualViewport.qml","GitMapControlHost.qml","GitMapCustodyController.qml","GitMapGenerationLease.qml")),
        ("scripts",("git_map_history_index.py","git_map_index_manager.py","git_map_reader_candidate.py")),
    ):
        dest=scene/folder
        dest.mkdir(parents=True)
        for name in names:
            shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapSharedCustodyNative.qml",scene/"smoke.qml")
    shutil.copy2(ROOT/"tests/git/fixtures/git_map_shared_custody_probe.py",scene/"probe.py")
    repo=base/"repo"
    repo.mkdir()
    for args in [("init","-b","main")]+[("commit","--allow-empty","-m",f"commit {i}") for i in range(40)]:
        subprocess.run(["/usr/bin/git","-C",str(repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
               MAP_MANAGED_REPO=str(repo))
    result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    print(result.stdout)
    if result.stdout.count("SHARED_CUSTODY_KERNEL_WITNESS_PASS")!=4:
        raise SystemExit("Missing integrated kernel witness")
    cache=Path(env["XDG_CACHE_HOME"])/"post-apollo-git-map-v1"
    def all_released():
        for path in cache.glob("*/*"):
            if not path.is_dir() or path.name.startswith("."): continue
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: return False
            finally: os.close(fd)
        return True
    deadline=time.monotonic()+5
    while not all_released():
        if time.monotonic()>=deadline: raise SystemExit("Integrated owner exit left locks held")
        time.sleep(.02)
    print("SHARED_CUSTODY_ALL_RELEASED")
    if (result.returncode or "GIT_MAP_SHARED_CUSTODY_PASS" not in result.stdout
            or any(x in result.stdout for x in ("GIT_MAP_SHARED_CUSTODY_FAIL","Binding loop detected","TypeError:","ReferenceError:"))):
        raise SystemExit("Native managed Git map fixture failed")
