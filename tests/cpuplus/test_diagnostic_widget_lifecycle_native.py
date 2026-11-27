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
    # Disposable transport witness: actual QML Process/receipt lifecycle,
    # synthetic memory rows only (not evidence of real /proc identity).
    scripts=scene/"scripts"
    scripts.mkdir()
    for name in ("cpuplus_diagnostic_workflow_catalog.py","cpuplus_diagnostic_archive.py","cpuplus_diagnostic_workflow.py"):
        shutil.copy2(ROOT/"scripts"/name,scripts/name)
    (scripts/"cpuplus_quickshell_memory_observer.py").write_text("""
import json,sys,time
assert sys.argv[1:]==["--workshop","--parent-quickshell","--duration","5","--interval","5"]
origin=round(time.time()*1000)
mono=round(time.monotonic()*1000)
def row(at,ms,ticks,cpu,interval):
    return dict(event="memory",pid=123,startTicks=456,tsMs=at,monotonicMs=ms,
        memoryKiB=dict(Rss=100,Pss=80,SwapPss=0),cpuTicks=ticks,cpuPct=cpu,sampleIntervalMs=interval)
print(json.dumps(row(origin,mono,10,None,None)),flush=True)
time.sleep(5.15)
elapsed=round(time.monotonic()*1000)-mono
print(json.dumps(row(origin+elapsed,mono+elapsed,60,10,elapsed)),flush=True)
print(json.dumps(dict(event="complete",pid=123,startTicks=456,workshopSchema="post-apollo-observer-calibration-v1",
    calibration=dict(kind="memory",durationSeconds=5,intervalMs=5000),samples=2,observedMs=elapsed,monotonicMs=mono+elapsed)),flush=True)
""")
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        directory=base/key
        directory.mkdir(mode=0o700)
        env[key]=str(directory)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="")
    result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=40,check=False)
    print(result.stdout)
    if result.returncode or "CPU_Q5_NATIVE_PASS" not in result.stdout or "CPU_Q5E_JOINT_PASS" not in result.stdout or "CPU_Q5F_SAVED_DUMP_PASS" not in result.stdout or "CPU_Q5_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native lifecycle witness failed")
