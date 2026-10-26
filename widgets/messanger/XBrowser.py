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

# LINE's official Chrome extension is the supported Linux personal-account
# client surface. Post-Apollo never downloads or side-loads it: setup opens
# the official Chrome Web Store inside LINE's isolated profile, and the user
# explicitly installs/logs in there.
LINE_EXTENSION_ID = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
LINE_EXTENSION_URL = f"chrome-extension://{LINE_EXTENSION_ID}/index.html#popout"
LINE_EXTENSION_STORE_URL = (
    "https://chromewebstore.google.com/detail/line/"
    + LINE_EXTENSION_ID
)
# Each service gets a distinct app id and browser data directory.
SITES = {
    "x": (X_URL, X_CLASS, "x-browser"),
    "instagram": ("https://www.instagram.com/", "post-apollo-instagram", "instagram-browser"),
    "facebook": ("https://www.facebook.com/", "post-apollo-facebook", "facebook-browser"),
    "reddit": ("https://www.reddit.com/", "post-apollo-reddit", "reddit-browser"),
    # Threads is Meta's separate text-focused network, not Instagram Reels.
    # Its independent profile provides a reliably Sway-addressable window.
    "threads": ("https://www.threads.com/", "post-apollo-threads", "threads-browser"),
    "pinterest": ("https://www.pinterest.com/", "post-apollo-pinterest", "pinterest-browser"),
    "truthsocial": ("https://truthsocial.com/", "post-apollo-truthsocial", "truthsocial-browser"),
    "bluesky": ("https://bsky.app/", "post-apollo-bluesky", "bluesky-browser"),
    "tumblr": ("https://www.tumblr.com/", "post-apollo-tumblr", "tumblr-browser"),
    "tiktok": ("https://www.tiktok.com/", "post-apollo-tiktok", "tiktok-browser"),
    "snapchat": ("https://web.snapchat.com/", "post-apollo-snapchat", "snapchat-browser"),
    # Official site-backed modes; some provider features still require mobile.
    "linkedin": ("https://www.linkedin.com/", "post-apollo-linkedin", "linkedin-browser"),
    "mastodon": ("https://mastodon.social/", "post-apollo-mastodon", "mastodon-browser"),
    "nextdoor": ("https://nextdoor.com/", "post-apollo-nextdoor", "nextdoor-browser"),
    "steamchat": ("https://steamcommunity.com/chat/", "post-apollo-steamchat", "steamchat-browser"),
    "element": ("https://app.element.io/", "post-apollo-element", "element-browser"),
    "groupme": ("https://web.groupme.com/", "post-apollo-groupme", "groupme-browser"),
    "lemon8": ("https://www.lemon8-app.com/", "post-apollo-lemon8", "lemon8-browser"),
    "quora": ("https://www.quora.com/", "post-apollo-quora", "quora-browser"),
    "pixelfed": ("https://pixelfed.social/", "post-apollo-pixelfed", "pixelfed-browser"),
    "zalo": ("https://chat.zalo.me/", "post-apollo-zalo", "zalo-browser"),
}

# Official web messaging fallbacks, NOT personal-message API adapters. They
# are visible only after an explicit in-menu Open Web click; each has a
# separate persistent Chromium profile and an independent Sway class.
WEB_FALLBACK_SITES = {
    "whatsappweb": ("https://web.whatsapp.com/", "post-apollo-whatsappweb", "whatsappweb-browser"),
    "messengerweb": ("https://www.facebook.com/messages/", "post-apollo-messengerweb", "messengerweb-browser"),
}

# Provider-owned extension UI. This is not a native inbox adapter and does not
# grant Post-Apollo access to LINE messages or credentials.
EXTENSION_SITES = {
    "linechrome": (LINE_EXTENSION_URL, "post-apollo-linechrome", "linechrome-browser"),
}
ALL_SITES = {**SITES, **WEB_FALLBACK_SITES, **EXTENSION_SITES}


def site_config(site: str) -> tuple[str, str, str]:
    if site not in ALL_SITES:
        raise ValueError(f"Unsupported Social browser site: {site}")
    return ALL_SITES[site]


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


def browser_profile(site: str, prefix: list[str] | None = None) -> Path:
    _, _, profile_dir = site_config(site)
    prefix = browser_prefix() if prefix is None else prefix
    if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]:
        # Flatpak Chromium cannot normally write into the host XDG_DATA_HOME.
        # Its own sandbox data directory is persistent and accessible instead.
        data_root = Path.home() / ".var" / "app" / prefix[2] / "data"
    else:
        data_root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    return data_root / "post-apollo" / profile_dir


def line_extension_installed(prefix: list[str] | None = None) -> bool:
    profile = browser_profile("linechrome", prefix)
    roots = [profile / "Default" / "Extensions" / LINE_EXTENSION_ID]
    roots.extend(profile.glob(f"Profile */Extensions/{LINE_EXTENSION_ID}"))
    return any(root.is_dir() and any(child.is_dir() for child in root.iterdir())
               for root in roots)


def browser_command(site: str = "x") -> list[str]:
    url, window_class, _ = site_config(site)
    prefix = browser_prefix()
    profile = browser_profile(site, prefix)
    if site == "linechrome" and not line_extension_installed(prefix):
        raise RuntimeError(
            "LINE for Chrome is not installed in the Post-Apollo LINE profile. "
            "Use SET UP LINE FOR CHROME first."
        )
    return prefix + [
        "--ozone-platform=x11",
        f"--class={window_class}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={url}",
    ]


def setup(site: str) -> None:
    if site != "linechrome":
        raise ValueError("Setup is only available for LINE for Chrome")
    prefix = browser_prefix()
    profile = browser_profile(site, prefix)
    command = prefix + [
        "--ozone-platform=x11",
        "--class=post-apollo-linechrome-setup",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--app={LINE_EXTENSION_STORE_URL}",
    ]
    subprocess.Popen(
        command, start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def show(site: str = "x") -> None:
    # Hiding a different site never logs it out or kills its browser process.
    site_config(site)
    for other in ALL_SITES:
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
    for site in ALL_SITES:
        hide(site)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("show", "hide", "status", "setup"))
    parser.add_argument("site", nargs="?", default="x", choices=(*ALL_SITES, "all"))
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
        elif args.action == "setup":
            if args.site == "all":
                raise ValueError("Cannot set up all browser sites")
            setup(args.site)
        elif args.site == "all":
            print(json.dumps({site: site_exists(site) for site in ALL_SITES}))
        else:
            payload = {
                "window": site_exists(args.site),
                "class": site_config(args.site)[1],
            }
            if args.site == "linechrome":
                payload["extensionInstalled"] = line_extension_installed()
                payload["extensionId"] = LINE_EXTENSION_ID
            print(json.dumps(payload))
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        print(f"Post-Apollo X: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
