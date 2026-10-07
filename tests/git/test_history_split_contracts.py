#!/usr/bin/env python3
"""Contracts + runtime smoke test for guarded file-group commit Split."""

from pathlib import Path
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SPLIT = "services/git/GitHistorySplitService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("FILE SPLIT REQUIRES AT LEAST TWO CHANGED FILES", "Split must reject one-file commits"),
    ("SPLIT FIRST SLICE DOES NOT SUPPORT RENAMES OR COPIES", "first file Split slice must reject rename/copy records"),
    ("SPLIT REQUIRES NON-EMPTY FILE GROUPS + TWO MESSAGES", "Split must require two non-empty groups and messages"),
    ("HISTORY BEFORE // SPLIT COMMIT", "Split must snapshot before mutation"),
    ("HISTORY AFTER // SPLIT COMMIT", "Split must snapshot after mutation"),
    ('"HISTORY/SPLIT_COMMIT"', "Split must have a dedicated journal kind"),
    ("SPLIT REHEARSAL CONFLICT OR FAILURE", "Split must rehearse before touching the live branch"),
    ('"worktree", "add", "--detach"', "Split must rehearse in a detached temporary worktree"),
    ('"reset", "--mixed", "HEAD^"', "Split must uncommit the target only in rehearsal"),
    ('"add", "-A", "--", *first_paths', "Split must stage the explicit first file group"),
    ('"add", "-A"', "Split must stage the remaining second file group"),
    ('"update-ref", ref, new_head, expected_head', "Split live ref move must use expected-old protection"),
    ('"reset", "--hard", new_head', "Split must realign the clean live worktree"),
    ("SPLIT WORKTREE REALIGN FAILED // REF ROLLED BACK", "Split must roll the ref back when realignment fails"),
):
    require(SPLIT, needle, message)

require(
    RECOVERY,
    'kind === "HISTORY/SPLIT_COMMIT"',
    "shared history rewrite Undo must recognize Split",
)
require(
    RECOVERY,
    'strategy: "RESTORE_REWRITTEN_BRANCH"',
    "Split must use guarded pre-rewrite HEAD restoration",
)


def run(args, cwd=None, env=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, env=None, check=True):
    return run(["git", "-C", str(repo), *args], env=env, check=check)


def commit_all(repo: Path, message: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def smoke_split_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-split-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()

        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        (repo / "a.txt").write_text("a0\n", encoding="utf-8")
        (repo / "b.txt").write_text("b0\n", encoding="utf-8")
        (repo / "later.txt").write_text("later0\n", encoding="utf-8")
        base = commit_all(repo, "base")

        (repo / "a.txt").write_text("a1\n", encoding="utf-8")
        (repo / "b.txt").write_text("b1\n", encoding="utf-8")
        target = commit_all(repo, "target combined")

        (repo / "later.txt").write_text("later1\n", encoding="utf-8")
        descendant = commit_all(repo, "later descendant")
        original_head = descendant
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        ordered = (
            git(repo, "rev-list", "--first-parent", "--reverse", f"{base}..{original_head}")
            .stdout.decode()
            .splitlines()
        )
        subjects = {
            sha: git(repo, "show", "-s", "--format=%s", sha).stdout.decode().strip()
            for sha in ordered
        }

        todo_lines = [
            f"{'edit' if sha == target else 'pick'} {sha} {subjects[sha]}"
            for sha in ordered
        ]

        rehearsal = root / "rehearsal"
        todo = root / "todo"
        editor = root / "sequence-editor"
        todo.write_text("\n".join(todo_lines) + "\n", encoding="utf-8")
        editor.write_text(
            '#!/bin/sh\ncp "$PA_SPLIT_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_SPLIT_TODO"] = str(todo)

        git(repo, "worktree", "add", "--detach", str(rehearsal), original_head)

        paused = git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "rebase",
            "-i",
            "--empty=keep",
            "--reapply-cherry-picks",
            base,
            env=env,
            check=False,
        )
        assert paused.returncode == 0, paused.stderr.decode()

        git(rehearsal, "reset", "--mixed", "HEAD^")
        git(rehearsal, "add", "-A", "--", "a.txt")
        git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target part 1",
        )
        git(rehearsal, "add", "-A")
        git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target part 2",
        )

        continued = git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "rebase",
            "--continue",
            env=env,
            check=False,
        )
        assert continued.returncode == 0, continued.stderr.decode()

        new_head = git(rehearsal, "rev-parse", "HEAD").stdout.decode().strip()
        messages = (
            git(rehearsal, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert messages == [
            "target part 1",
            "target part 2",
            "later descendant",
        ], messages
        assert (rehearsal / "a.txt").read_text(encoding="utf-8") == "a1\n"
        assert (rehearsal / "b.txt").read_text(encoding="utf-8") == "b1\n"
        assert (rehearsal / "later.txt").read_text(encoding="utf-8") == "later1\n"

        git(repo, "worktree", "remove", "--force", str(rehearsal))

        # Guarded live landing.
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head
        assert git(repo, "status", "--porcelain=v1").stdout == b""
        git(repo, "update-ref", "ORIG_HEAD", original_head)
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            new_head,
            original_head,
        )
        git(repo, "reset", "--hard", new_head)
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        # Shared RESTORE_REWRITTEN_BRANCH Undo.
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            original_head,
            new_head,
        )
        git(repo, "reset", "--hard", original_head)
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head
        assert git(repo, "status", "--porcelain=v1").stdout == b""


smoke_split_and_undo()

print("Git history Split contracts: PASS")
