"""Disposable Quickshell mount smoke for CPU++ shared Kill view.

The UI action tests use a synthetic owner. Independent real subprocess
witnesses use only test-owned disposable children. The priority witness
requires a reversible range or verifies refusal without mutation.
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
    shutil.copytree(ROOT / "services/kill", config / "services/kill")
    shutil.copytree(ROOT / "services/favorites", config / "services/favorites")
    for name in ("TaskManagerView.qml", "TaskGraphController.qml",
                 "HunterControls.qml", "ProcessTargetRow.qml", "ProcessMiniGraph.qml",
                 "ProcessSafetyLock.qml", "ProcessInformationButton.qml",
                 "ProcessInformationPanel.qml"):
        shutil.copy2(ROOT / "widgets/appcontrol" / name,
                     config / "widgets/appcontrol")
    # K8d resource console is an explicitly mounted local component, not
    # an optional plugin. Include its pure draft policy and reused instruments.
    for name in ("CpuPlusKillWorkspace.qml",
                 "CpuPlusKillResourceConsole.qml", "CpuPlusKillResourceDraft.js",
                 "CpuPlusDiagnosticSlider.qml", "CpuPlusMemoryReadout.qml",
                 "CpuPlusMemoryReadout.js"):
        shutil.copy2(ROOT / "widgets/cpuplus" / name,
                     config / "widgets/cpuplus")
    for name in ("GraphHistory.qml", "ProcessPresentationState.qml",
                 "HunterPresentation.qml", "ProcessTelemetry.qml",
                 "TaskSafety.qml", "ProcessControl.qml", "ProcessLimits.qml", "HunterExecutor.qml",
                 "ProcessPresentationController.qml"):
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

# Independent KillStore proof: no donor or recipient widget is loaded.
with tempfile.TemporaryDirectory(prefix="kill-store-") as tmp:
    base = Path(tmp)
    config = base / "scene"
    (config / "services/system").mkdir(parents=True)
    shutil.copytree(ROOT / "services/kill", config / "services/kill")
    shutil.copytree(ROOT / "services/favorites", config / "services/favorites")
    shutil.copytree(ROOT / "components", config / "components")
    for name in ("ProcessTelemetry.qml", "ProcessPresentationState.qml",
                 "HunterPresentation.qml", "TaskSafety.qml",
                 "ProcessControl.qml", "ProcessLimits.qml", "HunterExecutor.qml",
                 "ProcessPresentationController.qml"):
        shutil.copy2(ROOT / "services/system" / name, config / "services/system")
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/KillStoreStandaloneNative.qml",
                 config / "smoke.qml")
    env = os.environ.copy()
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    try:
        proc = subprocess.run(["qs", "-p", str(config / "smoke.qml"), "--no-color"],
                              cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=20, check=False)
    except subprocess.TimeoutExpired as exc:
        print(exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes)
              else (exc.stdout or ""))
        raise SystemExit("Independent KillStore native fixture timed out") from exc
    print(proc.stdout)
    if (proc.returncode or "KILL_STORE_NATIVE_PASS" not in proc.stdout
            or "KILL_STORE_NATIVE_FAIL" in proc.stdout):
        raise SystemExit("Independent KillStore native mount failed")

    # Real read-only inspection witness, isolated from synthetic action tests.
    import json
    import sys

    shutil.copy2(ROOT / "tests/cpuplus/fixtures/KillResourceEvidenceNative.qml",
                 config / "inspection.qml")
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        stat = Path(f"/proc/{child.pid}/stat").read_text()
        end = stat.rindex(")")
        identity = [child.pid, int(stat[end + 2:].split()[19]),
                    stat[stat.index("(") + 1:end]]
        env["POST_APOLLO_KILL_INSPECTION_CHILD"] = json.dumps(identity, separators=(",", ":"))
        try:
            proc = subprocess.run(
                ["qs", "-p", str(config / "inspection.qml"), "--no-color"],
                cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=22, check=False)
        except subprocess.TimeoutExpired as exc:
            print(exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes)
                  else (exc.stdout or ""))
            raise SystemExit("KILL inspection native fixture timed out") from exc
        print(proc.stdout)
        if (proc.returncode or "KILL_INSPECTION_NATIVE_PASS" not in proc.stdout
                or "KILL_INSPECTION_NATIVE_FAIL" in proc.stdout or child.poll() is not None):
            raise SystemExit("KILL inspection native lifecycle failed")
    finally:
        # Only the subprocess created by this disposable test runner.
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


# Native priority gateway witness. CI container runs as root, but production
# priority control explicitly refuses root. Drop both fixture and child to
# the same unprivileged account, without changing the host's resource limits.
with tempfile.TemporaryDirectory(prefix="kill-priority-") as tmp:
    import json
    import pwd
    import sys
    base = Path(tmp)
    config = base / "scene"
    (config / "services/system").mkdir(parents=True)
    shutil.copytree(ROOT / "services/kill", config / "services/kill")
    shutil.copy2(ROOT / "services/system/TaskSafety.qml", config / "services/system")
    shutil.copy2(ROOT / "tests/cpuplus/fixtures/KillPriorityGatewayNative.qml",
                 config / "priority.qml")
    env = os.environ.copy()
    identity_kwargs = {}
    uid, gid = os.getuid(), os.getgid()
    if os.geteuid() == 0:
        account = pwd.getpwnam("nobody")
        uid, gid = account.pw_uid, account.pw_gid
        identity_kwargs = dict(user=uid, group=gid, extra_groups=[])
        os.chown(base, uid, gid)
        env.update(USER=account.pw_name, LOGNAME=account.pw_name)
    for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
                "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        directory = base / key
        directory.mkdir(mode=0o700)
        if os.geteuid() == 0:
            os.chown(directory, uid, gid)
        env[key] = str(directory)
    env.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="", DISPLAY="")
    child = subprocess.Popen(
        [sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(60)"],
        stdout=subprocess.PIPE, text=True, **identity_kwargs)
    try:
        if child.stdout.readline().strip() != "ready":
            raise SystemExit("Priority disposable child failed to start")
        stat = Path(f"/proc/{child.pid}/stat").read_text()
        end = stat.rindex(")")
        identity = [child.pid, int(stat[end + 2:].split()[19]),
                    stat[stat.index("(") + 1:end]]
        original = os.getpriority(os.PRIO_PROCESS, child.pid)
        env["POST_APOLLO_KILL_PRIORITY_CHILD"] = json.dumps(identity, separators=(",", ":"))
        try:
            proc = subprocess.run(
                ["qs", "-p", str(config / "priority.qml"), "--no-color"],
                cwd=config, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=23, check=False, **identity_kwargs)
        except subprocess.TimeoutExpired as exc:
            print(exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes)
                  else (exc.stdout or ""))
            raise SystemExit("Priority gateway native fixture timed out") from exc
        print(proc.stdout)
        if (proc.returncode or "KILL_PRIORITY_NATIVE_PASS" not in proc.stdout
                or "KILL_PRIORITY_NATIVE_FAIL" in proc.stdout or child.poll() is not None
                or os.getpriority(os.PRIO_PROCESS, child.pid) != original):
            raise SystemExit("Priority gateway native lifecycle failed")
    finally:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
        child.stdout.close()
