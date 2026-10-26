#!/usr/bin/env python3
"""MACHINE M2d4: real Kitty native-format read in a DISPOSABLE CI sandbox.

This script MUST NOT be run on the operator's workstation. The only caller
is the dedicated Ubuntu GitHub Actions/Xvfb job. It creates a new isolated
Kitty instance with its own temporary HOME, UNIX socket and child process,
reads it once, validates the redacted projection, then tears it all down.
No existing user Kitty socket or user configuration is accessed.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time

# Explicit CI-only gate; this is not user authorization for a local run.
if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get(
        "MACHINE_KITTY_ISOLATED_CI") != "explicit_disposable_runner":
    raise SystemExit("MACHINE KITTY COMPATIBILITY TEST REQUIRES ISOLATED CI")
if not os.environ.get("DISPLAY") or not shutil.which("Xvfb"):
    raise SystemExit("ISOLATED X11 SERVER NOT AVAILABLE")
if not shutil.which("kitty") or not shutil.which("kitten"):
    raise SystemExit("KITTY AND KITTEN MUST BE INSTALLED IN DISPOSABLE CI")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineKittyRead import (
    KittyInventoryError, read_existing_kitty_inventory,
)

PRIVATE_SENTINEL = "MACHINE_TEST_PRIVATE_TERMINAL_CONTENT"
TIMEOUT_SECONDS = 18

# Do not capture or print raw Kitty's output, it can include private fields.
with tempfile.TemporaryDirectory(prefix="machine-kitty-ci-") as folder:
    base = Path(folder)
    os.chmod(base, 0o700)
    socket_pattern = "inventory-*"
    os_socket = str(base / "inventory-{kitty_pid}")
    child_home = base / "home"
    child_home.mkdir(mode=0o700)
    env = os.environ.copy()
    env["HOME"] = str(child_home)
    env["XDG_CONFIG_HOME"] = str(child_home / "config")
    env["XDG_DATA_HOME"] = str(child_home / "data")
    env["XDG_CACHE_HOME"] = str(child_home / "cache")
    env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    env.pop("KITTY_LISTEN_ON", None)
    env.pop("KITTY_WINDOW_ID", None)
    argv = [
        "kitty", "--config", "NONE",
        "-o", "allow_remote_control=socket-only",
        "--listen-on", "unix:" + os_socket,
        "/bin/sh", "-c", "printf '%s\\n' '" + PRIVATE_SENTINEL + "'; sleep 90",
    ]
    # A private socket requires restrictive umask, not just a private parent.
    old_mask = os.umask(0o077)
    try:
        proc = subprocess.Popen(
            argv, cwd=str(child_home), env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
    finally:
        os.umask(old_mask)
    try:
        endpoint = None
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise AssertionError("DISPOSABLE KITTY EXITED BEFORE SOCKET READ")
            candidates = [
                p for p in base.glob(socket_pattern) if p.is_socket()
            ]
            if len(candidates) > 1:
                raise AssertionError("AMBIGUOUS DISPOSABLE KITTY SOCKET")
            if len(candidates) == 1:
                endpoint = candidates[0]
                break
            time.sleep(0.15)
        if endpoint is None:
            raise AssertionError("DISPOSABLE KITTY SOCKET DID NOT APPEAR")
        info = os.lstat(endpoint)
        assert info.st_uid == os.geteuid()
        assert stat.S_ISSOCK(info.st_mode)
        assert info.st_mode & 0o077 == 0
        assert endpoint.parent == base

        # Socket existence can precede acceptance of Kitty control messages.
        # Readiness requests are the same fixed native READ-ONLY command,
        # but their raw JSON/stderr must never appear in build logs.
        native_argv = [
            "kitten", "@", "--to", "unix:" + str(endpoint),
            "ls", "--output-format=json",
        ]
        ready = False
        last_failure = "no_successful_read"
        for attempt in range(25):
            if proc.poll() is not None:
                raise AssertionError("DISPOSABLE KITTY TERMINATED DURING READINESS")
            try:
                probe = subprocess.run(
                    native_argv, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=3, check=False)
            except subprocess.TimeoutExpired:
                last_failure = "native_client_timeout"
            else:
                if probe.returncode == 0:
                    ready = True
                    break
                error = probe.stderr.lower()
                if b"connect" in error or b"socket" in error:
                    last_failure = "native_connection_unavailable"
                elif b"not allowed" in error or b"permission" in error:
                    last_failure = "native_permission_refused"
                elif b"invalid" in error or b"unknown" in error:
                    last_failure = "native_protocol_rejected"
                else:
                    last_failure = "native_client_error"
            time.sleep(0.2)
        if not ready:
            raise AssertionError(
                "DISPOSABLE KITTY NATIVE READ NEVER READY: " + last_failure)

        # The production reader is exercised against ONE real Kitty instance,
        # but only inside this disposable, explicitly isolated GitHub runner.
        try:
            projection = read_existing_kitty_inventory(
                target="unix:" + str(endpoint),
                runtime_directory=str(base),
                opt_in="explicit_read_only_kitty_inventory")
        except KittyInventoryError as exc:
            raise AssertionError("NATIVE KITTY READ FAILED: " + str(exc)) from exc

        assert projection["kind"] == "machine-kitty-native-inventory-projection"
        assert projection["read_only"] and not projection["executable"]
        assert projection["counts"]["os_windows"] >= 1
        assert projection["counts"]["tabs"] >= 1
        assert projection["counts"]["panes"] >= 1
        assert len(projection["os_windows"]) == projection["counts"]["os_windows"]
        assert projection["safe_actions"] == []
        assert projection["input_origin_verified"] is False
        assert projection["host_window_binding_verified"] is False
        assert projection["checkpoint_session_match"] is False
        assert projection["runtime_ids_ephemeral"] is True
        assert projection["capture_enabled"] is False
        assert projection["restore_enabled"] is False
        assert PRIVATE_SENTINEL not in repr(projection)
        for field in ("cwd", "cmdline", "env", "title", "pid"):
            assert field not in repr(projection).lower()
        print("MACHINE M2D4: ISOLATED KITTY NATIVE READ OK; REDACTED INVENTORY ONLY")
        print("MACHINE M2D4: EPHEMERAL OS WINDOWS/TABS/PANES FOUND; NO HOST BINDING")
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=4)
