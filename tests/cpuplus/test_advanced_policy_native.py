from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_ADVANCED_POLICY_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="cpu-advanced-policy-") as tmp:
    base = Path(tmp)
    config = base / "scene"
    (config / "widgets/cpuplus").mkdir(parents=True)
    shutil.copytree(ROOT / "components", config / "components")
    for name in ("CpuPlusAdvancedPolicy.js", "CpuPlusAdvancedPolicyPane.qml"):
        shutil.copy2(ROOT / "widgets/cpuplus" / name, config / "widgets/cpuplus")
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/AdvancedPolicyNative.qml", config / "smoke.qml")
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
    if proc.returncode or "ADVANCED_POLICY_NATIVE_PASS" not in proc.stdout or "ADVANCED_POLICY_NATIVE_FAIL" in proc.stdout:
        raise SystemExit("Native advanced policy fixture failed")
