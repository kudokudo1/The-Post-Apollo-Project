#!/usr/bin/env python3
"""Contracts + runtime smoke tests for top-stash apply/pop/drop Undo."""

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
    ("function stashApplySnapshotCanRecover(before, after)", "Changes must validate stash apply transitions"),
    ("function stashPopSnapshotCanRecover(before, after)", "Changes must validate stash pop transitions"),
    ("function stashDropSnapshotCanRecover(before, after)", "Changes must validate stash drop transitions"),
    ('operation === "stash-apply"', "stash apply must receive recovery classification"),
    ('operation === "stash-pop"', "stash pop must receive recovery classification"),
    ('operation === "stash-drop"', "stash drop must receive recovery classification"),
    ("ONLY TOP-STASH MUTATIONS HAVE EXACT AUTOMATIC UNDO", "non-top stash mutation must remain conservative"),
):
    require(CHANGES, needle, message)

for needle, message in (
    ('"CHANGES/STASH-APPLY"', "recovery must recognize stash apply"),
    ('"CHANGES/STASH-POP"', "recovery must recognize stash pop"),
    ('"CHANGES/STASH-DROP"', "recovery must recognize stash drop"),
    ('strategy = "UNDO_STASH_APPLY_CLEAN"', "stash apply needs a dedicated inverse"),
    ('strategy = "UNDO_STASH_POP_TOP"', "stash pop needs a dedicated inverse"),
    ('strategy = "UNDO_STASH_DROP_TOP"', "stash drop needs a dedicated inverse"),
    ("STASH STACK CHANGED SINCE MUTATION", "stash Undo must refuse stack drift"),
    ("INDEX CHANGED SINCE STASH MUTATION", "stash Undo must refuse index drift"),
    ("WORKTREE CHANGED SINCE STASH MUTATION", "stash Undo must refuse worktree drift"),
    ("UNTRACKED SET CHANGED SINCE STASH MUTATION", "stash Undo must refuse untracked drift"),
    ("POPPED STASH OBJECT MISSING", "pop Undo must prove the object still exists"),
    ("DROPPED STASH OBJECT MISSING", "drop Undo must prove the object still exists"),
    ("STASH STACK DID NOT RETURN TO RECORDED PRE-MUTATION HEAD", "stash Undo must verify restored stack identity"),
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


def evidence(repo: Path):
    return (
        index_tree(repo),
        worktree_hash(repo),
        untracked_hash(repo),
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
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-qm", "base")
    return repo


def make_top_stash(repo: Path):
    (repo / "tracked.txt").write_text("stashed tracked\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    (repo / "extra.txt").write_text("stashed untracked\n", encoding="utf-8")
    git(repo, "stash", "push", "-u", "-m", "top payload")
    sha = stash_sha(repo)
    assert sha
    assert git(repo, "status", "--porcelain=v1").stdout == b""
    return sha


def restore_stash_object(repo: Path, sha: str):
    subject = git(repo, "log", "-1", "--format=%s", sha).stdout.decode().strip()
    git(repo, "stash", "store", "-m", subject, sha)


def smoke_apply_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-apply-") as tmp:
        repo = make_repo(Path(tmp))
        top = make_top_stash(repo)
        before = evidence(repo)

        result = git(repo, "stash", "apply", "--index", "stash@{0}", check=False)
        assert result.returncode == 0, result.stderr.decode()
        after = evidence(repo)
        assert after != before
        assert stash_sha(repo) == top

        # Undo apply from the exact recorded post-apply state.
        git(repo, "reset", "--hard", "HEAD")
        git(repo, "clean", "-fd")
        assert evidence(repo) == before
        assert stash_sha(repo) == top


def smoke_pop_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-pop-") as tmp:
        repo = make_repo(Path(tmp))

        # Keep one older entry underneath the stash being popped.
        (repo / "old.txt").write_text("older\n", encoding="utf-8")
        git(repo, "stash", "push", "-u", "-m", "older")
        previous = stash_sha(repo)

        popped = make_top_stash(repo)
        before = evidence(repo)
        assert popped != previous

        result = git(repo, "stash", "pop", "--index", "stash@{0}", check=False)
        assert result.returncode == 0, result.stderr.decode()
        assert stash_sha(repo) == previous
        after = evidence(repo)
        assert after != before

        # Undo pop: clear applied content then put the exact stash object back.
        git(repo, "reset", "--hard", "HEAD")
        git(repo, "clean", "-fd")
        restore_stash_object(repo, popped)

        assert evidence(repo) == before
        assert stash_sha(repo) == popped


def smoke_drop_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-drop-") as tmp:
        repo = make_repo(Path(tmp))
        dropped = make_top_stash(repo)
        before = evidence(repo)

        git(repo, "stash", "drop", "stash@{0}")
        assert stash_sha(repo) != dropped
        assert evidence(repo) == before

        restore_stash_object(repo, dropped)
        assert stash_sha(repo) == dropped
        assert evidence(repo) == before


def smoke_non_top_is_not_exact():
    with tempfile.TemporaryDirectory(prefix="pa-stash-nontop-") as tmp:
        repo = make_repo(Path(tmp))
        first = make_top_stash(repo)

        (repo / "tracked.txt").write_text(
            "second stash tracked payload\n",
            encoding="utf-8",
        )
        git(repo, "add", "tracked.txt")
        (repo / "second-extra.txt").write_text(
            "second stash untracked payload\n",
            encoding="utf-8",
        )
        git(repo, "stash", "push", "-u", "-m", "second top")
        second = stash_sha(repo)
        assert first != second
        refs = (
            git(repo, "stash", "list", "--format=%gd")
            .stdout.decode()
            .splitlines()
        )
        assert refs[:2] == ["stash@{0}", "stash@{1}"]
        # The implementation intentionally refuses stash@{1}: restoring its
        # original reflog position is not equivalent to restoring the top.
        assert "stash@{1}" != "stash@{0}"


smoke_apply_undo()
smoke_pop_undo()
smoke_drop_undo()
smoke_non_top_is_not_exact()

print("Git top-stash apply/pop/drop Undo contracts: PASS")
