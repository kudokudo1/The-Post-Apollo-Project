#!/usr/bin/env python3
"""Actual gated host: delayed locked page and locate during repo switch."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
for mode in ("page","locate"):
    with tempfile.TemporaryDirectory(prefix="git-map-transition-") as tmp:
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
            for name in names: shutil.copy2(ROOT/folder/name,dest/name)
        shutil.copy2(ROOT/"tests/git/fixtures/GitMapTransitionNative.qml",scene/"smoke.qml")
        shutil.copy2(ROOT/"tests/git/fixtures/git_map_transition_probe.py",scene/"probe.py")
        control=base/"control"
        control.mkdir(mode=0o700)
        helper=scene/"scripts/git_map_history_index.py"
        source=helper.read_text()
        # Test-only barrier inside the real CLI locked_index context.
        anchor="def page(conn, snapshot, start):" if mode=="page" else "def locate(conn, snapshot, sha):"
        assert source.count(anchor)==1
        delay="""    import time
    control=Path(os.environ["MAP_TRANSITION_CONTROL"])
    if CONDITION and not (control/"started").exists():
        (control/"started").touch()
        deadline=time.monotonic()+4
        while not (control/"release").exists():
            if time.monotonic()>=deadline:
                raise ValueError("fixture release timeout")
            time.sleep(.01)
"""
        delay=delay.replace("CONDITION","start==256" if mode=="page" else "True")
        helper.write_text(source.replace(anchor,anchor+"\n"+delay.rstrip("\n")))
        repo=base/"repo"
        other=base/"other"
        for directory in (repo,other):
            directory.mkdir()
            subprocess.run(["git","-C",str(directory),"init","-b","main"],check=True,capture_output=True)
        lines=[]
        for i in range(1,301):
            lines.extend(["commit refs/heads/main",f"mark :{i}",
                f"committer Fixture <fixture@example.invalid> {1700000000+i} +0000",
                "data 1","x"])
            if i>1: lines.append(f"from :{i-1}")
            lines.append("")
        subprocess.run(["git","-C",str(repo),"fast-import","--quiet"],
                       input=("\n".join(lines)+"\n").encode(),check=True,capture_output=True)
        subprocess.run(["git","-C",str(repo),"reset","--hard","HEAD"],check=True,capture_output=True)
        subprocess.run(["git","-C",str(other),"-c","user.name=Fixture","-c","user.email=fixture@example.invalid",
                        "commit","--allow-empty","-m","other repository"],check=True,capture_output=True)
        env=os.environ.copy()
        for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
            d=base/key
            d.mkdir(mode=0o700)
            env[key]=str(d)
        env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
                   LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                   MAP_MANAGED_REPO=str(repo),MAP_OTHER_REPO=str(other),MAP_TRANSITION_MODE=mode,
                   MAP_TRANSITION_CONTROL=str(control))
        result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40)
        print(result.stdout)
        if (result.returncode or "GIT_MAP_TRANSITION_PASS "+mode not in result.stdout
                or "GIT_MAP_TRANSITION_KERNEL_PAIR_PASS" not in result.stdout
                or "GIT_MAP_TRANSITION_KERNEL_FINAL_PASS" not in result.stdout
                or any(x in result.stdout for x in ("GIT_MAP_TRANSITION_FAIL","Binding loop detected","TypeError:","ReferenceError:"))):
            raise SystemExit("Native transition fixture failed "+mode)
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
            assert time.monotonic()<deadline,"owner exit left lock held"
            time.sleep(.02)
        print("GIT_MAP_TRANSITION_ALL_RELEASED",mode,flush=True)
