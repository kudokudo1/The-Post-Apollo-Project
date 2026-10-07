#!/usr/bin/env python3
"""Contracts + runtime smoke tests for partially staged whole-file Transfer."""

from pathlib import Path
import base64
import hashlib
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
    ("function previewPartial(destinationPath, files, mode)", "backend must expose partial preview"),
    ('return "CHANGES/TRANSFER_PARTIAL";', "partial transfer needs a distinct journal kind"),
    ('pendingPreviewLayer = "partial"', "preview must retain partial layer identity"),
    ('"TRANSFER_PARTIAL"', "journal metadata must identify partial transfer"),
    ("STAGED64", "durable bundle must carry the staged patch marker"),
    ("WORKTREE64", "durable bundle must carry the worktree patch marker"),
    ("DESTINATION REHEARSAL WORKTREE CREATE FAILED", "preview must rehearse the two-layer landing"),
    ("MOVED PARTIALLY STAGED %s FILE(S)", "MOVE must preserve explicit partial semantics"),
    ("COPIED PARTIALLY STAGED %s FILE(S)", "COPY must preserve explicit partial semantics"),
    ("'  partial_apply() {',", "partial apply shell function must remain a valid QML array entry"),
    ("'  partial_remove() {',", "partial remove shell function must remain a valid QML array entry"),
):
    require(TRANSFER, needle, message)

for needle, message in (
    ("'      partial_apply() {',", "partial Undo shell helper must remain a valid QML command-array string"),
    ("'      partial_remove() {',", "partial Undo removal helper must remain a valid QML command-array string"),
):
    require(RECOVERY, needle, message)


for needle, message in (
    ('"CHANGES/TRANSFER_PARTIAL"', "Undo planner must recognize partial transfer"),
    ('layer !== "partial"', "Undo planner must accept the partial layer"),
    ('? " PARTIALLY STAGED "', "Undo summary must identify partial content"),
    ("PARTIAL RECOVERY BUNDLE IS INCOMPLETE", "Undo must validate the two-patch bundle"),
    ("UNDID PARTIALLY STAGED MOVE TRANSFER", "MOVE Undo must restore both source layers"),
    ("UNDID PARTIALLY STAGED COPY TRANSFER", "COPY Undo must remove both destination layers"),
):
    require(RECOVERY, needle, message)

for needle, message in (
    ("transferService.previewPartial(", "UI must route partial files to partial preview"),
    ("TRANSFER // PARTIALLY STAGED WHOLE FILE", "UI must disclose partial layer"),
):
    require(VIEW, needle, message)

for needle, message in (
    ("function partialFileTransferEligible()", "CHANGES must detect partially staged files"),
    ('? "partial"', "CHANGES must select the partial transfer layer"),
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


def staged_patch(repo: Path) -> bytes:
    return git(
        repo,
        "diff",
        "--cached",
        "--binary",
        "--full-index",
        "--",
        "sample.txt",
    ).stdout


def worktree_patch(repo: Path) -> bytes:
    return git(
        repo,
        "diff",
        "--binary",
        "--full-index",
        "--",
        "sample.txt",
    ).stdout


def bundle(staged: bytes, worktree: bytes) -> bytes:
    return (
        b"STAGED64\t"
        + base64.b64encode(staged)
        + b"\nWORKTREE64\t"
        + base64.b64encode(worktree)
        + b"\n"
    )


def make_pair(root: Path):
    source = root / "source"
    destination = root / "destination"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Post Apollo Test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "sample.txt").write_text(
        "alpha\nbeta\ngamma\ndelta\n",
        encoding="utf-8",
    )
    git(source, "add", "sample.txt")
    git(source, "commit", "-qm", "base")
    git(source, "branch", "destination")
    git(source, "worktree", "add", "-q", str(destination), "destination")
    return source, destination


def make_partial_change(source: Path):
    (source / "sample.txt").write_text(
        "alpha\nBETA STAGED\ngamma\ndelta\n",
        encoding="utf-8",
    )
    git(source, "add", "sample.txt")
    (source / "sample.txt").write_text(
        "alpha\nBETA STAGED\ngamma\nDELTA UNSTAGED\n",
        encoding="utf-8",
    )

    staged = staged_patch(source)
    worktree = worktree_patch(source)
    assert staged
    assert worktree
    assert git(source, "diff", "--cached", "--quiet", "--", "sample.txt", check=False).returncode == 1
    assert git(source, "diff", "--quiet", "--", "sample.txt", check=False).returncode == 1
    return staged, worktree


def apply_cached(repo: Path, patch: bytes, reverse=False, check_only=False):
    args = ["apply"]
    if reverse:
        args.append("-R")
    if check_only:
        args.append("--check")
    args.extend(["--cached", "--binary", "--whitespace=nowarn", "-"])
    return git(repo, *args, input_bytes=patch, check=False)


def apply_worktree(repo: Path, patch: bytes, reverse=False, check_only=False):
    args = ["apply"]
    if reverse:
        args.append("-R")
    if check_only:
        args.append("--check")
    args.extend(["--binary", "--whitespace=nowarn", "-"])
    return git(repo, *args, input_bytes=patch, check=False)


def apply_staged_layer(repo: Path, patch: bytes):
    assert apply_cached(repo, patch).returncode == 0
    assert apply_worktree(repo, patch).returncode == 0


def remove_staged_layer(repo: Path, patch: bytes):
    assert apply_worktree(repo, patch, reverse=True).returncode == 0
    assert apply_cached(repo, patch, reverse=True).returncode == 0


def assert_partial(repo: Path, staged: bytes, worktree: bytes):
    assert staged_patch(repo) == staged
    assert worktree_patch(repo) == worktree


def smoke_copy_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-partial-copy-") as tmp:
        source, destination = make_pair(Path(tmp))
        staged, worktree = make_partial_change(source)
        payload = bundle(staged, worktree)
        fingerprint = hashlib.sha256(payload).hexdigest()
        assert fingerprint

        assert apply_cached(destination, staged, check_only=True).returncode == 0
        apply_staged_layer(destination, staged)
        assert apply_worktree(destination, worktree).returncode == 0

        assert_partial(source, staged, worktree)
        assert_partial(destination, staged, worktree)

        # COPY Undo removes worktree layer first, then staged layer.
        assert apply_worktree(destination, worktree, reverse=True, check_only=True).returncode == 0
        assert apply_worktree(destination, worktree, reverse=True).returncode == 0
        remove_staged_layer(destination, staged)

        assert_partial(source, staged, worktree)
        assert status(destination) == ""


def smoke_move_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-partial-move-") as tmp:
        source, destination = make_pair(Path(tmp))
        staged, worktree = make_partial_change(source)

        # MOVE lands staged first, then worktree; source removes in reverse order.
        apply_staged_layer(destination, staged)
        assert apply_worktree(destination, worktree).returncode == 0
        assert apply_worktree(source, worktree, reverse=True).returncode == 0
        remove_staged_layer(source, staged)

        assert status(source) == ""
        assert_partial(destination, staged, worktree)

        # MOVE Undo restores source staged first, then worktree; removes destination in reverse.
        assert apply_cached(source, staged, check_only=True).returncode == 0
        apply_staged_layer(source, staged)
        assert apply_worktree(source, worktree).returncode == 0
        assert apply_worktree(destination, worktree, reverse=True).returncode == 0
        remove_staged_layer(destination, staged)

        assert_partial(source, staged, worktree)
        assert status(destination) == ""


smoke_copy_and_undo()
smoke_move_and_undo()

print("Git partially staged whole-file Transfer contracts: PASS")
