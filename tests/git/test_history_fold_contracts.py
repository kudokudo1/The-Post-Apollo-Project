#!/usr/bin/env python3
"""Contracts + runtime smoke test for guarded history Fold."""

from pathlib import Path
import base64
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FOLD = "services/git/GitHistoryFoldService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("FOLD REQUIRES AT LEAST TWO COMMITS", "Fold must reject a one-commit range"),
    ("REWRITE RANGE CONTAINS MERGE COMMITS", "Fold must not silently flatten merges"),
    ("FOLD RANGE IS NOT CONTIGUOUS ON CURRENT FIRST-PARENT CHAIN", "Fold must require a contiguous range"),
    ("HISTORY BEFORE // FOLD COMMITS", "Fold must snapshot before mutation"),
    ("HISTORY AFTER // FOLD COMMITS", "Fold must snapshot after mutation"),
    ('"HISTORY/FOLD_COMMITS"', "Fold must have a dedicated journal kind"),
    ("FOLD REHEARSAL CONFLICT OR FAILURE", "Fold must rehearse before touching the live branch"),
    ('"worktree", "add", "--detach"', "Fold must rehearse in a detached temporary worktree"),
    ('"update-ref", ref, new_head, expected_head', "Fold live ref move must use expected-old protection"),
    ('"reset", "--hard", new_head', "Fold must realign the clean live worktree"),
    ("FOLD WORKTREE REALIGN FAILED // REF ROLLED BACK", "Fold must roll the ref back when realignment fails"),
):
    require(FOLD, needle, message)

for kind in (
    "HISTORY/INTERACTIVE_REBASE",
    "HISTORY/INTERACTIVE_REBASE_SESSION",
    "HISTORY/FOLD_COMMITS",
):
    require(
        RECOVERY,
        f'kind === "{kind}"',
        f"shared history rewrite Undo must recognize {kind}",
    )

require(
    RECOVERY,
    'strategy: "RESTORE_REWRITTEN_BRANCH"',
    "history rewrites must use guarded pre-rewrite HEAD restoration",
)
require(
    RECOVERY,
    "HISTORY REWRITE REF TRANSITION IS NOT EXACT",
    "rewrite Undo must refuse an inexact ref transition",
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


def commit_file(repo: Path, path: str, text: str, message: str):
    (repo / path).write_text(text, encoding="utf-8")
    git(repo, "add", path)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def smoke_fold_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-fold-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        base = commit_file(repo, "base.txt", "base\n", "base")
        a = commit_file(repo, "a.txt", "A\n", "A")
        b = commit_file(repo, "b.txt", "B\n", "B")
        c = commit_file(repo, "c.txt", "C\n", "C")
        d = commit_file(repo, "d.txt", "D\n", "D")
        original_head = d
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        ordered = (
            git(repo, "rev-list", "--first-parent", "--reverse", f"{base}..{original_head}")
            .stdout.decode()
            .splitlines()
        )
        start_index = ordered.index(a)
        end_index = ordered.index(c)
        message = "A through C folded"
        payload = base64.b64encode(message.encode()).decode()

        subjects = {
            sha: git(repo, "show", "-s", "--format=%s", sha).stdout.decode().strip()
            for sha in ordered
        }
        todo_lines = []
        for index, sha in enumerate(ordered):
            action = "fixup" if start_index < index <= end_index else "pick"
            todo_lines.append(f"{action} {sha} {subjects[sha]}")
            if index == end_index:
                todo_lines.append(
                    "exec sh -c 'printf %s "
                    + payload
                    + " | base64 -d | git commit --amend --no-verify -F -'"
                )

        rehearsal = root / "rehearsal"
        todo = root / "todo"
        editor = root / "sequence-editor"
        todo.write_text("\n".join(todo_lines) + "\n", encoding="utf-8")
        editor.write_text(
            '#!/bin/sh\ncp "$PA_FOLD_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        git(repo, "worktree", "add", "--detach", str(rehearsal), original_head)
        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_FOLD_TODO"] = str(todo)

        result = git(
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
        assert result.returncode == 0, result.stderr.decode()

        new_head = git(rehearsal, "rev-parse", "HEAD").stdout.decode().strip()
        subjects_after = (
            git(rehearsal, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert subjects_after == [message, "D"], subjects_after
        for name in ("a.txt", "b.txt", "c.txt", "d.txt"):
            assert (rehearsal / name).exists(), name

        git(repo, "worktree", "remove", "--force", str(rehearsal))
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        # Same guarded landing used by the Fold service.
        git(repo, "update-ref", "ORIG_HEAD", original_head)
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            new_head,
            original_head,
        )
        git(repo, "reset", "--hard", new_head)
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == new_head
        assert git(repo, "status", "--porcelain=v1").stdout == b""

        # Same guarded rewrite Undo strategy used by OPERATIONS.
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            original_head,
            new_head,
        )
        git(repo, "reset", "--hard", original_head)
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head
        restored = (
            git(repo, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert restored == ["A", "B", "C", "D"], restored


smoke_fold_and_undo()

print("Git history Fold contracts: PASS")
