#!/usr/bin/env python3
"""Isolated Zoom Web App candidate hosted in Camera's click-through viewport.

Like Social's X/Instagram: Chromium is a real independent Sway XWayland
window, never QtWebEngine or a captured bitmap. This is a source-only, gated
candidate. The Quickshell input hole is enabled only for an exact class,
owner/process/profile and measured geometry match. No native Zoom Flatpak or
credential store is touched by this helper.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

ZOOM_WEB_URL = "https://app.zoom.us/wc"
ZOOM_CLASS = "post-apollo-camera-zoom-web"
IDENTITY_PATTERN = re.compile(r"identity-[1-9][0-9]{0,3}$")
MAX_TREE = 4_000_000
MAX_WINDOWS = 20000
TOLERANCE = 4


def _social_browser_prefix():
    # Reuse the already-installed browser preference/detection policy. Do not
    # edit Social's provider registry or borrow its cookie/profile files.
    path = Path(__file__).resolve().parents[2] / "widgets/messanger/XBrowser.py"
    spec = importlib.util.spec_from_file_location("_camera_read_only_xbrowser", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SOCIAL_BROWSER_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.browser_prefix()


def _private_profile(prefix, identity):
    if not IDENTITY_PATTERN.fullmatch(identity):
        raise ValueError("INVALID_SOCIAL_IDENTITY")
    # A Flatpak browser can only write inside its own sandbox's data root.
    if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]:
        root = Path.home() / ".var" / "app" / prefix[2] / "data"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or
                    Path.home() / ".local/share")
    profile = root / "post-apollo" / "camera" / "zoom-web" / identity
    for part in (profile.parent, profile):
        if part.is_symlink():
            raise RuntimeError("UNSAFE_ZOOM_PROFILE_LINK")
    profile.mkdir(parents=True, mode=0o700, exist_ok=True)
    st = profile.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("UNSAFE_ZOOM_PROFILE")
    return profile


def _sway_json(*args):
    swaymsg = shutil.which("swaymsg")
    if not swaymsg:
        raise RuntimeError("SWAY_IPC_UNAVAILABLE")
    p = subprocess.run([swaymsg, "-r", *args],
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, timeout=6, check=False)
    if p.returncode or len(p.stdout) > MAX_TREE:
        raise RuntimeError("SWAY_IPC_FAILED")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise RuntimeError("SWAY_IPC_INVALID") from None


def _sway_command(*args):
    result = _sway_json(*args)
    if not isinstance(result, list) or not result or not all(
            isinstance(v, dict) and v.get("success") is True for v in result):
        raise RuntimeError("SWAY_COMMAND_DENIED")


def _output_rect(output_name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,48}", output_name):
        raise ValueError("INVALID_OUTPUT")
    outputs = _sway_json("-t", "get_outputs")
    matches = [o for o in outputs if isinstance(o, dict)
               and o.get("name") == output_name and o.get("active") is True]
    if len(matches) != 1:
        raise RuntimeError("OUTPUT_NOT_FOUND")
    rect = matches[0].get("rect") or {}
    if any(type(rect.get(k)) is not int for k in ("x","y","width","height")):
        raise RuntimeError("OUTPUT_GEOMETRY_UNAVAILABLE")
    return rect


def _target_geometry(output_name, x, y, w, h):
    output = _output_rect(output_name)
    if not (w >= 480 and h >= 300 and w <= 4000 and h <= 2500
            and x >= 0 and y >= 0 and x + w <= output["width"]
            and y + h <= output["height"]):
        raise ValueError("INVALID_VIEWPORT")
    return (output["x"]+x, output["y"]+y, w, h)


def _actor_windows():
    root = _sway_json("-t", "get_tree")
    pending = [root]
    matches = []
    seen = 0
    while pending and seen < MAX_WINDOWS:
        node = pending.pop()
        seen += 1
        if not isinstance(node, dict):
            continue
        props = node.get("window_properties") or {}
        if isinstance(props, dict) and props.get("class") == ZOOM_CLASS:
            if (type(node.get("id")) is int and node["id"] > 0
                    and type(node.get("pid")) is int and node["pid"] > 1):
                matches.append(node)
        for key in ("nodes", "floating_nodes"):
            children = node.get(key)
            if isinstance(children, list):
                pending.extend(children[:MAX_WINDOWS])
    return matches


def _verified_process_profile(pid, profile):
    # A spoofed WM_CLASS is insufficient. Require a same-UID live browser
    # process ancestor with our exact private profile in its executable argv.
    expected = ("--user-data-dir=" + str(profile)).encode()
    checked = set()
    for _ in range(24):
        if pid in checked or pid <= 1:
            return False
        checked.add(pid)
        base = Path("/proc") / str(pid)
        try:
            st = base.stat()
            if st.st_uid != os.getuid():
                return False
            cmd = (base / "cmdline").read_bytes().split(b"\0")
            if expected in cmd and any(
                (b"chrom" in arg.lower() or b"brave" in arg.lower()
                 or b"chrome" in arg.lower() or b"vivaldi" in arg.lower()
                 or b"edge" in arg.lower()) for arg in cmd[:2]):
                return True
            stat_raw = (base / "stat").read_text()
            pid = int(stat_raw.rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
    return False


def _unique_actor(profile):
    matches = _actor_windows()
    if len(matches) != 1:
        return None, "ACTOR_MISSING" if not matches else "AMBIGUOUS_ACTOR"
    node = matches[0]
    if not _verified_process_profile(node["pid"], profile):
        return None, "ACTOR_ORIGIN_UNVERIFIED"
    return node, ""


def _near(node, geometry):
    r = node.get("rect") or {}
    return all(type(r.get(k)) is int and abs(r[k] - value) <= TOLERANCE
               for k,value in zip(("x","y","width","height"), geometry))


def status(identity, output, x, y, width, height):
    # Read-only: do not create profiles or launch browser.
    prefix = _social_browser_prefix()
    # Derive the prospective location without touching disk.
    if not IDENTITY_PATTERN.fullmatch(identity):
        raise ValueError("INVALID_SOCIAL_IDENTITY")
    root = (Path.home() / ".var/app" / prefix[2] / "data"
            if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]
            else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"))
    profile = root / "post-apollo" / "camera" / "zoom-web" / identity
    geometry = _target_geometry(output, x, y, width, height)
    actor, error = _unique_actor(profile)
    return {"ok": True, "kind": "zoom-web-status", "docked": bool(actor and _near(actor, geometry)),
            "state": "DOCKED" if actor and _near(actor, geometry) else error or "MISALIGNED",
            "authenticated": "UNKNOWN"}


def enter(identity, output, x, y, width, height):
    geometry = _target_geometry(output, x, y, width, height)
    prefix = _social_browser_prefix()
    profile = _private_profile(prefix, identity)
    actor, error = _unique_actor(profile)
    if not actor and error == "ACTOR_MISSING":
        cmd = prefix + ["--ozone-platform=x11", "--class="+ZOOM_CLASS,
                        "--user-data-dir="+str(profile), "--no-first-run",
                        "--no-default-browser-check", "--app="+ZOOM_WEB_URL]
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True,
                         close_fds=True)
        for _ in range(45):
            time.sleep(0.1)
            actor, error = _unique_actor(profile)
            if actor:
                break
    if not actor:
        return {"ok": False, "kind": "zoom-web-enter", "error": error or "ACTOR_NOT_READY",
                "docked": False, "authenticated": "UNKNOWN"}
    criteria = "[con_id=%d]" % actor["id"]
    if not actor.get("visible"):
        _sway_command(criteria, "scratchpad", "show")
    _sway_command(criteria, "floating", "enable")
    _sway_command(criteria, "resize", "set", "width", str(geometry[2]), "px",
                  "height", str(geometry[3]), "px")
    _sway_command(criteria, "move", "position", str(geometry[0]), str(geometry[1]))
    # Reobserve exact actor PID/class and measured bounds before enabling
    # QML's click-through/transparent bay.
    docked = False
    for _ in range(16):
        after, error = _unique_actor(profile)
        if after and after["id"] == actor["id"] and _near(after, geometry):
            docked = True
            break
        time.sleep(0.1)
    if not docked:
        # A failed dock must not leave an undocked login/profile window
        # competing with the operator's desktop.
        verified, _ = _unique_actor(profile)
        if verified and verified["id"] == actor["id"] and verified.get("visible"):
            _sway_command("[con_id=%d]" % actor["id"], "move", "scratchpad")
    return {"ok": docked, "kind": "zoom-web-enter", "docked": docked,
            "state": "DOCKED" if docked else "NOT_ALIGNED",
            "error": "" if docked else "GEOMETRY_UNVERIFIED",
            "authenticated": "UNKNOWN"}


def hide(identity):
    if not IDENTITY_PATTERN.fullmatch(identity):
        raise ValueError("INVALID_SOCIAL_IDENTITY")
    prefix = _social_browser_prefix()
    root = (Path.home() / ".var/app" / prefix[2] / "data"
            if len(prefix) >= 3 and prefix[:2] == ["flatpak", "run"]
            else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"))
    profile = root / "post-apollo" / "camera" / "zoom-web" / identity
    actor, error = _unique_actor(profile)
    if actor and actor.get("visible"):
        _sway_command("[con_id=%d]" % actor["id"], "move", "scratchpad")
    return {"ok": True, "kind": "zoom-web-hide", "hidden": bool(actor),
            "authenticated": "UNKNOWN"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("enter","status","hide"))
    parser.add_argument("--identity", default="identity-1")
    parser.add_argument("--output", default="")
    for field in ("x","y","width","height"):
        parser.add_argument("--"+field, type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.action == "hide":
            result = hide(args.identity)
        elif args.action == "status":
            result = status(args.identity, args.output, args.x,args.y,args.width,args.height)
        else:
            result = enter(args.identity,args.output,args.x,args.y,args.width,args.height)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        # Errors from helper functions are coded; never return command lines,
        # private paths, OAuth tokens or browser stderr into the QML panel.
        code = str(exc)
        if not re.fullmatch(r"[A-Z_]{4,64}", code):
            code = "ZOOM_WEB_HOST_UNAVAILABLE"
        result = {"ok": False, "kind": "zoom-web-"+args.action,
                  "error": code, "docked": False, "authenticated": "UNKNOWN"}
    print(json.dumps(result, separators=(",",":")))
    return 0


if __name__=="__main__":
    sys.exit(main())
