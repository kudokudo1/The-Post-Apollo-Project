#!/usr/bin/env python3
"""MACHINE M2: capture exact geometry from a fresh private headless Sway.

NEVER connects to an operator session. GitHub Actions only. Two private
headless outputs, two identically named app windows and one floating window.
Reads are bound to the child's verified socket, not inherited SWAYSOCK.
Nothing is saved in the user's SQLite database or restored to their desktop.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("HEADLESS GEOMETRY TEST REQUIRES GITHUB ACTIONS")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))
from MachineGeometryV2 import project_geometry, compare_to_v1
from MachineSwayRead import normalize
from MachineWindowResolver import _walk_live
from MachineCaptureSaveV2 import capture_and_save
from MachineSaveBridgeV2 import inspect as inspect_for_save, save_request
from MachineGeometryStoreV2 import load_geometry
import MachineCheckpointStore as legacy

APP = "machine-geometry-test"
FLOAT = "machine-geometry-float"
APP_IDS = frozenset((APP, FLOAT))
OUTPUT_NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}\Z")


def wait_for(fn, *, label, timeout=25):
    limit = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < limit:
        try:
            found = fn()
            if found:
                return found
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise AssertionError("TIMEOUT " + label + (": " + last_error if last_error else ""))


def stop_group(process):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.wait(timeout=5)


def tree_windows(tree):
    """Only use actual disposable foot windows; never leak arbitrary tree."""
    found = []
    def walk(node):
        if not isinstance(node, dict):
            return
        app = node.get("app_id")
        if node.get("type") in ("con", "floating_con") and app in APP_IDS:
            found.append(node)
        for kind in ("nodes", "floating_nodes"):
            for child in node.get(kind, []):
                walk(child)
    walk(tree)
    return found


with tempfile.TemporaryDirectory(prefix="machine-m2-headless-") as temp:
    root = Path(temp)
    runtime = root / "runtime"
    runtime.mkdir(mode=0o700)
    config = root / "sway.conf"
    config.write_text(
        "xwayland disable\n"
        "default_border none\n"
        "focus_follows_mouse no\n"
        "output * mode 1024x768\n",
        encoding="utf-8")

    env = os.environ.copy()
    for key in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY", "WAYLAND_SOCKET",
                "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        env.pop(key, None)
    env.update({
        "HOME": str(root),
        "XDG_RUNTIME_DIR": str(runtime),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_DATA_HOME": str(root / "data"),
        "XDG_SESSION_TYPE": "wayland",
        "WLR_BACKENDS": "headless",
        "WLR_HEADLESS_OUTPUTS": "2",
        "WLR_RENDERER": "pixman",
        "WLR_LIBINPUT_NO_DEVICES": "1",
    })

    log = (root / "sway.log").open("wb")
    clients_log = (root / "clients.log").open("wb")
    compositor, clients = None, []
    try:
        compositor = subprocess.Popen(
            ["sway", "--config", str(config)], env=env,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)

        def find_socket():
            if compositor.poll() is not None:
                raise AssertionError("ISOLATED SWAY EXITED")
            found = list(runtime.glob("sway-ipc.*.sock"))
            if len(found) != 1 or not found[0].is_socket():
                return None
            socket = found[0].resolve()
            if socket.parent != runtime:
                raise AssertionError("PRIVATE SOCKET ESCAPED TEMPORARY RUNTIME")
            return str(socket)
        ipc = wait_for(find_socket, label="private Sway socket")

        def run_ipc(argv):
            assert argv[:4] == ["swaymsg", "-r", "-t", argv[3]], argv
            assert argv[3] in ("get_tree", "get_workspaces",
                               "get_outputs", "command")
            return subprocess.run(["swaymsg", "-s", ipc, *argv[1:]],
                                  env=env, capture_output=True, check=True,
                                  timeout=4, shell=False)

        def get(kind):
            assert kind in ("get_tree", "get_workspaces", "get_outputs")
            return json.loads(run_ipc(["swaymsg", "-r", "-t", kind]).stdout)

        def command(value):
            assert isinstance(value, str) and ";" not in value and "\n" not in value
            answer = json.loads(
                run_ipc(["swaymsg", "-r", "-t", "command", value]).stdout)
            assert answer and all(result.get("success") is True for result in answer), answer

        outputs = wait_for(
            lambda: [item for item in get("get_outputs") if item.get("active")]
                    if len([item for item in get("get_outputs") if item.get("active")]) == 2
                    else None,
            label="two private virtual outputs")
        outputs = sorted(outputs, key=lambda item: item["name"])
        first, second = (x["name"] for x in outputs)
        assert OUTPUT_NAME.fullmatch(first) and OUTPUT_NAME.fullmatch(second)
        command("output " + first + " position 0 0")
        command("output " + second + " position 1024 0")
        command("workspace 1")
        command("move workspace to output " + first)
        command("workspace 2")
        command("move workspace to output " + second)
        command("workspace 1")

        def find_wayland():
            found = [x for x in runtime.glob("wayland-*") if x.is_socket()]
            return found[0].name if len(found) == 1 else None
        display = wait_for(find_wayland, label="private Wayland display")
        client_env = dict(env, WAYLAND_DISPLAY=display)

        def launch(app):
            clients.append(subprocess.Popen(
                ["foot", "--app-id=" + app, "sleep", "90"],
                env=client_env, stdin=subprocess.DEVNULL,
                stdout=clients_log, stderr=subprocess.STDOUT,
                start_new_session=True))
        launch(APP)
        launch(APP)
        launch(FLOAT)

        def three_windows():
            rows = _walk_live(get("get_tree"))
            matches = [x for x in rows if x["app_id"] in APP_IDS]
            return matches if len(matches) == 3 else None
        wait_for(three_windows, label="three real test windows")
        # Foot clients can inherit whichever output was last focused by the
        # isolated compositor. Place the fixture explicitly before asserting.
        command('[app_id="' + APP + '"] move container to workspace 1')
        command('[app_id="' + FLOAT + '"] floating enable')
        command('[app_id="' + FLOAT + '"] move container to workspace 2')
        command('[app_id="' + FLOAT + '"] resize set width 440 px height 300 px')

        def placements_ready():
            rows = _walk_live(get("get_tree"))
            paired = [x for x in rows if x["app_id"] == APP and x["workspace"] == "1"]
            lone = [x for x in rows if x["app_id"] == FLOAT and x["workspace"] == "2"]
            active_outputs = [x for x in get("get_outputs") if x.get("active")]
            return len(paired) == 2 and len(lone) == 1 and len(active_outputs) == 2
        try:
            wait_for(placements_ready, label="split and floating workspace placements")
        except AssertionError:
            # Print only synthetic app/workspace summaries, never raw tree or
            # arbitrary foot titles. Useful when a Sway version differs.
            rows = _walk_live(get("get_tree"))
            summary = [(x["app_id"], x["workspace"], x["floating"])
                       for x in rows if x["app_id"] in APP_IDS]
            print("HEADLESS PLACEMENT SUMMARY:", summary, flush=True)
            # List only fixture app IDs and Sway node types. This reveals
            # whether floating windows become floating_con rather than con.
            shapes = []
            def inspect_shape(node, workspace=None):
                if node.get("type") == "workspace":
                    workspace = node.get("name")
                if node.get("app_id") in APP_IDS:
                    shapes.append((node.get("type"), node.get("app_id"),
                                   workspace, node.get("floating")))
                for key in ("nodes", "floating_nodes"):
                    for child in node.get(key, []):
                        inspect_shape(child, workspace)
            inspect_shape(get("get_tree"))
            print("HEADLESS NODE SHAPES:", shapes, flush=True)
            print("HEADLESS WORKSPACES:", [
                (x["name"], x["output"]) for x in get("get_workspaces")
                if x["name"] in ("1", "2")], flush=True)
            raise

        live_outputs = get("get_outputs")
        live_workspaces = get("get_workspaces")
        live_tree = get("get_tree")
        test_windows = tree_windows(live_tree)
        assert len(test_windows) == 3
        ids = [x["id"] for x in test_windows]
        assert len(set(ids)) == 3
        keys = {id_: str(uuid.uuid4()) for id_ in ids}

        captured = project_geometry(
            live_outputs, live_workspaces, live_tree, window_keys=keys)
        assert len(captured["outputs"]) == 2
        assert len(captured["windows"]) == 3
        assert captured["coordinate_space"] == "sway-logical-pixels"
        assert captured["session_identity_verified"] is False
        apps = [x for x in captured["windows"] if x["app_id"] == APP]
        floaters = [x for x in captured["windows"] if x["app_id"] == FLOAT]
        assert len(apps) == 2 and len(floaters) == 1
        assert apps[0]["window_key"] != apps[1]["window_key"]
        assert all(x["workspace"] == "1" and not x["floating"] for x in apps)
        assert floaters[0]["workspace"] == "2" and floaters[0]["floating"]
        assert all(x["rect"]["width"] > 100 and x["rect"]["height"] > 100
                   for x in captured["windows"])
        assert apps[0]["rect"] != apps[1]["rect"], "Sway did not tile the windows"

        byname = {x["connector"]: x for x in captured["outputs"]}
        assert byname[first]["rect"]["x"] == 0
        assert byname[second]["rect"]["x"] == 1024
        mapping = {x["name"]: x for x in captured["workspaces"]}
        assert mapping["1"]["output"] == first
        assert mapping["2"]["output"] == second

        # The v2 snapshot must agree with the strict v1 projection of the
        # SAME native frame without assuming persistent window identity.
        original = normalize(live_outputs, live_workspaces, live_tree)
        saved_v1 = {
            "schema_version": 1,
            "kind": "sway-layout-selection-preview",
            "preview_only": True,
            "captured_at_utc": "2026-11-09T12:00:00+00:00",
            "label": "ISOLATED GEOMETRY TEST",
            "outputs": [{"connector": x["name"], "rect": x["rect"]}
                        for x in original["outputs"]],
            "workspaces": [{"name": x["name"], "output": x["output"]}
                           for x in original["workspaces"]],
            "windows": original["windows"],
        }
        assert compare_to_v1(captured, saved_v1) == {
            "v1_window_multiset_matches": True,
            "exact_session_match": False,
            "safe_restore_actions": [],
        }
        dumped = json.dumps(captured)
        assert "con_id" not in dumped
        assert "pid" not in dumped
        assert "title" not in dumped
        assert "url" not in dumped

        # Real end-to-end SAVE: two new read rounds against the exact same
        # private compositor socket, then atomic v1 + v2 persistence under
        # the same throwaway XDG root. Never touch the runner's home store.
        previous_xdg = os.environ.get("XDG_DATA_HOME")
        try:
            os.environ["XDG_DATA_HOME"] = str(root / "data")
            result = capture_and_save(
                label="CI DESKTOP SAVE",
                read_runner=lambda command, **options: run_ipc(command))
            assert result["status"] == "saved", result
            assert result["geometry_available"] is True
            assert result["session_identity_verified"] is False
            cid = result["checkpoint"]["id"]
            old_saved = legacy.load(cid)
            geometry_saved = load_geometry(cid)
            assert old_saved["document"]["label"] == "CI DESKTOP SAVE"
            assert old_saved["checkpoint"]["counts"]["windows"] == 3
            assert geometry_saved["status"] == "loaded"
            assert len(geometry_saved["geometry"]["outputs"]) == 2
            assert len(geometry_saved["geometry"]["windows"]) == 3
            assert len({w["window_key"] for w in geometry_saved["geometry"]["windows"]}) == 3
            assert sum(w["floating"] for w in geometry_saved["geometry"]["windows"]) == 1
            assert all(w["rect"]["width"] > 100 for w in geometry_saved["geometry"]["windows"])
            assert legacy.db_path().parent.is_relative_to(root)

            # Optional scope must use the same capture coordinator and
            # private SQLite writer, without a second capture-preview path.
            scoped = capture_and_save(
                label="CI FIRST MONITOR ONLY",
                selection={"outputs": [first]},
                read_runner=lambda command, **options: run_ipc(command))
            assert scoped["status"] == "saved", scoped
            assert scoped["checkpoint"]["counts"] == {
                "outputs": 1, "workspaces": 1, "windows": 2,
            }, scoped["checkpoint"]["counts"]
            selected = load_geometry(scoped["checkpoint"]["id"])
            assert selected["status"] == "loaded"
            assert [row["connector"] for row in
                    selected["geometry"]["outputs"]] == [first]
            assert [row["name"] for row in
                    selected["geometry"]["workspaces"]] == ["1"]
            assert all(row["app_id"] == APP
                       for row in selected["geometry"]["windows"])
            assert len({row["window_key"] for row in
                        selected["geometry"]["windows"]}) == 2
            assert legacy.load(cid)["checkpoint"]["counts"]["windows"] == 3
            # CUSTOMIZE review/selected save uses opaque per-capture keys,
            # never a guessed app_id or a stale window index.
            bound_reader = lambda command, **options: run_ipc(command)
            inspected = inspect_for_save(read_runner=bound_reader)
            assert inspected["status"] == "ready"
            assert inspected["counts"]["windows"] == 3
            left_window = next(x for x in inspected["windows"]
                               if x["app_id"] == APP and x["workspace"] == "1")
            selected_result = save_request({
                "label": "CI ONE WINDOW",
                "review": inspected["review"],
                "selection": {"windows": [left_window["window_key"]]},
            }, read_runner=bound_reader)
            assert selected_result["status"] == "saved"
            assert selected_result["checkpoint"]["counts"]["windows"] == 1
            chosen_record = load_geometry(selected_result["checkpoint"]["id"])
            assert chosen_record["geometry"]["windows"][0]["window_key"] == left_window["window_key"]
            assert chosen_record["geometry"]["windows"][0]["rect"] == left_window["rect"]
            assert legacy.load(cid)["checkpoint"]["counts"]["windows"] == 3
            # Exercise the exact Python -I entrypoint used by TimeW.qml,
            # not just a Python import with a preconfigured sys.path.
            # This subprocess inherits only the disposable CI XDG runtime,
            # with an explicitly pinned private child Sway socket.
            bridge_env = dict(client_env, SWAYSOCK=ipc,
                              XDG_DATA_HOME=str(root / "data"))
            bridge_cli = str(ROOT / "services/time/MachineSaveBridgeV2.py")
            cli_inspect = subprocess.run(
                ["python3", "-B", "-I", bridge_cli, "inspect"],
                env=bridge_env, capture_output=True, timeout=15)
            assert cli_inspect.returncode == 0, "ISOLATED CLI INSPECT FAILED"
            review_data = json.loads(cli_inspect.stdout)
            assert review_data["status"] == "ready"
            assert review_data["counts"]["outputs"] == 2
            assert review_data["counts"]["windows"] == 3

            cli_request = json.dumps({
                "label": "CI ACTUAL CLI SAVE",
                "review": None,
                "selection": None,
            }).encode() + b"\n"
            cli_save = subprocess.run(
                ["python3", "-B", "-I", bridge_cli, "save"],
                input=cli_request, env=bridge_env,
                capture_output=True, timeout=15)
            assert cli_save.returncode == 0, "ISOLATED CLI SAVE FAILED"
            saved_cli = json.loads(cli_save.stdout)
            assert saved_cli["status"] == "saved"
            assert saved_cli["verification"] == {
                "status": "readback_verified",
                "counts": {"outputs": 2, "workspaces": 2, "windows": 3},
                "geometry": True, "legacy": True,
            }
            assert saved_cli["checkpoint"]["counts"]["windows"] == 3
            cli_loaded = load_geometry(saved_cli["checkpoint"]["id"])
            assert cli_loaded["status"] == "loaded"
            assert len(cli_loaded["geometry"]["windows"]) == 3
            print("MACHINE PYTHON -I CLI // INSPECT AND SAVE TO PRIVATE SQLITE PASS")
            print("MACHINE M2 CUSTOM REVIEW-BOUND ONE-WINDOW SAVE // REAL SWAY PASS")
            print("MACHINE M2 CUSTOM SAVE // REAL HEADLESS SWAY SQLITE PASS")
            print("MACHINE M2 AUTOMATIC SAVE // REAL HEADLESS SWAY SQLITE PASS")
        finally:
            if previous_xdg is None:
                os.environ.pop("XDG_DATA_HOME", None)
            else:
                os.environ["XDG_DATA_HOME"] = previous_xdg
        print("MACHINE M2 GEOMETRY // REAL HEADLESS SWAY PASS")
        print("2 virtual outputs // 2 tiled duplicate-app windows // 1 floating")
        print("exact rectangles and split hierarchy // v1 matching // no live operator access")
    finally:
        for client in clients:
            stop_group(client)
        stop_group(compositor)
        clients_log.close()
        log.close()
