#!/usr/bin/env python3
"""Camera M1: local-only Sway screenshots, image inventory and reversible cleanup.

No daemon, network, JSON database or automatic scans. The owning QML widget
executes one action on user input. Destructive cleanup is limited to matching
screenshot-like files immediately inside Desktop, only after preview and a
second explicit confirmation. "Trash" uses GIO; no unlink/rm fallback.
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
import shutil
import stat
import subprocess
import sys
import time

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SCREENSHOT_NAME = re.compile(
    r"(screenshot|screen[\s_-]?shot|grim|spectacle|swappy|flameshot)",
    re.IGNORECASE,
)
PLAN_PATTERN = re.compile(r"^[a-f0-9]{32}$")
PLAN_TTL = 600
MAX_TRASH = 20000
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


def screenshots_root():
    return home() / "Pictures" / "Screenshots"


def plan_dir():
    base = Path(os.environ.get("XDG_STATE_HOME", str(home() / ".local" / "state")))
    return base / "post-apollo" / "camera-plans"


def is_image(entry):
    try:
        return (entry.is_file(follow_symlinks=False) and
                not entry.is_symlink() and
                Path(entry.name).suffix.lower() in IMAGE_EXTS)
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
                        "screenshotLikely": bool(shot_dir or is_screenshot_name(entry.name)),
                    }
        except OSError:
            continue
    return roots, list(by_path.values()), truncated


def gallery(page=0, query="", extra_folder="", shots_only=False):
    """Bounded local directory traversal, server-side search and paging."""
    if not isinstance(page, int) or page < 0 or page > 100000:
        return {"ok": False, "kind": "gallery", "error": "INVALID_PAGE"}
    if len(query) > 200:
        return {"ok": False, "kind": "gallery", "error": "QUERY_TOO_LONG"}
    roots, records, truncated = scan_gallery(extra_folder)
    if roots is None:
        return {"ok": False, "kind": "gallery", "error": "FOLDER_NOT_PERMITTED"}
    if shots_only:
        records = [row for row in records if row["screenshotLikely"]]
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
            selected = subprocess.run([slurp], capture_output=True, text=True,
                                      timeout=120, check=False)
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
    if target.suffix.lower() not in IMAGE_EXTS:
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
    if (target.suffix.lower() not in IMAGE_EXTS or
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="action", required=True)
    command.add_parser("status")
    gallery_parser = command.add_parser("gallery")
    gallery_parser.add_argument("--page", type=int, default=0)
    gallery_parser.add_argument("--query", default="")
    gallery_parser.add_argument("--folder", default="")
    gallery_parser.add_argument("--shots-only", action="store_true")
    capture_parser = command.add_parser("capture")
    capture_parser.add_argument("mode", choices=["region", "focused", "all"])
    command.add_parser("preview-trash")
    trash_parser = command.add_parser("trash")
    trash_parser.add_argument("plan_id")
    trash_parser.add_argument("confirmation")
    selected_preview = command.add_parser("preview-selected")
    selected_preview.add_argument("path")
    selected_trash = command.add_parser("trash-selected")
    selected_trash.add_argument("plan_id")
    selected_trash.add_argument("confirmation")
    options = parser.parse_args(argv)

    if options.action == "status":
        result = status()
    elif options.action == "gallery":
        result = gallery(options.page, options.query,
                         options.folder, options.shots_only)
    elif options.action == "capture":
        result = capture(options.mode)
    elif options.action == "preview-trash":
        result = preview_desktop_trash()
    elif options.action == "preview-selected":
        result = preview_selected_trash(options.path)
    elif options.action == "trash-selected":
        result = trash_selected(options.plan_id, options.confirmation)
    else:
        result = trash_plan(options.plan_id, options.confirmation)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
