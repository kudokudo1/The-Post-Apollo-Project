"""Disposable offscreen native fixture using exact candidate checkouts."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="cpu-queue-r3-") as tmp:
    base = Path(tmp)
    config = base / "scene"
    config.mkdir(mode=0o700)
    ui = ROOT / "candidate-ui"
    shutil.copytree(ui / "components", config / "components")
    widgets = config / "widgets/cpuplus"
    widgets.mkdir(parents=True)
    for name in ("CpuPlusQueuePane.qml", "CpuPlusQueueConsumer.js", "CpuPlusQueuePresentation.js"):
        shutil.copy2(ui / "widgets/cpuplus" / name, widgets / name)
    shutil.copytree(ROOT / "candidate-pipe/services/memory", config / "memory")
    shutil.copy2(ROOT / "candidate-expiry/services/memory/memory_queue_owner.py",
                 config / "memory/memory_queue_owner.py")
    shutil.copy2(ROOT / "tests/fixtures/CpuPlusQueuePipeNative.qml", config / "smoke.qml")
    child = config / "child.py"
    shutil.copy2(ROOT / "tests/fixtures/cpuplus_queue_pipe_child.py", child)
    (config / "private").mkdir(mode=0o700)
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        d = base / key
        d.mkdir(mode=0o700)
        env[key] = str(d)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="", POST_APOLLO_QUEUE_PIPE_CHILD=str(child))
    proc = subprocess.run(["qs", "-p", str(config / "smoke.qml"), "--no-color"],
                          cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=25, check=False)
    print(proc.stdout)
    if proc.returncode or "QUEUE_R3_NATIVE_PASS" not in proc.stdout or "QUEUE_R3_NATIVE_FAIL" in proc.stdout:
        raise SystemExit("Native queue pipe fixture failed")
