#!/usr/bin/env python3
"""Launch and show X as one isolated Chromium app window inside Post-Apollo Social.

An XWayland WM_CLASS is intentional: native Chromium Wayland --class does not
reliably set app_id, so Sway cannot safely target a particular browser window.
This never reads or stores X credentials. Chromium owns its persistent profile.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import tempfile
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

# Stable Post-Apollo organization IDs. An identity number is never a
# Chromium account ID, token, login assertion, shell fragment, or filesystem
# path supplied by the caller. Unknown IDs are rejected before path use.
IDENTITY_ID = re.compile(r"^identity-[1-9][0-9]{0,8}$")


def validated_identity(identity_id: str | None) -> str | None:
    if identity_id is None:
        return None  # Preserve the existing, unscoped browser lane as-is.
    if not isinstance(identity_id, str) or not IDENTITY_ID.fullmatch(identity_id):
        raise ValueError("Invalid Post-Apollo identity ID")
    return identity_id


def site_config(site: str) -> tuple[str, str, str]:
    if site not in ALL_SITES:
        raise ValueError(f"Unsupported Social browser site: {site}")
    return ALL_SITES[site]


def site_window_class(site: str, identity_id: str | None = None) -> str:
    legacy_class = site_config(site)[1]
    scoped_id = validated_identity(identity_id)
    return legacy_class if scoped_id is None else f"{legacy_class}-{scoped_id}"


def site_criteria(site: str, identity_id: str | None = None) -> str:
    return f'[class="{site_window_class(site, identity_id)}"]'

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


def site_exists(site: str, identity_id: str | None = None) -> bool:
    validated_identity(identity_id)
    if site == "x" and identity_id is None:
        return x_exists()
    window_class = site_window_class(site, identity_id)
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


def browser_profile(
    site: str, prefix: list[str] | None = None,
    identity_id: str | None = None,
) -> Path:
    _, _, profile_dir = site_config(site)
    scoped_id = validated_identity(identity_id)
    prefix = browser_prefix() if prefix is None else prefix
    if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]:
        # Flatpak Chromium cannot normally write into the host XDG_DATA_HOME.
        # Its own sandbox data directory is persistent and accessible instead.
        data_root = Path.home() / ".var" / "app" / prefix[2] / "data"
    else:
        data_root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    if scoped_id is None:
        # Do not auto-migrate or repurpose the operator's legacy profiles.
        return data_root / "post-apollo" / profile_dir
    return data_root / "post-apollo" / "identities" / scoped_id / profile_dir


def line_extension_installed(
    prefix: list[str] | None = None, identity_id: str | None = None,
) -> bool:
    profile = browser_profile("linechrome", prefix, identity_id)
    roots = [profile / "Default" / "Extensions" / LINE_EXTENSION_ID]
    roots.extend(profile.glob(f"Profile */Extensions/{LINE_EXTENSION_ID}"))
    return any(root.is_dir() and any(child.is_dir() for child in root.iterdir())
               for root in roots)


def browser_command(
    site: str = "x", identity_id: str | None = None,
) -> list[str]:
    url, _, _ = site_config(site)
    scoped_id = validated_identity(identity_id)
    window_class = site_window_class(site, scoped_id)
    prefix = browser_prefix()
    profile = browser_profile(site, prefix, scoped_id)
    if site == "linechrome" and not line_extension_installed(prefix, scoped_id):
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


def setup(site: str, identity_id: str | None = None) -> None:
    # The shared geometry bridge does not yet recognize identity-scoped
    # Chromium classes. Never open an undockable login window by surprise.
    if validated_identity(identity_id) is not None:
        raise RuntimeError("Identity-scoped browser setup awaits geometry integration")
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



# Session selection is ephemeral, not account authentication or a credentials
# store. It arbitrates overlapping show/hide requests across helper processes.
SELECTION_FILE = "browser-selection.json"
SELECTION_LOCK = ".browser-selection.lock"


def selection_runtime() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise RuntimeError("Isolated browsers require XDG_RUNTIME_DIR")
    base = Path(runtime)
    st = base.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("Unsafe browser runtime directory")
    root = base / "post-apollo-social"
    if not root.exists() and not root.is_symlink():
        root.mkdir(mode=0o700, exist_ok=True)
    st = root.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("Unsafe browser session directory")
    return root


def session_lock() -> tuple[int, Path]:
    root = selection_runtime()
    fd = os.open(root / SELECTION_LOCK,
                 os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        os.close(fd)
        raise RuntimeError("Unsafe browser session lock")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd, root


def load_selection(root: Path) -> dict[str, str]:
    file = root / SELECTION_FILE
    try:
        st = file.lstat()
    except FileNotFoundError:
        return {}
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("Unsafe browser selection marker")
    fd = os.open(file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(257)
    if len(raw) > 256:
        raise RuntimeError("Invalid browser selection marker")
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise RuntimeError("Invalid browser selection marker") from None
    if not isinstance(value, dict) or set(value) != {"identityId", "site", "token"}:
        raise RuntimeError("Invalid browser selection marker")
    if validated_identity(value["identityId"]) is None:
        raise RuntimeError("Invalid browser selection marker")
    site_config(value["site"])
    if not isinstance(value["token"], str) or not re.fullmatch("[a-f0-9]{32}", value["token"]):
        raise RuntimeError("Invalid browser selection marker")
    return value


def store_selection(root: Path, selection: dict[str, str]) -> None:
    fd, temporary = tempfile.mkstemp(dir=root, prefix=".browser-session-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(selection, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / SELECTION_FILE)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def claim_selection(site: str, identity_id: str) -> str:
    token = secrets.token_hex(16)
    fd, root = session_lock()
    try:
        load_selection(root)  # Never overwrite corrupt or unsafe runtime data.
        store_selection(root, {"site": site, "identityId": identity_id,
                               "token": token})
    finally:
        os.close(fd)
    return token


def selection_is_current(site: str, identity_id: str, token: str) -> bool:
    fd, root = session_lock()
    try:
        return load_selection(root) == {
            "site": site, "identityId": identity_id, "token": token}
    finally:
        os.close(fd)


def revoke_selection(identity_id: str, site: str | None = None) -> None:
    fd, root = session_lock()
    try:
        current = load_selection(root)
        if current.get("identityId") == identity_id and (
                site is None or current.get("site") == site):
            store_selection(root, {"site": current["site"],
                                   "identityId": identity_id,
                                   "token": secrets.token_hex(16)})
    finally:
        os.close(fd)


def ensure_private_profile(site: str, identity_id: str,
                           prefix: list[str]) -> Path:
    profile = browser_profile(site, prefix, identity_id)
    # Preserve the preexisting post-apollo base, which may hold the legacy
    # profiles. Protect the newly-created identities/ID/site directories.
    for folder in [profile.parents[2], profile.parents[1],
                   profile.parent, profile]:
        if not folder.exists() and not folder.is_symlink():
            folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = folder.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
            raise RuntimeError("Unsafe isolated profile directory")
        if folder != profile.parents[2] and st.st_mode & 0o077:
            raise RuntimeError("Insecure isolated profile permissions")
    return profile


def managed_browser_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    windows = []
    for node in walk_tree(tree):
        cls = (node.get("window_properties") or {}).get("class")
        if not isinstance(cls, str):
            continue
        if not any(cls == site_config(site)[1] or
                   (cls.startswith(site_config(site)[1] + "-")
                    and IDENTITY_ID.fullmatch(cls[len(site_config(site)[1])+1:]))
                   for site in ALL_SITES):
            continue
        cid = node.get("id")
        if type(cid) is not int or cid <= 0:
            raise RuntimeError("Managed browser window lacks Sway con_id")
        windows.append({"class": cls, "conId": cid,
                        "visible": bool(node.get("visible", False))})
    return windows


def scoped_target(windows: list[dict[str, Any]],
                  window_class: str) -> dict[str, Any] | None:
    found = [w for w in windows if w["class"] == window_class]
    if len(found) > 1:
        raise RuntimeError("Ambiguous isolated browser window")
    return found[0] if found else None


def show(site: str = "x", identity_id: str | None = None) -> None:
    # Only the legacy site-window classes are handled by DiscordGeometry.py.
    # Disable scoped launches until the host, Sway bridge and active identity
    # transition are all updated together. No profile or window is reused.
    if validated_identity(identity_id) is not None:
        raise RuntimeError("Identity-scoped browser launch awaits geometry integration")
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


def hide(site: str = "x", identity_id: str | None = None) -> None:
    validated_identity(identity_id)
    if identity_id is None:
        # Preserve the existing one-argument path for normal Social use.
        if site_exists(site):
            sway_command(f"{site_criteria(site)} move scratchpad")
    elif site_exists(site, identity_id):
        sway_command(f"{site_criteria(site, identity_id)} move scratchpad")


def hide_all(identity_id: str | None = None) -> None:
    validated_identity(identity_id)
    for site in ALL_SITES:
        hide(site, identity_id) if identity_id is not None else hide(site)


def profile_plan(site: str, identity_id: str) -> dict[str, Any]:
    """Pure, non-mutating scoped profile proposal; never reports login success."""
    scoped_id = validated_identity(identity_id)
    if scoped_id is None:
        raise ValueError("Identity ID required for scoped profile plan")
    _, _, profile_leaf = site_config(site)
    return {
        "identityId": scoped_id,
        "site": site,
        "windowClass": site_window_class(site, scoped_id),
        "profileRelative": f"post-apollo/identities/{scoped_id}/{profile_leaf}",
        "status": "GEOMETRY_INTEGRATION_PENDING",
        "authenticated": None,
        "launchAvailable": False,
        "migrationPerformed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("show", "hide", "status", "setup", "profile"))
    parser.add_argument("site", nargs="?", default="x", choices=(*ALL_SITES, "all"))
    parser.add_argument("--identity", dest="identity_id", default=None)
    args = parser.parse_args()

    try:
        identity_id = validated_identity(args.identity_id)
        if args.action == "profile":
            if args.site == "all" or identity_id is None:
                raise ValueError("Scoped profile plan requires one site and --identity")
            print(json.dumps(profile_plan(args.site, identity_id)))
        elif args.action == "show":
            if args.site == "all":
                raise ValueError("Cannot show all browser sites")
            show(args.site, identity_id) if identity_id is not None else show(args.site)
        elif args.action == "hide":
            if args.site == "all":
                hide_all(identity_id) if identity_id is not None else hide_all()
            else:
                hide(args.site, identity_id) if identity_id is not None else hide(args.site)
        elif args.action == "setup":
            if args.site == "all":
                raise ValueError("Cannot set up all browser sites")
            setup(args.site, identity_id) if identity_id is not None else setup(args.site)
        elif args.site == "all":
            print(json.dumps({
                site: site_exists(site, identity_id)
                if identity_id is not None else site_exists(site)
                for site in ALL_SITES
            }))
        else:
            payload = {
                "window": site_exists(args.site, identity_id)
                          if identity_id is not None else site_exists(args.site),
                "class": site_window_class(args.site, identity_id),
            }
            if args.site == "linechrome":
                payload["extensionInstalled"] = line_extension_installed(
                    identity_id=identity_id)
                payload["extensionId"] = LINE_EXTENSION_ID
            if identity_id is not None:
                payload["identityId"] = identity_id
                payload["authenticated"] = None
                payload["launchAvailable"] = False
            print(json.dumps(payload))
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        print(f"Post-Apollo X: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
