#!/usr/bin/env python3
"""Launch and show X as one isolated Chromium app window inside Post-Apollo Social.

An XWayland WM_CLASS is intentional: native Chromium Wayland --class does not
reliably set app_id, so Sway cannot safely target a particular browser window.
This never reads or stores X credentials. Chromium owns its persistent profile.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

X_CLASS = "post-apollo-x"
X_URL = "https://x.com"
CRITERIA = f'[class="{X_CLASS}"]'
BROWSERS = (
    "brave-browser",
    "brave-browser-stable",
    "chromium",
    "chromium-browser",
    "google-chrome-stable",
    "google-chrome",
    "microsoft-edge-stable",
    "microsoft-edge",
    "vivaldi-stable",
    "vivaldi",
)
FLATPAKS = (
    "com.brave.Browser",
    "org.chromium.Chromium",
    "com.google.Chrome",
    "com.microsoft.Edge",
)


def walk_tree(node: dict[str, Any]):
    yield node
    for key in ("nodes", "floating_nodes"):
        for child in node.get(key, []) or []:
            yield from walk_tree(child)


def is_x_window(node: dict[str, Any]) -> bool:
    props = node.get("window_properties") or {}
    return props.get("class") == X_CLASS


def sway_tree() -> dict[str, Any]:
    result = subprocess.run(
        ["swaymsg", "-r", "-t", "get_tree"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def x_exists() -> bool:
    return any(is_x_window(node) for node in walk_tree(sway_tree()))


def sway_command(command: str) -> None:
    result = subprocess.run(
        ["swaymsg", "-r", command],
        check=True, capture_output=True, text=True,
    )
    response = json.loads(result.stdout)
    if not isinstance(response, list) or not all(row.get("success") for row in response):
        raise RuntimeError(f"Sway rejected X window command: {response}")


def browser_prefix() -> list[str]:
    override = os.environ.get("POST_APOLLO_X_BROWSER", "").strip()
    if override:
        browser = shutil.which(override)
        if not browser:
            raise RuntimeError(f"POST_APOLLO_X_BROWSER not found: {override}")
        return [browser]

    for executable in BROWSERS:
        browser = shutil.which(executable)
        if browser:
            return [browser]

    if shutil.which("flatpak"):
        installed = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, check=False,
        )
        if installed.returncode == 0:
            available = set(installed.stdout.splitlines())
            for app in FLATPAKS:
                if app in available:
                    return ["flatpak", "run", app]

    raise RuntimeError(
        "No Chromium-family browser found. Install Chromium/Brave/Chrome, "
        "or set POST_APOLLO_X_BROWSER to its executable."
    )


def browser_command() -> list[str]:
    data_root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    profile = data_root / "post-apollo" / "x-browser"
    return browser_prefix() + [
        "--ozone-platform=x11",
        f"--class={X_CLASS}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={X_URL}",
    ]


def show() -> None:
    if not x_exists():
        command = browser_command()
        # Browser creates its own dedicated profile, never touching the user's
        # default Chromium/Brave session or Session's message database.
        subprocess.Popen(
            command, start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(70):
            time.sleep(0.1)
            if x_exists():
                break
        else:
            raise RuntimeError(
                "X browser window did not appear with class post-apollo-x. "
                "Check browser/XWayland availability."
            )

    # Reuse the exact same scratchpad lifecycle as Social's Vesktop window.
    sway_command(f"{CRITERIA} move scratchpad")
    sway_command(f"{CRITERIA} scratchpad show")


def hide() -> None:
    if x_exists():
        sway_command(f"{CRITERIA} move scratchpad")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("show", "hide", "status"))
    args = parser.parse_args()

    try:
        if args.action == "show":
            show()
        elif args.action == "hide":
            hide()
        else:
            print(json.dumps({"window": x_exists(), "class": X_CLASS}))
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        print(f"Post-Apollo X: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
