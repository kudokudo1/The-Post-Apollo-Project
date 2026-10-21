#!/usr/bin/env python3
"""No launch or real updates: dedicated Kitty/Sway/Zellij reviewer contracts."""
from pathlib import Path
import importlib.util
import os
import re
import tempfile
from unittest.mock import patch
import json

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/updates/launch_review.py"
RUST = ROOT / "scripts/updates/zellij/update-review-header/src/main.rs"
CARGO = ROOT / "scripts/updates/zellij/update-review-header/Cargo.toml"
INSTALL = ROOT / "scripts/updates/zellij/build_header.sh"
NOTIFIER = ROOT / "services/notifications/SoftwareUpdateOfferNotificationProducer.qml"
WORKFLOW = ROOT / ".github/workflows/notification-policy-contracts.yml"

spec = importlib.util.spec_from_file_location("apollo_update_window", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert 'zellij-tile = "=0.45.0"' in CARGO.read_text()
src = RUST.read_text()
assert "register_plugin!(UpdateReviewHeader)" in src
assert "EventType::Mouse" in src
assert "EventType::PermissionRequestResult" in src
assert "PermissionType::ChangeApplicationState" in src
assert "Mouse::LeftClick(line, column)" in src
assert "self.detach_allowed && close_hit(" in src
assert "detach();" in src
assert not re.search(r"\b(?:quit_zellij|close_focused_tab|close_tab_with_id|close_terminal_pane|close_focus|run_command)\(", src)
assert "fn x_only_in_right_edge_of_one_row_header()" in src
assert "wasm32-wasip1" in INSTALL.read_text()
assert "post_apollo_update_header.wasm" in INSTALL.read_text()
assert "test_update_review_window.py" in WORKFLOW.read_text()
assert 'Quickshell.shellPath("scripts/updates/launch_review.py")' in NOTIFIER.read_text()

assert mod.valid_offer("silverblue", "a"*24)
assert mod.valid_offer("flatpak-system", "b"*24)
assert not mod.valid_offer("firmware", "a"*24), "firmware uses GNOME Software"
assert not mod.valid_offer("flatpak-system", "../../../danger")
assert not mod.valid_offer("other", "c"*24)

tree = {
    "id": 1, "nodes": [
        {"id": 9, "app_id": "kitty", "pid": 123},
        {"id": 10, "floating_nodes": [
            {"id": 26, "app_id": mod.WINDOW_APP_ID, "pid": 124},
            {"id": 27, "app_id": mod.WINDOW_APP_ID, "pid": 125}
        ]}
    ]
}
assert mod.find_exact_kitty(tree, 124) == 26
assert mod.find_exact_kitty(tree, 125) == 27
assert mod.find_exact_kitty(tree, 123) is None
assert mod.find_exact_kitty(tree, 998) is None

with tempfile.TemporaryDirectory() as tmp:
    datadir = Path(tmp)
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(datadir)}):
        wasm = mod.plugin_file()
        assert str(wasm).endswith("/post-apollo/zellij/post_apollo_update_header.wasm")
        # No custom header installed: never prevent review; ordinary Kitty
        # remains a safe, user-confirmed fallback.
        with patch.object(mod.shutil, "which", side_effect=lambda name: "/usr/bin/"+name):
            command, has_header = mod.kitty_argv("flatpak-system", "a"*24)
        assert not has_header
        assert command[:5] == ["kitty", "--class", mod.WINDOW_APP_ID,
                               "--title", "POST-APOLLO // UPDATE REVIEW"]
        assert command[-3:] == ["review", "flatpak-system", "a"*24]
        # After a separately authorized build/install, Zellij runs an
        # isolated plugin + review command layout with no shell interpolation.
        wasm.parent.mkdir(parents=True)
        wasm.write_bytes(b"\x00asm\x01\x00\x00\x00")
        with patch.object(mod.shutil, "which", side_effect=lambda name: "/usr/bin/"+name):
            command, has_header = mod.kitty_argv("flatpak-system", "b"*24)
        assert has_header
        assert "/usr/bin/zellij" in command and "--layout-string" in command
        assert "--session-name" in command
        assert "--session" not in command, "must create, never attach to missing session"
        assert command[command.index("--session-name") + 1].startswith(
            "apollo-updates-flatpak-system-"
        )
        generated = command[-1]
        assert 'plugin location="file:' in generated
        assert "pane size=1 borderless=true" in generated
        assert 'command="/usr/bin/python3"' in generated
        assert '"review" "flatpak-system" "' in generated
        assert "bash -c" not in generated
        assert "session_serialization false" in generated
        assert "--hold" not in command
        assert "; reboot" not in generated

        # Quickshell's PATH can omit ~/.local/bin even when Zellij is installed.
        # With no Zellij anywhere, ordinary Kitty remains a safe fallback.
        missing_zellij = lambda name: "/usr/bin/kitty" if name == "kitty" else None
        with patch.object(mod.shutil, "which", side_effect=missing_zellij), \
             patch.object(mod.Path, "home", return_value=datadir):
            command, has_header = mod.kitty_argv("flatpak-system", "c"*24)
        assert not has_header
        assert "--hold" in command
        assert "zellij" not in command

        # A verified executable at ~/.local/bin/zellij fixes that environment
        # mismatch for this launcher only, without changing global PATH.
        local_zellij = datadir / ".local/bin/zellij"
        local_zellij.parent.mkdir(parents=True)
        local_zellij.touch()
        local_zellij.chmod(0o755)
        with patch.object(mod.shutil, "which", side_effect=missing_zellij), \
             patch.object(mod.Path, "home", return_value=datadir):
            command, has_header = mod.kitty_argv("flatpak-system", "d"*24)
        assert has_header
        assert command[command.index("-e") + 1] == str(local_zellij)
        assert "--session-name" in command
        assert "--session" not in command

class Result:
    returncode = 0
    stdout = json.dumps(tree)

class Spawn:
    pid = 124

with patch.object(mod.shutil, "which", side_effect=lambda name: "/usr/bin/"+name), \
     patch.object(mod.subprocess, "run", side_effect=[Result(), Result()]) as runner, \
     patch.object(mod.time, "sleep") as sleeper:
    assert mod.place_with_sway(124) is True
    assert runner.call_args_list[1].args[0] == [
        "swaymsg",
        "[con_id=26] floating enable, border pixel 2, "
        "resize set width 900 px height 580 px, move position center"
    ]
    sleeper.assert_not_called()

# Invalid selectors never create windows or send Sway commands.
with patch.object(mod.subprocess, "Popen") as popen:
    assert mod.main(["flatpak-user", "../bad"]) == 2
    popen.assert_not_called()

with patch.object(mod.shutil, "which", side_effect=lambda name: "/usr/bin/"+name), \
     patch.object(mod.subprocess, "Popen", return_value=Spawn()) as popen, \
     patch.object(mod, "place_with_sway", return_value=True):
    assert mod.main(["silverblue", "e"*24]) == 0
    assert popen.call_args.kwargs["start_new_session"] is True
    assert popen.call_args.kwargs["close_fds"] is True

print("Kitty/Sway/Zellij update window, X detach, safe fallback: PASS")
