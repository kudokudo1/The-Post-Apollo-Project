#!/usr/bin/env python3
"""Contracts + runtime smoke tests for generalized HISTORY Undo."""

from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for kind in (
    "HISTORY/MERGE",
    "HISTORY/CHERRY-PICK",
    "HISTORY/REVERT",
    "HISTORY/RESET",
):
    require(
        RECOVERY,
        f'kind === "{kind}"',
        f"{kind} must use guarded branch-head restoration",
    )

require(
    RECOVERY,
    'kind === "HISTORY/BRANCH"',
    "History branch creation must share exact created-branch Undo",
)
require(
    RECOVERY,
    'kind === "HISTORY/TAG"',
    "History tag creation must expose exact created-tag Undo",
)
require(
    RECOVERY,
    'strategy: "DELETE_CREATED_TAG"',
    "created tags must use guarded deletion",
)
require(
    RECOVERY,
    'kind === "HISTORY/DETACH"',
    "detached History navigation must expose guarded switch-back",
)
require(
    RECOVERY,
    'strategy: "SWITCH_BACK_FROM_DETACHED"',
    "detached Undo must have its own exact strategy",
)
require(
    RECOVERY,
    'strategy: "UNDO_RESET_SOFT_OR_MIXED"',
    "soft and mixed reset must use dedicated content-preserving recovery",
)
require(
    RECOVERY,
    "WORKTREE CONTENT NO LONGER MATCHES PRE-RESET TREE",
    "soft/mixed reset Undo must refuse worktree drift including reset-created untracked files",
)
require(
    RECOVERY,
    "MIXED RESET INDEX NO LONGER MATCHES RESET TARGET TREE",
    "mixed reset Undo must verify the recorded reset index exactly",
)
require(
    RECOVERY,
    "SOFT RESET INDEX NO LONGER MATCHES PRE-RESET TREE",
    "soft reset Undo must verify the pre-reset index was preserved",
)
require(
    RECOVERY,
    "OPERATION IS NOT CLEAN REF-RECOVERABLE",
    "unsupported dirty history outcomes must remain refused by the common recovery gate",
)
require(
    RECOVERY,
    "TAG MOVED SINCE RECORDED OPERATION",
    "tag Undo must refuse stale tag identity",
)
require(
    RECOVERY,
    "DETACHED HEAD MOVED SINCE OPERATION",
    "detach Undo must refuse HEAD drift",
)
require(
    RECOVERY,
    "PREVIOUS BRANCH MOVED SINCE DETACH",
    "detach Undo must refuse previous-branch drift",
)


def run(args, cwd=None, check=True, env=None):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, check=True, env=None):
    return run(["git", "-C", str(repo), *args], check=check, env=env)


def commit_file(repo: Path, name: str, value: str, message: str):
    (repo / name).write_text(value, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def make_repo(root: Path):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Post Apollo Test")
    git(repo, "config", "user.email", "test@example.invalid")
    base = commit_file(repo, "base.txt", "base\n", "base")
    branch = git(repo, "branch", "--show-current").stdout.decode().strip()
    return repo, base, branch


def guarded_restore_branch(repo: Path, branch: str, before: str, after: str):
    ref = f"refs/heads/{branch}"
    assert git(repo, "rev-parse", ref).stdout.decode().strip() == after
    assert git(repo, "status", "--porcelain=v1").stdout == b""
    git(repo, "update-ref", "ORIG_HEAD", after)
    git(repo, "update-ref", ref, before, after)
    git(repo, "reset", "--hard", before)
    assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == before
    assert git(repo, "status", "--porcelain=v1").stdout == b""


def smoke_fast_forward_merge_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-merge-ff-") as tmp:
        repo, before, branch = make_repo(Path(tmp))
        git(repo, "switch", "-qc", "donor")
        donor = commit_file(repo, "donor.txt", "donor\n", "donor")
        git(repo, "switch", "-q", branch)
        git(repo, "merge", "--no-edit", donor)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert after == donor
        guarded_restore_branch(repo, branch, before, after)
        assert not (repo / "donor.txt").exists()


def smoke_merge_commit_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-merge-commit-") as tmp:
        repo, base, branch = make_repo(Path(tmp))
        git(repo, "switch", "-qc", "donor")
        donor = commit_file(repo, "donor.txt", "donor\n", "donor")
        git(repo, "switch", "-q", branch)
        before = commit_file(repo, "local.txt", "local\n", "local")
        git(repo, "merge", "--no-edit", donor)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        parents = git(repo, "show", "-s", "--format=%P", after).stdout.decode().split()
        assert len(parents) == 2
        assert base in git(repo, "merge-base", before, donor).stdout.decode()
        guarded_restore_branch(repo, branch, before, after)
        assert (repo / "local.txt").read_text(encoding="utf-8") == "local\n"
        assert not (repo / "donor.txt").exists()


def smoke_cherry_pick_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-cherry-") as tmp:
        repo, before, branch = make_repo(Path(tmp))
        git(repo, "switch", "-qc", "donor")
        donor = commit_file(repo, "donor.txt", "donor\n", "donor")
        git(repo, "switch", "-q", branch)
        git(repo, "cherry-pick", donor)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert after != before
        guarded_restore_branch(repo, branch, before, after)
        assert not (repo / "donor.txt").exists()


def smoke_revert_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-revert-") as tmp:
        repo, _base, branch = make_repo(Path(tmp))
        before = commit_file(repo, "feature.txt", "present\n", "feature")
        git(repo, "revert", "--no-edit", before)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert not (repo / "feature.txt").exists()
        guarded_restore_branch(repo, branch, before, after)
        assert (repo / "feature.txt").read_text(encoding="utf-8") == "present\n"


def smoke_hard_reset_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-reset-") as tmp:
        repo, base, branch = make_repo(Path(tmp))
        before = commit_file(repo, "later.txt", "later\n", "later")
        git(repo, "reset", "--hard", base)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert after == base
        guarded_restore_branch(repo, branch, before, after)
        assert (repo / "later.txt").read_text(encoding="utf-8") == "later\n"


def materialized_worktree_tree(repo: Path, restore: str) -> str:
    with tempfile.TemporaryDirectory(prefix="pa-reset-index-") as tmp:
        index_path = Path(tmp) / "index"
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(index_path)
        git(repo, "read-tree", restore, env=env)
        git(repo, "add", "-A", "--", ".", env=env)
        return git(repo, "write-tree", env=env).stdout.decode().strip()


def guarded_restore_reset(
    repo: Path,
    branch: str,
    restore: str,
    expected: str,
    mode: str,
):
    ref = f"refs/heads/{branch}"
    assert git(repo, "rev-parse", ref).stdout.decode().strip() == expected

    expected_tree = git(repo, "rev-parse", f"{expected}^{{tree}}").stdout.decode().strip()
    restore_tree = git(repo, "rev-parse", f"{restore}^{{tree}}").stdout.decode().strip()
    index_tree = git(repo, "write-tree").stdout.decode().strip()

    if mode == "soft":
        assert index_tree == restore_tree
    elif mode == "mixed":
        assert index_tree == expected_tree
    else:
        raise AssertionError(mode)

    assert materialized_worktree_tree(repo, restore) == restore_tree

    git(repo, "update-ref", ref, restore, expected)
    if mode == "mixed":
        git(repo, "reset", "--mixed", restore)

    assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == restore
    assert git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout == b""


def smoke_soft_reset_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-soft-reset-") as tmp:
        repo, base, branch = make_repo(Path(tmp))
        before = commit_file(repo, "later.txt", "later\n", "later")
        git(repo, "reset", "--soft", base)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert after == base
        assert git(repo, "diff", "--cached", "--name-only").stdout != b""
        guarded_restore_reset(repo, branch, before, after, "soft")
        assert (repo / "later.txt").read_text(encoding="utf-8") == "later\n"


def smoke_mixed_reset_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-mixed-reset-") as tmp:
        repo, base, branch = make_repo(Path(tmp))
        (repo / "base.txt").write_text("base changed\n", encoding="utf-8")
        (repo / "later.txt").write_text("later\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "later")
        before = git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        git(repo, "reset", "--mixed", base)
        after = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        assert b"base.txt" in status
        assert b"later.txt" in status

        guarded_restore_reset(repo, branch, before, after, "mixed")
        assert (repo / "base.txt").read_text(encoding="utf-8") == "base changed\n"
        assert (repo / "later.txt").read_text(encoding="utf-8") == "later\n"


def smoke_mixed_reset_drift_is_refused():
    with tempfile.TemporaryDirectory(prefix="pa-history-mixed-reset-drift-") as tmp:
        repo, base, _branch = make_repo(Path(tmp))
        before = commit_file(repo, "later.txt", "later\n", "later")
        git(repo, "reset", "--mixed", base)
        (repo / "later.txt").write_text("drifted after reset\n", encoding="utf-8")
        restore_tree = git(repo, "rev-parse", f"{before}^{{tree}}").stdout.decode().strip()
        assert materialized_worktree_tree(repo, before) != restore_tree


def smoke_created_branch_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-branch-") as tmp:
        repo, head, _branch = make_repo(Path(tmp))
        git(repo, "branch", "review-point", head)
        ref = "refs/heads/review-point"
        assert git(repo, "rev-parse", ref).stdout.decode().strip() == head
        git(repo, "update-ref", "-d", ref, head)
        assert git(repo, "rev-parse", "-q", "--verify", ref, check=False).returncode != 0


def smoke_created_tag_undo():
    with tempfile.TemporaryDirectory(prefix="pa-history-tag-") as tmp:
        repo, head, _branch = make_repo(Path(tmp))
        git(repo, "tag", "review-tag", head)
        ref = "refs/tags/review-tag"
        assert git(repo, "rev-parse", ref).stdout.decode().strip() == head
        git(repo, "update-ref", "-d", ref, head)
        assert git(repo, "rev-parse", "-q", "--verify", ref, check=False).returncode != 0


def smoke_detach_switch_back():
    with tempfile.TemporaryDirectory(prefix="pa-history-detach-") as tmp:
        repo, base, branch = make_repo(Path(tmp))
        later = commit_file(repo, "later.txt", "later\n", "later")
        branch_sha = git(repo, "rev-parse", f"refs/heads/{branch}").stdout.decode().strip()
        assert branch_sha == later
        git(repo, "switch", "--detach", base)
        assert git(repo, "symbolic-ref", "-q", "HEAD", check=False).returncode != 0
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == base
        assert git(repo, "rev-parse", f"refs/heads/{branch}").stdout.decode().strip() == later
        git(repo, "switch", branch)
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == later


smoke_fast_forward_merge_undo()
smoke_merge_commit_undo()
smoke_cherry_pick_undo()
smoke_revert_undo()
smoke_hard_reset_undo()
smoke_soft_reset_undo()
smoke_mixed_reset_undo()
smoke_mixed_reset_drift_is_refused()
smoke_created_branch_undo()
smoke_created_tag_undo()
smoke_detach_switch_back()

print("Git generalized HISTORY Undo contracts: PASS")
