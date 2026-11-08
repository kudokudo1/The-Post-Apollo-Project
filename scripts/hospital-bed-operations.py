#!/usr/bin/env python3
"""Hospital Bed operations: bounded opt-in register/create/list.

The registry is discovery metadata only. It cannot grant Assignment authority
or waive PX's provider-launch validation. No branch is forcibly moved, reset,
stashed or cleaned. No network fetches are performed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


class Refused(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("GIT_COMMAND_UNAVAILABLE") from None
    if result.returncode:
        raise Refused("GIT_CHECK_REFUSED")
    return result.stdout.strip()


def repository_slug(text: str) -> str:
    text = str(text or "").strip()
    if text.startswith("git@github.com:"):
        candidate = text[len("git@github.com:"):]
    else:
        match = re.fullmatch(
            r"(?:https?|ssh)://(?:git@)?github\.com/([^?#]+)", text,
            flags=re.IGNORECASE,
        )
        candidate = match.group(1) if match else text
    candidate = candidate.removesuffix(".git").strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", candidate):
        return ""
    return candidate.lower()


def origin_slug(remote: str) -> str:
    """Only anchored GitHub transports establish Patient remote identity."""
    remote = str(remote or "").strip()
    if remote.startswith("git@github.com:"):
        return repository_slug(remote)
    if re.match(r"^(?:https?|ssh)://(?:git@)?github\.com/", remote, re.I):
        return repository_slug(remote)
    return ""


def verify_branch(branch: str) -> str:
    branch = str(branch or "").strip()
    if not branch or branch.startswith("-") or branch in ("HEAD", "DETACHED"):
        raise Refused("BRANCH_UNRESOLVED")
    try:
        answer = subprocess.run(
            ["git", "check-ref-format", "--branch", branch],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("BRANCH_UNRESOLVED") from None
    if answer.returncode:
        raise Refused("BRANCH_UNRESOLVED")
    return branch


def inspect(path_text: str, repository: str, branch: str = "") -> dict:
    expected = repository_slug(repository)
    if not expected:
        raise Refused("PATIENT_REPOSITORY_UNVERIFIED")
    if branch:
        branch = verify_branch(branch)
    if not str(path_text or "").strip():
        raise Refused("BED_PATH_MISSING")
    raw_path = Path(path_text).expanduser()
    if not raw_path.is_absolute():
        raise Refused("BED_PATH_NOT_ABSOLUTE")
    bed = raw_path.resolve()
    if not bed.is_dir():
        raise Refused("BED_MISSING")
    try:
        root = Path(git(bed, "rev-parse", "--show-toplevel")).resolve()
        current_branch = git(bed, "symbolic-ref", "--quiet", "--short", "HEAD")
        origin = git(bed, "remote", "get-url", "origin")
        sha = git(bed, "rev-parse", "HEAD")
        common_raw = git(bed, "rev-parse", "--git-common-dir")
        common = (bed / common_raw).resolve()
        dirty = bool(git(bed, "status", "--porcelain"))
    except Refused:
        raise Refused("BED_GIT_UNRESOLVED") from None
    if root != bed:
        raise Refused("BED_NOT_REPOSITORY_ROOT")
    actual = origin_slug(origin)
    if not actual or actual != expected:
        raise Refused("PATIENT_REPOSITORY_MISMATCH")
    if branch and current_branch != branch:
        raise Refused("BED_BRANCH_MISMATCH")
    return {
        "path": str(bed),
        "label": bed.name,
        "origin": origin,
        "repository": actual,
        "branch": current_branch,
        "head": sha,
        "commonDir": str(common),
        "worktree": "DIRTY" if dirty else "CLEAN",
        "dirty": dirty,
        "isLive": bed == (Path.home() / ".config/quickshell").resolve(),
        "verification": "CANDIDATE_UNVERIFIED",
    }


def registry_path(value: str) -> Path:
    default = Path(os.environ.get(
        "XDG_STATE_HOME", str(Path.home() / ".local/state")
    )) / "post-apollo/hospital/registered-beds.json"
    return Path(value).expanduser().resolve() if value else default


def read_registry(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("not list")
        return [r for r in data if isinstance(r, dict)]
    except (ValueError, OSError):
        raise Refused("BED_REGISTRY_UNREADABLE") from None


def remember(candidate: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with open(lock_path, "a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = read_registry(path)
        entry = {
            "path": candidate["path"],
            "repository": candidate["repository"],
        }
        rows = [r for r in rows if r.get("path") != entry["path"]]
        rows.append(entry)
        fd, temporary = tempfile.mkstemp(
            prefix=".registered-beds-", dir=path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                os.fchmod(handle.fileno(), 0o600)
                json.dump(rows, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def list_registered(path: Path, repository: str) -> dict:
    wanted = repository_slug(repository) if repository else ""
    if repository and not wanted:
        raise Refused("PATIENT_REPOSITORY_UNVERIFIED")
    beds: list[dict] = []
    stale: list[dict] = []
    for record in read_registry(path):
        path_text = str(record.get("path") or "")
        repo = str(record.get("repository") or "")
        if wanted and repo != wanted:
            continue
        try:
            beds.append(inspect(path_text, repo))
        except Refused as error:
            stale.append({"path": path_text, "reason": error.code})
    return {"ok": True, "beds": beds, "stale": stale}


def create_worktree(
    seed_path: str, repository: str, branch: str,
    bed_root: str, name: str,
) -> dict:
    branch = verify_branch(branch)
    # Seed is allowed on another branch; its Patient identity is not.
    seed = inspect(seed_path, repository)
    seed_root = Path(seed["path"])
    if bed_root and not Path(bed_root).expanduser().is_absolute():
        raise Refused("BED_ROOT_NOT_ABSOLUTE")
    root = Path(bed_root).expanduser().resolve() if bed_root else (
        Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        / "post-apollo/hospital/beds"
    ).resolve()
    if name:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,72}", name) or name in (".", ".."):
            raise Refused("BED_NAME_INVALID")
        directory = name
    else:
        digest = hashlib.sha256((seed["repository"] + "|" + branch).encode()).hexdigest()[:8]
        safe = re.sub(r"[^A-Za-z0-9_.-]", "-", branch)[:48]
        directory = f"{safe}-{digest}"

    # Worktree directory is always a single child of a fixed managed root.
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = root / directory
    if target.exists() or target.is_symlink():
        raise Refused("BED_DESTINATION_EXISTS")
    # Human-readable early refusal; Git itself still guards against races.
    worktree_index = git(seed_root, "worktree", "list", "--porcelain")
    if ("branch refs/heads/" + branch) in worktree_index.splitlines():
        raise Refused("BRANCH_ALREADY_OCCUPIED")
    local_ref = "refs/heads/" + branch
    remote_ref = "refs/remotes/origin/" + branch
    try:
        git(seed_root, "show-ref", "--verify", local_ref)
        mode = "local"
    except Refused:
        try:
            git(seed_root, "show-ref", "--verify", remote_ref)
            mode = "remote"
        except Refused:
            raise Refused("BRANCH_NOT_AVAILABLE_LOCALLY") from None

    command = ["git", "-C", str(seed_root), "worktree", "add"]
    if mode == "remote":
        command += ["-b", branch]
    # Always pass the exact requested branch/ref. Omitting this operand
    # makes Git manufacture a branch from the target directory name.
    command += ["--", str(target), branch if mode == "local" else remote_ref]
    try:
        result = subprocess.run(
            command, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=90, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("WORKTREE_COMMAND_UNAVAILABLE_OR_TIMED_OUT") from None
    if result.returncode:
        raise Refused("WORKTREE_CREATION_REFUSED")
    candidate = inspect(str(target), repository, branch)
    if candidate["commonDir"] != seed["commonDir"]:
        raise Refused("WORKTREE_FAMILY_MISMATCH")
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser(description="Conservative Hospital Bed recovery operations")
    ap.add_argument("--registry", default="")
    sp = ap.add_subparsers(dest="command", required=True)
    reg = sp.add_parser("register")
    reg.add_argument("--path", required=True)
    reg.add_argument("--repository", required=True)
    reg.add_argument("--branch", required=True)
    listing = sp.add_parser("list")
    listing.add_argument("--repository", default="")
    create = sp.add_parser("create")
    create.add_argument("--seed-path", required=True)
    create.add_argument("--repository", required=True)
    create.add_argument("--branch", required=True)
    create.add_argument("--bed-root", default="")
    create.add_argument("--name", default="")
    args = ap.parse_args()
    try:
        where = registry_path(args.registry)
        if args.command == "register":
            candidate = inspect(args.path, args.repository, args.branch)
            remember(candidate, where)
            answer = {"ok": True, "bed": candidate}
        elif args.command == "create":
            candidate = create_worktree(
                args.seed_path, args.repository, args.branch,
                args.bed_root, args.name
            )
            remember(candidate, where)
            answer = {"ok": True, "bed": candidate}
        else:
            answer = list_registered(where, args.repository)
        print(json.dumps(answer, sort_keys=True))
        return 0
    except Refused as exc:
        print(json.dumps({"ok": False, "code": exc.code}))
        return 1
    except (OSError, PermissionError):
        print(json.dumps({"ok": False, "code": "BED_OPERATION_IO_REFUSED"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
