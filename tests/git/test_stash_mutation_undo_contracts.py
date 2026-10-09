#!/usr/bin/env python3
"""Contracts + runtime smoke tests for selected-stash apply/pop/drop Undo."""

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
    ("stashEntries: stashEntries", "repository snapshots must persist the ordered stash stack"),
    ("untrackedContentHash: untrackedContentHash", "repository snapshots must persist untracked-content identity"),
):
    require(SNAPSHOT, needle, message)

for needle, message in (
    ("function stashEntry(snapshot, refName)", "Changes must resolve the selected stash ref"),
    ("function stashStackAfterRemoving(before, refName)", "Changes must model removal at an arbitrary stack position"),
    ("function stashApplySnapshotCanRecover(before, after, refName)", "apply classification must be selected-ref aware"),
    ("function stashPopSnapshotCanRecover(before, after, refName)", "pop classification must be selected-ref aware"),
    ("function stashDropSnapshotCanRecover(before, after, refName)", "drop classification must be selected-ref aware"),
    ("untrackedContentHash", "stash mutation evidence must include untracked file content"),
):
    require(CHANGES, needle, message)

for needle, message in (
    ('strategy = "UNDO_STASH_APPLY_REF"', "new apply records need selected-ref recovery"),
    ('strategy = "UNDO_STASH_POP_REF"', "new pop records need selected-ref recovery"),
    ('strategy = "UNDO_STASH_DROP_REF"', "new drop records need selected-ref recovery"),
    ("OLDER JOURNAL RECORD LACKS SELECTED-STASH STACK EVIDENCE", "legacy non-top records must remain conservative"),
    ("rebuild_stash_stack()", "recovery must own exact stack reconstruction"),
    ('rebuild_stash_stack "$repo" "$before_stack"', "pop/drop Undo must reconstruct the recorded object order"),
    ("UNTRACKED CONTENT CHANGED SINCE STASH MUTATION", "stash Undo must refuse untracked-content drift"),
    ('strategy.indexOf("UNDO_STASH_") !== 0', "stash strategies must bypass only the generic clean-state gate"),
    ("STASH MUTATION UNDO EVIDENCE MISMATCH // POST-STATE RESTORED", "failed verification must roll back to the recorded post-state"),
    ("UNDO_STASH_POP_TOP", "legacy top-pop journal records must remain supported"),
    ("UNDO_STASH_DROP_TOP", "legacy top-drop journal records must remain supported"),
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


def stack(repo: Path):
    raw = git(repo, "stash", "list", "--format=%H").stdout.decode()
    return [line for line in raw.splitlines() if line]


def rebuild_stack(repo: Path, shas):
    git(repo, "update-ref", "-d", "refs/stash", check=False)
    for sha in reversed(shas):
        subject = git(repo, "log", "-1", "--format=%s", sha).stdout.decode().strip()
        result = git(repo, "stash", "store", "-m", subject, sha, check=False)
        assert result.returncode == 0, result.stderr.decode()


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


def make_stash(repo: Path, label: str, payload: str):
    (repo / "tracked.txt").write_text(payload + "\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    (repo / f"{label}.txt").write_text(
        f"{label} untracked\n",
        encoding="utf-8",
    )
    git(repo, "stash", "push", "-u", "-m", label)
    result = stack(repo)
    assert result
    assert git(repo, "status", "--porcelain=v1").stdout == b""
    return result[0]


def make_three_stashes(repo: Path):
    first = make_stash(repo, "one", "one")
    second = make_stash(repo, "two", "two")
    third = make_stash(repo, "three", "three")
    assert stack(repo) == [third, second, first]
    return third, second, first


def smoke_non_top_apply_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-apply-ref-") as tmp:
        repo = make_repo(Path(tmp))
        _top, selected, _bottom = make_three_stashes(repo)
        before_stack = stack(repo)

        result = git(repo, "stash", "apply", "--index", "stash@{1}", check=False)
        assert result.returncode == 0, result.stderr.decode()
        assert stack(repo) == before_stack
        assert (repo / "two.txt").exists()

        # Selected-stash apply Undo returns to the clean pre-apply state while
        # leaving the entire stack object order unchanged.
        git(repo, "reset", "--hard", "HEAD")
        git(repo, "clean", "-fd")
        assert git(repo, "status", "--porcelain=v1").stdout == b""
        assert stack(repo) == before_stack
        assert selected == before_stack[1]


def smoke_non_top_pop_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-pop-ref-") as tmp:
        repo = make_repo(Path(tmp))
        top, selected, bottom = make_three_stashes(repo)
        before_stack = stack(repo)

        result = git(repo, "stash", "pop", "--index", "stash@{1}", check=False)
        assert result.returncode == 0, result.stderr.decode()
        assert stack(repo) == [top, bottom]
        assert (repo / "two.txt").exists()

        git(repo, "reset", "--hard", "HEAD")
        git(repo, "clean", "-fd")
        rebuild_stack(repo, before_stack)

        assert git(repo, "status", "--porcelain=v1").stdout == b""
        assert stack(repo) == before_stack
        assert selected == before_stack[1]


def smoke_non_top_drop_undo():
    with tempfile.TemporaryDirectory(prefix="pa-stash-drop-ref-") as tmp:
        repo = make_repo(Path(tmp))
        top, selected, bottom = make_three_stashes(repo)
        before_stack = stack(repo)

        git(repo, "stash", "drop", "stash@{1}")
        assert stack(repo) == [top, bottom]
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        rebuild_stack(repo, before_stack)
        assert stack(repo) == before_stack
        assert selected == before_stack[1]


def smoke_stack_rebuild_requires_objects():
    with tempfile.TemporaryDirectory(prefix="pa-stash-stack-objects-") as tmp:
        repo = make_repo(Path(tmp))
        make_three_stashes(repo)
        before_stack = stack(repo)
        for sha in before_stack:
            assert git(
                repo,
                "cat-file",
                "-e",
                f"{sha}^{{commit}}",
                check=False,
            ).returncode == 0
        rebuild_stack(repo, before_stack)
        assert stack(repo) == before_stack


smoke_non_top_apply_undo()
smoke_non_top_pop_undo()
smoke_non_top_drop_undo()
smoke_stack_rebuild_requires_objects()

print("Git selected-stash apply/pop/drop Undo contracts: PASS")
