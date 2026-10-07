#!/usr/bin/env python3
"""Contracts + runtime smoke tests for untracked whole-file transfer."""

from pathlib import Path
import hashlib
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

SERVICE = "services/git/GitChangeTransferService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"
TRANSFER_VIEW = "widgets/GitChangeTransferView.qml"
CHANGES_VIEW = "widgets/GitChangesView.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("function previewUntracked(destinationPath, files, mode)", "service must expose untracked preview"),
    ('pendingPreviewLayer = "untracked"', "preview must retain untracked layer identity"),
    ('return "CHANGES/TRANSFER_UNTRACKED";', "journal must use a distinct untracked kind"),
    ('? "TRANSFER_UNTRACKED"', "journal metadata must name untracked transfer"),
    ("UNTRACKED TRANSFER SUPPORTS REGULAR FILES ONLY", "first slice must refuse directories/special files"),
    ("DESTINATION PATH ALREADY EXISTS", "preview must refuse destination collisions"),
    ("UNTRACKED PATCH GENERATION FAILED", "preview must build an exact creation patch"),
    ("SOURCE PATH BECAME TRACKED", "execution must revalidate source identity"),
    ("DESTINATION PATH APPEARED SINCE PREVIEW", "execution must revalidate destination absence"),
    ("UNTRACKED PATCH REGENERATION FAILED", "execution must regenerate the exact patch"),
):
    require(SERVICE, needle, message)

for needle, message in (
    ('"CHANGES/TRANSFER_UNTRACKED"', "recovery must recognize untracked transfer records"),
    ('layer !== "untracked"', "recovery must accept the untracked layer"),
    ('? " UNTRACKED "', "recovery preview must identify untracked Undo"),
    ("UNDO_TRANSFER_CONTENT", "untracked transfer must reuse exact content Undo"),
):
    require(RECOVERY, needle, message)

for needle, message in (
    ("property bool untrackedSource: false", "Transfer view must know the source layer"),
    ("transferService.previewUntracked(", "untracked UI preview must call the new backend"),
    ("UNTRACKED REGULAR FILE", "Transfer UI must disclose strict untracked semantics"),
    ("onUntrackedSourceChanged: invalidatePreview()", "layer changes must invalidate stale previews"),
):
    require(TRANSFER_VIEW, needle, message)

for needle, message in (
    ("Boolean(row.untracked)", "CHANGES must allow selected untracked files into whole-file Transfer"),
    ("wholeFileCandidate", "whole-file eligibility must distinguish tracked and untracked candidates"),
    ("untrackedSource:", "CHANGES must pass selected file layer into the Transfer view"),
):
    require(CHANGES_VIEW, needle, message)


def run(args, cwd=None, input_bytes=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, check=True, input_bytes=None):
    return run(
        ["git", "-C", str(repo), *args],
        check=check,
        input_bytes=input_bytes,
    )


def make_pair(root: Path):
    source = root / "source"
    destination = root / "destination"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Post Apollo Test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "base.txt").write_text("base\n", encoding="utf-8")
    git(source, "add", "base.txt")
    git(source, "commit", "-qm", "base")
    git(source, "branch", "destination")
    git(source, "worktree", "add", "-q", str(destination), "destination")
    return source, destination


def creation_patch(source: Path, path: str) -> bytes:
    proc = git(
        source,
        "diff",
        "--no-index",
        "--binary",
        "--full-index",
        "--",
        "/dev/null",
        path,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr.decode()
    assert proc.stdout
    return proc.stdout


def apply(
    repo: Path,
    patch: bytes,
    reverse=False,
    check_only=False,
    check=True,
):
    args = ["apply"]
    if reverse:
        args.append("-R")
    if check_only:
        args.append("--check")
    args.extend(["--binary", "-"])
    return git(repo, *args, input_bytes=patch, check=check)


def smoke_copy_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-untracked-copy-") as tmp:
        source, destination = make_pair(Path(tmp))
        source_head = git(source, "rev-parse", "HEAD").stdout.decode().strip()
        destination_head = git(destination, "rev-parse", "HEAD").stdout.decode().strip()

        payload = b"untracked copy\n\x00binary-safe\n"
        (source / "new.bin").write_bytes(payload)
        patch = creation_patch(source, "new.bin")
        fingerprint = hashlib.sha256(patch).hexdigest()
        assert fingerprint

        assert git(source, "status", "--porcelain=v1", "--", "new.bin").stdout.startswith(b"?? ")
        assert not (destination / "new.bin").exists()

        apply(destination, patch, check_only=True)
        apply(destination, patch)

        assert git(source, "rev-parse", "HEAD").stdout.decode().strip() == source_head
        assert git(destination, "rev-parse", "HEAD").stdout.decode().strip() == destination_head
        assert (source / "new.bin").read_bytes() == payload
        assert (destination / "new.bin").read_bytes() == payload

        # COPY Undo removes only the exact destination creation.
        apply(destination, patch, reverse=True, check_only=True)
        apply(destination, patch, reverse=True)
        assert (source / "new.bin").read_bytes() == payload
        assert not (destination / "new.bin").exists()


def smoke_move_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-untracked-move-") as tmp:
        source, destination = make_pair(Path(tmp))
        payload = b"untracked move\nsecond line\n"
        (source / "move.txt").write_bytes(payload)
        patch = creation_patch(source, "move.txt")

        # MOVE: create destination first, then reverse exact creation at source.
        apply(destination, patch, check_only=True)
        apply(destination, patch)
        apply(source, patch, reverse=True, check_only=True)
        apply(source, patch, reverse=True)

        assert not (source / "move.txt").exists()
        assert (destination / "move.txt").read_bytes() == payload

        # MOVE Undo restores source first, then removes destination.
        apply(source, patch, check_only=True)
        apply(destination, patch, reverse=True, check_only=True)
        apply(source, patch)
        apply(destination, patch, reverse=True)

        assert (source / "move.txt").read_bytes() == payload
        assert not (destination / "move.txt").exists()


def smoke_collision_refusal():
    with tempfile.TemporaryDirectory(prefix="pa-untracked-collision-") as tmp:
        source, destination = make_pair(Path(tmp))
        (source / "same.txt").write_text("source\n", encoding="utf-8")
        (destination / "same.txt").write_text("destination\n", encoding="utf-8")
        patch = creation_patch(source, "same.txt")

        result = apply(destination, patch, check=False)
        assert result.returncode != 0
        assert (destination / "same.txt").read_text(encoding="utf-8") == "destination\n"


smoke_copy_and_undo()
smoke_move_and_undo()
smoke_collision_refusal()

print("Git untracked transfer contracts: PASS")
