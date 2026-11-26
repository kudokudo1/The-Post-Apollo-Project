#!/usr/bin/env python3
"""Actual WorkflowLibraryView with fake dispatch service, never remote writes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_WORKFLOW_LIBRARY_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="git-workflow-library-") as tmp:
    base = Path(tmp)
    scene = base / "scene"
    scene.mkdir()
    shutil.copytree(ROOT / "components", scene / "components")
    for file in ("widgets/WorkflowLibraryView.qml", "services/github/WorkflowSearchPolicy.js",
                 "services/github/WorkflowLibraryStore.qml"):
        destination = scene / file
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / file, destination)
    shutil.copy2(ROOT / "tests/git/fixtures/WorkflowLibraryNative.qml", scene / "smoke.qml")
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    result = subprocess.run(["qs", "-p", str(scene / "smoke.qml"), "--no-color"],
                            cwd=scene, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=25)
    print(result.stdout)
    if result.returncode or "GIT_WORKFLOW_LIBRARY_PASS" not in result.stdout or any(
        marker in result.stdout for marker in ("GIT_WORKFLOW_LIBRARY_FAIL", "TypeError:", "ReferenceError:", "Binding loop detected")
    ):
        raise SystemExit("Native workflow library failed")
