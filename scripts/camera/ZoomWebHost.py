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


def _workarea_top_offset(output_name, output, workspaces):
    """Measure the actual workarea origin for Camera's layer-shell panel.

    Camera's QML frame is positioned relative to the visible Sway workarea.
    The window actor is positioned using Sway's absolute output coordinates.
    On the operator's DP-3, workarea.y=82 and output.y=0; not applying
    this delta placed 82 logical pixels of Zoom behind Camera's header.
    Never infer the offset from the panel theme, screen size, or a constant.
    """
    if not isinstance(workspaces, list):
        raise RuntimeError("WORKAREA_UNAVAILABLE")
    candidates = [item for item in workspaces
                  if isinstance(item, dict)
                  and item.get("output") == output_name
                  and item.get("visible") is True]
    if len(candidates) != 1:
        raise RuntimeError("WORKAREA_UNAVAILABLE")
    rect = candidates[0].get("rect") or {}
    if type(rect.get("y")) is not int:
        raise RuntimeError("WORKAREA_GEOMETRY_INVALID")
    offset = rect["y"] - output["y"]
    if not (0 <= offset <= min(512, output["height"] // 2)):
        raise RuntimeError("WORKAREA_OFFSET_INVALID")
    return offset


def _target_geometry(output_name, x, y, w, h):
    output = _output_rect(output_name)
    if not (w >= 480 and h >= 300 and w <= 4000 and h <= 2500
            and x >= 0 and y >= 0 and x + w <= output["width"]
            and y + h <= output["height"]):
        raise ValueError("INVALID_VIEWPORT")
    # Apply the measured workarea origin once, at the Sway IPC boundary.
    # QML input-hole geometry stays frame-local and must not be shifted.
    top = _workarea_top_offset(
        output_name, output, _sway_json("-t", "get_workspaces"))
    if y + top + h > output["height"]:
        raise ValueError("VIEWPORT_OUTSIDE_WORKAREA")
    return (output["x"] + x, output["y"] + y + top, w, h)


def _actor_windows(tree=None):
    # Social-style persistent followers can pass a direct Sway IPC snapshot.
    # The legacy one-shot enter/hide path keeps its existing swaymsg probe.
    root = tree if tree is not None else _sway_json("-t", "get_tree")
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


def _unique_actor(profile, tree=None):
    matches = _actor_windows(tree=tree)
    if len(matches) != 1:
        return None, "ACTOR_MISSING" if not matches else "AMBIGUOUS_ACTOR"
    node = matches[0]
    if not _verified_process_profile(node["pid"], profile):
        return None, "ACTOR_ORIGIN_UNVERIFIED"
    return node, ""


def _client_insets(node):
    """Bounded Sway window-content margins, not a guessed browser titlebar.

    Sway's rect is the container; window_rect is the actual client area
    relative to that rect. The client area, not its decorated container,
    must fit Camera's visible Zoom bay. Missing window_rect means zero
    margins; malformed or oversized margins fail closed.
    """
    rect = node.get("rect") or {}
    inner = node.get("window_rect")
    if inner is None:
        return (0, 0, 0, 0)
    keys = ("x", "y", "width", "height")
    if (not isinstance(inner, dict)
            or any(type(rect.get(k)) is not int for k in keys)
            or any(type(inner.get(k)) is not int for k in keys)):
        raise ValueError("INVALID_CLIENT_RECT")
    left, top = inner["x"], inner["y"]
    right = rect["width"] - inner["width"] - left
    bottom = rect["height"] - inner["height"] - top
    # Only a top/left window frame may be tucked behind Camera's chrome;
    # reject layouts that would extend the browser beyond its bottom/right.
    if not (0 <= left <= 48 and 0 <= top <= 128
            and 0 <= right <= 8 and 0 <= bottom <= 8
            and inner["width"] >= 300 and inner["height"] >= 200):
        raise ValueError("UNSAFE_CLIENT_INSETS")
    return (left, top, right, bottom)


def _client_rect(node):
    rect = node.get("rect") or {}
    keys = ("x", "y", "width", "height")
    if any(type(rect.get(k)) is not int for k in keys):
        return None
    left, top, right, bottom = _client_insets(node)
    return (rect["x"] + left, rect["y"] + top,
            rect["width"] - left - right,
            rect["height"] - top - bottom)


def _near(node, geometry):
    actual = _client_rect(node)
    return (actual is not None and all(abs(a - b) <= TOLERANCE
                                       for a, b in zip(actual, geometry)))


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
    docked = bool(actor and actor.get("visible") is True
                  and _near(actor, geometry))
    return {"ok": True, "kind": "zoom-web-status", "docked": docked,
            "state": "DOCKED" if docked else error or "MISALIGNED",
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
    # Match Social's tested docking recipe. Sway's 'move position' is
    # workspace-relative, whereas our target rectangle is output-global.
    # An ordinary Sway titlebar/border also distorts the measured actor rect.
    # All commands still target ONLY the verified, positive con_id.
    _sway_command(criteria, "floating", "enable")
    _sway_command(criteria, "border", "none")
    # Border changes can change the reported client rect. Measure *after*
    # removing decorations, and fit the browser content rather than its
    # containing frame. Do not change other windows or Zoom's web page CSS.
    measured, error = _unique_actor(profile)
    if not measured or measured["id"] != actor["id"]:
        raise RuntimeError("ACTOR_ORIGIN_UNVERIFIED")
    try:
        left, top, right, bottom = _client_insets(measured)
        outer_x = geometry[0] - left
        outer_y = geometry[1] - top
        outer_w = geometry[2] + left + right
        outer_h = geometry[3] + top + bottom
        if any((left, top, right, bottom)):
            # _target_geometry already bounds the ordinary zero-inset window.
            # Only an expanded outer container requires an output guard.
            output_rect = _output_rect(output)
            if (outer_x < output_rect["x"] or outer_y < output_rect["y"]
                    or outer_x + outer_w > output_rect["x"] + output_rect["width"]
                    or outer_y + outer_h > output_rect["y"] + output_rect["height"]):
                raise RuntimeError("CLIENT_FRAME_OUTSIDE_OUTPUT")
    except (ValueError, RuntimeError):
        # Never leave an unverified browser floating above the desktop.
        _sway_command(criteria, "move", "scratchpad")
        raise
    _sway_command(criteria, "resize", "set", "width", str(outer_w), "px",
                  "height", str(outer_h), "px")
    _sway_command(criteria, "move", "absolute", "position",
                  str(outer_x), "px", str(outer_y), "px")
    # Reobserve exact actor PID/class and measured bounds before enabling
    # QML's click-through/transparent bay.
    docked = False
    for _ in range(16):
        after, error = _unique_actor(profile)
        if (after and after["id"] == actor["id"]
                and after.get("visible") is True
                and _near(after, geometry)):
            docked = True
            break
        time.sleep(0.1)
    if not docked:
        # A failed dock must not leave an undocked login/profile window
        # competing with the operator's desktop.
        verified, _ = _unique_actor(profile)
        if verified and verified["id"] == actor["id"] and verified.get("visible"):
            _sway_command("[con_id=%d]" % actor["id"], "move", "scratchpad")
    # Keep diagnostics limited to geometry offsets. No titles, URLs, process
    # command lines, profile paths or Zoom session contents escape this helper.
    delta = None
    if not docked and after and after["id"] == actor["id"]:
        rect = _client_rect(after)
        if rect is not None:
            delta = [max(-5000, min(5000, actual - expected))
                     for actual, expected in zip(rect, geometry)]
    return {"ok": docked, "kind": "zoom-web-enter", "docked": docked,
            "state": "DOCKED" if docked else "NOT_ALIGNED",
            "error": "" if docked else (
                "WINDOW_NOT_VISIBLE" if after and after["id"] == actor["id"]
                and after.get("visible") is not True else "GEOMETRY_UNVERIFIED"),
            "rectDelta": delta,
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
