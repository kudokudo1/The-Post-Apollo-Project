#!/usr/bin/env python3
"""Disposable native QML signal witness; no live shell or service access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="cpu-lifecycle-native-") as tmp:
    base=Path(tmp)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"services/diagnostics",scene/"services/diagnostics")
    shutil.copy2(ROOT/"tests/cpuplus/fixtures/DiagnosticWidgetLifecycleNative.qml",scene/"smoke.qml")
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        directory=base/key
        directory.mkdir(mode=0o700)
        env[key]=str(directory)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="")
    result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=12,check=False)
    print(result.stdout)
    if result.returncode or "CPU_Q5_NATIVE_PASS" not in result.stdout or "CPU_Q5_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native lifecycle witness failed")
