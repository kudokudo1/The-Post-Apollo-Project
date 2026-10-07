#!/usr/bin/env python3
"""Contracts + runtime smoke test for the rich three-way conflict editor."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "services/git/GitConflictEditorService.qml"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


for needle, message in (
    ('"show", ":" + str(stage) + ":" + path', "editor must load Git index stages"),
    ('"stage1": entries.get(1, "")', "editor must retain BASE stage identity"),
    ('"stage2": entries.get(2, "")', "editor must retain OURS stage identity"),
    ('"stage3": entries.get(3, "")', "editor must retain THEIRS stage identity"),
    ('function takeOurs(index)', "editor must support per-block ours"),
    ('function takeTheirs(index)', "editor must support per-block theirs"),
    ('function takeBoth(index)', "editor must support per-block both"),
    ('function takeBase(index)', "editor must support per-block base"),
    ('function setResultText(value)', "editor must support manual RESULT editing"),
    ('CANNOT STAGE RESULT WHILE CONFLICT MARKERS REMAIN', "stage must refuse unresolved markers"),
    ('CONFLICT STAGES CHANGED SINCE EDITOR LOAD', "writes must reverify exact unmerged stages"),
    ('"CHANGES/CONFLICT_RESOLVE"', "staged resolutions must be journaled"),
    ('"CHANGES/CONFLICT_DRAFT"', "draft result writes must be journaled"),
    ('PATH REMAINS UNMERGED AFTER STAGE', "stage must verify index resolution"),
):
    require(SERVICE, needle, message)

# The editor intentionally resolves one path only. Continue/abort/skip of the
# enclosing Git operation remains owned by GitChangesService.
assert "rebase --continue" not in read(SERVICE)
assert "merge --continue" not in read(SERVICE)
assert "cherry-pick --continue" not in read(SERVICE)


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


def commit_all(repo: Path, message: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def parse_unmerged(repo: Path, path: str):
    raw = git(repo, "ls-files", "-u", "--", path).stdout.decode()
    entries = {}
    for line in raw.splitlines():
        left, sep, _entry_path = line.partition("\t")
        fields = left.split()
        if sep and len(fields) >= 3:
            entries[int(fields[2])] = fields[1]
    return entries


def smoke_three_way_resolution():
    with tempfile.TemporaryDirectory(prefix="pa-conflict-editor-") as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Post Apollo Test")
        git(repo, "config", "user.email", "test@example.invalid")

        story = repo / "story.txt"
        story.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        commit_all(repo, "base")
        main_branch = git(repo, "branch", "--show-current").stdout.decode().strip()

        git(repo, "switch", "-qc", "theirs")
        story.write_text("alpha\nbeta from theirs\ngamma\n", encoding="utf-8")
        commit_all(repo, "theirs edit")

        git(repo, "switch", "-q", main_branch)
        story.write_text("alpha\nbeta from ours\ngamma\n", encoding="utf-8")
        commit_all(repo, "ours edit")
        pre_merge_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()

        merge = git(repo, "merge", "theirs", check=False)
        assert merge.returncode != 0
        entries = parse_unmerged(repo, "story.txt")
        assert set(entries) == {1, 2, 3}, entries

        base = git(repo, "show", ":1:story.txt").stdout.decode()
        ours = git(repo, "show", ":2:story.txt").stdout.decode()
        theirs = git(repo, "show", ":3:story.txt").stdout.decode()
        result = story.read_text(encoding="utf-8")

        assert "beta\n" in base
        assert "beta from ours" in ours
        assert "beta from theirs" in theirs
        assert "<<<<<<<" in result and "=======" in result and ">>>>>>>" in result

        # Draft write must not clear the exact unmerged stages.
        story.write_text(result + "\n# draft note\n", encoding="utf-8")
        assert parse_unmerged(repo, "story.txt") == entries

        # Resolve and stage, then verify Git no longer reports an unmerged path.
        resolved = "alpha\nbeta from ours\nbeta from theirs\ngamma\n"
        story.write_text(resolved, encoding="utf-8")
        git(repo, "add", "--", "story.txt")
        assert parse_unmerged(repo, "story.txt") == {}
        assert git(repo, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0

        # Editor does not finish the enclosing operation. Abort still restores
        # the exact pre-merge branch state.
        git(repo, "merge", "--abort")
        assert git(repo, "rev-parse", "HEAD").stdout.decode().strip() == pre_merge_head
        assert git(repo, "status", "--porcelain=v1").stdout == b""


smoke_three_way_resolution()

print("Git three-way conflict editor backend contracts: PASS")
