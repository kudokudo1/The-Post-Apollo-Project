#!/usr/bin/env python3
"""Launch a dedicated Sway-positioned Kitty + Zellij update reviewer.

The exact pinned update still requires update_offers.py's typed authorization.
No window-control command may mutate/interrupt any running update process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

KIND = frozenset({"silverblue", "flatpak-user", "flatpak-system",
                  "oh-my-zsh", "powerlevel10k"})
TOKEN = re.compile(r"[a-f0-9]{24}\Z")
WINDOW_APP_ID = "post-apollo-update-review"
MAX_WAIT_SECONDS = 4.0


def plugin_file() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return base / "post-apollo/zellij/post_apollo_update_header.wasm"


def update_script() -> Path:
    return Path(__file__).resolve().parent / "update_offers.py"


def valid_offer(kind: str, token: str) -> bool:
    return kind in KIND and TOKEN.fullmatch(token) is not None


def kdl_quote(value: str) -> str:
    # KDL v1 permits quoted, JSON-style escaped strings.
    # Never use unsanitized shell text or interpolated CLI command strings.
    return json.dumps(value, ensure_ascii=True)


def layout(kind: str, token: str, wasm: Path) -> str:
    script = str(update_script())
    plugin = "file:" + str(wasm.resolve())
    return """layout {
    pane split_direction="horizontal" {
        pane size=1 borderless=true {
            plugin location=%s
        }
        pane focus=true borderless=true command="/usr/bin/python3" {
            args %s "review" %s %s
        }
    }
}
""" % (kdl_quote(plugin), kdl_quote(script),
       kdl_quote(kind), kdl_quote(token))


def kitty_argv(kind: str, token: str) -> tuple[list[str], bool]:
    if not valid_offer(kind, token):
        raise ValueError("unknown update offer")
    if not shutil.which("kitty"):
        raise RuntimeError("Kitty is not installed")
    head = ["kitty", "--class", WINDOW_APP_ID,
            "--title", "POST-APOLLO // UPDATE REVIEW", "-e"]
    wasm = plugin_file()
    if shutil.which("zellij") and wasm.is_file() and wasm.stat().st_size > 0:
        # Separate session name: never attach to the user's ordinary Zellij
        # session or replay an old operation in a reused named session.
        session = "apollo-updates-" + kind + "-" + token[:8] + "-" + str(os.getpid())
        return head + ["zellij", "--session", session,
                       "--layout-string", layout(kind, token, wasm)], True
    # Non-destructive fallback. This still gets the Sway floating placement,
    # but does not pretend that a clickable Zellij X is available.
    return head + ["/usr/bin/python3", str(update_script()),
                   "review", kind, token], False


def find_exact_kitty(tree: dict, child_pid: int) -> int | None:
    if not isinstance(tree, dict):
        return None
    if tree.get("app_id") == WINDOW_APP_ID and tree.get("pid") == child_pid:
        node_id = tree.get("id")
        return node_id if isinstance(node_id, int) and node_id > 0 else None
    for group in ("nodes", "floating_nodes"):
        for child in tree.get(group, []):
            result = find_exact_kitty(child, child_pid)
            if result is not None:
                return result
    return None


def place_with_sway(child_pid: int) -> bool:
    if not shutil.which("swaymsg"):
        return False
    until = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < until:
        try:
            tree_result = subprocess.run(
                ["swaymsg", "-t", "get_tree", "-r"],
                capture_output=True, text=True, timeout=1.5, check=False)
            if tree_result.returncode == 0:
                node = find_exact_kitty(json.loads(tree_result.stdout), child_pid)
                if node is not None:
                    cmd = (f"[con_id={node}] floating enable, "
                           "border pixel 2, "
                           "resize set width 900 px height 580 px, "
                           "move position center")
                    done = subprocess.run(["swaymsg", cmd], capture_output=True,
                                          text=True, timeout=2.0, check=False)
                    return done.returncode == 0
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.15)
    return False


def main(args: list[str]) -> int:
    if len(args) != 2 or not valid_offer(args[0], args[1]):
        print("Usage: launch_review.py KIND TOKEN (known update only)", file=sys.stderr)
        return 2
    try:
        command, has_header = kitty_argv(args[0], args[1])
        child = subprocess.Popen(command, close_fds=True, start_new_session=True)
    except (OSError, RuntimeError, ValueError) as exc:
        print("UPDATE REVIEW // Could not launch Kitty: " + str(exc), file=sys.stderr)
        return 2
    place_with_sway(child.pid)
    if not has_header:
        print("UPDATE REVIEW // Zellij header unavailable; using normal "
              "Kitty review. Install plugin with build_header.sh.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
