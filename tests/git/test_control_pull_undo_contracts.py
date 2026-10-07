#!/usr/bin/env python3
"""Contracts + runtime smoke tests for guarded CONTROL/PULL Undo."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GIT_SERVICE = "services/git/GitService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ('pendingProcessAction === "pull"', "CONTROL journaling must preserve pull target metadata"),
    ('pullMode: String(pullMode || "")', "pull journal metadata must preserve FF vs merge mode"),
    ('localTarget: String(selectedLocalBranch || branch || "")', "pull journal metadata must preserve local target branch"),
    ('git -C "$repo" pull --ff-only', "CONTROL must expose checked-out FF pull"),
    ('git -C "$repo" pull --no-rebase', "CONTROL must expose checked-out merge pull"),
    ('git -C "$repo" branch -f "$local_target" "$target"', "CONTROL must expose background FF sync"),
):
    require(GIT_SERVICE, needle, message)

for needle, message in (
    ('String(row.kind || "") !== "CONTROL/PULL"', "recovery must recognize CONTROL/PULL records"),
    ('strategy: "RESTORE_PULLED_BRANCH"', "checked-out pull needs guarded local branch restoration"),
    ('strategy: "RESTORE_BACKGROUND_PULL_REF"', "background FF pull needs ref-only restoration"),
    ("PULL DOES NOT HAVE CLEAN REF-RECOVERABLE EVIDENCE", "dirty/inexact pulls must remain refused"),
    ("PULLED BRANCH MOVED SINCE OPERATION", "checked-out pull Undo must refuse local ref drift"),
    ("BACKGROUND PULL TARGET MOVED SINCE OPERATION", "background pull Undo must refuse target ref drift"),
    ("BACKGROUND PULL TARGET IS NOW CHECKED OUT IN A WORKTREE", "background Undo must not move a live worktree branch"),
    ("FETCHED REMOTE REFS RETAINED", "pull Undo must state that fetch evidence remains"),
):
    require(RECOVERY, needle, message)


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


def commit_file(repo: Path, path: str, value: str, message: str):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")
    git(repo, "add", path)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def setup_remote(root: Path):
    remote = root / "origin.git"
    seed = root / "seed"
    local = root / "local"

    git(root, "init", "--bare", str(remote))
    seed.mkdir()
    git(seed, "init", "-q")
    git(seed, "config", "user.name", "Post Apollo Test")
    git(seed, "config", "user.email", "test@example.invalid")
    git(seed, "branch", "-M", "main")
    base = commit_file(seed, "base.txt", "base\n", "base")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-q", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    run(["git", "clone", "-q", str(remote), str(local)])
    git(local, "config", "user.name", "Post Apollo Test")
    git(local, "config", "user.email", "test@example.invalid")
    return remote, seed, local, base


def restore_checked_out_pull(local: Path, branch: str, before: str, after: str):
    ref = f"refs/heads/{branch}"
    assert git(local, "rev-parse", ref).stdout.decode().strip() == after
    assert git(local, "status", "--porcelain=v1").stdout == b""
    git(local, "update-ref", "ORIG_HEAD", after)
    git(local, "update-ref", ref, before, after)
    git(local, "reset", "--hard", before)
    assert git(local, "rev-parse", "HEAD").stdout.decode().strip() == before
    assert git(local, "status", "--porcelain=v1").stdout == b""


def smoke_checked_out_ff_pull_undo():
    with tempfile.TemporaryDirectory(prefix="pa-pull-ff-") as tmp:
        _remote, seed, local, base = setup_remote(Path(tmp))
        remote_head = commit_file(seed, "remote.txt", "remote\n", "remote advance")
        git(seed, "push", "-q", "origin", "main")

        git(local, "fetch", "-q", "origin")
        before = git(local, "rev-parse", "HEAD").stdout.decode().strip()
        assert before == base
        git(local, "pull", "-q", "--ff-only", "origin", "main")
        after = git(local, "rev-parse", "HEAD").stdout.decode().strip()
        assert after == remote_head

        restore_checked_out_pull(local, "main", before, after)

        # Undo local time, not fetched knowledge.
        assert (
            git(local, "rev-parse", "refs/remotes/origin/main")
            .stdout.decode()
            .strip()
            == remote_head
        )


def smoke_checked_out_merge_pull_undo():
    with tempfile.TemporaryDirectory(prefix="pa-pull-merge-") as tmp:
        _remote, seed, local, _base = setup_remote(Path(tmp))

        before = commit_file(local, "local.txt", "local\n", "local advance")
        remote_head = commit_file(seed, "remote.txt", "remote\n", "remote advance")
        git(seed, "push", "-q", "origin", "main")

        git(local, "pull", "-q", "--no-rebase", "origin", "main")
        after = git(local, "rev-parse", "HEAD").stdout.decode().strip()
        assert after != before
        parents = (
            git(local, "rev-list", "--parents", "-n", "1", after)
            .stdout.decode()
            .strip()
            .split()
        )
        assert len(parents) == 3, parents

        restore_checked_out_pull(local, "main", before, after)

        assert (
            git(local, "rev-parse", "refs/remotes/origin/main")
            .stdout.decode()
            .strip()
            == remote_head
        )


def smoke_background_ff_pull_undo():
    with tempfile.TemporaryDirectory(prefix="pa-pull-bg-") as tmp:
        _remote, seed, local, base = setup_remote(Path(tmp))

        git(seed, "switch", "-qc", "topic", base)
        topic_first = commit_file(seed, "topic.txt", "topic one\n", "topic one")
        git(seed, "push", "-q", "-u", "origin", "topic")
        git(seed, "switch", "-q", "main")

        git(local, "fetch", "-q", "origin")
        git(local, "branch", "topic", topic_first)
        current_before = git(local, "rev-parse", "HEAD").stdout.decode().strip()

        git(seed, "switch", "-q", "topic")
        topic_after = commit_file(seed, "topic2.txt", "topic two\n", "topic two")
        git(seed, "push", "-q", "origin", "topic")
        git(seed, "switch", "-q", "main")

        git(local, "fetch", "-q", "origin")
        before = git(local, "rev-parse", "refs/heads/topic").stdout.decode().strip()
        assert before == topic_first
        git(local, "branch", "-f", "topic", "refs/remotes/origin/topic")
        after = git(local, "rev-parse", "refs/heads/topic").stdout.decode().strip()
        assert after == topic_after
        assert git(local, "rev-parse", "HEAD").stdout.decode().strip() == current_before

        # Background Undo moves only the target branch ref.
        git(local, "update-ref", "refs/heads/topic", before, after)
        assert git(local, "rev-parse", "refs/heads/topic").stdout.decode().strip() == before
        assert git(local, "rev-parse", "HEAD").stdout.decode().strip() == current_before
        assert (
            git(local, "rev-parse", "refs/remotes/origin/topic")
            .stdout.decode()
            .strip()
            == topic_after
        )


smoke_checked_out_ff_pull_undo()
smoke_checked_out_merge_pull_undo()
smoke_background_ff_pull_undo()

print("Git CONTROL/PULL guarded Undo contracts: PASS")
