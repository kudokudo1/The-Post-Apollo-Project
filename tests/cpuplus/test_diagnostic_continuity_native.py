#!/usr/bin/env python3
"""Native QML lifetime test using real Process and a disposable fake report."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")

with tempfile.TemporaryDirectory(prefix="cpu-diag-native-") as temporary:
    base = Path(temporary)
    config = base / "scene"
    config.mkdir()
    shutil.copytree(ROOT / "components", config / "components")
    shutil.copytree(ROOT / "services/diagnostics", config / "services/diagnostics")
    destination = config / "widgets/cpuplus"
    destination.mkdir(parents=True)
    for name in ("CpuPlusMemoryActuatorPane.qml", "CpuPlusMemoryCapacitySlider.qml",
                 "CpuPlusMemoryAddControl.qml", "CpuPlusSwapComposition.qml",
                 "CpuPlusMemorySnapshot.js", "CpuPlusDiagnosticsPane.qml"):
        shutil.copy2(ROOT / "widgets/cpuplus" / name, destination / name)
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/DiagnosticContinuityNative.qml", config / "smoke.qml")
    memory = config / "services/memory"
    memory.mkdir(parents=True)
    (memory / "qmldir").write_text("module qs.services.memory\n\nsingleton MemoryOperation 1.0 MemoryOperation.qml\n")
    (memory / "MemoryOperation.qml").write_text("""pragma Singleton
import QtQuick
import Quickshell
Scope {
    property bool busy: false
    property int revision: 0
    property string feedback: "TEST ONLY"
    function request(action, value) { throw new Error("unexpected privileged request") }
}
""")
    scripts = config / "scripts"
    scripts.mkdir()
    (scripts / "cpuplus_qml_workload_inventory.py").write_text(
        'import json,time\ntime.sleep(3)\nprint(json.dumps({"schema":"post-apollo-qml-workload-inventory-v1",'
        '"trackedQml":826,"scannedQml":826,"skipped":[],"totals":{"Timer":426,"Process":415,"Repeater":743}}))\n')
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    result = subprocess.run(["qs", "-p", str(config / "smoke.qml"), "--no-color"],
                            cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=25, check=False)
    print(result.stdout)
    if result.returncode or "CPU_DIAG_NATIVE_PASS" not in result.stdout or "CPU_DIAG_NATIVE_FAIL" in result.stdout:
        raise SystemExit("Native diagnostic continuity failed")
