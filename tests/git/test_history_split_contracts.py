#!/usr/bin/env python3
"""Contracts + runtime smoke test for file-based commit Split."""

from pathlib import Path
import base64
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
    ("FILE SPLIT REQUIRES AT LEAST TWO CHANGED PATHS", "Split must require multiple paths"),
    ("RENAME/COPY TARGETS ARE NOT SUPPORTED IN FILE SPLIT YET", "first slice must refuse rename/copy targets"),
    ("SPLIT REQUIRES A NON-EMPTY STRICT FILE SUBSET + TWO MESSAGES", "Split must require two non-empty file groups and messages"),
    ("HISTORY BEFORE // SPLIT COMMIT BY FILE", "Split must snapshot before mutation"),
    ("HISTORY AFTER // SPLIT COMMIT BY FILE", "Split must snapshot after mutation"),
    ('"HISTORY/SPLIT_COMMIT"', "Split must have a dedicated journal kind"),
    ('todo = ["edit {} {}".format(target, subjects[target])]', "Split must pause the target in rehearsal"),
    ('reset", "HEAD^"', "Split must uncommit the target in rehearsal"),
    ('"add", "-A", "--", *first_files', "Split must stage only the first file subset"),
    ('"add", "-A"', "Split must stage the remaining target content"),
    ("SPLIT REPLACEMENT TREE DOES NOT MATCH ORIGINAL TARGET", "replacement commits must reproduce the target tree exactly"),
    ("SPLIT FINAL TREE DOES NOT MATCH ORIGINAL HEAD", "later replay must reproduce the original final tree"),
    ('"update-ref", ref, new_head, expected_head', "Split live ref move must be expected-old guarded"),
    ("SPLIT WORKTREE REALIGN FAILED // REF ROLLED BACK", "Split landing must roll the ref back if realignment fails"),
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
    "Split must use exact pre-rewrite HEAD restoration",
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


def commit_all(repo: Path, message: str, env=None):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message, env=env)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def smoke_split_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-split-file-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        (repo / "base.txt").write_text("base\n", encoding="utf-8")
        base = commit_all(repo, "base")

        author_env = dict(os.environ)
        author_env["GIT_AUTHOR_NAME"] = "Original Author"
        author_env["GIT_AUTHOR_EMAIL"] = "author@example.invalid"
        author_env["GIT_AUTHOR_DATE"] = "2024-01-02T03:04:05+00:00"

        (repo / "a.txt").write_text("A\n", encoding="utf-8")
        (repo / "b.txt").write_text("B\n", encoding="utf-8")
        target = commit_all(repo, "Target combined", env=author_env)

        (repo / "later.txt").write_text("later\n", encoding="utf-8")
        original_head = commit_all(repo, "Later C")
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        rehearsal = root / "rehearsal"
        todo = root / "todo"
        editor = root / "sequence-editor"
        todo.write_text(
            f"edit {target} Target combined\n"
            f"pick {original_head} Later C\n",
            encoding="utf-8",
        )
        editor.write_text(
            '#!/bin/sh\ncp "$PA_SPLIT_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        git(repo, "worktree", "add", "--detach", str(rehearsal), original_head)
        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_SPLIT_TODO"] = str(todo)

        start = git(
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

        gd_raw = git(rehearsal, "rev-parse", "--git-dir").stdout.decode().strip()
        gd = Path(gd_raw) if os.path.isabs(gd_raw) else rehearsal / gd_raw
        assert (gd / "rebase-merge").is_dir() or (gd / "rebase-apply").is_dir(), (
            start.stdout.decode(),
            start.stderr.decode(),
        )

        git(rehearsal, "reset", "HEAD^")
        git(rehearsal, "add", "-A", "--", "a.txt")

        first_env = dict(os.environ)
        first_env["GIT_AUTHOR_NAME"] = "Original Author"
        first_env["GIT_AUTHOR_EMAIL"] = "author@example.invalid"
        first_env["GIT_AUTHOR_DATE"] = "2024-01-02T03:04:05+00:00"
        git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "Target part A",
            env=first_env,
        )

        git(rehearsal, "add", "-A")
        git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "Target part B",
            env=first_env,
        )

        assert git(
            rehearsal,
            "diff",
            "--quiet",
            target,
            "HEAD",
            check=False,
        ).returncode == 0

        continue_env = dict(os.environ)
        continue_env["GIT_EDITOR"] = ":"
        continued = git(
            rehearsal,
            "rebase",
            "--continue",
            env=continue_env,
            check=False,
        )
        assert continued.returncode == 0, continued.stderr.decode()

        new_head = git(rehearsal, "rev-parse", "HEAD").stdout.decode().strip()
        assert git(
            rehearsal,
            "diff",
            "--quiet",
            original_head,
            new_head,
            check=False,
        ).returncode == 0

        subjects = (
            git(rehearsal, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert subjects == ["Target part A", "Target part B", "Later C"], subjects

        authors = (
            git(
                rehearsal,
                "log",
                "--reverse",
                "--format=%an%x09%ae",
                f"{base}..HEAD",
            )
            .stdout.decode()
            .splitlines()
        )
        assert authors[0] == "Original Author\tauthor@example.invalid", authors
        assert authors[1] == "Original Author\tauthor@example.invalid", authors

        git(repo, "worktree", "remove", "--force", str(rehearsal))
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        # Guarded live landing.
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

        # Shared guarded history-rewrite Undo.
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            original_head,
            new_head,
        )
        git(repo, "reset", "--hard", original_head)

        restored = (
            git(repo, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert restored == ["Target combined", "Later C"], restored
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head


smoke_split_and_undo()

print("Git file Split contracts: PASS")
