#!/usr/bin/env python3
"""Bounded, local WAV tone import for the shared Post-Apollo Sound Library.

Invoked on explicit user action by Quickshell. Only the host copies/deletes
files. Never executes media, shell commands, network calls or an input path.
The manifest and audio live below Quickshell.dataDir/sounds-library-v1.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from urllib.parse import urlsplit, unquote
import wave

VERSION = 1
MAX_TONES = 32
MAX_BYTES = 8 * 1024 * 1024
MAX_SECONDS = 30
NAME_MAX = 40
ID = re.compile(r"^user-[0-9a-f]{64}$")
ALLOWED_RATES = (24000, 48000)


class Refused(Exception):
    pass


def name_ok(name):
    return isinstance(name, str) and 0 < len(name.strip()) <= NAME_MAX and not any(
        ord(c) < 32 or ord(c) == 127 for c in name
    )


def source_path(url):
    parts = urlsplit(url)
    if parts.scheme != "file" or parts.netloc not in ("", "localhost") or parts.query or parts.fragment:
        raise Refused("LOCAL_FILE_REQUIRED")
    path = Path(unquote(parts.path))
    if not path.is_absolute() or path.suffix.lower() != ".wav":
        raise Refused("WAV_FILE_REQUIRED")
    return path


def root_dir(data_dir, create=False):
    root = Path(data_dir)
    if not root.is_absolute():
        raise Refused("INVALID_DATA_DIR")
    dest = root / "sounds-library-v1"
    if dest.is_symlink():
        raise Refused("UNSAFE_LIBRARY_DIR")
    if create:
        dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    if dest.exists() and (not dest.is_dir() or dest.is_symlink()):
        raise Refused("INVALID_LIBRARY_DIR")
    return dest


def manifest_path(root):
    return root / "index-v1.json"


def check_regular(path):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES or st.st_size == 0:
        raise Refused("INVALID_WAV_FILE")


def load(root):
    index = manifest_path(root)
    if not index.exists():
        return []
    if index.is_symlink():
        raise Refused("UNSAFE_LIBRARY_INDEX")
    if index.stat().st_size > 32768:
        raise Refused("INDEX_TOO_LARGE")
    try:
        obj = json.loads(index.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, ValueError) as e:
        raise Refused("INVALID_LIBRARY_INDEX") from e
    if not isinstance(obj, dict) or obj.get("version") != VERSION or not isinstance(obj.get("tones"), list):
        raise Refused("INVALID_LIBRARY_INDEX")
    tones = obj["tones"]
    if len(tones) > MAX_TONES:
        raise Refused("TOO_MANY_TONES")
    seen = set()
    for item in tones:
        if not isinstance(item, dict) or set(item) != {"id", "name", "seconds"}:
            raise Refused("INVALID_TONE_RECORD")
        tone_id = item["id"]
        if not isinstance(tone_id, str) or not ID.fullmatch(tone_id) or tone_id in seen or not name_ok(item["name"]):
            raise Refused("INVALID_TONE_RECORD")
        if not isinstance(item["seconds"], (int, float)) or isinstance(item["seconds"], bool) or not 0 < item["seconds"] <= MAX_SECONDS:
            raise Refused("INVALID_TONE_RECORD")
        seen.add(tone_id)
        wav = root / (tone_id + ".wav")
        try:
            check_regular(wav)
        except (FileNotFoundError, OSError) as e:
            raise Refused("MISSING_LIBRARY_AUDIO") from e
    return tones


def write_index(root, tones):
    dest = manifest_path(root)
    fd, temp = tempfile.mkstemp(prefix=".sound-index-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump({"version": VERSION, "tones": tones}, out, ensure_ascii=False, separators=(",", ":"))
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, dest)
        dirfd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def inspected_wav(source):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(source, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size < 100 or st.st_size > MAX_BYTES:
            raise Refused("INVALID_WAV_SIZE")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            with wave.open(handle, "rb") as wav:
                channels, width, rate = wav.getnchannels(), wav.getsampwidth(), wav.getframerate()
                frames = wav.getnframes()
                if wav.getcomptype() != "NONE" or channels not in (1, 2) or width != 2 or rate not in ALLOWED_RATES:
                    raise Refused("UNSUPPORTED_WAV_PCM")
                seconds = frames / rate
                if not (0.2 <= seconds <= MAX_SECONDS):
                    raise Refused("WAV_DURATION_OUT_OF_RANGE")
            handle.seek(0)
            h = hashlib.sha256()
            while True:
                part = handle.read(64 * 1024)
                if not part:
                    break
                h.update(part)
        return fd, h.hexdigest(), round(seconds, 3)
    except BaseException:
        os.close(fd)
        raise


def import_wav(root, args):
    source = source_path(args.source)
    if not name_ok(args.name):
        raise Refused("INVALID_TONE_NAME")
    fd, digest, seconds = inspected_wav(source)
    try:
        existing = load(root)
        tone_id = "user-" + digest
        if any(item["id"] == tone_id for item in existing):
            return {"ok": True, "status": "already-imported", "tones": with_urls(root, existing), "selectedId": tone_id}
        if len(existing) >= MAX_TONES:
            raise Refused("LIBRARY_FULL")
        root_dir(args.data_dir, create=True)
        target = root / (tone_id + ".wav")
        if target.exists() or target.is_symlink():
            raise Refused("TARGET_COLLISION")
        temporary_fd, temporary = tempfile.mkstemp(prefix=".tone-", dir=root)
        try:
            os.fchmod(temporary_fd, 0o600)
            os.lseek(fd, 0, os.SEEK_SET)
            with os.fdopen(temporary_fd, "wb") as out:
                while True:
                    block = os.read(fd, 64 * 1024)
                    if not block:
                        break
                    out.write(block)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
            # Immutable content ID. The original may be removed afterwards.
            new_tones = existing + [{"id": tone_id, "name": args.name.strip(), "seconds": seconds}]
            write_index(root, new_tones)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return {"ok": True, "status": "imported", "tones": with_urls(root, new_tones), "selectedId": tone_id}
    finally:
        os.close(fd)


def with_urls(root, tones):
    return [{**item, "url": (root / (item["id"] + ".wav")).as_uri()} for item in tones]


def rename(root, args):
    tones = load(root)
    if not ID.fullmatch(args.tone_id or "") or not name_ok(args.name):
        raise Refused("INVALID_TONE")
    if not any(x["id"] == args.tone_id for x in tones):
        raise Refused("TONE_NOT_FOUND")
    for item in tones:
        if item["id"] == args.tone_id:
            item["name"] = args.name.strip()
    write_index(root, tones)
    return {"ok": True, "status": "renamed", "tones": with_urls(root, tones)}


def in_use(data_dir, tone_id):
    path = Path(data_dir) / "time-alarms-v2.json"
    # On unreadable alarm records, deletion fails closed.
    if path.is_symlink():
        raise Refused("UNSAFE_ALARM_REFERENCE")
    if not path.exists():
        return False
    if path.stat().st_size > 2 * 1024 * 1024:
        raise Refused("ALARM_REFERENCE_UNREADABLE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        alarms = data["alarms"]
        if not isinstance(alarms, list):
            raise ValueError()
        return any(isinstance(a, dict) and a.get("soundId") == tone_id for a in alarms)
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise Refused("ALARM_REFERENCE_UNREADABLE") from e


def delete(root, args):
    tones = load(root)
    tone_id = args.tone_id or ""
    if not ID.fullmatch(tone_id) or not any(x["id"] == tone_id for x in tones):
        raise Refused("TONE_NOT_FOUND")
    if in_use(args.data_dir, tone_id):
        raise Refused("TONE_ASSIGNED_TO_ALARM")
    # Update the index first. A failed unlink leaves an unreferenced file,
    # rather than a saved alarm pointing at a now-missing source.
    remaining = [x for x in tones if x["id"] != tone_id]
    write_index(root, remaining)
    (root / (tone_id + ".wav")).unlink()
    return {"ok": True, "status": "deleted", "tones": with_urls(root, remaining)}


def run(args):
    root = root_dir(args.data_dir, create=args.operation == "import")
    if args.operation == "list":
        return {"ok": True, "status": "ready", "tones": with_urls(root, load(root))}
    if args.operation == "import":
        return import_wav(root, args)
    if args.operation == "rename":
        return rename(root, args)
    if args.operation == "delete":
        return delete(root, args)
    raise Refused("INVALID_OPERATION")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--operation", choices=("list", "import", "rename", "delete"), required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--tone-id", default="")
    args = parser.parse_args()
    try:
        result = run(args)
    except (Refused, OSError, ValueError, wave.Error, EOFError) as exc:
        result = {"ok": False, "error": str(exc) if isinstance(exc, Refused) else "AUDIO_IMPORT_FAILED"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
