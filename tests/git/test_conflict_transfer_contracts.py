#!/usr/bin/env python3
"""Contracts + runtime smoke test for copy-only conflicted RESULT Transfer."""

from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TRANSFER = "services/git/GitChangeTransferService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"
VIEW = "widgets/GitChangeTransferView.qml"
CHANGES = "widgets/GitChangesView.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("function previewConflictResult(destinationPath, file, mode)", "backend must expose conflict RESULT preview"),
    ('return "CHANGES/TRANSFER_CONFLICT_RESULT";', "conflict RESULT copy needs an explicit journal kind"),
    ('pendingPreviewLayer = "conflict-result"', "preview must retain conflict-result layer identity"),
    ('? "TRANSFER_CONFLICT_RESULT"', "journal metadata must identify conflict RESULT copy"),
    ("CONFLICT RESULT TRANSFER IS COPY-ONLY", "MOVE must be deliberately refused"),
    ("SOURCE CONFLICT STAGES CHANGED SINCE PREVIEW", "execution must reverify exact unmerged stages"),
    ("SOURCE CONFLICT OPERATION CHANGED SINCE PREVIEW", "execution must reverify the enclosing operation"),
    ("DESTINATION DOES NOT TRACK CONFLICT PATH", "first slice must refuse destination topology changes"),
    ("COPIED CONFLICT RESULT // SOURCE OPERATION + STAGES LEFT UNTOUCHED", "execution must state source conflict preservation"),
):
    require(TRANSFER, needle, message)

for needle, message in (
    ('"CHANGES/TRANSFER_CONFLICT_RESULT"', "recovery must recognize conflict RESULT records"),
    ('layer !== "conflict-result"', "recovery plan must accept the conflict-result layer"),
    ('layer === "conflict-result"', "Undo execution must special-case conflict-result semantics"),
    ("DESTINATION NO LONGER CONTAINS EXACT CONFLICT RESULT COPY", "Undo must verify the exact destination result patch"),
    ("UNDID CONFLICT RESULT COPY // SOURCE CONFLICT LEFT UNTOUCHED", "Undo must preserve source conflict state"),
):
    require(RECOVERY, needle, message)

for needle, message in (
    ("transferService.previewConflictResult(", "view must call the guarded conflict preview"),
    ("TRANSFER // CONFLICT RESULT COPY", "view must label conflict RESULT semantics"),
    ("!root.conflictResultLayer", "MOVE control must be disabled for conflict RESULT"),
):
    require(VIEW, needle, message)

for needle, message in (
    ("function conflictFileTransferEligible()", "CHANGES must expose conflicted rows to Transfer"),
    ('? "conflict-result"', "CHANGES must select the conflict-result content layer"),
):
    require(CHANGES, needle, message)


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


def status(repo: Path) -> str:
    return git(repo, "status", "--porcelain=v1").stdout.decode()


def stage_rows(repo: Path) -> bytes:
    return git(repo, "ls-files", "-u", "--", "sample.txt").stdout


def make_conflict_pair(root: Path):
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
    base = git(source, "rev-parse", "HEAD").stdout.decode().strip()

    git(source, "branch", "destination", base)
    git(source, "checkout", "-qb", "theirs", base)
    (source / "sample.txt").write_text(
        "alpha\nTHEIRS\ngamma\n",
        encoding="utf-8",
    )
    git(source, "commit", "-qam", "theirs")
    theirs = git(source, "rev-parse", "HEAD").stdout.decode().strip()

    git(source, "checkout", "-q", "master")
    (source / "sample.txt").write_text(
        "alpha\nOURS\ngamma\n",
        encoding="utf-8",
    )
    git(source, "commit", "-qam", "ours")
    git(source, "worktree", "add", "-q", str(destination), "destination")

    merge = git(source, "merge", "--no-edit", theirs, check=False)
    assert merge.returncode != 0
    assert (source / ".git").exists() or git(source, "rev-parse", "--git-dir").returncode == 0
    assert stage_rows(source)
    return source, destination


def conflict_fingerprint(repo: Path) -> str:
    rows = stage_rows(repo)
    assert rows
    return hashlib.sha256(rows).hexdigest()


def create_destination_patch(source: Path, destination: Path, root: Path) -> bytes:
    destination_head = git(destination, "rev-parse", "HEAD").stdout.decode().strip()
    rehearsal = root / "rehearsal"
    git(source, "worktree", "add", "--detach", "-q", str(rehearsal), destination_head)
    try:
        assert git(rehearsal, "ls-files", "--error-unmatch", "--", "sample.txt", check=False).returncode == 0
        shutil.copyfile(source / "sample.txt", rehearsal / "sample.txt")
        patch = git(
            rehearsal,
            "diff",
            "--binary",
            "--full-index",
            "--",
            "sample.txt",
        ).stdout
        assert patch
        return patch
    finally:
        git(source, "worktree", "remove", "--force", str(rehearsal), check=False)


def smoke_conflict_result_copy_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-conflict-result-") as tmp:
        root = Path(tmp)
        source, destination = make_conflict_pair(root)

        original_stages = stage_rows(source)
        original_fingerprint = conflict_fingerprint(source)
        gitdir = Path(git(source, "rev-parse", "--git-dir").stdout.decode().strip())
        if not gitdir.is_absolute():
            gitdir = source / gitdir
        assert (gitdir / "MERGE_HEAD").exists()

        # Simulate manual conflict-editor work without staging or resolving.
        result_text = "alpha\nMANUAL RESULT DRAFT\ngamma\n"
        (source / "sample.txt").write_text(result_text, encoding="utf-8")
        assert stage_rows(source) == original_stages
        assert conflict_fingerprint(source) == original_fingerprint

        patch = create_destination_patch(source, destination, root)
        assert git(destination, "apply", "--check", "--binary", "-", input_bytes=patch, check=False).returncode == 0
        assert git(destination, "apply", "--binary", "-", input_bytes=patch, check=False).returncode == 0

        # Destination receives an ordinary worktree change, not fake unmerged stages.
        assert (destination / "sample.txt").read_text(encoding="utf-8") == result_text
        assert git(destination, "ls-files", "-u").stdout == b""
        assert git(destination, "diff", "--cached", "--quiet", check=False).returncode == 0
        assert git(destination, "diff", "--quiet", check=False).returncode == 1

        # Source operation and all unmerged stage identities remain untouched.
        assert (gitdir / "MERGE_HEAD").exists()
        assert stage_rows(source) == original_stages
        assert conflict_fingerprint(source) == original_fingerprint

        # Undo removes only the destination copy.
        assert git(destination, "apply", "-R", "--check", "--binary", "-", input_bytes=patch, check=False).returncode == 0
        assert git(destination, "apply", "-R", "--binary", "-", input_bytes=patch, check=False).returncode == 0
        assert status(destination) == ""
        assert (gitdir / "MERGE_HEAD").exists()
        assert stage_rows(source) == original_stages


smoke_conflict_result_copy_and_undo()

print("Git conflict RESULT Transfer contracts: PASS")
