#!/usr/bin/env python3
"""Real Quickshell 0.3.0 H1 lifecycle smoke in an isolated fake-reader tree.

NEVER installs native reader, touches the operator's desktop, opens real
Hospital records or invokes PX. The production QML is copied verbatim except
one exact fixed reader-path substitution into a temp directory. A separate
Node test already exercises JS callbacks; this tests actual Qt/QML objects,
Timer delivery, Process.running=false and child termination on a CI runner.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/hospital/HospitalDoctorService.qml"
POLICY = ROOT / "services/hospital/HospitalDoctorDirectoryExitPolicy.js"
SHELL = ROOT / "tests/hospital/quickshell/shell.qml"
FAKE = ROOT / "tests/hospital/quickshell/fake_doctor_reader.py"
ORIGINAL = '"/usr/libexec/post-apollo/hospital/hospital-room-read"'
NEEDED_MARKERS = (
    "H1_QS_LIFECYCLE_TIMEOUT_PASS",
    "H1_QS_LIFECYCLE_OLD_TIMER_REFUSED",
    "H1_QS_LIFECYCLE_RETRY_PASS",
)


def checked_copy(source, destination):
    destination.write_bytes(source.read_bytes())


def pid_exists(pid):
    """A zombie has NOT been reaped; refuse to claim lifecycle success."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def fake_pid_is_ours(pid, fake_path):
    cmd_path = Path(f"/proc/{pid}/cmdline")
    try:
        cmd = cmd_path.read_bytes().replace(b"\x00", b" ")
    except (FileNotFoundError, PermissionError):
        return False
    return str(fake_path).encode() in cmd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quickshell", required=True)
    args = parser.parse_args()
    qs = Path(args.quickshell).resolve()
    if not qs.is_file():
        raise RuntimeError("PINNED_QUICKSHELL_BINARY_MISSING")
    if not all(p.is_file() for p in (SOURCE, POLICY, SHELL, FAKE)):
        raise RuntimeError("H1_FIXTURE_SOURCE_MISSING")

    version = subprocess.run([str(qs), "--version"], capture_output=True,
                             text=True, timeout=15)
    version_text = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or "0.3.0" not in version_text:
        raise RuntimeError("QUICKSHELL_VERSION_MISMATCH: " + version_text[:350])
    print("H1 REAL QUICKSHELL VERSION // " + version_text, flush=True)

    with tempfile.TemporaryDirectory(prefix="h1-quickshell-", dir="/tmp") as d:
        work = Path(d)
        service = work / "service"
        state = work / "state"
        home = work / "home"
        runtime = work / "run"
        for folder in (service, state, home, runtime,
                       work / "cache", work / "config", work / "data"):
            folder.mkdir(mode=0o700)
        runtime.chmod(0o700)
        fake = work / "hospital-room-read"
        checked_copy(FAKE, fake)
        fake.chmod(0o700)
        checked_copy(POLICY, service / POLICY.name)
        checked_copy(SHELL, work / "shell.qml")

        raw = SOURCE.read_text(encoding="utf-8")
        if raw.count(ORIGINAL) != 1:
            raise RuntimeError("NOT_EXACTLY_ONE_NATIVE_CLIENT_PATH")
        replacement = json.dumps(str(fake))
        patched = raw.replace(ORIGINAL, replacement)
        # This is the *only* permitted difference from production QML.
        if patched.replace(replacement, ORIGINAL) != raw:
            raise RuntimeError("UNEXPECTED_QML_FIXTURE_MODIFICATION")
        (service / SOURCE.name).write_text(patched, encoding="utf-8")

        env = os.environ.copy()
        env.update({
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_CACHE_HOME": str(work / "cache"),
            "XDG_DATA_HOME": str(work / "data"),
            "XDG_RUNTIME_DIR": str(runtime),
            "H1_DISPOSABLE_STATE_DIR": str(state),
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "NO_COLOR": "1",
        })
        if not env.get("DISPLAY"):
            raise RuntimeError("NO_DISPOSABLE_XVFB_DISPLAY")

        cmd = [str(qs), "--path", str(work / "shell.qml"), "--no-color"]
        print("H1 REAL QUICKSHELL START // disposable offscreen Qt fixture", flush=True)
        proc = subprocess.Popen(cmd, env=env, cwd=work,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        try:
            output, _ = proc.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate(timeout=10)
            raise RuntimeError("QUICKSHELL_LIFECYCLE_TEST_HUNG\n" + output[-7500:])
        print(output[-15000:], flush=True)
        if proc.returncode != 0:
            raise RuntimeError("QUICKSHELL_NONZERO_EXIT: " + str(proc.returncode))
        if "H1_QS_LIFECYCLE_FAIL" in output:
            raise RuntimeError("QUICKSHELL_QML_ASSERTION_FAILED")
        for marker in NEEDED_MARKERS:
            if marker not in output:
                raise RuntimeError("QUICKSHELL_MISSING_WITNESS: " + marker)

        events_file = state / "events.jsonl"
        if not events_file.is_file():
            raise RuntimeError("FAKE_READER_NEVER_EXECUTED")
        events = [json.loads(line) for line in
                  events_file.read_text(encoding="utf-8").splitlines()]
        def has(invocation, name):
            return any(x["invocation"] == invocation and
                       x["event"] == name for x in events)
        for invocation, event in (
            (1, "start"), (1, "stdout_closed"), (1, "sigterm"),
            (2, "start"), (2, "success")
        ):
            if not has(invocation, event):
                raise RuntimeError(f"FAKE_READER_MISSING_{invocation}_{event}")
        if any(x["invocation"] > 2 for x in events):
            raise RuntimeError("UNEXPECTED_EXTRA_NATIVE_READ")

        # Termination is not sufficient if the child remains alive/zombied.
        # Observe actual PIDs after Quickshell exits. If a fixture process
        # survives, kill ONLY our own verified fake executable and FAIL.
        child_pids = {x["pid"] for x in events if x["event"] == "start"}
        alive = set(child_pids)
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and alive:
            alive = {pid for pid in alive if pid_exists(pid)}
            if alive:
                time.sleep(0.1)
        if alive:
            for pid in alive:
                if fake_pid_is_ours(pid, fake):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            raise RuntimeError("FAKE_READER_NOT_REAPED: " + repr(sorted(alive)))
        print(
            "HOSPITAL H1 REAL QUICKSHELL // PASS // pinned 0.3.0, "
            "hung fake reader terminated and reaped, 12-second timeout, "
            "stale timer refused and immediate fresh retry accepted "
            "// DISPOSABLE CI ONLY", flush=True
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("HOSPITAL H1 REAL QUICKSHELL // FAIL // " + str(e), file=sys.stderr)
        raise SystemExit(1)
