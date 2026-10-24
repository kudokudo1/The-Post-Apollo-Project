#!/usr/bin/env python3
"""M1m: real Sway IPC integration, confined to a fresh CI-only headless session.

NEVER connects to the user's SWAYSOCK. All swaymsg calls use -s with the
new child's socket inside a private TemporaryDirectory. No live UI wiring.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time

# Fail shut in normal desktops, even if the operator runs this test by mistake.
if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("M1m headless integration is only enabled on GitHub Actions")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))
from MachineMoveJournal import MoveJournal
from MachineWindowMovePilot import MoveRefused, execute_one, preview_one
from MachineWindowResolver import _walk_live

APP = "machine-ci-window"
ANCHOR = "machine-ci-anchor"


def wait_for(fn, *, seconds=24, label="state"):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            value = fn()
            if value:
                return value
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            last = str(exc)
        time.sleep(.2)
    raise AssertionError("TIMEOUT " + label + (": " + last if last else ""))


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


with tempfile.TemporaryDirectory(prefix="machine-m1m-") as tmp:
    base = Path(tmp)
    runtime = base / "runtime"
    runtime.mkdir(mode=0o700)
    conf = base / "sway.conf"
    conf.write_text(
        "xwayland disable\n"
        "default_border none\n"
        "focus_follows_mouse no\n"
        "output * mode 1024x768\n", encoding="utf-8")
    # The child session is independent of any user's Wayland/Sway/DBus sockets.
    env = os.environ.copy()
    for key in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY", "WAYLAND_SOCKET",
                "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        env.pop(key, None)
    env.update({
        "HOME": str(base), "XDG_RUNTIME_DIR": str(runtime),
        "XDG_CONFIG_HOME": str(base / "config"),
        "XDG_DATA_HOME": str(base / "data"),
        "XDG_SESSION_TYPE": "wayland",
        "WLR_BACKENDS": "headless",
        "WLR_HEADLESS_OUTPUTS": "1",
        "WLR_RENDERER": "pixman",
        "WLR_LIBINPUT_NO_DEVICES": "1",
    })
    log = (base / "sway.log").open("wb")
    clients_log = (base / "clients.log").open("wb")
    compositor = None
    clients = []
    try:
        compositor = subprocess.Popen(
            ["sway", "--config", str(conf)],
            env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)
        def find_socket():
            if compositor.poll() is not None:
                raise AssertionError("headless sway exited early")
            possible = list(runtime.glob("sway-ipc.*.sock"))
            if len(possible) != 1 or not possible[0].is_socket():
                return None
            found = possible[0].resolve()
            if found.parent != runtime:
                raise AssertionError("IPC socket escaped temporary runtime")
            return str(found)
        ipc = wait_for(find_socket, label="private Sway IPC socket")

        def ipc_run(argv, **kw):
            if not argv or argv[0] != "swaymsg":
                raise AssertionError("unexpected executable")
            if any(str(item).find(";") >= 0 for item in argv):
                raise AssertionError("multi-command injection")
            return subprocess.run(
                ["swaymsg", "-s", ipc, *argv[1:]], env=env, **kw)

        def read(argv, **kw):
            if argv not in (
                ["swaymsg", "-r", "-t", "get_outputs"],
                ["swaymsg", "-r", "-t", "get_workspaces"],
                ["swaymsg", "-r", "-t", "get_tree"]):
                raise AssertionError("unexpected Sway read path")
            return ipc_run(argv, **kw)

        commands = []
        def move_command(argv, **kw):
            commands.append(argv)
            assert len(commands) == 1, "more than one move attempted"
            assert argv[:4] == ["swaymsg", "-r", "-t", "command"]
            assert re.fullmatch(
                r"\[con_id=[1-9][0-9]*\] move --no-auto-back-and-forth "
                r"container to workspace 2", argv[4])
            assert kw == {"check": False, "capture_output": True,
                          "timeout": 3, "shell": False}
            return ipc_run(argv, **kw)

        def get(typ):
            x = ipc_run(
                ["swaymsg", "-r", "-t", typ],
                capture_output=True, check=True, timeout=3, shell=False)
            return json.loads(x.stdout)
        def command(text):
            x = ipc_run(
                ["swaymsg", "-r", "-t", "command", text],
                capture_output=True, check=True, timeout=3, shell=False)
            data = json.loads(x.stdout)
            assert len(data) == 1 and data[0]["success"] is True, data

        def find_wayland():
            possible = [p for p in runtime.glob("wayland-*") if p.is_socket()]
            return possible[0].name if len(possible) == 1 else None
        wayland_display = wait_for(find_wayland, label="private Wayland display")
        client_env = dict(env, WAYLAND_DISPLAY=wayland_display)
        active = wait_for(
            lambda: next((x for x in get("get_outputs") if x.get("active")), None),
            label="headless output")

        def launch(app):
            clients.append(subprocess.Popen(
                ["foot", "--app-id=" + app, "sleep", "90"],
                env=client_env, stdin=subprocess.DEVNULL,
                stdout=clients_log, stderr=subprocess.STDOUT,
                start_new_session=True))
        launch(APP)
        launch(ANCHOR)
        def windows():
            return _walk_live(get("get_tree"))
        wait_for(lambda: len([x for x in windows() if x["app_id"] in (APP, ANCHOR)]) == 2,
                 label="two isolated test windows")
        command('[app_id="' + ANCHOR + '"] move container to workspace 2')

        def ready():
            rows = windows()
            t = [x for x in rows if x["app_id"] == APP]
            a = [x for x in rows if x["app_id"] == ANCHOR]
            return len(t) == len(a) == 1 and t[0]["workspace"] == "1" and a[0]["workspace"] == "2"
        wait_for(ready, label="two populated workspaces")
        workspaces = get("get_workspaces")
        assert set(x["name"] for x in workspaces) >= {"1", "2"}
        selected = next(x for x in windows() if x["app_id"] == APP)
        assert selected["con_id"] is not None and not selected["floating"]
        saved = {
            "schema_version": 1, "kind": "sway-layout-selection-preview",
            "preview_only": True,
            "captured_at_utc": "2026-10-24T12:00:00+00:00",
            "label": "M1m TEST",
            "outputs": [{"connector": active["name"], "rect": active["rect"]}],
            "workspaces": [{"name": str(n), "output": active["name"]}
                           for n in (1, 2)],
            "windows": [{"app_id": APP, "workspace": "2", "floating": False}]
        }
        request = {
            "intent": "single-existing-window-workspace-move",
            "approved": True, "app_id": APP,
            "con_id": selected["con_id"],
            "from_workspace": "1", "to_workspace": "2"
        }

        # Preview and wrong-ID rejection must never issue any command.
        before = preview_one(saved, dict(request, approved=False), read_runner=read)
        assert before["status"] == "ready_for_review" and not before["executable"]
        journal = MoveJournal(base / "journal" / "move-operations.db")
        try:
            execute_one(saved, dict(request, con_id=request["con_id"] + 9000),
                        read_runner=read, command_runner=move_command, journal=journal)
            raise AssertionError("stale live container ID accepted")
        except MoveRefused:
            pass
        assert commands == [] and not journal.path.exists()

        # One real move, ONLY inside the newly spawned temporary headless Sway.
        result = execute_one(saved, request, read_runner=read,
                             command_runner=move_command, journal=journal)
        assert result["status"] == "verified_moved", result["status"]
        assert result["observed_workspace"] == "2"
        assert len(commands) == 1
        assert journal.pending() == []
        assert journal.get(result["operation_id"])["phase"] == "verified_moved"
        current = [x for x in windows() if x["app_id"] == APP]
        assert len(current) == 1 and current[0]["workspace"] == "2"
        anchor = [x for x in windows() if x["app_id"] == ANCHOR]
        assert len(anchor) == 1 and anchor[0]["workspace"] == "2"
        assert result["no_automatic_undo"] is True

        # Old approval/request cannot be reused after the window has moved.
        try:
            execute_one(saved, request, read_runner=read,
                        command_runner=move_command, journal=journal)
            raise AssertionError("stale approved request was replayed")
        except MoveRefused:
            pass
        assert len(commands) == 1
        print("MACHINE M1m: HEADLESS REAL SWAY MOVE PASS / ISOLATED IPC / JOURNALED")
    finally:
        for p in clients:
            stop_group(p)
        stop_group(compositor)
        clients_log.close()
        log.close()
