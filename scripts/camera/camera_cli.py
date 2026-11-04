#!/usr/bin/env python3
"""Camera M1: local-only Sway screenshots, image inventory and reversible cleanup.

No daemon, network, JSON database or automatic scans. The owning QML widget
executes one action on user input. Destructive cleanup is limited to matching
screenshot-like files immediately inside Desktop, only after preview and a
second explicit confirmation. "Trash" uses GIO; no unlink/rm fallback.
"""
import argparse
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
MAX_GALLERY = 150
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


def gallery():
    records = (direct_images(pictures(), "camera") +
               direct_images(screenshots_root(), "screenshots") +
               direct_images(desktop(), "desktop"))
    records.sort(key=lambda row: (-row["modifiedMs"], row["path"]))
    total = len(records)
    size = sum(r["bytes"] for r in records)
    # Exact paths and names are local view data, not network requests.
    for row in records:
        row.pop("signature")
    return {
        "ok": True, "kind": "gallery", "total": total,
        "totalBytes": size,
        "shown": min(total, MAX_GALLERY),
        "files": records[:MAX_GALLERY],
        "roots": [str(pictures()), str(screenshots_root()), str(desktop())],
        "limitNote": "First 150 newest files; no files were moved.",
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="action", required=True)
    command.add_parser("status")
    command.add_parser("gallery")
    capture_parser = command.add_parser("capture")
    capture_parser.add_argument("mode", choices=["region", "focused", "all"])
    command.add_parser("preview-trash")
    trash_parser = command.add_parser("trash")
    trash_parser.add_argument("plan_id")
    trash_parser.add_argument("confirmation")
    options = parser.parse_args(argv)

    if options.action == "status":
        result = status()
    elif options.action == "gallery":
        result = gallery()
    elif options.action == "capture":
        result = capture(options.mode)
    elif options.action == "preview-trash":
        result = preview_desktop_trash()
    else:
        result = trash_plan(options.plan_id, options.confirmation)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
