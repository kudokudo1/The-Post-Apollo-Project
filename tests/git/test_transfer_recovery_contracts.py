#!/usr/bin/env python3
"""Contracts + runtime smoke tests for transfer content recovery."""

from pathlib import Path
import base64
import hashlib
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


JOURNAL = "services/git/GitOperationJournalService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"
TRANSFER = "services/git/GitChangeTransferService.qml"
LINE = "services/git/GitLineTransferService.qml"

require(
    JOURNAL,
    'beforeClass === "CONTENT_RECOVERABLE"',
    "journal completion must preserve content-recoverable operations",
)
require(
    JOURNAL,
    'return "CONTENT_RECOVERABLE";',
    "journal must retain content recovery classification",
)

for service in (TRANSFER, LINE):
    require(
        service,
        "maxRecoveryPatchBytes: 524288",
        "transfer recovery payloads must have a bounded durable size",
    )
    require(
        service,
        '"CONTENT_RECOVERABLE"',
        "transfer must mark exact persisted patches as content-recoverable",
    )
    require(
        service,
        "patchBase64",
        "transfer journal metadata must carry the exact accepted patch",
    )

require_regex(
    TRANSFER,
    r'printf "PATCH64\\\\t"',
    "whole-file/hunk preview must emit a bounded recovery payload",
)
require(
    LINE,
    "PATCH64",
    "line preview must emit a recovery payload marker",
)
require(
    LINE,
    "base64.b64encode(patch)",
    "line preview must persist its exact minimal patch",
)

require(
    RECOVERY,
    'strategy: "UNDO_TRANSFER_CONTENT"',
    "recovery preview must expose transfer-content Undo",
)
for kind in (
    "CHANGES/TRANSFER",
    "CHANGES/TRANSFER_HUNK",
    "CHANGES/TRANSFER_LINE",
):
    require(
        RECOVERY,
        f'"{kind}"',
        f"recovery must recognize {kind}",
    )

require(
    RECOVERY,
    "TRANSFER DOES NOT HAVE DURABLE CONTENT RECOVERY",
    "legacy/evidence-only transfers must remain non-undoable",
)
require(
    RECOVERY,
    "SOURCE HEAD CHANGED SINCE TRANSFER",
    "content Undo must refuse source HEAD drift",
)
require(
    RECOVERY,
    "DESTINATION HEAD CHANGED SINCE TRANSFER",
    "content Undo must refuse destination HEAD drift",
)
require(
    RECOVERY,
    "RECOVERY PATCH FINGERPRINT MISMATCH",
    "stored patch integrity must be verified",
)
require(
    RECOVERY,
    "DESTINATION NO LONGER CONTAINS EXACT TRANSFER",
    "content Undo must prove the destination still contains the patch",
)
require(
    RECOVERY,
    "SOURCE CAN NO LONGER RECEIVE TRANSFERRED CONTENT",
    "MOVE Undo must prove the source can receive the patch",
)
require(
    RECOVERY,
    "DESTINATION REMOVE FAILED // SOURCE ROLLED BACK",
    "MOVE Undo must roll source restoration back on destination failure",
)
require_regex(
    RECOVERY,
    r'if \[ "\$strategy" != "UNDO_TRANSFER_CONTENT" \]; then.*'
    r'WORKTREE DIRTY // UNDO WILL NOT DISCARD CONTENT',
    "content Undo must use its own exact guards instead of generic clean-worktree refusal",
)
require_regex(
    RECOVERY,
    r'strategy !== "UNDO_TRANSFER_CONTENT".*'
    r'snapshotClass !== "REF_RECOVERABLE"',
    "content Undo must be allowed to snapshot a deliberately dirty transfer state",
)


def run(args, cwd=None, input_bytes=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, check=True):
    return run(["git", "-C", str(repo), *args], check=check)


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def status(repo: Path) -> str:
    return git(repo, "status", "--porcelain=v1").stdout.decode()


def apply(repo: Path, patch: bytes, reverse=False, check_only=False):
    args = ["git", "-C", str(repo), "apply"]
    if reverse:
        args.append("-R")
    if check_only:
        args.append("--check")
    args.extend(["--binary", "--whitespace=nowarn", "-"])
    return run(args, input_bytes=patch)


def make_pair(root: Path):
    source = root / "source"
    destination = root / "destination"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Post Apollo Test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "sample.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    git(source, "add", "sample.txt")
    git(source, "commit", "-qm", "base")
    git(source, "branch", "destination")
    git(source, "worktree", "add", "-q", str(destination), "destination")
    return source, destination


def transfer_patch(source: Path) -> bytes:
    (source / "sample.txt").write_text(
        "alpha\nBETA TRANSFERRED\ngamma\n",
        encoding="utf-8",
    )
    patch = git(
        source,
        "diff",
        "--binary",
        "--full-index",
        "--",
        "sample.txt",
    ).stdout
    assert patch
    return patch


def assert_patch_integrity(patch: bytes):
    payload = base64.b64encode(patch)
    decoded = base64.b64decode(payload, validate=True)
    assert decoded == patch
    assert hashlib.sha256(decoded).hexdigest() == hashlib.sha256(patch).hexdigest()


def smoke_copy_undo():
    with tempfile.TemporaryDirectory(prefix="pa-copy-undo-") as tmp:
        source, destination = make_pair(Path(tmp))
        source_head = head(source)
        destination_head = head(destination)
        patch = transfer_patch(source)
        assert_patch_integrity(patch)

        apply(destination, patch)
        assert head(source) == source_head
        assert head(destination) == destination_head
        assert status(source)
        assert status(destination)

        # COPY Undo: source keeps its original change; destination loses it.
        apply(destination, patch, reverse=True, check_only=True)
        apply(destination, patch, reverse=True)
        assert status(source)
        assert status(destination) == ""


def smoke_move_undo():
    with tempfile.TemporaryDirectory(prefix="pa-move-undo-") as tmp:
        source, destination = make_pair(Path(tmp))
        source_head = head(source)
        destination_head = head(destination)
        patch = transfer_patch(source)
        assert_patch_integrity(patch)

        # MOVE: apply destination, reverse source.
        apply(destination, patch)
        apply(source, patch, reverse=True)
        assert status(source) == ""
        assert status(destination)

        # Guard assumptions used by recovery.
        assert head(source) == source_head
        assert head(destination) == destination_head
        apply(destination, patch, reverse=True, check_only=True)
        apply(source, patch, check_only=True)

        # MOVE Undo: restore source first; remove destination second.
        apply(source, patch)
        apply(destination, patch, reverse=True)
        assert status(source)
        assert status(destination) == ""


smoke_copy_undo()
smoke_move_undo()

print("Git transfer content recovery contracts: PASS")
