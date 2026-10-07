#!/usr/bin/env python3
"""Contracts + runtime smoke for creating a Transfer destination worktree."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
VIEW = "widgets/GitChangeTransferView.qml"
BRANCH_SERVICE = "services/git/GitBranchWorkspaceService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("property bool createDestinationOpen: false", "Transfer must own explicit destination-creation UI state"),
    ("property string pendingCreatedDestinationPath", "Transfer must remember the pending destination path"),
    ("function defaultDestinationPath(branchName)", "Transfer must provide a deterministic default worktree path"),
    ("function createDestination()", "Transfer must expose guarded destination creation"),
    ("branchWorkspaceService.createWorktree(", "Transfer must reuse the shared branch/worktree service"),
    ('"HEAD"', "new Transfer destinations must start from the source HEAD"),
    ('String(action || "") !== "NEW-WORKTREE"', "Transfer must wait for the branch service completion signal"),
    ("root.chooseDestination(createdPath)", "created worktree must be selected only after topology refresh"),
    ("PREVIEW REQUIRED", "creation must not bypass the normal Transfer preview gate"),
    ("SEPARATE GUARDED OPERATION", "UI must disclose that creation and Transfer are separate mutations"),
):
    require(VIEW, needle, message)

for needle, message in (
    ("function createWorktree(path, branch, startPoint)", "shared branch service must expose worktree creation"),
    ('runAction("new-worktree"', "worktree creation must stay in the shared guarded mutation path"),
    ('"BRANCH_WORKSPACE/"', "worktree creation must stay journaled through branch workspace operations"),
):
    require(BRANCH_SERVICE, needle, message)

view = read(VIEW)
action_start = view.index("function onActionFinished(action, success, detail)")
refresh_start = view.index("function onRefreshed()", action_start)
component_start = view.index("component DestinationEditor", refresh_start)
action_block = view[action_start:refresh_start]
refresh_block = view[refresh_start:component_start]

assert "requestPreview(" not in action_block, (
    "destination creation completion must not auto-preview Transfer"
)
assert "executeTransfer(" not in action_block, (
    "destination creation completion must not auto-execute Transfer"
)
assert "requestPreview(" not in refresh_block, (
    "destination refresh must only select the new worktree; preview remains explicit"
)
assert "executeTransfer(" not in refresh_block, (
    "destination refresh must never auto-execute Transfer"
)


def run(args, cwd=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, check=True):
    return run(["git", "-C", str(repo), *args], check=check)


def smoke_new_destination_from_head():
    with tempfile.TemporaryDirectory(prefix="pa-transfer-destination-") as tmp:
        root = Path(tmp)
        source = root / "source"
        destination = root / "destination"
        source.mkdir()

        git(source, "init", "-q", "-b", "main")
        git(source, "config", "user.name", "Post Apollo Test")
        git(source, "config", "user.email", "test@example.invalid")
        (source / "sample.txt").write_text("base\n", encoding="utf-8")
        git(source, "add", "sample.txt")
        git(source, "commit", "-qm", "base")

        source_head = git(source, "rev-parse", "HEAD").stdout.decode().strip()
        git(source, "worktree", "add", "-q", "-b", "transfer-target", str(destination), "HEAD")

        destination_head = git(destination, "rev-parse", "HEAD").stdout.decode().strip()
        destination_branch = git(destination, "branch", "--show-current").stdout.decode().strip()

        assert destination_head == source_head
        assert destination_branch == "transfer-target"
        assert git(destination, "status", "--porcelain=v1").stdout == b""
        assert git(source, "branch", "--show-current").stdout.decode().strip() == "main"
        assert git(source, "status", "--porcelain=v1").stdout == b""


smoke_new_destination_from_head()

print("Git Transfer destination creation contracts: PASS")
