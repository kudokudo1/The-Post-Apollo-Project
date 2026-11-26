"""Disposable Quickshell mount smoke for CPU++ shared Kill view.

No real processes are probed or mutated. A synthetic AppControl owner
satisfies the live-row and guarded-action contracts.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_CPU_KILL_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")

with tempfile.TemporaryDirectory(prefix="cpu-shared-kill-") as tmp:
    base = Path(tmp)
    config = base / "scene"
    (config / "widgets/appcontrol").mkdir(parents=True)
    (config / "widgets/cpuplus").mkdir(parents=True)
    (config / "services/system").mkdir(parents=True)
    shutil.copytree(ROOT / "components", config / "components")
    for name in ("TaskManagerView.qml", "TaskGraphController.qml",
                 "HunterControls.qml", "ProcessTargetRow.qml",
                 "ProcessSafetyLock.qml"):
        shutil.copy2(ROOT / "widgets/appcontrol" / name,
                     config / "widgets/appcontrol")
    shutil.copy2(ROOT / "widgets/cpuplus/CpuPlusKillWorkspace.qml",
                 config / "widgets/cpuplus")
    for name in ("GraphHistory.qml", "ProcessPresentationState.qml",
                 "HunterPresentation.qml"):
        shutil.copy2(ROOT / "services/system" / name,
                     config / "services/system")
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/SharedKillRecipientNative.qml",
                 config / "smoke.qml")

    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen",
               QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1",
               QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")

    proc = subprocess.run(
        ["qs", "-p", str(config / "smoke.qml"), "--no-color"],
        cwd=config, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=35, check=False)
    print(proc.stdout)
    if (proc.returncode
            or "CPU_KILL_NATIVE_PASS" not in proc.stdout
            or "CPU_KILL_NATIVE_FAIL" in proc.stdout):
        raise SystemExit("CPU++ shared Kill native mount failed")
