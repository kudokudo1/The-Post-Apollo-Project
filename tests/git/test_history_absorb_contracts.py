#!/usr/bin/env python3
"""Contracts + runtime smoke test for staged Absorb and content Undo."""

from pathlib import Path
import base64
import hashlib
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ABSORB = "services/git/GitHistoryAbsorbService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ("NO STAGED CHANGES TO ABSORB", "Absorb must require staged content"),
    ("UNSTAGED CHANGES PRESENT", "Absorb must refuse unstaged content"),
    ("UNTRACKED FILES PRESENT", "Absorb first slice must refuse untracked content"),
    ("CONFLICTED INDEX", "Absorb must refuse conflicted content"),
    ("STAGED PATCH EXCEEDS RECOVERY PAYLOAD LIMIT", "Absorb must bound durable recovery payload"),
    ("HISTORY BEFORE // ABSORB STAGED", "Absorb must snapshot before rewrite"),
    ("HISTORY AFTER // ABSORB STAGED", "Absorb must snapshot after rewrite"),
    ('"HISTORY/ABSORB_STAGED"', "Absorb must have a dedicated journal kind"),
    ('out.recoveryClass = "CONTENT_RECOVERABLE"', "Absorb must promote exact-patch evidence"),
    ("ABSORB REHEARSAL CONFLICT OR FAILURE", "Absorb must rehearse before live mutation"),
    ('"commit", "--no-verify", "--fixup=" + target', "Absorb rehearsal must create a targeted fixup"),
    ('"rebase", "-i", "--autosquash"', "Absorb must autosquash the fixup into the target"),
    ("STAGED PATCH CHANGED AFTER REHEARSAL", "Absorb must reverify exact live staged content"),
    ("ABSORB REALIGN FAILED // HISTORY + STAGED PATCH ROLLED BACK", "failed landing must restore history and staged content"),
):
    require(ABSORB, needle, message)

for needle, message in (
    ('kind !== "HISTORY/ABSORB_STAGED"', "recovery must recognize staged Absorb"),
    ('strategy: "UNDO_ABSORB_STAGED"', "Absorb must expose dedicated content Undo"),
    ("PRE-ABSORB STAGED PATCH NO LONGER APPLIES", "Undo must preflight the staged patch against old history"),
    ("ABSORB RECOVERY PATCH FINGERPRINT MISMATCH", "Undo must verify exact patch identity"),
    ("RESTORED PRE-ABSORB HISTORY + STAGED PATCH", "Undo must restore history and the index"),
    ("ABSORB PATCH RESTORE FAILED // HISTORY ROLLED BACK", "failed patch restoration must return to post-absorb history"),
):
    require(RECOVERY, needle, message)


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


def smoke_absorb_and_undo():
    with tempfile.TemporaryDirectory(prefix="pa-absorb-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        story = repo / "story.txt"
        story.write_text("base\n", encoding="utf-8")
        base = commit_all(repo, "base")

        story.write_text("base\ntarget line\n", encoding="utf-8")
        target = commit_all(repo, "A target")

        (repo / "later.txt").write_text("later B\n", encoding="utf-8")
        _b = commit_all(repo, "B later")

        (repo / "tail.txt").write_text("tail C\n", encoding="utf-8")
        original_head = commit_all(repo, "C tail")
        branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        # The current staged change to absorb.
        story.write_text(
            "base\ntarget line + absorbed detail\n",
            encoding="utf-8",
        )
        git(repo, "add", "story.txt")
        patch = git(repo, "diff", "--cached", "--binary", "--full-index").stdout
        assert patch
        fingerprint = hashlib.sha256(patch).hexdigest()

        # Rehearse: apply exact staged patch at HEAD, make fixup, autosquash.
        rehearsal = root / "rehearsal"
        git(repo, "worktree", "add", "--detach", str(rehearsal), original_head)

        applied = git(
            rehearsal,
            "apply",
            "--index",
            "--binary",
            "--whitespace=nowarn",
            "-",
            input_bytes=patch,
            check=False,
        )
        assert applied.returncode == 0, applied.stderr.decode()

        fixup = git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "commit",
            "--no-verify",
            f"--fixup={target}",
            check=False,
        )
        assert fixup.returncode == 0, fixup.stderr.decode()

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = ":"
        env["GIT_EDITOR"] = ":"
        rebased = git(
            rehearsal,
            "-c",
            "commit.gpgSign=false",
            "rebase",
            "-i",
            "--autosquash",
            "--empty=keep",
            "--reapply-cherry-picks",
            base,
            env=env,
            check=False,
        )
        assert rebased.returncode == 0, rebased.stderr.decode()

        new_head = git(rehearsal, "rev-parse", "HEAD").stdout.decode().strip()
        subjects = (
            git(rehearsal, "log", "--reverse", "--format=%s", f"{base}..HEAD")
            .stdout.decode()
            .splitlines()
        )
        assert subjects == ["A target", "B later", "C tail"], subjects
        assert (
            rehearsal / "story.txt"
        ).read_text(encoding="utf-8") == "base\ntarget line + absorbed detail\n"

        git(repo, "worktree", "remove", "--force", str(rehearsal))

        # Live landing clears the staged patch because it now lives in history.
        assert hashlib.sha256(
            git(repo, "diff", "--cached", "--binary", "--full-index").stdout
        ).hexdigest() == fingerprint
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

        # Undo preflight at the old head.
        preflight = root / "preflight"
        git(repo, "worktree", "add", "--detach", str(preflight), original_head)
        check = git(
            preflight,
            "apply",
            "--check",
            "--index",
            "--binary",
            "--whitespace=nowarn",
            "-",
            input_bytes=patch,
            check=False,
        )
        assert check.returncode == 0, check.stderr.decode()
        git(repo, "worktree", "remove", "--force", str(preflight))

        # Restore old history then exact staged patch.
        git(
            repo,
            "update-ref",
            f"refs/heads/{branch}",
            original_head,
            new_head,
        )
        git(repo, "reset", "--hard", original_head)
        restore = git(
            repo,
            "apply",
            "--index",
            "--binary",
            "--whitespace=nowarn",
            "-",
            input_bytes=patch,
            check=False,
        )
        assert restore.returncode == 0, restore.stderr.decode()
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == original_head
        restored_patch = git(
            repo,
            "diff",
            "--cached",
            "--binary",
            "--full-index",
        ).stdout
        assert hashlib.sha256(restored_patch).hexdigest() == fingerprint
        assert restored_patch == patch


smoke_absorb_and_undo()

print("Git staged Absorb contracts: PASS")
