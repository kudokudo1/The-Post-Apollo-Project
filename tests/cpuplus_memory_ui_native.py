#!/usr/bin/env python3
"""Run actual QML in an isolated offscreen Quickshell CI fixture; no host writes."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="cpu-memory-ui-") as tmp:
    base = Path(tmp)
    config = base / "scene"
    config.mkdir()
    for name in ("components", "widgets/cpuplus"):
        shutil.copytree(ROOT / name, config / name)
    shutil.copy2(ROOT / "tests/fixtures/CpuPlusMemoryUiNative.qml", config / "smoke.qml")
    service = config / "services/memory"
    service.mkdir(parents=True)
    (service / "qmldir").write_text("module qs.services.memory\n\nsingleton MemoryOperation 1.0 MemoryOperation.qml\n")
    (service / "MemoryOperation.qml").write_text("""pragma Singleton
import QtQuick
import Quickshell
Scope {
    property bool busy: false
    property int revision: 0
    property string feedback: "TEST ONLY"
    property int requests: 0
    function request(action, value) { requests++; }
}
""")
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    proc = subprocess.run(["qs", "-p", str(config / "smoke.qml"), "--no-color"],
                          cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=25, check=False)
    print(proc.stdout)
    if proc.returncode or "CPU_MEMORY_UI_NATIVE_PASS" not in proc.stdout or "CPU_MEMORY_UI_NATIVE_FAIL" in proc.stdout:
        raise SystemExit("Native UI fixture failed")
