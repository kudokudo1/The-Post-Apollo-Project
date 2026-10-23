#!/usr/bin/env python3
"""Disposable exact-output proof for Git refresh's merged-ref fast path.

Run the real QML-embedded Bash refresh payload and compare it to the same
payload with the fast-path removed. No user repository, Quickshell, or network.
"""
import ast
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "services/git/GitService.qml").read_text()
match = re.search(
    r'refreshProcess\.exec\(\[\s*"bash",\s*"-lc",\s*\[(.*?)'
    r'\]\.join\("\\n"\)',
    src, re.S,
)
assert match, "GitService refresh Bash payload not found"
commands = []
for raw in match.group(1).splitlines():
    token = raw.strip().removesuffix(",")
    if not token or token.startswith("//"):
        continue
    assert token.startswith("'") and token.endswith("'"), token
    commands.append(ast.literal_eval(token))
script = "\n".join(commands)

prefilter = "\n".join([
    'merged_remote_refs="|"',
    'while IFS= read -r ref; do',
    '  [ -n "$ref" ] || continue',
    '  merged_remote_refs="${merged_remote_refs}${ref}|"',
    'done < <(git -C "$root" for-each-ref --merged=HEAD --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
])
skip = '  case "$merged_remote_refs" in *"|$ref|"*) continue ;; esac'
assert script.count(prefilter) == 1
assert script.count(skip) == 1
assert script.count('git -C "$root" cherry HEAD "$ref"') == 1
original = script.replace(prefilter + "\n", "").replace(skip + "\n", "")
assert original != script

def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result.stdout.strip()

def refresh(source, repo):
    result = subprocess.run(
        ["bash", "-lc", source, "pa-git-refresh", str(repo)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    return result.stdout

def remote_rows(output):
    return {
        v[1]: v for line in output.splitlines()
        if (v := line.split("\t"))[0] == "REMOTEBRANCH"
    }

with tempfile.TemporaryDirectory(prefix="pa-git-refresh-merged-") as temp:
    repo = Path(temp) / "fixture"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Disposable Check")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("baseline\n")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("baseline\nshared patch\n")
    git(repo, "commit", "-qam", "main version")
    main = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "-qb", "equivalent", base)
    (repo / "tracked.txt").write_text("baseline\nshared patch\n")
    git(repo, "commit", "-qam", "equivalent with different commit identity")
    equivalent = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")

    git(repo, "checkout", "-qb", "diverged", base)
    (repo / "tracked.txt").write_text("baseline\nnew remote work\n")
    git(repo, "commit", "-qam", "remote-only change")
    diverged = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")

    for i in range(18):
        git(repo, "update-ref", f"refs/remotes/origin/merged-{i:02}", base if i % 2 else main)
    for name, sha in [
        ("main", main),
        ("equivalent", equivalent),
        ("diverged", diverged),
    ]:
        git(repo, "update-ref", "refs/remotes/origin/" + name, sha)

    baseline = refresh(original, repo)
    faster = refresh(script, repo)
    assert faster == baseline, (
        "refresh output changed, including branch, status, or topology\n"
        + repr(baseline) + "\n\n" + repr(faster)
    )
    rows = remote_rows(faster)
    assert rows["origin/main"][2] == "0", rows["origin/main"]
    assert rows["origin/merged-00"][2] == "0", rows["origin/merged-00"]
    assert rows["origin/equivalent"][2] == "0", rows["origin/equivalent"]
    assert rows["origin/diverged"][2] == "1", rows["origin/diverged"]
    assert (repo / "tracked.txt").read_text() == "baseline\nshared patch\n"

print("Git refresh merged-ref prefilter: exact-output and patch-equivalence PASS")
