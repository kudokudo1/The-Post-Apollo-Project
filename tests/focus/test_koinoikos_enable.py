#!/usr/bin/env python3
"""Safety contracts for the user-initiated Koinoikos config installer."""
from pathlib import Path
import os
import socket
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
        ok, message = installer.enable(path, "sway")
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
        ok, message = installer.enable(path, "sway")
        assert ok and "already present" in message, message
        run.assert_not_called()
    assert path.read_text() == installed

    # A failed Sway config validation may not modify the original or
    # produce a misleading second backup.
    path.write_text(initial)
    failed = SimpleNamespace(returncode=1, stdout="", stderr="invalid syntax")
    with patch.object(installer.subprocess, "run", return_value=failed):
        ok, message = installer.enable(path, "sway")
        assert not ok and "original untouched" in message
    assert path.read_text() == initial
    assert len(list(Path(directory).glob("config.before-koinoikos-*.bak"))) == 1

    # Symlinks are standard for a user-managed Sway dotfiles checkout:
    # the config link must survive unchanged and the resolved real file
    # must receive the include, with a backup next to the real file.
    dotfiles = Path(directory) / "dotfiles"
    dotfiles.mkdir()
    actual = dotfiles / "sway-config"
    actual.write_text(initial)
    sway_dir = Path(directory) / "live-sway"
    sway_dir.mkdir()
    alias = sway_dir / "config"
    alias.symlink_to(Path("../dotfiles/sway-config"))  # relative target
    original_link = alias.readlink()
    with patch.object(installer.subprocess, "run", return_value=success) as run:
        ok, message = installer.enable(alias, "sway")
        assert ok and "symlink preserved" in message, message
        validate_path = Path(run.call_args.args[0][3])
        assert validate_path.parent == alias.parent
    assert alias.is_symlink() and alias.readlink() == original_link
    assert alias.resolve() == actual
    assert "include " + str(installer.INCLUDE.resolve()) in actual.read_text()
    backups = list(dotfiles.glob("sway-config.before-koinoikos-*.bak"))
    assert len(backups) == 1 and backups[0].read_text() == initial
    # A second install follows the symlink but does not duplicate or write.
    with patch.object(installer.subprocess, "run") as run:
        ok, message = installer.enable(alias, "sway")
        assert ok and "already present" in message
        run.assert_not_called()
    assert len(list(dotfiles.glob("sway-config.before-koinoikos-*.bak"))) == 1

    # Multi-link chains must not be atomically replaced at any link level.
    chained = sway_dir / "chained"
    chained.symlink_to("config")
    assert chained.is_symlink()
    with patch.object(installer.subprocess, "run") as run:
        ok, message = installer.enable(chained, "sway")
        assert ok and "already present" in message
        run.assert_not_called()
    assert chained.is_symlink() and chained.readlink() == Path("config")

    # Refuse failed validation without changing the real target or link.
    actual.write_text(initial)
    with patch.object(installer.subprocess, "run", return_value=failed):
        ok, message = installer.enable(chained, "sway")
        assert not ok and "original untouched" in message
    assert actual.read_text() == initial
    assert alias.is_symlink() and chained.is_symlink()
    assert len(list(dotfiles.glob("sway-config.before-koinoikos-*.bak"))) == 1

    # Refuse broken targets and directories, preserving the link and content.
    broken = sway_dir / "broken"
    broken.symlink_to("missing")
    ok, message = installer.enable(broken, "sway")
    assert not ok and "cannot be resolved" in message
    assert broken.is_symlink()

    folder_link = sway_dir / "not-a-file"
    folder_link.symlink_to(dotfiles, target_is_directory=True)
    ok, message = installer.enable(folder_link, "sway")
    assert not ok and "not a regular file" in message

# The default validator must be the *running compositor*, not /usr/bin/sway.
# A fabricated Unix socket with a Linux-style Sway IPC name exercises the
# selection without launching an actual compositor in CI.
with tempfile.TemporaryDirectory() as directory:
    sock = Path(directory) / f"sway-ipc.{os.getuid()}.123456.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(sock))
        with patch.dict(os.environ, {"SWAYSOCK": str(sock)}, clear=False):
            with patch.object(installer.os, "readlink",
                              return_value="/usr/local/bin/swayfx"):
                assert installer.running_compositor_executable() == "/proc/123456/exe"
                validator, display = installer.resolve_validator(None)
                assert validator == "/proc/123456/exe"
                assert display == "/usr/local/bin/swayfx"

            with patch.object(installer.os, "readlink",
                              return_value="/usr/local/bin/python3"):
                assert installer.running_compositor_executable() is None

            # Guard against a mismatched UID and stale/non-socket filenames.
            with patch.dict(os.environ, {"SWAYSOCK": str(sock).replace(
                              f"sway-ipc.{os.getuid()}.", "sway-ipc.99999999.")},
                            clear=False):
                assert installer.running_compositor_executable() is None

with patch.dict(os.environ, {"SWAYSOCK": ""}, clear=False):
    with patch.object(installer, "running_compositor_executable", return_value=None):
        validator, message = installer.resolve_validator(None)
        assert validator is None and "--sway" in message
        explicit, description = installer.resolve_validator("/my/fork/sway")
        assert explicit == "/my/fork/sway" and description == explicit

# A missing or unidentifiable running compositor must refuse installation
# without falling back silently to the stock sway binary.
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "config"
    original = "set $mod Mod4\n"
    path.write_text(original)
    with patch.object(installer, "running_compositor_executable", return_value=None):
        with patch.object(installer.subprocess, "run") as run:
            ok, message = installer.enable(path)
            assert not ok and "--sway" in message
            run.assert_not_called()
    assert path.read_text() == original

print("KOINOIKOS SAFE INSTALL // PASS")
