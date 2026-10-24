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
# Each service gets a distinct app id and browser data directory.
SITES = {
    "x": (X_URL, X_CLASS, "x-browser"),
    "instagram": ("https://www.instagram.com/", "post-apollo-instagram", "instagram-browser"),
    "facebook": ("https://www.facebook.com/", "post-apollo-facebook", "facebook-browser"),
    "reddit": ("https://www.reddit.com/", "post-apollo-reddit", "reddit-browser"),
}


def site_config(site: str) -> tuple[str, str, str]:
    if site not in SITES:
        raise ValueError(f"Unsupported Social browser site: {site}")
    return SITES[site]


def site_criteria(site: str) -> str:
    return f'[class="{site_config(site)[1]}"]'

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


def site_exists(site: str) -> bool:
    if site == "x":
        return x_exists()
    _, window_class, _ = site_config(site)
    return any(
        (node.get("window_properties") or {}).get("class") == window_class
        for node in walk_tree(sway_tree())
    )


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


def browser_command(site: str = "x") -> list[str]:
    url, window_class, profile_dir = site_config(site)
    prefix = browser_prefix()
    if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]:
        # Flatpak Chromium cannot normally write into the host XDG_DATA_HOME.
        # Its own sandbox data directory is persistent and accessible instead.
        data_root = Path.home() / ".var" / "app" / prefix[2] / "data"
    else:
        data_root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    profile = data_root / "post-apollo" / profile_dir
    return prefix + [
        "--ozone-platform=x11",
        f"--class={window_class}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={url}",
    ]


def show(site: str = "x") -> None:
    # Hiding a different site never logs it out or kills its browser process.
    site_config(site)
    for other in SITES:
        if other != site and site_exists(other):
            sway_command(f"{site_criteria(other)} move scratchpad")

    if not site_exists(site):
        command = browser_command(site)
        # Chromium retains credentials in a site-specific profile.
        subprocess.Popen(
            command, start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(70):
            time.sleep(0.1)
            if site_exists(site):
                break
        else:
            raise RuntimeError(
                f"{site} browser window did not appear with its Post-Apollo class. "
                "Check browser/XWayland availability."
            )

    criteria = site_criteria(site)
    sway_command(f"{criteria} move scratchpad")
    sway_command(f"{criteria} scratchpad show")


def hide(site: str = "x") -> None:
    if site_exists(site):
        sway_command(f"{site_criteria(site)} move scratchpad")


def hide_all() -> None:
    for site in SITES:
        hide(site)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("show", "hide", "status"))
    parser.add_argument("site", nargs="?", default="x", choices=(*SITES, "all"))
    args = parser.parse_args()

    try:
        if args.action == "show":
            if args.site == "all":
                raise ValueError("Cannot show all browser sites")
            show(args.site)
        elif args.action == "hide":
            if args.site == "all":
                hide_all()
            else:
                hide(args.site)
        elif args.site == "all":
            print(json.dumps({site: site_exists(site) for site in SITES}))
        else:
            print(json.dumps({
                "window": site_exists(args.site),
                "class": site_config(args.site)[1],
            }))
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        print(f"Post-Apollo X: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
