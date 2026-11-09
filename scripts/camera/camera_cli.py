#!/usr/bin/env python3
"""Camera M1: local-only Sway screenshots, image inventory and reversible cleanup.

No daemon, network, JSON database or automatic scans. The owning QML widget
executes one action on user input. Desktop screenshot cleanup and Gallery
batch/individual selections require a short-lived plan plus an explicit
second confirmation. Only validated media files may enter the Gallery batch.
"Trash" uses GIO, never an irreversible unlink/rm fallback.
"""
import argparse
from collections import deque
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS
VIDEO_DEVICE = re.compile(r"^/dev/video[0-9]+$")
SCREENSHOT_NAME = re.compile(
    r"(screenshot|screen[\s_-]?shot|grim|spectacle|swappy|flameshot)",
    re.IGNORECASE,
)
PLAN_PATTERN = re.compile(r"^[a-f0-9]{32}$")
PLAN_TTL = 600
MAX_TRASH = 20000
# M1 Batch: explicit selected Gallery records, never unrestricted bulk globbing.
MAX_BATCH_TRASH = 500
MAX_BATCH_ARG_BYTES = 100000
GALLERY_PAGE_SIZE = 120
MAX_SCAN_FILES = 60000
MAX_SCAN_DIRS = 1600
MAX_SCAN_DEPTH = 4
MAX_OUTPUT_BYTES = 1000000


def home():
    return Path.home()


def desktop():
    return home() / "Desktop"


def pictures():
    return home() / "Pictures" / "Screenshots" / "Post-Apollo"


def video_root():
    return home() / "Videos" / "Post-Apollo"


def webcam_root():
    return home() / "Pictures" / "Camera" / "Post-Apollo"


def recording_state_path():
    return plan_dir().parent / "camera-recording.json"


def screenshots_root():
    return home() / "Pictures" / "Screenshots"


def plan_dir():
    base = Path(os.environ.get("XDG_STATE_HOME", str(home() / ".local" / "state")))
    return base / "post-apollo" / "camera-plans"


def is_image(entry):
    try:
        return (entry.is_file(follow_symlinks=False) and
                not entry.is_symlink() and
                Path(entry.name).suffix.lower() in MEDIA_EXTS)
    except OSError:
        return False


def is_screenshot_name(name):
    return bool(SCREENSHOT_NAME.search(name))


def direct_images(root, source, only_screenshots=False):
    """No recursion, symlink dereference or hidden folders."""
    if root.is_symlink() or not root.is_dir():
        return []
    out = []
    try:
        with os.scandir(root) as scan:
            for entry in scan:
                if not is_image(entry):
                    continue
                # Desktop cleanup remains image-only; videos must never enter
                # its screenshot-like deletion preview.
                if Path(entry.name).suffix.lower() not in IMAGE_EXTS:
                    continue
                if only_screenshots and not is_screenshot_name(entry.name):
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                path = root / entry.name
                out.append({
                    "id": hashlib.sha256(os.fsencode(str(path))).hexdigest()[:24],
                    "path": str(path),
                    "name": entry.name,
                    "source": source,
                    "bytes": st.st_size,
                    "modifiedMs": st.st_mtime_ns // 1000000,
                    "screenshotLikely": is_screenshot_name(entry.name),
                    "mediaType": media_type(path, source),
                    "signature": [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns],
                })
    except OSError:
        return []
    return out


def safe_user_folder(raw):
    """User-requested local folder. Refuse HOME root and symlink traversal."""
    candidate = os.path.expanduser(str(raw or "").strip())
    if not candidate or not os.path.isabs(candidate):
        return None
    path = Path(candidate)
    if ".." in path.parts or any(piece.startswith(".") for piece in
                                  path.parts[len(home().parts):]):
        return None
    try:
        relative = path.relative_to(home())
    except ValueError:
        return None
    if not relative.parts or relative.parts[0] in (
            ".cache", ".config", ".local", ".ssh"):
        return None
    current = home()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    return path if path.is_dir() else None


def gallery_roots(extra_folder=""):
    # Pictures covers legacy nested screenshot folders, while Desktop and
    # Downloads catch screenshots saved before Camera existed. Do not scan
    # the whole home, network mounts or private dotdirectories by default.
    roots = [
        (webcam_root(), "webcam"),
        (video_root(), "recordings"),
        (pictures(), "camera"),
        (screenshots_root(), "screenshots"),
        (home() / "Pictures", "pictures"),
        (desktop(), "desktop"),
        (home() / "Downloads", "downloads"),
        (home() / "Screenshots", "screenshots"),
    ]
    if extra_folder:
        custom = safe_user_folder(extra_folder)
        if custom is None:
            return None
        roots.append((custom, "chosen-folder"))
    return roots


def scan_gallery(extra_folder=""):
    roots = gallery_roots(extra_folder)
    if roots is None:
        return None, [], True
    by_path = {}
    seen_dirs = set()
    queue = deque((root, source, 0) for root, source in roots)
    files_examined = 0
    folders_examined = 0
    truncated = False
    while queue:
        root, source, depth = queue.popleft()
        if root in seen_dirs or root.is_symlink() or not root.is_dir():
            continue
        if folders_examined >= MAX_SCAN_DIRS:
            truncated = True
            break
        seen_dirs.add(root)
        folders_examined += 1
        try:
            with os.scandir(root) as listing:
                for entry in listing:
                    if entry.name.startswith(".") or entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if depth < MAX_SCAN_DEPTH:
                            queue.append((root / entry.name, source, depth + 1))
                        else:
                            truncated = True
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    files_examined += 1
                    if files_examined > MAX_SCAN_FILES:
                        truncated = True
                        queue.clear()
                        break
                    if not is_image(entry):
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    path = root / entry.name
                    if str(path) in by_path:
                        continue
                    shot_dir = (source in ("camera", "screenshots") or
                                "screenshot" in str(root).lower())
                    by_path[str(path)] = {
                        "id": hashlib.sha256(os.fsencode(str(path))).hexdigest()[:24],
                        "path": str(path),
                        "name": entry.name,
                        "source": source,
                        "bytes": st.st_size,
                        "modifiedMs": st.st_mtime_ns // 1000000,
                        "screenshotLikely": bool(shot_dir or is_screenshot_name(entry.name)) and path.suffix.lower() in IMAGE_EXTS,
                        "mediaType": media_type(path, source),
                    }
        except OSError:
            continue
    return roots, list(by_path.values()), truncated


def gallery(page=0, query="", extra_folder="", shots_only=False, media_filter="all"):
    """Bounded local directory traversal, server-side search and paging."""
    if not isinstance(page, int) or page < 0 or page > 100000:
        return {"ok": False, "kind": "gallery", "error": "INVALID_PAGE"}
    if len(query) > 200:
        return {"ok": False, "kind": "gallery", "error": "QUERY_TOO_LONG"}
    roots, records, truncated = scan_gallery(extra_folder)
    if roots is None:
        return {"ok": False, "kind": "gallery", "error": "FOLDER_NOT_PERMITTED"}
    if media_filter not in ("all", "screenshots", "webcam", "videos", "screen-recordings"):
        return {"ok": False, "kind": "gallery", "error": "INVALID_FILTER"}
    if shots_only or media_filter == "screenshots":
        records = [row for row in records if row["screenshotLikely"]]
    elif media_filter == "webcam":
        records = [row for row in records if row["mediaType"] in ("webcam-photo", "webcam-video")]
    elif media_filter == "videos":
        records = [row for row in records if row["mediaType"] in ("webcam-video", "screen-video", "other-video")]
    elif media_filter == "screen-recordings":
        records = [row for row in records if row["mediaType"] == "screen-video"]
    if query.strip():
        needle = query.strip().casefold()
        records = [row for row in records
                   if needle in row["name"].casefold()]
    records.sort(key=lambda row: (-row["modifiedMs"], row["path"]))
    total = len(records)
    start = page * GALLERY_PAGE_SIZE
    result = records[start:start + GALLERY_PAGE_SIZE]
    return {
        "ok": True, "kind": "gallery", "page": page,
        "pageSize": GALLERY_PAGE_SIZE, "total": total,
        "shown": len(result), "files": result,
        "hasMore": start + len(result) < total,
        "truncated": truncated,
        "roots": [str(root) for root, _ in roots],
        "query": query,
        "shotsOnly": bool(shots_only),
        "mediaFilter": media_filter,
        "extraFolder": extra_folder,
        "limitNote": "Paged; only capped by the reported directory scan safety limits.",
    }


def outputs():
    tool = shutil.which("swaymsg")
    if not tool:
        return []
    try:
        done = subprocess.run([tool, "-r", "-t", "get_outputs"],
                              capture_output=True, text=True, timeout=5,
                              check=True)
        data = json.loads(done.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    if not isinstance(data, list):
        return []
    return [
        {"name": row["name"], "focused": bool(row.get("focused"))}
        for row in data if isinstance(row, dict)
        and isinstance(row.get("name"), str)
        and row.get("active", False)
    ]


def status():
    return {
        "ok": True, "kind": "status",
        "grim": bool(shutil.which("grim")),
        "slurp": bool(shutil.which("slurp")),
        "gio": bool(shutil.which("gio")),
        "swaymsg": bool(shutil.which("swaymsg")),
        "outputs": outputs(),
        "saveDirectory": str(pictures()),
        "webcamDirectory": str(webcam_root()),
        "recordingDirectory": str(video_root()),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "wfRecorder": bool(shutil.which("wf-recorder")),
        "videoDevices": video_devices(),
        "recording": recording_status(),
        "desktop": str(desktop()),
    }


def capture(mode):
    """Explicit user action; output names are discovered from active Sway."""
    if mode not in ("region", "focused", "all"):
        return {"ok": False, "kind": "capture", "error": "INVALID_MODE"}
    grim = shutil.which("grim")
    if not grim:
        return {"ok": False, "kind": "capture", "error": "GRIM_NOT_INSTALLED"}
    args = [grim]
    if mode == "focused":
        found = outputs()
        focused = next((x["name"] for x in found if x["focused"]), None)
        if focused is None:
            return {"ok": False, "kind": "capture", "error": "NO_FOCUSED_OUTPUT"}
        args.extend(["-o", focused])
    elif mode == "region":
        slurp = shutil.which("slurp")
        if not slurp:
            return {"ok": False, "kind": "capture", "error": "SLURP_NOT_INSTALLED"}
        try:
            # slurp reads rectangles from stdin when launched without a TTY.
            # Quickshell's child pipe can remain open and block slurp before
            # its Wayland selector appears. Give it EOF immediately.
            # -d shows live dimensions; high-contrast Post-Apollo colors
            # make the native drag rectangle obvious on every monitor.
            selected = subprocess.run([
                slurp, "-d", "-b", "1B062399", "-c", "C74EC7FF",
                "-s", "55CFCA44", "-w", "3",
            ], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "kind": "capture", "error": "REGION_SELECTOR_TIMEOUT"}
        except (OSError, subprocess.SubprocessError):
            return {"ok": False, "kind": "capture", "error": "REGION_UNAVAILABLE"}
        geometry = selected.stdout.strip()
        if selected.returncode != 0 or not re.fullmatch(
                r"-?\d+,-?\d+ \d+x\d+", geometry):
            return {"ok": False, "kind": "capture", "error": "REGION_CANCELLED"}
        args.extend(["-g", geometry])

    root = pictures()
    if root.is_symlink():
        return {"ok": False, "kind": "capture", "error": "SAVE_DIR_SYMLINK"}
    try:
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        now = dt.datetime.now().astimezone()
        filename = "post-apollo_%s_%s_%s.png" % (
            mode, now.strftime("%Y%m%d_%H%M%S_%f"),
            secrets.token_hex(3))
        target = root / filename
        if target.exists():
            return {"ok": False, "kind": "capture", "error": "OUTPUT_EXISTS"}
        result = subprocess.run(args + [str(target)], capture_output=True,
                                timeout=40, check=False)
        if result.returncode or not target.is_file() or target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            return {"ok": False, "kind": "capture", "error": "GRIM_FAILED"}
        return {
            "ok": True, "kind": "capture", "path": str(target),
            "name": filename, "bytes": target.stat().st_size, "mode": mode,
        }
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "kind": "capture", "error": "CAPTURE_UNAVAILABLE"}


def preview_desktop_trash():
    """Preview ONLY files named like screenshots, not every desktop image."""
    files = direct_images(desktop(), "desktop", only_screenshots=True)
    files.sort(key=lambda item: (item["name"].lower(), item["path"]))
    if len(files) > MAX_TRASH:
        return {"ok": False, "kind": "preview", "error": "TOO_MANY_FILES"}
    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "preview", "error": "PLAN_DIR_SYMLINK"}
    if not files:
        return {"ok": True, "kind": "preview", "count": 0, "bytes": 0,
                "planId": "", "sample": [], "source": "Desktop screenshot-like PNG/JPEG/WEBP"}
    try:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        token = secrets.token_hex(16)
        plan = {
            "version": 1, "createdAt": time.time(), "root": str(desktop()),
            "records": [
                {"path": item["path"], "signature": item["signature"]}
                for item in files
            ],
        }
        target = directory / (token + ".json")
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(plan, out, separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        return {
            "ok": True, "kind": "preview", "planId": token,
            "count": len(files), "bytes": sum(item["bytes"] for item in files),
            "sample": [item["name"] for item in files[:12]],
            "source": "Desktop screenshot-like PNG/JPEG/WEBP",
            "expiresSeconds": PLAN_TTL,
            "warning": "Next confirmation moves only verified matching originals to Trash, not permanent deletion.",
        }
    except OSError:
        return {"ok": False, "kind": "preview", "error": "PLAN_SAVE_FAILED"}


def trash_plan(token, confirmed):
    """Two-stage reversible batch cleanup. Never silently recurse/unlink."""
    if confirmed != "MOVE_TO_TRASH" or not PLAN_PATTERN.fullmatch(token or ""):
        return {"ok": False, "kind": "trash", "error": "CONFIRMATION_REQUIRED"}
    gio = shutil.which("gio")
    if not gio:
        return {"ok": False, "kind": "trash", "error": "GIO_NOT_INSTALLED"}
    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "trash", "error": "PLAN_DIR_SYMLINK"}
    path = directory / (token + ".json")
    if path.is_symlink() or not path.is_file():
        return {"ok": False, "kind": "trash", "error": "PLAN_NOT_FOUND"}
    try:
        if path.stat().st_size > MAX_OUTPUT_BYTES * 5:
            return {"ok": False, "kind": "trash", "error": "PLAN_TOO_LARGE"}
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": False, "kind": "trash", "error": "PLAN_INVALID"}
    if (not isinstance(plan, dict) or plan.get("version") != 1
            or plan.get("root") != str(desktop())
            or not isinstance(plan.get("records"), list)
            or len(plan["records"]) > MAX_TRASH
            or not isinstance(plan.get("createdAt"), (int, float))
            or not 0 <= time.time() - plan["createdAt"] <= PLAN_TTL):
        return {"ok": False, "kind": "trash", "error": "PLAN_EXPIRED_OR_INVALID"}

    moved = 0
    skipped = 0
    failed = 0
    for record in plan["records"]:
        if not isinstance(record, dict):
            skipped += 1
            continue
        target = Path(str(record.get("path", "")))
        # No arbitrary paths, no directories, no symlinks, no changed files.
        if target.parent != desktop() or not is_screenshot_name(target.name):
            skipped += 1
            continue
        try:
            st = target.lstat()
            signature = [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]
            if not stat.S_ISREG(st.st_mode) or signature != record.get("signature"):
                skipped += 1
                continue
            proc = subprocess.run([gio, "trash", str(target)], timeout=18,
                                  capture_output=True, check=False)
            if proc.returncode:
                failed += 1
            else:
                moved += 1
        except (OSError, subprocess.SubprocessError):
            failed += 1
    try:
        path.unlink(missing_ok=True)  # Remove only the expired/consumed PLAN.
    except OSError:
        pass
    return {
        "ok": failed == 0 and skipped == 0, "kind": "trash",
        "moved": moved, "skipped": skipped, "failed": failed,
        "recoverable": True, "destination": "Freedesktop Trash",
    }


def preview_selected_trash(raw_path):
    """Selection-specific preview. This action never alters the picture."""
    target = Path(str(raw_path or ""))
    if target.suffix.lower() not in MEDIA_EXTS:
        return {"ok": False, "kind": "preview-selected", "error": "NOT_AN_IMAGE"}
    # The path must stay under HOME, with no hidden/private/symlink parent.
    # Explicitly chosen extra galleries follow the same guard as defaults.
    if safe_user_folder(str(target.parent)) != target.parent:
        return {"ok": False, "kind": "preview-selected",
                "error": "FOLDER_NOT_PERMITTED"}
    try:
        st = target.lstat()
        if not stat.S_ISREG(st.st_mode) or target.is_symlink():
            return {"ok": False, "kind": "preview-selected", "error": "NOT_A_FILE"}
    except OSError:
        return {"ok": False, "kind": "preview-selected", "error": "NOT_A_FILE"}
    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "preview-selected", "error": "PLAN_DIR_SYMLINK"}
    try:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        token = secrets.token_hex(16)
        plan = {
            "version": 2, "createdAt": time.time(),
            "root": str(home()),
            "records": [{"path": str(target), "signature": [
                st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns
            ]}],
        }
        fd = os.open(directory / (token + ".json"),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(plan, out, separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        return {
            "ok": True, "kind": "preview-selected", "planId": token,
            "name": target.name, "path": str(target), "bytes": st.st_size,
            "expiresSeconds": PLAN_TTL,
            "warning": "A separate confirmation moves this one unchanged file to Trash.",
        }
    except OSError:
        return {"ok": False, "kind": "preview-selected", "error": "PLAN_SAVE_FAILED"}


def trash_selected(token, confirmation):
    """Confirmed one-file GIO Trash with a checked one-use, short-lived plan."""
    if confirmation != "MOVE_TO_TRASH" or not PLAN_PATTERN.fullmatch(token or ""):
        return {"ok": False, "kind": "trash-selected",
                "error": "CONFIRMATION_REQUIRED"}
    gio = shutil.which("gio")
    if not gio:
        return {"ok": False, "kind": "trash-selected", "error": "GIO_NOT_INSTALLED"}
    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "trash-selected", "error": "PLAN_DIR_SYMLINK"}
    path = directory / (token + ".json")
    if path.is_symlink() or not path.is_file():
        return {"ok": False, "kind": "trash-selected", "error": "PLAN_NOT_FOUND"}
    try:
        if path.stat().st_size > MAX_OUTPUT_BYTES:
            return {"ok": False, "kind": "trash-selected", "error": "PLAN_TOO_LARGE"}
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": False, "kind": "trash-selected", "error": "PLAN_INVALID"}
    if (not isinstance(plan, dict) or plan.get("version") != 2
            or plan.get("root") != str(home())
            or not isinstance(plan.get("records"), list)
            or len(plan["records"]) != 1
            or not isinstance(plan.get("createdAt"), (int, float))
            or not 0 <= time.time() - plan["createdAt"] <= PLAN_TTL):
        return {"ok": False, "kind": "trash-selected",
                "error": "PLAN_EXPIRED_OR_INVALID"}
    record = plan["records"][0]
    if not isinstance(record, dict):
        return {"ok": False, "kind": "trash-selected", "error": "PLAN_INVALID"}
    target = Path(str(record.get("path", "")))
    if (target.suffix.lower() not in MEDIA_EXTS or
            safe_user_folder(str(target.parent)) != target.parent):
        return {"ok": False, "kind": "trash-selected", "error": "FOLDER_NOT_PERMITTED"}
    try:
        st = target.lstat()
        fingerprint = [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]
        if not stat.S_ISREG(st.st_mode) or target.is_symlink() or (
                fingerprint != record.get("signature")):
            return {"ok": False, "kind": "trash-selected", "error": "FILE_CHANGED"}
        proc = subprocess.run([gio, "trash", str(target)], timeout=18,
                              capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "kind": "trash-selected", "error": "TRASH_FAILED"}
    if proc.returncode:
        return {"ok": False, "kind": "trash-selected", "error": "TRASH_FAILED"}
    try:
        path.unlink(missing_ok=True)  # Only the used plan, never a screenshot.
    except OSError:
        pass
    return {
        "ok": True, "kind": "trash-selected", "moved": 1,
        "name": target.name, "recoverable": True, "destination": "Freedesktop Trash",
    }




def preview_batch_trash(raw_paths, extra_folder=""):
    """Prepare an explicit Gallery selection. Nothing is moved in preview."""
    if not isinstance(raw_paths, str) or len(raw_paths.encode("utf-8")) > MAX_BATCH_ARG_BYTES:
        return {"ok": False, "kind": "preview-batch", "error": "SELECTION_TOO_LARGE"}
    try:
        paths = json.loads(raw_paths)
    except (TypeError, ValueError):
        return {"ok": False, "kind": "preview-batch", "error": "INVALID_SELECTION"}
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_BATCH_TRASH:
        return {"ok": False, "kind": "preview-batch", "error": "INVALID_SELECTION_SIZE"}
    if (not all(isinstance(raw, str) and raw.startswith("/")
                and len(raw) <= 4096 for raw in paths)
            or len(set(paths)) != len(paths)):
        return {"ok": False, "kind": "preview-batch", "error": "INVALID_OR_DUPLICATE_PATH"}

    roots, gallery_records, truncated = scan_gallery(extra_folder)
    if roots is None:
        return {"ok": False, "kind": "preview-batch", "error": "FOLDER_NOT_PERMITTED"}
    if truncated:
        return {"ok": False, "kind": "preview-batch", "error": "SCAN_TRUNCATED"}
    inventory = {row["path"]: row for row in gallery_records}
    records = []
    total_bytes = 0
    sample = []
    # Every candidate must have been discovered in the current bounded
    # Gallery scan. Reject the whole preview on any stale/invalid selection.
    for raw in paths:
        if raw not in inventory:
            return {"ok": False, "kind": "preview-batch", "error": "NOT_IN_GALLERY"}
        target = Path(raw)
        if (target.suffix.lower() not in MEDIA_EXTS or
                safe_user_folder(str(target.parent)) != target.parent):
            return {"ok": False, "kind": "preview-batch", "error": "FOLDER_NOT_PERMITTED"}
        try:
            st = target.lstat()
        except OSError:
            return {"ok": False, "kind": "preview-batch", "error": "FILE_CHANGED"}
        if not stat.S_ISREG(st.st_mode) or target.is_symlink():
            return {"ok": False, "kind": "preview-batch", "error": "FILE_CHANGED"}
        records.append({"path": raw, "signature": [
            st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]})
        total_bytes += st.st_size
        if len(sample) < 12:
            sample.append(target.name)

    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "preview-batch", "error": "PLAN_DIR_SYMLINK"}
    try:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        token = secrets.token_hex(16)
        plan = {"version": 3, "root": str(home()), "createdAt": time.time(),
                "source": "gallery-batch", "records": records}
        fd = os.open(directory / (token + ".json"),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(plan, out, separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        return {"ok": True, "kind": "preview-batch", "planId": token,
                "count": len(records), "bytes": total_bytes,
                "sample": sample, "expiresSeconds": PLAN_TTL,
                "warning": "REVIEW FIRST // Only unchanged selected originals move to recoverable Trash."}
    except OSError:
        return {"ok": False, "kind": "preview-batch", "error": "PLAN_SAVE_FAILED"}


def trash_batch_now(raw_paths, confirmation, extra_folder=""):
    """One user action: validate selected Gallery originals and GIO-trash.

    The same preview signature and one-use plan protections still apply,
    but no extra UI confirmation or separate user gesture is needed.
    The literal confirmation token represents the explicit Trash button.
    """
    if confirmation != "MOVE_TO_TRASH":
        return {"ok": False, "kind": "trash-batch-now",
                "error": "CONFIRMATION_REQUIRED"}
    plan = preview_batch_trash(raw_paths, extra_folder)
    if not plan.get("ok") or not plan.get("planId"):
        return {"ok": False, "kind": "trash-batch-now",
                "error": str(plan.get("error") or "PREVIEW_FAILED")}
    # Retain the existing one-use 10m plan, file-change checks, and
    # recoverable GIO operation, all in the SAME CLI process.
    result = trash_batch(plan["planId"], confirmation)
    if result.get("ok"):
        result["kind"] = "trash-batch-now"
    return result


def trash_batch(token, confirmation):
    """Consume one short-lived plan and move verified items to GIO Trash."""
    if confirmation != "MOVE_TO_TRASH" or not PLAN_PATTERN.fullmatch(token or ""):
        return {"ok": False, "kind": "trash-batch", "error": "CONFIRMATION_REQUIRED"}
    gio = shutil.which("gio")
    if not gio:
        return {"ok": False, "kind": "trash-batch", "error": "GIO_NOT_INSTALLED"}
    directory = plan_dir()
    if directory.is_symlink():
        return {"ok": False, "kind": "trash-batch", "error": "PLAN_DIR_SYMLINK"}
    source = directory / (token + ".json")
    claimed = directory / (token + ".claimed")
    if (source.is_symlink() or not source.is_file() or
            claimed.exists() or claimed.is_symlink()):
        return {"ok": False, "kind": "trash-batch", "error": "PLAN_NOT_FOUND"}
    # Atomically claim before any side effects. Concurrent/replayed actions
    # cannot use the same plan twice. Aborted claims are never replayed.
    try:
        os.rename(source, claimed)
    except OSError:
        return {"ok": False, "kind": "trash-batch", "error": "PLAN_NOT_FOUND"}
    try:
        if claimed.is_symlink() or claimed.stat().st_size > MAX_OUTPUT_BYTES * 5:
            return {"ok": False, "kind": "trash-batch", "error": "PLAN_INVALID"}
        try:
            plan = json.loads(claimed.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"ok": False, "kind": "trash-batch", "error": "PLAN_INVALID"}
        if (not isinstance(plan, dict) or plan.get("version") != 3
                or plan.get("source") != "gallery-batch"
                or plan.get("root") != str(home())
                or not isinstance(plan.get("createdAt"), (int, float))
                or not 0 <= time.time() - plan["createdAt"] <= PLAN_TTL
                or not isinstance(plan.get("records"), list)
                or not 1 <= len(plan["records"]) <= MAX_BATCH_TRASH):
            return {"ok": False, "kind": "trash-batch",
                    "error": "PLAN_EXPIRED_OR_INVALID"}

        seen = set()
        targets = []
        # Validate the COMPLETE plan before moving any files. A corrupted
        # plan cannot trick the backend into processing arbitrary paths.
        for row in plan["records"]:
            if not isinstance(row, dict) or not isinstance(row.get("signature"), list):
                return {"ok": False, "kind": "trash-batch", "error": "PLAN_INVALID"}
            raw = row.get("path")
            if not isinstance(raw, str) or raw in seen:
                return {"ok": False, "kind": "trash-batch", "error": "PLAN_INVALID"}
            target = Path(raw)
            if (not target.is_absolute() or target.suffix.lower() not in MEDIA_EXTS
                    or safe_user_folder(str(target.parent)) != target.parent):
                return {"ok": False, "kind": "trash-batch", "error": "FOLDER_NOT_PERMITTED"}
            seen.add(raw)
            targets.append((target, row["signature"]))

        moved = 0
        skipped = 0
        failed = 0
        unmoved_paths = []
        for target, signature in targets:
            try:
                st = target.lstat()
                current = [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]
                if (not stat.S_ISREG(st.st_mode) or target.is_symlink()
                        or current != signature):
                    skipped += 1
                    unmoved_paths.append(str(target))
                    continue
                proc = subprocess.run([gio, "trash", str(target)], timeout=18,
                                      capture_output=True, check=False)
                if proc.returncode:
                    failed += 1
                    unmoved_paths.append(str(target))
                else:
                    moved += 1
            except FileNotFoundError:
                skipped += 1
                unmoved_paths.append(str(target))
            except (OSError, subprocess.SubprocessError):
                failed += 1
                unmoved_paths.append(str(target))
        return {"ok": True, "kind": "trash-batch", "moved": moved,
                "skipped": skipped, "failed": failed,
                "unmovedPaths": unmoved_paths,
                "recoverable": True, "destination": "Freedesktop Trash"}
    finally:
        try:
            claimed.unlink(missing_ok=True)
        except OSError:
            pass


def media_type(path, source):
    """Classify by owned output folder and extension, never filename alone for videos."""
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTS:
        if source == "recordings":
            return "webcam-video" if path.name.startswith("webcam_") else "screen-video" if path.name.startswith("screen_") else "other-video"
        return "other-video"
    if source == "webcam":
        return "webcam-photo"
    if source in ("camera", "screenshots") or is_screenshot_name(path.name):
        return "screenshot"
    return "other-image"


def video_devices():
    """Read-only V4L2 device discovery; capture requires an explicit valid node."""
    return [str(p) for p in sorted(Path("/dev").glob("video[0-9]*"))
            if VIDEO_DEVICE.fullmatch(str(p)) and p.exists()]


def camera_device(raw):
    candidate = str(raw or "")
    if not candidate:
        devices = video_devices()
        candidate = devices[0] if devices else ""
    return candidate if VIDEO_DEVICE.fullmatch(candidate) and Path(candidate).exists() else None


def output_target(root, prefix, suffix):
    if root.is_symlink() or any(p.is_symlink() for p in (root.parent,)):
        raise OSError("SYMLINK_OUTPUT")
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    now = dt.datetime.now().astimezone()
    name = prefix + "_" + now.strftime("%Y%m%d_%H%M%S_%f") + "_" + secrets.token_hex(3) + suffix
    target = root / name
    if target.exists():
        raise OSError("OUTPUT_EXISTS")
    return target


def webcam_photo_capture(device=""):
    ffmpeg = shutil.which("ffmpeg")
    node = camera_device(device)
    if not ffmpeg:
        return {"ok": False, "kind": "webcam-photo", "error": "FFMPEG_MISSING"}
    if not node:
        return {"ok": False, "kind": "webcam-photo", "error": "NO_WEBCAM_DEVICE"}
    try:
        target = output_target(webcam_root(), "webcam", ".jpg")
        result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error",
            "-nostdin", "-f", "video4linux2", "-i", node,
            "-frames:v", "1", "-y", str(target)], timeout=25,
            capture_output=True, check=False)
        if result.returncode or not target.is_file() or target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            return {"ok": False, "kind": "webcam-photo", "error": "WEBCAM_CAPTURE_FAILED"}
        return {"ok": True, "kind": "webcam-photo", "path": str(target),
                "name": target.name, "bytes": target.stat().st_size}
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "kind": "webcam-photo", "error": "WEBCAM_UNAVAILABLE"}


def _pid_start_ticks(pid):
    try:
        # /proc/PID/stat field 22; the command name may contain spaces.
        fields = Path("/proc/%d/stat" % pid).read_text().rsplit(")", 1)[1].strip().split()
        return fields[19]
    except (OSError, ValueError, IndexError):
        return None


def _read_recording():
    path = recording_state_path()
    if path.is_symlink() or not path.is_file():
        return None
    try:
        if path.stat().st_size > 4096:
            return None
        data = json.loads(path.read_text())
        if (not isinstance(data, dict) or
                type(data.get("pid")) is not int or data["pid"] <= 1 or
                not isinstance(data.get("ticks"), str) or
                data.get("mode") not in ("webcam", "screen") or
                not isinstance(data.get("path"), str)):
            return None
        return data
    except (OSError, ValueError):
        return None


def _recording_alive(data):
    return bool(data and _pid_start_ticks(data["pid"]) == data["ticks"])


def recording_status():
    data = _read_recording()
    live = _recording_alive(data)
    return {"ok": True, "kind": "record-status", "recording": live,
            "mode": data["mode"] if live else "",
            "path": data["path"] if live else ""}


def record_start_action(mode, device=""):
    if _recording_alive(_read_recording()):
        return {"ok": False, "kind": "record-start", "error": "ALREADY_RECORDING"}
    if mode == "webcam":
        tool = shutil.which("ffmpeg")
        node = camera_device(device)
        if not tool or not node:
            return {"ok": False, "kind": "record-start", "error": "WEBCAM_OR_FFMPEG_MISSING"}
    else:
        tool = shutil.which("wf-recorder")
        if not tool:
            return {"ok": False, "kind": "record-start", "error": "WF_RECORDER_MISSING"}
    state = recording_state_path()
    if state.is_symlink() or state.parent.is_symlink():
        return {"ok": False, "kind": "record-start", "error": "STATE_SYMLINK"}
    try:
        target = output_target(video_root(), mode, ".mp4")
        if mode == "webcam":
            args = [tool, "-hide_banner", "-loglevel", "error", "-nostdin",
                    "-f", "video4linux2", "-i", node, "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(target)]
        else:
            args = [tool, "-f", str(target)]
        # No shell or network. Start an isolated process group for an explicit
        # STOP action; persist PID and Linux start ticks to avoid PID reuse.
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True)
        ticks = None
        for _ in range(10):
            ticks = _pid_start_ticks(process.pid)
            if ticks:
                break
            time.sleep(0.01)
        if not ticks:
            process.terminate()
            return {"ok": False, "kind": "record-start", "error": "PROCESS_NOT_TRACKABLE"}
        state.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd = os.open(state, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump({"pid": process.pid, "ticks": ticks, "mode": mode,
                       "path": str(target)}, out)
        return {"ok": True, "kind": "record-start", "recording": True,
                "mode": mode, "path": str(target), "name": target.name}
    except OSError:
        return {"ok": False, "kind": "record-start", "error": "RECORD_START_FAILED"}


def record_stop_action():
    data = _read_recording()
    if not _recording_alive(data):
        return {"ok": False, "kind": "record-stop", "error": "NOT_RECORDING"}
    try:
        # The process was started as its own session; only stop the exact
        # still-matching process, never an unrelated PID after reuse.
        os.kill(data["pid"], signal.SIGINT)
        for _ in range(40):
            if not _recording_alive(data):
                break
            time.sleep(0.1)
        if _recording_alive(data):
            return {"ok": False, "kind": "record-stop", "error": "STOP_TIMEOUT"}
        recording_state_path().unlink(missing_ok=True)
        target = Path(data["path"])
        return {"ok": True, "kind": "record-stop", "recording": False,
                "path": str(target), "name": target.name,
                "bytes": target.stat().st_size if target.is_file() else 0}
    except OSError:
        return {"ok": False, "kind": "record-stop", "error": "STOP_FAILED"}



# Installation is never part of status, tab activation or client launch.
# The only package-writing path is a separate, explicitly confirmed action.
ZOOM_FLATPAK_ID = "us.zoom.Zoom"
ZOOM_FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"
ZOOM_INSTALL_CONFIRMATION = "CONFIRM_ZOOM_INSTALL"


def _zoom_install_command(argv, timeout):
    """Fixed argv only; do not expose package-manager output or run a shell."""
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return False


def _zoom_official_rpm():
    """Bound installation to the expected downloaded Fedora x86_64 Zoom RPM."""
    downloads = home() / "Downloads"
    if downloads.is_symlink() or not downloads.is_dir():
        return None, "DOWNLOADS_UNAVAILABLE"
    target = downloads / "zoom_x86_64.rpm"
    try:
        info = target.lstat()
    except OSError:
        return None, "ZOOM_RPM_NOT_DOWNLOADED"
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_size < 4096 or info.st_size > 1_000_000_000
            or info.st_mode & (stat.S_IWOTH | stat.S_IWGRP)):
        return None, "ZOOM_RPM_UNSAFE_FILE"
    return target, ""


def zoom_install_client(method, confirmation):
    """Explicit interactive setup action. No installation on passive checks."""
    if confirmation != ZOOM_INSTALL_CONFIRMATION:
        return {"ok": False, "kind": "zoom-install", "error": "INSTALL_CONFIRMATION_REQUIRED"}
    if method not in ("official-rpm", "community-flatpak"):
        return {"ok": False, "kind": "zoom-install", "error": "INSTALL_METHOD_UNSUPPORTED"}
    if zoom_client_command():
        return {"ok": False, "kind": "zoom-install", "error": "ZOOM_ALREADY_INSTALLED"}

    if method == "community-flatpak":
        flatpak = shutil.which("flatpak")
        if not flatpak:
            return {"ok": False, "kind": "zoom-install", "error": "FLATPAK_NOT_AVAILABLE"}
        # The confirmation UI explicitly discloses addition of a per-user
        # Flathub remote (if absent); system remotes and packages are untouched.
        remote = _zoom_install_command([
            flatpak, "remote-add", "--user", "--if-not-exists",
            "flathub", ZOOM_FLATHUB_REPO], timeout=45)
        if remote is None:
            code = "FLATHUB_REMOTE_TIMEOUT"
        elif remote is False or remote.returncode:
            code = "FLATHUB_REMOTE_FAILED"
        else:
            code = ""
        if code:
            return {"ok": False, "kind": "zoom-install", "error": code}
        installed = _zoom_install_command([
            flatpak, "install", "--user", "--noninteractive", "--assumeyes",
            "flathub", ZOOM_FLATPAK_ID], timeout=900)
        if installed is None:
            code = "FLATPAK_INSTALL_TIMEOUT_CHECK_STATUS"
        elif installed is False or installed.returncode:
            code = "FLATPAK_INSTALL_FAILED"
        else:
            code = ""
        if code:
            return {"ok": False, "kind": "zoom-install", "error": code}
        # Never claim success based only on process exit status.
        verified = _zoom_install_command([
            flatpak, "info", "--user", ZOOM_FLATPAK_ID], timeout=15)
        if verified is None or verified is False or verified.returncode:
            return {"ok": False, "kind": "zoom-install",
                    "error": "FLATPAK_INSTALL_NOT_VERIFIED"}
        return {"ok": True, "kind": "zoom-install", "method": method,
                "installed": True, "restartRequired": False,
                "authentication": "UNKNOWN"}

    # Publisher RPM path. Never fetch an arbitrary user-supplied URL or install
    # an arbitrary RPM. Signed file must already be downloaded explicitly.
    target, failure = _zoom_official_rpm()
    if failure:
        return {"ok": False, "kind": "zoom-install", "error": failure}
    rpm = shutil.which("rpm")
    rpmkeys = shutil.which("rpmkeys")
    ostree = shutil.which("rpm-ostree")
    if not rpm or not rpmkeys or not ostree:
        return {"ok": False, "kind": "zoom-install",
                "error": "RPM_INSTALL_TOOLS_MISSING"}
    info = _zoom_install_command([
        rpm, "-qp", "--queryformat", "%{NAME} %{ARCH}", str(target)], timeout=15)
    if info is None or info is False or info.returncode or info.stdout.strip() != b"zoom x86_64":
        return {"ok": False, "kind": "zoom-install",
                "error": "ZOOM_RPM_INVALID_PACKAGE"}
    signature = _zoom_install_command([
        rpmkeys, "--checksig", str(target)], timeout=15)
    if signature is None or signature is False:
        return {"ok": False, "kind": "zoom-install",
                "error": "ZOOM_RPM_SIGNATURE_UNVERIFIED"}
    message = (signature.stdout + signature.stderr).lower()
    if (signature.returncode or b"nokey" in message or
            b"not ok" in message or b"signature" not in message or
            b"ok" not in message):
        return {"ok": False, "kind": "zoom-install",
                "error": "ZOOM_RPM_SIGNATURE_UNVERIFIED"}
    # Polkit is expected to request privileged authorization if needed.
    # No sudo passwords are read, no automatic reboot, no shell invocation.
    polkit = shutil.which("pkexec")
    command = ([polkit, ostree, "install", str(target)] if polkit else
               [ostree, "install", str(target)])
    result = _zoom_install_command(command, timeout=900)
    if result is None:
        return {"ok": False, "kind": "zoom-install",
                "error": "RPM_INSTALL_TIMEOUT_CHECK_DEPLOYMENT"}
    if result is False or result.returncode:
        return {"ok": False, "kind": "zoom-install",
                "error": "RPM_INSTALL_FAILED_OR_AUTH_DENIED"}
    return {"ok": True, "kind": "zoom-install", "method": method,
            "installed": False, "staged": True,
            "restartRequired": True, "authentication": "UNKNOWN"}


def zoom_client_command():
    """Discover the actual installed Zoom location; never use a browser fallback."""
    native = shutil.which("zoom")
    if native:
        return [native]
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return None
    # Installation is explicitly per-user in Camera's installer. Avoid relying
    # on Flatpak's implicit search when user and system installations coexist.
    for scope in ("--user", "--system"):
        try:
            check = subprocess.run(
                [flatpak, "info", scope, ZOOM_FLATPAK_ID],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=8, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if check.returncode == 0:
            return [flatpak, "run", scope, ZOOM_FLATPAK_ID]
    return None


def zoom_client_status():
    """Installation is not evidence of a running app or authenticated account."""
    command = zoom_client_command()
    return {"ok": True, "kind": "zoom-status",
            "available": bool(command),
            "client": "native" if command and len(command) == 1 else
                      "flatpak" if command else "none",
            "installation": command[2].lstrip("-") if command and len(command) == 4 else "none",
            "authentication": "UNKNOWN",
            "embedded": False,
            "socialAuthShared": False}


def _zoom_sway_window_state():
    """Inspect only app ID/class (never titles or content) for visible Zoom windows."""
    swaymsg = shutil.which("swaymsg")
    if not swaymsg:
        return "UNKNOWN"
    try:
        response = subprocess.run([swaymsg, "-t", "get_tree"],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, timeout=5, check=False)
        if response.returncode or len(response.stdout) > 2_000_000:
            return "UNKNOWN"
        tree = json.loads(response.stdout)
    except (OSError, ValueError, subprocess.SubprocessError, TypeError):
        return "UNKNOWN"
    pending = [tree]
    visited = 0
    found = False
    exact = {"zoom", "us.zoom.zoom", "zoom workplace", "zoom-client"}
    while pending and visited < 12000:
        item = pending.pop()
        visited += 1
        if not isinstance(item, dict):
            continue
        props = item.get("window_properties") or {}
        if not isinstance(props, dict):
            props = {}
        identities = (item.get("app_id"), props.get("class"), props.get("instance"))
        if any(isinstance(value, str) and value.strip().casefold() in exact
               for value in identities):
            if item.get("visible") is True:
                return "VISIBLE"
            found = True
        for key in ("nodes", "floating_nodes"):
            nodes = item.get(key)
            if isinstance(nodes, list):
                pending.extend(nodes[:12000])
    return "OTHER_WORKSPACE" if found else "NOT_FOUND"


def zoom_launch_check():
    """Read-only launch inspection, not a claim of authentication or meeting state."""
    argv = zoom_client_command()
    if not argv:
        return {"ok": True, "kind": "zoom-launch-check", "installed": False,
                "windowState": "NOT_FOUND", "flatpakRunning": False}
    running = None
    if len(argv) == 4:
        try:
            result = subprocess.run([argv[0], "ps", "--columns=application"],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, timeout=6, check=False)
            if result.returncode == 0 and len(result.stdout) < 100_000:
                running = ZOOM_FLATPAK_ID in result.stdout.decode(
                    "utf-8", "replace").splitlines()
        except (OSError, subprocess.SubprocessError, TypeError):
            pass
    return {"ok": True, "kind": "zoom-launch-check", "installed": True,
            "windowState": _zoom_sway_window_state(), "flatpakRunning": running}


def _zoom_native_focus():
    """Focus an existing Zoom app container after an explicit user click.

    Match only exact application IDs/classes, never window titles or user data.
    No shell, no arbitrary command arguments and no focus on mode entry.
    """
    swaymsg = shutil.which("swaymsg")
    if not swaymsg:
        return False
    try:
        tree_result = subprocess.run([swaymsg, "-t", "get_tree"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=5, check=False)
        if tree_result.returncode != 0 or len(tree_result.stdout) > 2_000_000:
            return False
        tree = json.loads(tree_result.stdout)
        todo = [tree]
        visits = 0
        exact = {"zoom", "us.zoom.zoom", "zoom workplace", "zoom-client"}
        while todo and visits < 12000:
            item = todo.pop()
            visits += 1
            if not isinstance(item, dict):
                continue
            props = item.get("window_properties") or {}
            if not isinstance(props, dict):
                props = {}
            match = any(isinstance(value, str) and value.strip().casefold() in exact
                        for value in (item.get("app_id"), props.get("class"),
                                      props.get("instance")))
            if match and isinstance(item.get("id"), int) and item["id"] > 0:
                # Only the exact compositor-owned con_id observed above.
                result = subprocess.run(
                    [swaymsg, "[con_id=%d]" % item["id"], "focus"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=5, check=False)
                return result.returncode == 0
            for key in ("nodes", "floating_nodes"):
                nodes = item.get(key)
                if isinstance(nodes, list):
                    todo.extend(nodes[:12000])
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        pass
    return False


def zoom_activate_client():
    """Explicit OPEN ZOOM action: focus its window or request native launch.

    A background Flatpak process by itself must not prevent the user from
    attempting to open Zoom's actual GUI. No call or login is invented.
    """
    if not zoom_client_command():
        return {"ok": False, "kind": "zoom-activate",
                "error": "ZOOM_CLIENT_NOT_INSTALLED"}
    if _zoom_native_focus():
        return {"ok": True, "kind": "zoom-activate",
                "activation": "WINDOW_FOCUSED", "windowVerified": True,
                "authentication": "UNKNOWN"}
    result = zoom_client_open()
    result["kind"] = "zoom-activate"
    if result["ok"]:
        result["activation"] = "LAUNCH_REQUESTED_WINDOW_UNVERIFIED"
        result["windowVerified"] = False
    return result


def zoom_client_open():
    """Check immediate launch failure; a spawned process is not a visible window."""
    argv = zoom_client_command()
    if not argv:
        return {"ok": False, "kind": "zoom-open", "error": "ZOOM_CLIENT_NOT_INSTALLED"}
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True)
        # Flatpak may fail immediately (missing runtime, display, session bus).
        # A short, bounded observation catches a nonzero exit without blocking
        # until the actual video-call app closes or logging credentials.
        deadline = time.monotonic() + 1.5
        exit_code = process.poll()
        while exit_code is None and time.monotonic() < deadline:
            time.sleep(0.1)
            exit_code = process.poll()
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "kind": "zoom-open", "error": "ZOOM_LAUNCH_FAILED"}
    if exit_code is not None and exit_code != 0:
        return {"ok": False, "kind": "zoom-open",
                "error": "ZOOM_START_EXITED_NONZERO",
                "exitCode": exit_code if 0 < exit_code < 256 else -1}
    return {"ok": True, "kind": "zoom-open", "launchRequested": True,
            "launchState": "PROCESS_RUNNING_UNVERIFIED" if exit_code is None
                           else "HANDOFF_UNVERIFIED",
            "authentication": "UNKNOWN", "embedded": False}


# Read-only checks run only while the user is viewing Zoom mode. HTTPS probes
# disclose the computer's public network address to the fixed destinations;
# they do not send identity labels, credentials, cookies or meeting data.
ZOOM_REACHABILITY_URL = "https://zoom.us/"
INTERNET_REACHABILITY_URL = "https://example.com/"


def _camera_https_reachable(url):
    """Network/TLS path only. Even a response is not Zoom login confirmation."""
    try:
        request = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "Post-Apollo-Camera/1"})
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status < 500
    except urllib.error.HTTPError as error:
        # The host answered over HTTPS, but a 5xx is not a healthy endpoint.
        return error.code < 500
    except (OSError, ValueError, urllib.error.URLError):
        return False


def zoom_connectivity():
    """Independent external reachability probes, never provider account state."""
    internet = _camera_https_reachable(INTERNET_REACHABILITY_URL)
    zoom = _camera_https_reachable(ZOOM_REACHABILITY_URL)
    return {"ok": True, "kind": "zoom-connectivity",
            # A single HEAD failure cannot prove internet or Zoom is offline.
            # Do not turn two transient web probes into red offline badges.
            "internet": "REACHABLE" if internet else "UNVERIFIED",
            "zoomService": "REACHABLE" if zoom else "UNVERIFIED",
            "account": "UNKNOWN",
            "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def zoom_enter_mode():
    """User-selected ZOOM mode opens installed client once, without repeat launch."""
    check = zoom_launch_check()
    if not check["installed"]:
        return {"ok": True, "kind": "zoom-enter",
                "installed": False, "client": "none", "installation": "none",
                "launch": "NOT_INSTALLED", "windowState": "NOT_FOUND",
                "account": "UNKNOWN", "embedded": False}
    argv = zoom_client_command()
    status = {"ok": True, "kind": "zoom-enter", "installed": True,
              "client": "native" if len(argv) == 1 else "flatpak",
              "installation": argv[2].lstrip("-") if len(argv) == 4 else "none",
              "windowState": check["windowState"],
              "flatpakRunning": check["flatpakRunning"],
              "account": "UNKNOWN", "embedded": False}
    if check["windowState"] in ("VISIBLE", "OTHER_WORKSPACE") or check["flatpakRunning"] is True:
        status["launch"] = "ALREADY_RUNNING"
        return status
    result = zoom_client_open()
    if result["ok"]:
        status["launch"] = "SUBMITTED_UNVERIFIED"
    else:
        status["launch"] = "FAILED"
        status["launchError"] = result["error"]
    return status


def main(argv=None):
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="action", required=True)
    command.add_parser("status")
    command.add_parser("zoom-status")
    command.add_parser("zoom-open")
    command.add_parser("zoom-activate")
    command.add_parser("zoom-launch-check")
    command.add_parser("zoom-enter")
    command.add_parser("zoom-connectivity")
    zoom_install = command.add_parser("zoom-install")
    zoom_install.add_argument("method", choices=["official-rpm", "community-flatpak"])
    zoom_install.add_argument("confirmation")
    gallery_parser = command.add_parser("gallery")
    gallery_parser.add_argument("--page", type=int, default=0)
    gallery_parser.add_argument("--query", default="")
    gallery_parser.add_argument("--folder", default="")
    gallery_parser.add_argument("--shots-only", action="store_true")
    gallery_parser.add_argument("--media-filter", default="all", choices=["all", "screenshots", "webcam", "videos", "screen-recordings"])
    capture_parser = command.add_parser("capture")
    capture_parser.add_argument("mode", choices=["region", "focused", "all"])
    webcam_photo = command.add_parser("webcam-photo")
    webcam_photo.add_argument("--device", default="")
    record_start = command.add_parser("record-start")
    record_start.add_argument("mode", choices=["webcam", "screen"])
    record_start.add_argument("--device", default="")
    command.add_parser("record-status")
    command.add_parser("record-stop")
    command.add_parser("preview-trash")
    trash_parser = command.add_parser("trash")
    trash_parser.add_argument("plan_id")
    trash_parser.add_argument("confirmation")
    selected_preview = command.add_parser("preview-selected")
    selected_preview.add_argument("path")
    selected_trash = command.add_parser("trash-selected")
    selected_trash.add_argument("plan_id")
    selected_trash.add_argument("confirmation")
    batch_preview = command.add_parser("preview-batch")
    batch_preview.add_argument("paths_json")
    batch_preview.add_argument("--folder", default="")
    batch_trash = command.add_parser("trash-batch")
    batch_trash.add_argument("plan_id")
    batch_trash.add_argument("confirmation")
    batch_now = command.add_parser("trash-batch-now")
    batch_now.add_argument("paths_json")
    batch_now.add_argument("confirmation")
    batch_now.add_argument("--folder", default="")
    options = parser.parse_args(argv)

    if options.action == "status":
        result = status()
    elif options.action == "zoom-status":
        result = zoom_client_status()
    elif options.action == "zoom-open":
        result = zoom_client_open()
    elif options.action == "zoom-activate":
        result = zoom_activate_client()
    elif options.action == "zoom-launch-check":
        result = zoom_launch_check()
    elif options.action == "zoom-enter":
        result = zoom_enter_mode()
    elif options.action == "zoom-connectivity":
        result = zoom_connectivity()
    elif options.action == "zoom-install":
        result = zoom_install_client(options.method, options.confirmation)
    elif options.action == "gallery":
        result = gallery(options.page, options.query,
                         options.folder, options.shots_only, options.media_filter)
    elif options.action == "capture":
        result = capture(options.mode)
    elif options.action == "webcam-photo":
        result = webcam_photo_capture(options.device)
    elif options.action == "record-start":
        result = record_start_action(options.mode, options.device)
    elif options.action == "record-stop":
        result = record_stop_action()
    elif options.action == "record-status":
        result = recording_status()
    elif options.action == "preview-trash":
        result = preview_desktop_trash()
    elif options.action == "preview-selected":
        result = preview_selected_trash(options.path)
    elif options.action == "trash-selected":
        result = trash_selected(options.plan_id, options.confirmation)
    elif options.action == "preview-batch":
        result = preview_batch_trash(options.paths_json, options.folder)
    elif options.action == "trash-batch":
        result = trash_batch(options.plan_id, options.confirmation)
    elif options.action == "trash-batch-now":
        result = trash_batch_now(options.paths_json, options.confirmation,
                                 options.folder)
    else:
        result = trash_plan(options.plan_id, options.confirmation)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
