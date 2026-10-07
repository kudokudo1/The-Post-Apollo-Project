#!/usr/bin/env python3
"""Contracts + runtime smoke test for guarded line-level commit Split."""

from pathlib import Path
import difflib
import os
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitHistorySplitLineService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("LINE SPLIT REQUIRES AN EXISTING MODIFIED PATH", "line Split must refuse add/delete/rename semantics"),
    ("LINE SPLIT DOES NOT SUPPORT BINARY PATHS", "line Split must refuse binary paths"),
    ("LINE SPLIT DOES NOT SUPPORT MODE OR TYPE CHANGES", "line Split must preserve simple text-file semantics"),
    ("SELECTED LINES WOULD LEAVE EMPTY PART 2", "line Split must preserve a non-empty remainder"),
    ("HISTORY BEFORE // SPLIT COMMIT LINES", "line Split must snapshot before"),
    ("HISTORY AFTER // SPLIT COMMIT LINES", "line Split must snapshot after"),
    ('"HISTORY/SPLIT_COMMIT_LINE"', "line Split must have a dedicated journal kind"),
    ('autojunk=False', "line Split must use deterministic text matching"),
    ('"edit" if sha == target else "pick"', "rehearsal must pause only at the target commit"),
    ('"reset", "--mixed", "HEAD^"', "rehearsal must uncommit target content"),
    ("LINE SPLIT PART 1 IS EMPTY", "selected edits must produce a real first commit"),
    ("LINE SPLIT PART 2 IS EMPTY", "unselected edits must produce a real remainder"),
    ("LINE SPLIT REHEARSAL CONFLICT OR FAILURE", "descendant replay must finish in rehearsal"),
    ('"update-ref", ref, new_head, expected_head', "live branch move must be expected-old guarded"),
    ("LINE SPLIT REALIGN FAILED // REF ROLLED BACK", "failed live realignment must roll ref back"),
):
    require(SERVICE, needle, message)

require(
    RECOVERY,
    'kind === "HISTORY/SPLIT_COMMIT_LINE"',
    "shared history rewrite Undo must recognize line Split",
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


def selected_content(base_lines, target_lines, selected):
    matcher = difflib.SequenceMatcher(
        a=base_lines,
        b=target_lines,
        autojunk=False,
    )
    out = []
    unit = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.extend(base_lines[i1:i2])
            continue
        if tag == "replace":
            common = min(i2 - i1, j2 - j1)
            for k in range(common):
                out.append(
                    target_lines[j1 + k]
                    if unit in selected
                    else base_lines[i1 + k]
                )
                unit += 1
            for k in range(common, i2 - i1):
                if unit not in selected:
                    out.append(base_lines[i1 + k])
                unit += 1
            for k in range(common, j2 - j1):
                if unit in selected:
                    out.append(target_lines[j1 + k])
                unit += 1
        elif tag == "delete":
            for k in range(i1, i2):
                if unit not in selected:
                    out.append(base_lines[k])
                unit += 1
        elif tag == "insert":
            for k in range(j1, j2):
                if unit in selected:
                    out.append(target_lines[k])
                unit += 1
    return out, unit


def smoke_line_split_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-line-split-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        story = repo / "story.txt"
        base_lines = [f"line {i:02d}\n" for i in range(1, 13)]
        story.write_text("".join(base_lines), encoding="utf-8")
        (repo / "later.txt").write_text("later0\n", encoding="utf-8")
        base = commit_all(repo, "base")

        target_lines = list(base_lines)
        target_lines[1] = "line 02 // first selected edit\n"
        target_lines[9] = "line 10 // second remainder edit\n"
        story.write_text("".join(target_lines), encoding="utf-8")
        target = commit_all(repo, "target two line edits")

        (repo / "later.txt").write_text("later1\n", encoding="utf-8")
        original_head = commit_all(repo, "later descendant")
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        part1_lines, total = selected_content(base_lines, target_lines, {0})
        assert total == 2, total
        assert part1_lines[1] == "line 02 // first selected edit\n"
        assert part1_lines[9] == base_lines[9]

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
            '#!/bin/sh\ncp "$PA_LINE_SPLIT_TODO" "$1"\n',
            encoding="utf-8",
        )
        editor.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = str(editor)
        env["GIT_EDITOR"] = ":"
        env["PA_LINE_SPLIT_TODO"] = str(todo)

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
        wt_story = wt / "story.txt"
        wt_story.write_text("".join(part1_lines), encoding="utf-8")
        git(wt, "add", "story.txt")
        assert git(wt, "diff", "--cached", "--quiet", check=False).returncode != 0
        git(
            wt,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target line part 1",
        )

        wt_story.write_text("".join(target_lines), encoding="utf-8")
        git(wt, "add", "-A")
        assert git(wt, "diff", "--cached", "--quiet", check=False).returncode != 0
        git(
            wt,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            "-qm",
            "target line part 2",
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
            "target line part 1",
            "target line part 2",
            "later descendant",
        ], messages

        first_text = git(wt, "show", f"{rewritten[0]}:story.txt").stdout.decode()
        assert "line 02 // first selected edit" in first_text
        assert "line 10 // second remainder edit" not in first_text

        second_text = git(wt, "show", f"{rewritten[1]}:story.txt").stdout.decode()
        assert "line 02 // first selected edit" in second_text
        assert "line 10 // second remainder edit" in second_text

        new_head = git(wt, "rev-parse", "HEAD").stdout.decode().strip()
        git(repo, "worktree", "remove", "--force", str(wt))

        # Same expected-old guarded landing used by the service.
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


smoke_line_split_and_undo()

print("Git line-level history Split contracts: PASS")
