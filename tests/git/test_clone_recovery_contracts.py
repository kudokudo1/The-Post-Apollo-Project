#!/usr/bin/env python3
"""Contracts + runtime smoke tests for exact Clone journal recovery."""

from pathlib import Path
import hashlib
import os
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GIT_SERVICE = "services/git/GitService.qml"
JOURNAL = "services/git/GitOperationJournalService.qml"
RECOVERY = "services/git/GitOperationRecoveryService.qml"
GITW = "widgets/GitW.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ('"track-checkout",\n            "clone"', "CONTROL clone must enter the journaled action family"),
    ("readonly property string cloneDestinationPath", "clone must have a stable pre-creation journal key"),
    ("function cloneBoundaryBeforeSnapshot()", "clone must record synthetic pre-creation evidence"),
    ("function cloneBoundaryAfterSnapshot()", "clone must record synthetic post-creation evidence"),
    ('"CONTROL/CLONE"', "clone must use an explicit operation kind"),
    ('"EXTERNAL_RECOVERABLE"', "clone must use an external recovery class"),
    ('"__PA_CLONE_META__', "clone must return exact created-checkout evidence"),
    ("fingerprint_tree()", "clone must fingerprint the created directory"),
    ("pendingCloneCreated", "clone must distinguish newly-created from already-local"),
):
    require(GIT_SERVICE, needle, message)

for needle, message in (
    ('beforeClass === "EXTERNAL_RECOVERABLE"', "journal must preserve external recovery"),
    ('afterClass === "EXTERNAL_RECOVERABLE"', "journal completion must require matching external evidence"),
):
    require(JOURNAL, needle, message)

for needle, message in (
    ("function cloneRecoveryPlan(record)", "recovery must plan Clone Undo explicitly"),
    ('String(row.kind || "") !== "CONTROL/CLONE"', "Clone Undo must only match clone records"),
    ('strategy: "DELETE_EXACT_CLONE"', "Clone Undo needs a dedicated strategy"),
    ("CLONE DOES NOT HAVE EXACT EXTERNAL RECOVERY EVIDENCE", "incomplete clone evidence must refuse Undo"),
    ("CLONE DESTINATION IS OUTSIDE PROJECTS ROOT", "Clone Undo must be path-confined"),
    ("CLONE HEAD CHANGED SINCE CREATION", "Clone Undo must revalidate HEAD"),
    ("CLONE BRANCH CHANGED SINCE CREATION", "Clone Undo must revalidate branch"),
    ("CLONE ORIGIN CHANGED SINCE CREATION", "Clone Undo must revalidate origin"),
    ("CLONE HAS ADDITIONAL WORKTREES", "Clone Undo must refuse expanded worktree topology"),
    ("CLONE DIRECTORY CHANGED SINCE CREATION", "Clone Undo must revalidate the full directory fingerprint"),
    ("UNDID CLONE // EXACT CREATED REPOSITORY REMOVED", "Clone Undo must report exact deletion"),
    ('externalBoundary: "CLONE_UNDO"', "successful Clone Undo needs a synthetic post-delete state"),
    ("destinationPresent: false", "post-delete evidence must state the destination is absent"),
):
    require(RECOVERY, needle, message)

for needle, message in (
    (": gitService.cloneDestinationPath", "remote-only Clone journal must be keyed to the future local path"),
    ('String(record.kind || "") !== "CONTROL/CLONE"', "host refresh must be scoped to Clone Undo"),
    ("gitService.discoverRepos()", "successful Clone Undo must rediscover repositories"),
):
    require(GITW, needle, message)


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


def fingerprint_tree(root: Path) -> str:
    root = Path(os.path.realpath(root))
    digest = hashlib.sha256()

    for dirpath, dirnames, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        dirnames.sort()
        filenames.sort()

        for name in list(dirnames) + list(filenames):
            path = Path(dirpath) / name
            rel = os.path.relpath(path, root)
            st = os.lstat(path)
            digest.update(rel.encode("utf-8", "surrogateescape") + b"\0")
            digest.update(
                str(stat.S_IFMT(st.st_mode)).encode()
                + b":"
                + str(stat.S_IMODE(st.st_mode)).encode()
                + b"\0"
            )

            if stat.S_ISLNK(st.st_mode):
                digest.update(
                    os.readlink(path).encode("utf-8", "surrogateescape")
                )
            elif stat.S_ISREG(st.st_mode):
                with open(path, "rb") as handle:
                    while True:
                        chunk = handle.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)

            digest.update(b"\0")

    return digest.hexdigest()


def make_origin(root: Path) -> Path:
    origin = root / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    git(origin, "config", "user.name", "Post Apollo Test")
    git(origin, "config", "user.email", "test@example.invalid")
    (origin / ".gitignore").write_text("ignored.tmp\n", encoding="utf-8")
    (origin / "sample.txt").write_text("base\n", encoding="utf-8")
    git(origin, "add", ".gitignore", "sample.txt")
    git(origin, "commit", "-qm", "base")
    return origin


def clone_into(origin: Path, destination: Path):
    run(["git", "clone", "-q", "--no-local", str(origin), str(destination)])
    assert git(destination, "rev-parse", "--is-inside-work-tree").stdout.strip() == b"true"


def exercise_snapshot_like_reads(repo: Path):
    git(repo, "branch", "--show-current")
    git(repo, "rev-parse", "HEAD")
    git(repo, "symbolic-ref", "-q", "HEAD", check=False)
    git(repo, "for-each-ref", "--format=%(refname)%09%(objectname)", "refs/heads", "refs/remotes")
    git(repo, "write-tree")
    git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    git(repo, "diff", "--cached", "--binary")
    git(repo, "diff", "--binary")
    git(repo, "worktree", "list", "--porcelain")


def smoke_pristine_clone_identity_and_delete():
    with tempfile.TemporaryDirectory(prefix="pa-clone-recovery-") as tmp:
        root = Path(tmp)
        projects = root / "Projects"
        projects.mkdir()
        origin = make_origin(root)
        destination = projects / "sample"
        clone_into(origin, destination)

        expected_head = git(destination, "rev-parse", "HEAD").stdout.decode().strip()
        expected_branch = git(destination, "branch", "--show-current").stdout.decode().strip()
        expected_origin = git(destination, "remote", "get-url", "origin").stdout.decode().strip()
        expected_fingerprint = fingerprint_tree(destination)

        exercise_snapshot_like_reads(destination)

        assert git(destination, "rev-parse", "HEAD").stdout.decode().strip() == expected_head
        assert git(destination, "branch", "--show-current").stdout.decode().strip() == expected_branch
        assert git(destination, "remote", "get-url", "origin").stdout.decode().strip() == expected_origin
        assert fingerprint_tree(destination) == expected_fingerprint

        shutil.rmtree(destination)
        assert not destination.exists()


def smoke_ignored_content_blocks_exact_delete():
    with tempfile.TemporaryDirectory(prefix="pa-clone-drift-") as tmp:
        root = Path(tmp)
        projects = root / "Projects"
        projects.mkdir()
        origin = make_origin(root)
        destination = projects / "sample"
        clone_into(origin, destination)

        expected_fingerprint = fingerprint_tree(destination)
        (destination / "ignored.tmp").write_text(
            "local generated content\n",
            encoding="utf-8",
        )

        # Git status intentionally stays clean, proving the filesystem
        # fingerprint catches content that ordinary dirty checks cannot.
        assert git(
            destination,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout == b""
        assert fingerprint_tree(destination) != expected_fingerprint


smoke_pristine_clone_identity_and_delete()
smoke_ignored_content_blocks_exact_delete()

print("Git exact Clone journal/recovery contracts: PASS")
