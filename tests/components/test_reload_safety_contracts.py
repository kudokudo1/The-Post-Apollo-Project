#!/usr/bin/env python3
"""Contracts for crash-safe Quickshell update/restart policy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
RESTART = (ROOT / "scripts" / "restart_quickshell_safe.sh").read_text(
    encoding="utf-8"
)

assert "Quickshell.watchFiles = false;" in SHELL, (
    "live shell must disable automatic QML hot reload"
)
assert "Quickshell.watchFiles = true" not in SHELL, (
    "live shell must not silently re-enable automatic hot reload"
)

for needle in (
    "pkill -KILL -x quickshell",
    "QS_DISABLE_FILE_WATCHER=1",
    "quickshell --no-duplicate --daemonize --path",
):
    assert needle in RESTART, f"safe restart helper missing {needle!r}"

command_lines = "\n".join(
    line for line in RESTART.splitlines()
    if line.strip() and not line.lstrip().startswith("#")
).lower()
assert "quickshell reload" not in command_lines, (
    "safe restart must cross a process boundary, not use in-process reload"
)

print("Quickshell reload safety contracts: PASS")
