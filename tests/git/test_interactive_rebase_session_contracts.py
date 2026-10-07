#!/usr/bin/env python3
"""Contracts + runtime smoke tests for persistent interactive rebase sessions."""

from pathlib import Path
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

JOURNAL = "services/git/GitOperationJournalService.qml"
PLANNER = "services/git/GitInteractiveRebaseService.qml"
SESSION = "services/git/GitInteractiveRebaseSessionService.qml"
IGNORE = ".gitignore"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


require(
    JOURNAL,
    "Boolean(metadata.durableSession)",
    "durable running operations must survive journal reload",
)
require(
    JOURNAL,
    "const durableRunning",
    "journal load must distinguish durable sessions from interrupted mutations",
)
require(
    IGNORE,
    "git-rebase-sessions.json",
    "local persistent rebase session state must not enter Git history",
)

require(
    PLANNER,
    '"edit"',
    "interactive rebase planner must support edit",
)
require(
    PLANNER,
    "function requiresPersistentSession()",
    "planner must identify edit plans as persistent sessions",
)
require(
    PLANNER,
    "EDIT REQUIRES THE PERSISTENT REBASE SESSION ENGINE",
    "one-shot engine must refuse edit plans",
)

for needle, message in (
    ("git-rebase-sessions.json", "session identity must persist across UI reloads"),
    ('durableSession: true', "persistent rebase journal record must be durable"),
    ('"HISTORY/INTERACTIVE_REBASE_SESSION"', "persistent rebase needs its own operation kind"),
    ('allowed = {"pick", "reword", "squash", "fixup", "drop", "edit"}', "session engine must support edit"),
    ('rehearsal_todo.append("pick {} {}".format(sha, subject))', "edit must rehearse as a non-pausing pick"),
    ('live_todo.append("edit {} {}".format(sha, subject))', "live plan must preserve edit"),
    ('"rebase-merge"', "session inspector must understand interactive rebase state"),
    ('"rebase-apply"', "session inspector must handle alternate rebase state"),
    ('"diff", "--name-only", "--diff-filter=U"', "session inspector must expose conflicted paths"),
    ('function continueSession()', "persistent session must continue"),
    ('function skipSession()', "persistent session must skip"),
    ('function abortSession(confirmed)', "persistent session must abort explicitly"),
    ('ABORT REQUIRES CONFIRMATION', "abort must be explicitly confirmed"),
    ('signal conflictHandoffRequested(var files)', "session must expose neutral conflict handoff"),
    ('STORED REBASE SESSION EXISTS BUT GIT HAS NO ACTIVE REBASE', "lost Git/session correspondence must be reported as uncertain"),
):
    require(SESSION, needle, message)


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


def commit(repo: Path, message: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def rebase_dir(repo: Path):
    raw = git(repo, "rev-parse", "--git-dir").stdout.decode().strip()
    gd = Path(raw) if os.path.isabs(raw) else repo / raw
    for name in ("rebase-merge", "rebase-apply"):
        candidate = gd / name
        if candidate.is_dir():
            return candidate
    return None


def start_edit_rebase(repo: Path, base: str, edit_sha: str):
    with tempfile.TemporaryDirectory(prefix="pa-session-todo-") as tmp:
        tmp_path = Path(tmp)
        todo = tmp_path / "todo"
        editor = tmp_path / "sequence-editor"
        rows = (
            git(repo, "log", "--reverse", "--format=%H%x09%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        commands = []
        for row in rows:
            sha, subject = row.split("\t", 1)
            action = "edit" if sha == edit_sha else "pick"
            commands.append(f"{action} {sha} {subject}")

        todo.write_text("\n".join(commands) + "\n", encoding="utf-8")
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
            repo,
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
        assert rebase_dir(repo) is not None, (
            result.stdout.decode(),
            result.stderr.decode(),
        )


def make_repo(root: Path):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Post Apollo Test")
    git(repo, "config", "user.email", "test@example.invalid")

    target = repo / "story.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    base = commit(repo, "base")

    target.write_text("alpha A\nbeta\ngamma\n", encoding="utf-8")
    a = commit(repo, "A")

    target.write_text("alpha A\nbeta B\ngamma\n", encoding="utf-8")
    b = commit(repo, "B")

    target.write_text("alpha A\nbeta B\ngamma C\n", encoding="utf-8")
    c = commit(repo, "C")
    return repo, base, a, b, c


def smoke_edit_continue():
    with tempfile.TemporaryDirectory(prefix="pa-rebase-edit-") as tmp:
        repo, base, a, _b, original_head = make_repo(Path(tmp))
        start_edit_rebase(repo, base, a)
        assert rebase_dir(repo) is not None

        story = repo / "story.txt"
        text = story.read_text(encoding="utf-8")
        story.write_text(text.replace("alpha A", "alpha A edited"), encoding="utf-8")
        git(repo, "add", "story.txt")
        git(repo, "commit", "--amend", "-qm", "A edited")

        env = dict(os.environ)
        env["GIT_EDITOR"] = ":"
        result = git(repo, "rebase", "--continue", env=env, check=False)
        assert result.returncode == 0, result.stderr.decode()
        assert rebase_dir(repo) is None
        assert git(repo, "status", "--porcelain=v1").stdout == b""
        new_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        assert new_head != original_head
        subjects = (
            git(repo, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert subjects == ["A edited", "B", "C"], subjects


def smoke_edit_abort():
    with tempfile.TemporaryDirectory(prefix="pa-rebase-abort-") as tmp:
        repo, base, a, _b, original_head = make_repo(Path(tmp))
        start_edit_rebase(repo, base, a)
        assert rebase_dir(repo) is not None
        git(repo, "rebase", "--abort")
        assert rebase_dir(repo) is None
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head
        assert git(repo, "status", "--porcelain=v1").stdout == b""


def smoke_conflict_handoff():
    with tempfile.TemporaryDirectory(prefix="pa-rebase-conflict-") as tmp:
        repo, base, a, _b, _c = make_repo(Path(tmp))
        start_edit_rebase(repo, base, a)
        assert rebase_dir(repo) is not None

        # Rewrite the edited commit so the later B commit cannot replay cleanly.
        story = repo / "story.txt"
        story.write_text("alpha A edited\nbeta user rewrite\ngamma\n", encoding="utf-8")
        git(repo, "add", "story.txt")
        git(repo, "commit", "--amend", "-qm", "A conflicting edit")

        env = dict(os.environ)
        env["GIT_EDITOR"] = ":"
        result = git(repo, "rebase", "--continue", env=env, check=False)
        assert result.returncode != 0
        assert rebase_dir(repo) is not None
        conflicts = (
            git(repo, "diff", "--name-only", "--diff-filter=U")
            .stdout.decode()
            .splitlines()
        )
        assert "story.txt" in conflicts, conflicts
        git(repo, "rebase", "--abort")


smoke_edit_continue()
smoke_edit_abort()
smoke_conflict_handoff()

print("Git persistent interactive rebase session contracts: PASS")
