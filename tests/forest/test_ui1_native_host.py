#!/usr/bin/env python3
"""CI-only real ForestW in a fresh private headless Sway. No operator desktop."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("FOREST_HOST_REQUIRES_GITHUB_ACTIONS")
if os.getuid() == 0:
    raise SystemExit("FOREST_HOST_REQUIRES_UNPRIVILEGED_UID")
ROOT = Path(__file__).resolve().parents[2]


def stop(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=4)


def trial(width, height, count):
    with tempfile.TemporaryDirectory(prefix="forest-private-wayland-") as name:
        work = Path(name)
        for d in ("run", "home", "cache", "config-home", "data", "config"):
            (work / d).mkdir(mode=0o700)
        scene = work / "config"
        # Stage actual sources under the isolated Quickshell config root.
        for directory in ("components", "widgets", "services", "assets"):
            shutil.copytree(ROOT / directory, scene / directory)
        helper = "scripts/forest/ui_model_preferences.py"
        (scene / helper).parent.mkdir(parents=True)
        shutil.copy2(ROOT / helper, scene / helper)
        # Do not stage Ollama, model inference or host dispatch helpers.
        shutil.copy2(ROOT / "tests/forest/ui1_native_host/shell.qml", scene / "shell.qml")
        for relative in ("widgets/ForestW.qml", "widgets/forest/ui2/PublicConversationFixture.qml",
                         "widgets/forest/ui2/PublicPreviewGate.qml", "components/ConversationFeed.qml", helper):
            if (ROOT / relative).read_bytes() != (scene / relative).read_bytes():
                raise AssertionError("SOURCE_MISMATCH " + relative)
        config = work / "sway.conf"
        config.write_text(f"xwayland disable\noutput * mode {width}x{height}\n", encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8", "HOME": str(work / "home"),
            "XDG_RUNTIME_DIR": str(work / "run"), "XDG_CONFIG_HOME": str(work / "config-home"),
            "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
            "XDG_SESSION_TYPE": "wayland", "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "1", "WLR_RENDERER": "pixman",
            "WLR_LIBINPUT_NO_DEVICES": "1",
            "QT_QPA_PLATFORM": "wayland", "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "QT_LOGGING_RULES": "qml.debug=true;qml.info=true;qml.warning=true;qml.critical=true",
        }
        compositor = qs = None
        sway_log = work / "sway.log"
        try:
            with sway_log.open("wb") as log:
                compositor = subprocess.Popen(["sway", "--config", str(config)], env=env,
                    cwd=work, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
            for _ in range(100):
                sockets = [p for p in (work / "run").glob("wayland-*") if p.is_socket()]
                if compositor.poll() is not None:
                    raise AssertionError("PRIVATE_SWAY_EXITED")
                if len(sockets) == 1:
                    env["WAYLAND_DISPLAY"] = sockets[0].name
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("PRIVATE_WAYLAND_SOCKET_MISSING")
            qs_log = work / "quickshell.log"
            with qs_log.open("wb") as log:
                qs = subprocess.Popen(["quickshell", "--path", str(scene / "shell.qml"),
                    "--no-color", "--log-rules", env["QT_LOGGING_RULES"]],
                    env=env, cwd=work, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True)
                code = qs.wait(timeout=35)
            output = qs_log.read_text(errors="replace")
            print(output, flush=True)
            phases = [line.split("FOREST_HOST_PHASE_PASS ", 1)[1].strip()
                      for line in output.splitlines() if "FOREST_HOST_PHASE_PASS " in line]
            if (code != 0 or "FOREST_HOST_FAIL" in output or
                    phases != [str(i) for i in range(count)] or
                    output.count("FOREST_HOST_NATIVE_PASS") != 1):
                raise AssertionError("FOREST_HOST_INCOMPLETE")
            print(f"FOREST_HOST_OUTPUT_PASS {width}x{height} phases={count}", flush=True)
        finally:
            stop(qs)
            stop(compositor)
            if sway_log.exists():
                print(sway_log.read_text(errors="replace")[-5000:], flush=True)
            if (work / "quickshell.log").exists() and qs and qs.returncode is None:
                print((work / "quickshell.log").read_text(errors="replace")[-10000:], flush=True)


if __name__ == "__main__":
    trial(1366, 900, 10)
    trial(420, 340, 3)
