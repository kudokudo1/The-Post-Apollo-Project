#!/usr/bin/env python3
"""Contracts + runtime smoke tests for content-preserving commit/amend Undo."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CHANGES = "services/git/GitChangesService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("property var pendingBeforeSnapshot: null", "Changes must retain BEFORE evidence through commit execution"),
    ("function commitSnapshotCanRecover(before, after)", "commit recovery must compare exact before/after evidence"),
    ('out.recoveryClass = "CONTENT_RECOVERABLE";', "exact commit transitions must become content-recoverable"),
    ("COMMIT/AMEND CONTENT TRANSITION IS NOT EXACT", "inexact commit transitions must fall back to evidence-only"),
    ("beforeWorking.worktreePatchHash", "commit recovery must preserve worktree patch identity"),
    ("beforeWorking.untrackedListHash", "commit recovery must preserve untracked-set identity"),
    ("String(beforeIndex.tree || "") !== expectedIndexTree", "commit recovery must preserve index tree identity"),
):
    require(CHANGES, needle, message)

for needle, message in (
    ('String(row.kind || "") !== "CHANGES/COMMIT"', "recovery must scope content inverse to commit records"),
    ('strategy: "UNDO_COMMIT_TO_STAGED"', "commit recovery must expose a dedicated strategy"),
    ("COMMIT BRANCH MOVED SINCE OPERATION", "commit Undo must refuse ref drift"),
    ("INDEX CHANGED SINCE COMMIT", "commit Undo must refuse index drift"),
    ("WORKTREE CHANGED SINCE COMMIT", "commit Undo must refuse worktree drift"),
    ("UNTRACKED FILE SET CHANGED SINCE COMMIT", "commit Undo must refuse untracked-set drift"),
    ("GUARDED COMMIT UNDO REF RESTORE FAILED", "commit Undo must use expected-old ref restoration"),
    ("RESTORED PRE-COMMIT HEAD + STAGED CONTENT", "commit Undo must preserve the staged payload"),
):
    require(RECOVERY, needle, message)

require(
    RECOVERY,
    'strategy !== "UNDO_COMMIT_TO_STAGED"',
    "commit Undo must have a narrow dirty-state snapshot exception",
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


def hash_stdout(repo: Path, producer):
    first = subprocess.Popen(
        producer,
        cwd=repo,
        stdout=subprocess.PIPE,
    )
    second = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "--stdin"],
        stdin=first.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    first.stdout.close()
    assert first.wait() == 0
    return second.stdout.decode().strip()


def index_tree(repo: Path):
    return git(repo, "write-tree").stdout.decode().strip()


def worktree_hash(repo: Path):
    return hash_stdout(
        repo,
        ["git", "-C", str(repo), "diff", "--binary"],
    )


def untracked_hash(repo: Path):
    return hash_stdout(
        repo,
        [
            "git", "-C", str(repo),
            "ls-files", "--others", "--exclude-standard", "-z",
        ],
    )


def init_repo(root: Path):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Post Apollo Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "staged.txt").write_text("staged base\n", encoding="utf-8")
    (repo / "unstaged.txt").write_text("unstaged base\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    branch = git(repo, "branch", "--show-current").stdout.decode().strip()
    return repo, branch


def guarded_soft_ref_undo(repo: Path, branch: str, restore: str, expected: str):
    ref = f"refs/heads/{branch}"
    assert git(repo, "rev-parse", ref).stdout.decode().strip() == expected
    git(repo, "update-ref", "ORIG_HEAD", expected)
    git(repo, "update-ref", ref, restore, expected)
    assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == restore


def smoke_commit_undo_preserves_layers():
    with tempfile.TemporaryDirectory(prefix="pa-commit-undo-") as tmp:
        repo, branch = init_repo(Path(tmp))

        (repo / "staged.txt").write_text(
            "staged committed payload\n",
            encoding="utf-8",
        )
        git(repo, "add", "staged.txt")
        (repo / "unstaged.txt").write_text(
            "unstaged survives\n",
            encoding="utf-8",
        )
        (repo / "untracked.txt").write_text(
            "untracked survives\n",
            encoding="utf-8",
        )

        before_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        before_index = index_tree(repo)
        before_worktree = worktree_hash(repo)
        before_untracked = untracked_hash(repo)

        git(repo, "commit", "-qm", "commit staged payload")
        after_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        assert after_head != before_head
        assert index_tree(repo) == before_index
        assert worktree_hash(repo) == before_worktree
        assert untracked_hash(repo) == before_untracked
        assert git(repo, "diff", "--cached", "--quiet", check=False).returncode == 0

        guarded_soft_ref_undo(
            repo,
            branch,
            before_head,
            after_head,
        )

        # Index/worktree are untouched by the guarded ref rewind.
        assert index_tree(repo) == before_index
        assert worktree_hash(repo) == before_worktree
        assert untracked_hash(repo) == before_untracked
        assert git(repo, "diff", "--cached", "--quiet", check=False).returncode != 0
        assert (repo / "unstaged.txt").read_text(encoding="utf-8") == "unstaged survives\n"
        assert (repo / "untracked.txt").read_text(encoding="utf-8") == "untracked survives\n"


def smoke_amend_undo_restores_old_commit_and_staging():
    with tempfile.TemporaryDirectory(prefix="pa-amend-undo-") as tmp:
        repo, branch = init_repo(Path(tmp))

        (repo / "feature.txt").write_text("original feature\n", encoding="utf-8")
        git(repo, "add", "feature.txt")
        git(repo, "commit", "-qm", "original feature")
        old_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        (repo / "staged.txt").write_text(
            "staged into amendment\n",
            encoding="utf-8",
        )
        git(repo, "add", "staged.txt")
        (repo / "unstaged.txt").write_text(
            "amend unrelated unstaged\n",
            encoding="utf-8",
        )
        (repo / "untracked.txt").write_text(
            "amend untracked\n",
            encoding="utf-8",
        )

        before_index = index_tree(repo)
        before_worktree = worktree_hash(repo)
        before_untracked = untracked_hash(repo)

        git(repo, "commit", "--amend", "-qm", "amended feature")
        amended_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        assert amended_head != old_head
        assert index_tree(repo) == before_index
        assert worktree_hash(repo) == before_worktree
        assert untracked_hash(repo) == before_untracked

        guarded_soft_ref_undo(
            repo,
            branch,
            old_head,
            amended_head,
        )

        assert git(repo, "show", "-s", "--format=%s", "HEAD").stdout.decode().strip() == "original feature"
        assert index_tree(repo) == before_index
        assert git(repo, "diff", "--cached", "--quiet", check=False).returncode != 0
        assert worktree_hash(repo) == before_worktree
        assert untracked_hash(repo) == before_untracked


smoke_commit_undo_preserves_layers()
smoke_amend_undo_restores_old_commit_and_staging()

print("Git commit/amend content-preserving Undo contracts: PASS")
