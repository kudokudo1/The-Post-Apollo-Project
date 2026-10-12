#!/usr/bin/env python3
"""Safety contracts for the user-initiated Koinoikos config installer."""
from pathlib import Path
import importlib.util
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "enable_koinoikos_focus", ROOT / "scripts/enable_koinoikos_focus.py")
assert spec and spec.loader
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "config"
    initial = "set $mod Mod4\nbindsym $mod+h focus left\n"
    path.write_text(initial)
    success = SimpleNamespace(returncode=0, stdout="Config valid", stderr="")

    with patch.object(installer.subprocess, "run", return_value=success) as run:
        ok, message = installer.enable(path)
        assert ok and "backed up" in message, message
        run.assert_called_once()
        assert run.call_args.args[0][1:3] == ["-C", "-c"]

    installed = path.read_text()
    assert initial in installed
    assert "include " + str(installer.INCLUDE.resolve()) in installed
    assert installed.count("include " + str(installer.INCLUDE.resolve())) == 1
    backup = list(Path(directory).glob("config.before-koinoikos-*.bak"))
    assert len(backup) == 1
    assert backup[0].read_text() == initial

    with patch.object(installer.subprocess, "run") as run:
        ok, message = installer.enable(path)
        assert ok and "already present" in message, message
        run.assert_not_called()
    assert path.read_text() == installed

    # A failed Sway config validation may not modify the original or
    # produce a misleading second backup.
    path.write_text(initial)
    failed = SimpleNamespace(returncode=1, stdout="", stderr="invalid syntax")
    with patch.object(installer.subprocess, "run", return_value=failed):
        ok, message = installer.enable(path)
        assert not ok and "original untouched" in message
    assert path.read_text() == initial
    assert len(list(Path(directory).glob("config.before-koinoikos-*.bak"))) == 1

    alias = Path(directory) / "config-link"
    alias.symlink_to(path)
    ok, message = installer.enable(alias)
    assert not ok and "symlinked" in message
    assert path.read_text() == initial

print("KOINOIKOS SAFE INSTALL // PASS")
