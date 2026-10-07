#!/usr/bin/env python3
"""Contracts + runtime smoke tests for staged whole-file transfer."""

from pathlib import Path
import hashlib
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TRANSFER = "services/git/GitChangeTransferService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ('function previewStaged(destinationPath, files, mode)', "transfer backend must expose staged whole-file preview"),
    ('pendingPreviewLayer: "worktree"', "transfer preview must track its content layer"),
    ('previewLayer: "worktree"', "accepted transfer evidence must retain its content layer"),
    ('return "CHANGES/TRANSFER_STAGED";', "staged transfer must have an explicit journal kind"),
    ('layer: String(previewLayer || "worktree")', "journal metadata must record staged/worktree semantics"),
    ('git -C "$source" diff --cached --binary --full-index', "staged preview must be generated from HEAD to index"),
    ('function previewPartial(destinationPath, files, mode)', "partially staged files must route to the dedicated two-layer backend"),
    ('apply --check --index --binary', "staged preview must prove index-preserving applicability"),
    ('apply -R --check --index --binary', "staged MOVE must prove source index removal"),
    ('MOVED STAGED %s FILE(S)', "staged MOVE execution must be explicit"),
    ('COPIED STAGED %s FILE(S)', "staged COPY execution must be explicit"),
):
    require(TRANSFER, needle, message)

for needle, message in (
    ('"CHANGES/TRANSFER_STAGED"', "recovery must recognize staged transfer records"),
    ('String(metadata.layer || "worktree")', "legacy transfers must default to worktree layer"),
    ('layer: layer', "recovery plan must retain transfer layer"),
    ('DESTINATION NO LONGER CONTAINS EXACT STAGED TRANSFER', "staged Undo must verify destination index state"),
    ('SOURCE CAN NO LONGER RECEIVE STAGED TRANSFERRED CONTENT', "staged MOVE Undo must preflight source index restoration"),
    ('UNDID STAGED MOVE TRANSFER', "staged MOVE Undo must restore source staging"),
    ('UNDID STAGED COPY TRANSFER', "staged COPY Undo must remove destination staging"),
):
    require(RECOVERY, needle, message)


def run(args, cwd=None, input_bytes=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, input_bytes=None, check=True):
    return run(
        ["git", "-C", str(repo), *args],
        input_bytes=input_bytes,
        check=check,
    )


def status(repo: Path):
    return git(repo, "status", "--porcelain=v1").stdout.decode()


def staged_patch(repo: Path):
    return git(
        repo,
        "diff",
        "--cached",
        "--binary",
        "--full-index",
        "--",
        "sample.txt",
    ).stdout


def make_pair(root: Path):
    source = root / "source"
    destination = root / "destination"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Post Apollo Test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "sample.txt").write_text(
        "alpha\nbeta\ngamma\n",
        encoding="utf-8",
    )
    git(source, "add", "sample.txt")
    git(source, "commit", "-qm", "base")
    git(source, "branch", "destination")
    git(source, "worktree", "add", "-q", str(destination), "destination")
    return source, destination


def make_staged_change(source: Path):
    (source / "sample.txt").write_text(
        "alpha\nBETA STAGED\ngamma\n",
        encoding="utf-8",
    )
    git(source, "add", "sample.txt")
    assert git(source, "diff", "--quiet", "--", "sample.txt", check=False).returncode == 0
    patch = staged_patch(source)
    assert patch
    return patch


def apply_index(repo: Path, patch: bytes, reverse=False, check_only=False):
    args = ["apply"]
    if reverse:
        args.append("-R")
    if check_only:
        args.append("--check")
    args.extend(["--index", "--binary", "--whitespace=nowarn", "-"])
    return git(repo, *args, input_bytes=patch, check=False)


def smoke_copy_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-staged-copy-") as tmp:
        source, destination = make_pair(Path(tmp))
        patch = make_staged_change(source)
        fingerprint = hashlib.sha256(patch).hexdigest()

        assert apply_index(destination, patch, check_only=True).returncode == 0
        assert apply_index(destination, patch).returncode == 0
        assert staged_patch(source) == patch
        assert staged_patch(destination) == patch
        assert hashlib.sha256(staged_patch(destination)).hexdigest() == fingerprint

        # COPY Undo removes the staged delta from destination only.
        assert apply_index(destination, patch, reverse=True, check_only=True).returncode == 0
        assert apply_index(destination, patch, reverse=True).returncode == 0
        assert staged_patch(source) == patch
        assert staged_patch(destination) == b""
        assert status(destination) == ""


def smoke_move_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-staged-move-") as tmp:
        source, destination = make_pair(Path(tmp))
        patch = make_staged_change(source)

        # MOVE: stage at destination, remove exact staged delta from source.
        assert apply_index(destination, patch).returncode == 0
        assert apply_index(source, patch, reverse=True, check_only=True).returncode == 0
        assert apply_index(source, patch, reverse=True).returncode == 0
        assert status(source) == ""
        assert staged_patch(destination) == patch

        # MOVE Undo: restore source staging first, then remove destination staging.
        assert apply_index(source, patch, check_only=True).returncode == 0
        assert apply_index(destination, patch, reverse=True, check_only=True).returncode == 0
        assert apply_index(source, patch).returncode == 0
        assert apply_index(destination, patch, reverse=True).returncode == 0

        assert staged_patch(source) == patch
        assert git(source, "diff", "--quiet", "--", "sample.txt", check=False).returncode == 0
        assert status(destination) == ""


def smoke_partial_staging_shape():
    with tempfile.TemporaryDirectory(prefix="pa-staged-partial-") as tmp:
        source, _destination = make_pair(Path(tmp))
        _patch = make_staged_change(source)

        # Add a worktree-only remainder after staging.
        (source / "sample.txt").write_text(
            "alpha\nBETA STAGED\ngamma unstaged\n",
            encoding="utf-8",
        )
        assert git(source, "diff", "--cached", "--quiet", "--", "sample.txt", check=False).returncode == 1
        assert git(source, "diff", "--quiet", "--", "sample.txt", check=False).returncode == 1


smoke_copy_and_undo()
smoke_move_and_undo()
smoke_partial_staging_shape()

print("Git staged whole-file transfer contracts: PASS")
