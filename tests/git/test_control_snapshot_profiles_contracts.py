#!/usr/bin/env python3
"""Executable disposable proof for CONTROL/FETCH and CONTROL/PULL snapshots.

This extracts the actual bash payload from GitRepositorySnapshotService.qml.
It never touches a real working tree, provider, user file, or network.
"""
import ast
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "services/git/GitRepositorySnapshotService.qml").read_text()

match = re.search(
    r'snapshotProcess\.exec\(\[\s*"bash",\s*"-lc",\s*\[(.*?)'
    r'\]\.join\("\\n"\)',
    SOURCE, re.S,
)
assert match, "Snapshot subprocess Bash payload was not found"
commands = []
for raw in match.group(1).splitlines():
    token = raw.strip().removesuffix(",")
    if not token:
        continue
    assert token.startswith("'") and token.endswith("'"), token
    commands.append(ast.literal_eval(token))
script = "\n".join(commands)


def run(*argv, cwd=None):
    done = subprocess.run(
        argv, cwd=cwd, text=True, capture_output=True, timeout=20,
        check=False,
    )
    assert done.returncode == 0, (argv, done.returncode, done.stderr)
    return done.stdout


def snapshot(repo, profile):
    raw = run("bash", "-lc", script, "git-repository-snapshot", str(repo), profile)
    lines = raw.splitlines()
    assert f"PROFILE\t{profile}" in lines
    assert any(row.startswith("IDENTITY\t") for row in lines)
    assert any(row.startswith("REF\trefs/heads/main\t") for row in lines)
    return lines


with tempfile.TemporaryDirectory(prefix="pa-git-snapshot-") as temp:
    repo = Path(temp) / "fixture"
    repo.mkdir()
    run("git", "init", "-q", "-b", "main", cwd=repo)
    run("git", "config", "user.email", "test@example.invalid", cwd=repo)
    run("git", "config", "user.name", "Disposable Test", cwd=repo)
    (repo / "tracked.txt").write_text("source state\n")
    run("git", "add", "tracked.txt", cwd=repo)
    run("git", "commit", "-qm", "initial", cwd=repo)
    # Dirty source must NOT silently become recoverable in a Pull snapshot.
    (repo / "untracked.txt").write_text("untracked payload\n")
    (repo / "tracked.txt").write_text("modified state\n")

    fetch = snapshot(repo, "REFS_ONLY")
    assert not any(row.startswith(("STATUS\t", "INDEX\t", "WORKTREE\t"))
                   for row in fetch), "FETCH must avoid content inventory"

    pull = snapshot(repo, "PULL_REF_SAFE")
    status = next(row for row in pull if row.startswith("STATUS\t")).split("\t")
    assert len(status) == 10, status
    assert status[1] == "0" and status[2] == "1" and status[3] == "1", status
    assert all(not value for value in status[6:]), (
        "PULL_REF_SAFE must skip expensive binary/untracked-content hashing"
    )
    assert any(row.startswith("OPSTATE\t") for row in pull)
    assert any(row.startswith("WORKTREE\t") for row in pull)

    full = snapshot(repo, "FULL")
    full_status = next(row for row in full if row.startswith("STATUS\t")).split("\t")
    assert any(full_status[6:]), "FULL must retain content-hash evidence"
    assert (repo / "untracked.txt").read_text() == "untracked payload\n"
    assert (repo / "tracked.txt").read_text() == "modified state\n"

print("Git snapshot profile disposable execution: PASS")
