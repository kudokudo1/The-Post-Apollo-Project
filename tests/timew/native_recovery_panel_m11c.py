#!/usr/bin/env python3
"""Real Quickshell panel in an isolated CI Xvfb session, not a desktop install."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
import MachineCheckpointStore as legacy
from MachineGeometryV2 import project_geometry
import MachineV3OriginalSaveIdentity as original
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore, suggested_path as exact_path
from MachineV3LocalFractionalAttemptJournal import LocalFractionalAttemptJournal, suggested_path as journal_path
from MachineV2ExactLogicalGeometry import capture_value, PHASE_CURRENT
from MachineV3CoordinatedLocalSave import save_once

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"
KEY_C = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def leaf(con, app, rectangle, *, floating=False):
    return {
        "type": "con", "id": con, "app_id": app,
        "rect": rectangle, "percent": 0.5 if app == "brave" else None,
        "layout": "none", "floating": "user_on" if floating else "auto_off",
        "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "PRIVATE TITLE",
        "pid": 7700,
    }


def fixture():
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(2560, 0, 1360, 768), "scale": 1.0,
         "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 2560, 1440),
            "nodes": [leaf(101, "brave", rect(0, 0, 1280, 1440)),
                      leaf(102, "brave", rect(1280, 0, 1280, 1440))],
            "floating_nodes": [],
        }]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [{
            "type": "workspace", "name": "2", "layout": "splith",
            "rect": rect(2560, 0, 1360, 768), "nodes": [],
            "floating_nodes": [
                leaf(103, "kitty", rect(2790, 40, 700, 600), floating=True)],
        }]},
    ]}
    geometry = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: KEY_A, 102: KEY_B, 103: KEY_C})
    legacy_doc = {
        "schema_version": 1, "kind": "sway-layout-selection-preview",
        "preview_only": True, "label": "Exact work layout",
        "captured_at_utc": "2026-11-09T17:48:00+00:00",
        "outputs": [
            {"connector": item["connector"], "rect": item["rect"]}
            for item in geometry["outputs"]],
        "workspaces": [
            {"name": item["name"], "output": item["output"]}
            for item in geometry["workspaces"]],
        "windows": [
            {"app_id": item["app_id"], "workspace": item["workspace"],
             "floating": item["floating"]}
            for item in geometry["windows"]],
    }
    return legacy_doc, geometry


old, geo = fixture()
exact = [
    dict(window_key=w["window_key"], app_id=w["app_id"], output_id=w["output"],
         workspace_id=w["workspace"], value=capture_value(
             PHASE_CURRENT, x=12.125, y=math.nextafter(92.5, math.inf),
             width=700.5, height=600.25))
    for w in geo["windows"]
]

def owners():
    return LocalFractionalAttemptJournal(journal_path()), LocalExactCaptureStore(exact_path())

def save(cid, obs=exact, **kwargs):
    journal, store = owners()
    return save_once(identity=cid, v1_document=old, geometry_document=geo,
                     observations=obs, journal=journal, store=store, **kwargs)



PREPARED_ID = "11111111-1111-4111-8111-111111111111"
COMPLETE_ID = "22222222-2222-4222-8222-222222222222"
MARKERS = ("M11C_NATIVE_LIST_PASS", "M11C_NATIVE_INSPECT_RESIZE_PASS",
           "M11C_NATIVE_CONTEXT_PASS", "M11C_NATIVE_DEADLINE_PASS",
           "M11C_NATIVE_NONZERO_PASS", "M11C_NATIVE_PASS")

# A controlled PATH shim passes through to the actual unchanged Python bridge,
# except for two delays and one deliberately failed exit. Never emits fake JSON.
WRAPPER = '''import json, os, sys, time
from pathlib import Path
trace = Path(os.environ["TIMEW_M11C_TRACE"])
args = sys.argv[1:]
expected = Path(os.environ["TIMEW_M11C_ROOT"]) / "services/time/MachineV3LocalSaveRecoveryUiRead.py"
assert len(args) in (5,6) and args[:2] == ["-B","-I"]
assert Path(args[2]).resolve() == expected and args[3] in ("list","inspect")
assert (len(args) == 5) == (args[3] == "list")
n = len(trace.read_text().splitlines()) + 1 if trace.exists() else 1
with trace.open("a") as f:
    f.write(json.dumps({"n": n, "args": args[3:]}) + "\\n")
    f.flush()
if n == 4:
    time.sleep(2)
if n == 6:
    time.sleep(47)
if n == 7:
    sys.exit(9)
os.execv(os.environ["TIMEW_M11C_PYTHON"], [os.environ["TIMEW_M11C_PYTHON"], *args])
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_M11C_DISPOSABLE_CI") != "1"
            or not os.environ.get("DISPLAY")):
        raise RuntimeError("M11C_REFUSES_NON_CI_NATIVE_LAUNCH")
    qs = shutil.which("qs") or shutil.which("quickshell")
    if not qs:
        raise RuntimeError("M11C_REAL_QUICKSHELL_UNAVAILABLE")
    version = subprocess.run([qs, "--version"], text=True,
                             capture_output=True, timeout=10)
    assert version.returncode == 0 and "0.3.2" in version.stdout + version.stderr
    print("M11C REAL QUICKSHELL VERSION // " + (version.stdout + version.stderr).strip())

    with tempfile.TemporaryDirectory(prefix="timew-m11c-native-") as temp:
        work = Path(temp)
        # Use the actual repository panel, policy, controls and Python readers,
        # copied byte-for-byte, never the production shell or desktop config.
        (work / "widgets").mkdir()
        (work / "services").mkdir()
        shutil.copy2(ROOT / "widgets/MachineSaveRecoveryPanel.qml",
                     work / "widgets/MachineSaveRecoveryPanel.qml")
        shutil.copytree(ROOT / "components", work / "components")
        shutil.copytree(SERVICE, work / "services/time")
        shutil.copy2(ROOT / "tests/timew/fixtures/M11cRecoveryNative.qml", work / "shell.qml")
        assert digest(work / "widgets/MachineSaveRecoveryPanel.qml") == digest(ROOT / "widgets/MachineSaveRecoveryPanel.qml")
        assert digest(work / "services/time/MachineV3LocalSaveRecoveryUiRead.py") == digest(SERVICE / "MachineV3LocalSaveRecoveryUiRead.py")
        env = os.environ.copy()
        for key, sub in (("HOME","home"),("XDG_CONFIG_HOME","config"),
                         ("XDG_DATA_HOME","data"),("XDG_STATE_HOME","state"),
                         ("XDG_CACHE_HOME","cache"),("XDG_RUNTIME_DIR","runtime")):
            p = work / sub
            p.mkdir(mode=0o700)
            env[key] = str(p)
        env.update({
            "QT_QPA_PLATFORM": "xcb", "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1", "WAYLAND_DISPLAY": "",
            "NO_COLOR": "1", "POST_APOLLO_TIMEW_M11C": "CI_DISPOSABLE_ONLY",
            "TIMEW_M11C_ROOT": str(work), "TIMEW_M11C_TRACE": str(work / "trace.jsonl"),
            "TIMEW_M11C_PYTHON": sys.executable,
        })
        env.pop("SWAYSOCK", None)
        env.pop("I3SOCK", None)
        # No live XDG path is consulted by the fixture writer.
        previous = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = env["XDG_DATA_HOME"]
        try:
            (Path(env["XDG_DATA_HOME"]) / "post-apollo").mkdir(mode=0o700)
            def stop(stage):
                if stage == "after_reserve":
                    raise ValueError("disposable interruption")
            assert save(PREPARED_ID, stage_hook=stop)["ordinary_status"] == original.PREPARED
            assert save(COMPLETE_ID)["status"] == "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED"
            j, s = owners()
            paths = [legacy.db_path(), j.path, s.path]
            assert all(p.is_relative_to(work) for p in paths)
            before = {p: digest(p) for p in paths}
        finally:
            if previous is None:
                os.environ.pop("XDG_DATA_HOME", None)
            else:
                os.environ["XDG_DATA_HOME"] = previous
        shim = work / "bin"
        shim.mkdir(mode=0o700)
        wrapper = shim / "python3"
        wrapper.write_text("#!" + sys.executable + "\n" + WRAPPER)
        wrapper.chmod(0o700)
        env["PATH"] = str(shim) + os.pathsep + env["PATH"]
        process = subprocess.Popen([qs, "-p", str(work / "shell.qml"), "--no-color"],
                                   cwd=work, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True,
                                   errors="replace", start_new_session=True)
        try:
            output, _ = process.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate(timeout=10)
            print(output[-16000:])
            raise RuntimeError("M11C_NATIVE_PROCESS_WATCHDOG")
        finally:
            # The fixture process group is ours; prevent leaked delayed readers.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        print(output[-18000:])
        assert process.returncode == 0 and "M11C_NATIVE_FAIL" not in output
        for marker in MARKERS:
            assert marker in output, "missing " + marker
        events = [json.loads(x) for x in (work / "trace.jsonl").read_text().splitlines()]
        assert [x["n"] for x in events] == list(range(1, 9))
        assert [x["args"][0] for x in events] == ["list","inspect","inspect","list","list","inspect","list","list"]
        assert [x["args"][2] for x in events if x["args"][0] == "inspect"] == [PREPARED_ID, COMPLETE_ID, PREPARED_ID]
        assert len({x["args"][1] for x in events}) == 8
        assert {p: digest(p) for p in paths} == before, "native panel changed fixture main files"
        print("TIMEW M11C // REAL QUICKSHELL 8 explicit Process launches, real 45s deadline, local data unchanged PASS")


if __name__ == "__main__":
    main()
