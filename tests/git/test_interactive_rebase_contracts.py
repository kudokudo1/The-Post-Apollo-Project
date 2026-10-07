#!/usr/bin/env python3
"""Contracts + runtime smoke test for rehearsed interactive rebase."""

from pathlib import Path
import base64
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitInteractiveRebaseService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for action in ("pick", "reword", "squash", "fixup", "drop"):
    require(
        SERVICE,
        f'"{action}"',
        f"interactive rebase must support {action}",
    )

require(
    SERVICE,
    "function moveEntry(fromIndex, toIndex)",
    "interactive rebase must expose plan reordering",
)
require(
    SERVICE,
    "REWORD REQUIRES A NEW MESSAGE",
    "reword must require an explicit replacement message",
)
require(
    SERVICE,
    "FIRST KEPT COMMIT CANNOT SQUASH OR FIXUP",
    "invalid first squash/fixup plans must be refused",
)
require(
    SERVICE,
    "RANGE CONTAINS MERGE COMMITS // MERGE-PRESERVING REBASE NOT IMPLEMENTED",
    "first slice must refuse merge-containing ranges rather than flatten silently",
)
require(
    SERVICE,
    '"worktree", "add", "--detach"',
    "rewrite must rehearse in a temporary detached worktree",
)
require(
    SERVICE,
    '"rebase", "-i", "--empty=keep", "--reapply-cherry-picks"',
    "rehearsal must use deterministic interactive rebase semantics",
)
require(
    SERVICE,
    "REHEARSAL CONFLICT OR FAILURE",
    "rehearsal failures must refuse the live rewrite",
)
require(
    SERVICE,
    '"update-ref", ref, new_head, expected_head',
    "live branch movement must use expected-old guarded update-ref",
)
require(
    SERVICE,
    '"reset", "--hard", new_head',
    "clean live worktree must be realigned to the rehearsed head",
)
require(
    SERVICE,
    "WORKTREE REALIGN FAILED // REF ROLLED BACK",
    "failed worktree realignment must roll the branch ref back",
)
require(
    SERVICE,
    '"HISTORY/INTERACTIVE_REBASE"',
    "interactive rebase must have its own journal kind",
)
require(
    SERVICE,
    "HISTORY BEFORE // INTERACTIVE REBASE",
    "interactive rebase must snapshot BEFORE execution",
)
require(
    SERVICE,
    "HISTORY AFTER // INTERACTIVE REBASE",
    "interactive rebase must snapshot AFTER execution",
)
require(
    SERVICE,
    '!== "REF_RECOVERABLE"',
    "interactive rebase must require a clean ref-recoverable BEFORE state",
)

require(
    RECOVERY,
    'kind === "HISTORY/INTERACTIVE_REBASE"',
    "operation recovery must recognize interactive rebase",
)
require(
    RECOVERY,
    'strategy: "RESTORE_REWRITTEN_BRANCH"',
    "interactive rebase must expose guarded branch-head restoration",
)
require(
    RECOVERY,
    "REWRITTEN BRANCH MOVED SINCE OPERATION",
    "rebase Undo must refuse stale rewritten refs",
)
require(
    RECOVERY,
    "PRE-REWRITE COMMIT MISSING",
    "rebase Undo must verify the original commit still exists",
)
require(
    RECOVERY,
    "REWRITE WORKTREE REALIGN FAILED // REF ROLLED BACK",
    "rebase Undo must roll ref restoration back if worktree alignment fails",
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


def commit_file(repo: Path, name: str, content: str, message: str):
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def runtime_smoke():
    with tempfile.TemporaryDirectory(prefix="pa-rebase-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        base = commit_file(repo, "base.txt", "base\n", "base")
        a = commit_file(repo, "a.txt", "a\n", "A")
        b = commit_file(repo, "b.txt", "b\n", "B")
        c = commit_file(repo, "c.txt", "c\n", "C")
        d = commit_file(repo, "d.txt", "d\n", "D")
        original_head = d
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        rehearsal_root = root / "rehearsal"
        worktree = rehearsal_root / "worktree"
        rehearsal_root.mkdir()
        git(repo, "worktree", "add", "--detach", str(worktree), original_head)

        message = "A rewritten"
        payload = base64.b64encode(message.encode()).decode()
        todo = rehearsal_root / "todo"
        todo.write_text(
            "\n".join(
                [
                    f"pick {b} B",
                    f"pick {a} A",
                    (
                        "exec sh -c 'printf %s "
                        + payload
                        + " | base64 -d | "
                        + "git commit --amend --no-verify -F -'"
                    ),
                    f"fixup {c} C",
                    f"drop {d} D",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        editor = rehearsal_root / "sequence-editor"
        editor.write_text(
            '#!/bin/sh\ncp "$PA_REBASE_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_REBASE_TODO"] = str(todo)

        result = git(
            worktree,
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

        new_head = git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
        subjects = (
            git(worktree, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert subjects == ["B", "A rewritten"], subjects

        git(repo, "worktree", "remove", "--force", str(worktree))

        # Same guarded live landing used by the service.
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
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == new_head

        # Guarded Undo strategy: exact rewritten head -> original head.
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
        restored = (
            git(repo, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert restored == ["A", "B", "C", "D"], restored


runtime_smoke()

print("Git interactive rebase contracts: PASS")
