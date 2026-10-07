#!/usr/bin/env python3
"""Contracts + runtime smoke test for guarded hunk-level commit Split."""

from pathlib import Path
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitHistorySplitPatchService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("HUNK SPLIT DOES NOT SUPPORT BINARY PATHS", "hunk Split must refuse binary paths"),
    ("HUNK SPLIT DOES NOT SUPPORT RENAMES OR COPIES", "hunk Split must refuse rename/copy records"),
    ("SELECTED HUNKS WOULD LEAVE EMPTY PART 2", "hunk Split must preserve a non-empty remainder"),
    ("HISTORY BEFORE // SPLIT COMMIT HUNKS", "hunk Split must snapshot before"),
    ("HISTORY AFTER // SPLIT COMMIT HUNKS", "hunk Split must snapshot after"),
    ('"HISTORY/SPLIT_COMMIT_HUNK"', "hunk Split must have a dedicated journal kind"),
    ('"edit" if sha == target else "pick"', "rehearsal must pause only at the target commit"),
    ('"reset", "--mixed", "HEAD^"', "rehearsal must uncommit target content"),
    ('"apply", "--cached"', "selected historical hunks must stage into part 1"),
    ("HUNK SPLIT PART 2 IS EMPTY", "remainder must be revalidated in rehearsal"),
    ("HUNK SPLIT REHEARSAL CONFLICT OR FAILURE", "descendant replay must finish in rehearsal"),
    ('"update-ref", ref, new_head, expected_head', "live branch move must be expected-old guarded"),
    ("HUNK SPLIT REALIGN FAILED // REF ROLLED BACK", "failed live realignment must roll ref back"),
):
    require(SERVICE, needle, message)

require(
    RECOVERY,
    'kind === "HISTORY/SPLIT_COMMIT_HUNK"',
    "shared history rewrite Undo must recognize hunk Split",
)


def run(args, cwd=None, env=None, input_bytes=None, check=True):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(repo: Path, *args: str, env=None, input_bytes=None, check=True):
    return run(
        ["git", "-C", str(repo), *args],
        env=env,
        input_bytes=input_bytes,
        check=check,
    )


def commit_all(repo: Path, message: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def extract_hunks(repo: Path, base: str, target: str, path: str):
    raw = git(
        repo,
        "diff",
        "--no-ext-diff",
        "--binary",
        base,
        target,
        "--",
        path,
    ).stdout.decode("utf-8", "surrogateescape").splitlines(True)
    header, groups, current = [], [], None
    for line in raw:
        if line.startswith("@@"):
            if current is not None:
                groups.append(current)
            current = [line]
        elif current is None:
            header.append(line)
        else:
            current.append(line)
    if current is not None:
        groups.append(current)
    return header, groups


def smoke_hunk_split_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-hunk-split-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        story = repo / "story.txt"
        base_lines = [f"line {i:02d}\n" for i in range(1, 31)]
        story.write_text("".join(base_lines), encoding="utf-8")
        (repo / "later.txt").write_text("later0\n", encoding="utf-8")
        base = commit_all(repo, "base")

        target_lines = list(base_lines)
        target_lines[1] = "line 02 // first hunk\n"
        target_lines[26] = "line 27 // second hunk\n"
        story.write_text("".join(target_lines), encoding="utf-8")
        target = commit_all(repo, "target two hunks")

        (repo / "later.txt").write_text("later1\n", encoding="utf-8")
        original_head = commit_all(repo, "later descendant")
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        header, groups = extract_hunks(repo, base, target, "story.txt")
        assert len(groups) == 2, len(groups)
        patch = "".join(header + groups[0]).encode("utf-8", "surrogateescape")

        ordered = (
            git(repo, "rev-list", "--first-parent", "--reverse", f"{base}..{original_head}")
            .stdout.decode()
            .splitlines()
        )
        subjects = {
            sha: git(repo, "show", "-s", "--format=%s", sha).stdout.decode().strip()
            for sha in ordered
        }
        todo = root / "todo"
        editor = root / "sequence-editor"
        todo.write_text(
            "\n".join(
                f"{'edit' if sha == target else 'pick'} {sha} {subjects[sha]}"
                for sha in ordered
            )
            + "\n",
            encoding="utf-8",
        )
        editor.write_text(
            '#!/bin/sh\ncp "$PA_SPLIT_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_SPLIT_TODO"] = str(todo)

        wt = root / "rehearsal"
        git(repo, "worktree", "add", "--detach", str(wt), original_head)
        paused = git(
            wt,
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

        git(wt, "reset", "--mixed", "HEAD^")
        applied = git(
            wt,
            "apply",
            "--cached",
            "--binary",
            "--whitespace=nowarn",
            "-",
            input_bytes=patch,
            check=False,
        )
        assert applied.returncode == 0, applied.stderr.decode()
        git(
            wt,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target part 1",
        )
        git(wt, "add", "-A")
        git(
            wt,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target part 2",
        )
        continued = git(
            wt,
            "-c",
            "commit.gpgSign=false",
            "rebase",
            "--continue",
            env=env,
            check=False,
        )
        assert continued.returncode == 0, continued.stderr.decode()

        new_head = git(wt, "rev-parse", "HEAD").stdout.decode().strip()
        rewritten = (
            git(wt, "rev-list", "--reverse", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        messages = [
            git(wt, "show", "-s", "--format=%s", sha).stdout.decode().strip()
            for sha in rewritten
        ]
        assert messages == [
            "target part 1",
            "target part 2",
            "later descendant",
        ], messages

        part1_text = git(
            wt,
            "show",
            f"{rewritten[0]}:story.txt",
        ).stdout.decode()
        assert "line 02 // first hunk" in part1_text
        assert "line 27 // second hunk" not in part1_text

        part2_text = git(
            wt,
            "show",
            f"{rewritten[1]}:story.txt",
        ).stdout.decode()
        assert "line 02 // first hunk" in part2_text
        assert "line 27 // second hunk" in part2_text

        git(repo, "worktree", "remove", "--force", str(wt))

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

        # Shared history-rewrite Undo.
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


smoke_hunk_split_and_undo()

print("Git history hunk Split contracts: PASS")
