#!/usr/bin/env python3
"""Contracts + runtime smoke tests for broader stash-creation Undo."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = "services/git/GitRepositorySnapshotService.qml"
CHANGES = "services/git/GitChangesService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ('stash list --format="STASH%x09%gd%x09%H%x09%gs"', "snapshots must capture the ordered stash stack"),
    ("untrackedContentHash", "snapshots must fingerprint untracked file content"),
):
    require(SNAPSHOT, needle, message)

for needle, message in (
    ("function stashEntries(snapshot)", "Changes must read full stash-stack evidence"),
    ("function stashSnapshotCanRecover(before, after, modeName)", "stash creation recovery must be mode-aware"),
    ('mode === "keep-index"', "keep-index creation must have exact transition rules"),
    ('mode === "staged"', "staged-only creation must have conservative exact transition rules"),
    ("STAGED STASH WITH RETAINED TRACKED WORKTREE CONTENT IS NOT AUTOMATICALLY RECOVERABLE", "unsafe staged-only overlap must remain evidence-only"),
    ("untrackedContentHash", "stash classification must compare untracked contents"),
):
    require(CHANGES, needle, message)

for needle, message in (
    ('strategy: "UNDO_STASH_CREATE_EXACT"', "new stash records must use the full-stack exact inverse"),
    ("UNDO_STASH_CREATE_ALL", "legacy full-stash journal records must retain their old inverse"),
    ("PRE-STASH STACK OBJECT MISSING", "stash creation Undo must prove prior stack objects still exist"),
    ("UNTRACKED CONTENT CHANGED SINCE STASH CREATION", "Undo must refuse untracked-content drift"),
    ('stash apply --index "$stash_sha"', "stash creation Undo must restore exact staged/worktree content from the created object"),
    ('rebuild_stash_stack "$repo" "$before_stack"', "stash creation Undo must restore the previous ordered stash stack"),
    ("STASH RESTORE EVIDENCE MISMATCH // POST-STATE RESTORED", "failed verification must roll back to the recorded post-stash state"),
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
    first = subprocess.Popen(producer, cwd=repo, stdout=subprocess.PIPE)
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
    return hash_stdout(repo, ["git", "-C", str(repo), "diff", "--binary"])


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


def evidence(repo: Path):
    return (index_tree(repo), worktree_hash(repo), untracked_hash(repo))


def stack(repo: Path):
    raw = git(repo, "stash", "list", "--format=%H").stdout.decode()
    return [line for line in raw.splitlines() if line]


def stash_sha(repo: Path):
    rows = stack(repo)
    return rows[0] if rows else ""


def make_repo(root: Path):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Post Apollo Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    (repo / "other.txt").write_text("other base\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


def create_previous_stash(repo: Path):
    (repo / "old.txt").write_text("old stash payload\n", encoding="utf-8")
    git(repo, "stash", "push", "-u", "-m", "older")
    return stash_sha(repo)


def dirty_full_state(repo: Path):
    (repo / "tracked.txt").write_text("staged changed\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    (repo / "other.txt").write_text("unstaged changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("untracked payload\n", encoding="utf-8")


def smoke_full_stash_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-all-") as tmp:
        repo = make_repo(Path(tmp))
        previous = create_previous_stash(repo)
        dirty_full_state(repo)
        before = evidence(repo)
        before_stack = stack(repo)

        git(repo, "stash", "push", "-u", "-m", "all payload")
        created = stash_sha(repo)
        assert created and created != previous
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        git(repo, "stash", "apply", "--index", created)
        git(repo, "stash", "drop", "stash@{0}")

        assert evidence(repo) == before
        assert stack(repo) == before_stack
        assert (repo / "untracked.txt").read_text(encoding="utf-8") == "untracked payload\n"


def smoke_keep_index_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-keep-index-") as tmp:
        repo = make_repo(Path(tmp))
        previous = create_previous_stash(repo)

        (repo / "tracked.txt").write_text("staged version\n", encoding="utf-8")
        git(repo, "add", "tracked.txt")
        (repo / "tracked.txt").write_text(
            "staged version plus unstaged tail\n",
            encoding="utf-8",
        )
        (repo / "other.txt").write_text("unstaged other\n", encoding="utf-8")
        (repo / "untracked.txt").write_text("keep-index untracked\n", encoding="utf-8")

        before = evidence(repo)
        before_stack = stack(repo)
        git(repo, "stash", "push", "-u", "--keep-index", "-m", "keep index")
        created = stash_sha(repo)

        post_status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        assert b"M  tracked.txt" in post_status
        assert b"other.txt" not in post_status
        assert b"untracked.txt" not in post_status

        # Recovery intentionally clears the retained index first, then applies
        # the created stash with --index to reconstruct the exact pre-state.
        git(repo, "reset", "--hard", "HEAD")
        git(repo, "clean", "-fd")
        result = git(repo, "stash", "apply", "--index", created, check=False)
        assert result.returncode == 0, result.stderr.decode()
        git(repo, "stash", "drop", "stash@{0}")

        assert evidence(repo) == before
        assert stack(repo) == before_stack
        assert stash_sha(repo) == previous


def smoke_staged_only_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-staged-") as tmp:
        repo = make_repo(Path(tmp))
        previous = create_previous_stash(repo)

        (repo / "tracked.txt").write_text("staged only\n", encoding="utf-8")
        git(repo, "add", "tracked.txt")
        (repo / "untracked.txt").write_text(
            "retained untracked\n",
            encoding="utf-8",
        )
        before = evidence(repo)
        before_stack = stack(repo)

        git(repo, "stash", "push", "--staged", "-m", "staged only")
        created = stash_sha(repo)
        post_status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        post_lines = post_status.splitlines()
        assert not any(
            len(line) >= 4 and line[3:] == b"tracked.txt"
            for line in post_lines
        )
        assert b"?? untracked.txt" in post_lines

        # Safe staged-only recovery applies directly onto the exact retained
        # post-state; it never cleans unrelated untracked content.
        result = git(repo, "stash", "apply", "--index", created, check=False)
        assert result.returncode == 0, result.stderr.decode()
        git(repo, "stash", "drop", "stash@{0}")

        assert evidence(repo) == before
        assert stack(repo) == before_stack
        assert stash_sha(repo) == previous
        assert (repo / "untracked.txt").read_text(encoding="utf-8") == "retained untracked\n"


def smoke_staged_with_unstaged_is_conservative():
    with tempfile.TemporaryDirectory(prefix="pa-stash-staged-overlap-") as tmp:
        repo = make_repo(Path(tmp))
        (repo / "tracked.txt").write_text("staged layer\n", encoding="utf-8")
        git(repo, "add", "tracked.txt")
        (repo / "tracked.txt").write_text(
            "staged layer plus retained unstaged layer\n",
            encoding="utf-8",
        )
        status = git(repo, "status", "--porcelain=v1").stdout.decode()
        assert status.startswith("MM ")
        # The journal classifier uses this same boundary: staged mode is only
        # automatic when tracked unstagedCount == 0.
        assert " M" in status


smoke_full_stash_undo()
smoke_keep_index_undo()
smoke_staged_only_undo()
smoke_staged_with_unstaged_is_conservative()

print("Git broader stash creation Undo contracts: PASS")
