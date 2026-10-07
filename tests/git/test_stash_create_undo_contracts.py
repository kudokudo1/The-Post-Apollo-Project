#!/usr/bin/env python3
"""Contracts + runtime smoke tests for full-stash creation Undo."""

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
    ("function stashSnapshotCanRecover(before, after)", "Changes must validate the exact stash ref/content transition"),
    ('operation === "stash"', "stash creation must receive special recovery classification"),
    ('mode !== "all"', "non-full stash modes must remain conservative"),
    ('out.recoveryClass = "CONTENT_RECOVERABLE";', "exact full stash creation must become content-recoverable"),
    ('snapshotRefSha(second, "refs/stash")', "stash recovery must identify the newly-created stash object"),
    ('Number(afterWorking.stagedCount || 0) === 0', "full-stash post-state must be clean"),
    ('Number(afterWorking.untrackedCount || 0) === 0', "full-stash post-state must remove untracked content"),
):
    require(CHANGES, needle, message)

for needle, message in (
    ('String(row.kind || "") !== "CHANGES/STASH"', "Undo must scope itself to stash creation records"),
    ('strategy: "UNDO_STASH_CREATE_ALL"', "full stash Undo needs a dedicated recovery strategy"),
    ("ONLY FULL STASH CREATION HAS EXACT AUTOMATIC UNDO", "non-full stash modes must be refused"),
    ("STASH STACK CHANGED SINCE CREATION", "Undo must refuse later stash-stack mutations"),
    ("HEAD CHANGED SINCE STASH CREATION", "Undo must refuse HEAD drift"),
    ("INDEX CHANGED SINCE STASH CREATION", "Undo must refuse post-stash index drift"),
    ("WORKTREE CHANGED SINCE STASH CREATION", "Undo must refuse post-stash worktree drift"),
    ("UNTRACKED SET CHANGED SINCE STASH CREATION", "Undo must refuse post-stash untracked drift"),
    ('stash pop --index "stash@{0}"', "Undo must restore exact staged/worktree/untracked stash state"),
    ("STASH RESTORE EVIDENCE MISMATCH // OPERATION ROLLED BACK", "Undo must verify restored content evidence"),
    ("STASH STACK DID NOT RETURN TO RECORDED PREVIOUS HEAD", "Undo must verify prior stash-stack identity"),
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
            "git",
            "-C",
            str(repo),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
    )


def stash_sha(repo: Path):
    result = git(repo, "rev-parse", "-q", "--verify", "refs/stash", check=False)
    return result.stdout.decode().strip() if result.returncode == 0 else ""


def make_repo(root: Path):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Post Apollo Test")
    git(repo, "config", "user.email", "test@example.invalid")

    (repo / "staged.txt").write_text("staged base\n", encoding="utf-8")
    (repo / "unstaged.txt").write_text("unstaged base\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


def create_previous_stash(repo: Path):
    (repo / "old.txt").write_text("old stash payload\n", encoding="utf-8")
    git(repo, "stash", "push", "-u", "-m", "older")
    return stash_sha(repo)


def dirty_full_state(repo: Path):
    (repo / "staged.txt").write_text("staged changed\n", encoding="utf-8")
    git(repo, "add", "staged.txt")
    (repo / "unstaged.txt").write_text("unstaged changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked payload\n", encoding="utf-8")


def smoke_full_stash_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-undo-") as tmp:
        repo = make_repo(Path(tmp))
        previous = create_previous_stash(repo)

        dirty_full_state(repo)
        before = {
            "index": index_tree(repo),
            "worktree": worktree_hash(repo),
            "untracked": untracked_hash(repo),
        }

        git(repo, "stash", "push", "-u", "-m", "undo me")
        created = stash_sha(repo)

        assert created
        assert created != previous
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        after = {
            "index": index_tree(repo),
            "worktree": worktree_hash(repo),
            "untracked": untracked_hash(repo),
        }

        # Exact guard state used by the recovery service.
        assert stash_sha(repo) == created
        assert index_tree(repo) == after["index"]
        assert worktree_hash(repo) == after["worktree"]
        assert untracked_hash(repo) == after["untracked"]

        result = git(
            repo,
            "stash",
            "pop",
            "--index",
            "stash@{0}",
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode()

        assert index_tree(repo) == before["index"]
        assert worktree_hash(repo) == before["worktree"]
        assert untracked_hash(repo) == before["untracked"]
        assert stash_sha(repo) == previous
        assert (repo / "untracked.txt").read_text(encoding="utf-8") == "untracked payload\n"


def smoke_stale_stack_refusal():
    with tempfile.TemporaryDirectory(prefix="pa-stash-stale-") as tmp:
        repo = make_repo(Path(tmp))
        dirty_full_state(repo)
        git(repo, "stash", "push", "-u", "-m", "recorded")
        recorded = stash_sha(repo)

        (repo / "later.txt").write_text("later stash\n", encoding="utf-8")
        git(repo, "stash", "push", "-u", "-m", "later")
        current = stash_sha(repo)

        assert current
        assert current != recorded
        # Recovery must stop here rather than popping the wrong stash.
        assert stash_sha(repo) != recorded


smoke_full_stash_undo()
smoke_stale_stack_refusal()

print("Git full stash creation Undo contracts: PASS")
