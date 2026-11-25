#!/usr/bin/env python3
"""Disposable exact-output proof for Git refresh's merged-ref fast path.

Run the real QML-embedded Bash refresh payload and compare it to the same
payload with the fast-path removed. No user repository, Quickshell, or network.
"""
import ast
from pathlib import Path
import re
import subprocess
import sys
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

# Frozen baseline blocks from the reviewed pre-optimization source.
# Compare the full live payload against the former implementation, not a
# hand-written prediction of branch relationships.
old_block = "diag_mark merged_refs\nmerged_remote_refs=\"|\"\nwhile IFS= read -r ref; do\n  [ -n \"$ref\" ] || continue\n  merged_remote_refs=\"${merged_remote_refs}${ref}|\"\ndone < <(git -C \"$root\" for-each-ref --merged=HEAD --format=\"%(refname:short)\" refs/remotes/origin 2>/dev/null)\ntrace_refresh_stage \"merged_refs\"\ndiag_mark cherry\npending_refs=\"|\"\npending_count=0\nwhile IFS=\"$(printf \"\\t\")\" read -r ref changed; do\n  [ -z \"$ref\" ] && continue\n  [ \"$ref\" = \"origin\" ] && continue\n  [ \"$ref\" = \"origin/HEAD\" ] && continue\n  case \"$ref\" in */*) ;; *) continue ;; esac\n  case \"$merged_remote_refs\" in *\"|$ref|\"*) continue ;; esac\n  if git -C \"$root\" cherry HEAD \"$ref\" 2>/dev/null | grep -q \"^+\"; then\n    pending_refs=\"${pending_refs}${ref}|\"\n    pending_count=$((pending_count + 1))\n    [ \"$pending_count\" -ge 5 ] && break\n  fi\ndone < <(git -C \"$root\" for-each-ref --sort=-committerdate --count=24 --format=\"%(refname:short)%09%(committerdate:unix)\" refs/remotes/origin 2>/dev/null)\ntrace_refresh_stage \"cherry\""
new_block = "diag_mark merged_refs\nmapfile -t recent_remote_rows < <(git -C \"$root\" for-each-ref --sort=-committerdate --count=24 --format=\"%(refname)%09%(refname:short)%09%(committerdate:unix)\" refs/remotes/origin 2>/dev/null)\ncandidate_refs=()\ndeclare -A candidate_dates=()\nwhile IFS=\"$(printf \"\\t\")\" read -r full_ref ref changed; do\n  [ -z \"$ref\" ] && continue\n  [ \"$ref\" = \"origin\" ] && continue\n  [ \"$ref\" = \"origin/HEAD\" ] && continue\n  case \"$ref\" in */*) ;; *) continue ;; esac\n  candidate_refs+=(\"$full_ref\")\n  candidate_dates[\"$ref\"]=\"$changed\"\ndone < <(printf \"%s\\n\" \"${recent_remote_rows[@]}\")\nmerged_remote_refs=\"|\"\nif [ \"${#candidate_refs[@]}\" -gt 0 ]; then\n  while IFS= read -r ref; do\n    [ -n \"$ref\" ] || continue\n    merged_remote_refs=\"${merged_remote_refs}${ref}|\"\n  done < <(git -C \"$root\" for-each-ref --merged=HEAD --format=\"%(refname:short)\" \"${candidate_refs[@]}\" 2>/dev/null)\nfi\ntrace_refresh_stage \"merged_refs\"\ndiag_mark cherry\npending_refs=\"|\"\npending_count=0\nwhile IFS=\"$(printf \"\\t\")\" read -r full_ref ref changed; do\n  [ -z \"$ref\" ] && continue\n  [ \"$ref\" = \"origin\" ] && continue\n  [ \"$ref\" = \"origin/HEAD\" ] && continue\n  case \"$ref\" in */*) ;; *) continue ;; esac\n  case \"$merged_remote_refs\" in *\"|$ref|\"*) continue ;; esac\n  if git -C \"$root\" cherry HEAD \"$ref\" 2>/dev/null | grep -q \"^+\"; then\n    pending_refs=\"${pending_refs}${ref}|\"\n    pending_count=$((pending_count + 1))\n    [ \"$pending_count\" -ge 5 ] && break\n  fi\ndone < <(printf \"%s\\n\" \"${recent_remote_rows[@]}\")\ntrace_refresh_stage \"cherry\""
old_remote = "diag_mark remote_branches\nwhile IFS=\"$(printf \"\\t\")\" read -r ref changed; do\n  [ -z \"$ref\" ] && continue\n  [ \"$ref\" = \"origin\" ] && continue\n  [ \"$ref\" = \"origin/HEAD\" ] && continue\n  case \"$ref\" in */*) ;; *) continue ;; esac\n  local_branch=\"${ref#origin/}\"\n  remote_only=0\n  if [ -z \"${local_branch_refs[\"$local_branch\"]+present}\" ]; then remote_only=1; fi\n  unpulled=0\n  case \"$pending_refs\" in *\"|$ref|\"*) unpulled=1 ;; esac\n  if [ \"$unpulled\" -eq 0 ]; then changed=0; fi\n  printf \"REMOTEBRANCH\\t%s\\t%s\\t%s\\t%s\\n\" \"$ref\" \"$unpulled\" \"$remote_only\" \"$changed\"\ndone < <(git -C \"$root\" for-each-ref --format=\"%(refname:short)%09%(committerdate:unix)\" refs/remotes/origin 2>/dev/null)"
new_remote = "diag_mark remote_branches\nwhile IFS= read -r ref; do\n  [ -z \"$ref\" ] && continue\n  [ \"$ref\" = \"origin\" ] && continue\n  [ \"$ref\" = \"origin/HEAD\" ] && continue\n  case \"$ref\" in */*) ;; *) continue ;; esac\n  local_branch=\"${ref#origin/}\"\n  remote_only=0\n  if [ -z \"${local_branch_refs[\"$local_branch\"]+present}\" ]; then remote_only=1; fi\n  unpulled=0\n  case \"$pending_refs\" in *\"|$ref|\"*) unpulled=1 ;; esac\n  changed=0\n  if [ \"$unpulled\" -gt 0 ]; then changed=\"${candidate_dates[\"$ref\"]:-0}\"; fi\n  printf \"REMOTEBRANCH\\t%s\\t%s\\t%s\\t%s\\n\" \"$ref\" \"$unpulled\" \"$remote_only\" \"$changed\"\ndone < <(git -C \"$root\" for-each-ref --format=\"%(refname:short)\" refs/remotes/origin 2>/dev/null)"
assert script.count(new_block) == 1
assert script.count(new_remote) == 1
previous = script.replace(new_block, old_block, 1).replace(new_remote, old_remote, 1)
prefilter = "\n".join([
    'merged_remote_refs="|"',
    'while IFS= read -r ref; do',
    '  [ -n "$ref" ] || continue',
    '  merged_remote_refs="${merged_remote_refs}${ref}|"',
    'done < <(git -C "$root" for-each-ref --merged=HEAD --format="%(refname:short)" refs/remotes/origin 2>/dev/null)',
])
skip = '  case "$merged_remote_refs" in *"|$ref|"*) continue ;; esac'
assert previous.count(prefilter) == 1
assert previous.count(skip) == 1
assert script.count('git -C "$root" cherry HEAD "$ref"') == 1
original = previous.replace(prefilter + "\n", "").replace(skip + "\n", "")
assert original != previous and previous != script

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
    prior = refresh(previous, repo)
    faster = refresh(script, repo)
    def stable(output):
        return "".join(line for line in output.splitlines(keepends=True)
                       if not re.fullmatch(r"DIAGTIME\t(?:repo_check|metadata|status|upstream|merged_refs|cherry|local_branches|remote_branches|history|finished)\t\d+\n", line))
    assert stable(prior) == stable(baseline), "previous merged prefilter parity"
    assert stable(faster) == stable(baseline), (
        "refresh output changed, including branch, status, or topology\n"
        + repr(baseline) + "\n\n" + repr(faster)
    )
    rows = remote_rows(faster)
    assert rows["origin/main"][2] == "0", rows["origin/main"]
    assert rows["origin/merged-00"][2] == "0", rows["origin/merged-00"]
    assert rows["origin/equivalent"][2] == "0", rows["origin/equivalent"]
    assert rows["origin/diverged"][2] == "1", rows["origin/diverged"]
    assert (repo / "tracked.txt").read_text() == "baseline\nshared patch\n"

    # Cross the candidate limit; old refs must still be visible, not marked
    # pending just because the ancestry prefilter is now narrower.
    for i in range(90):
        git(repo, "update-ref", f"refs/remotes/origin/bulk-{i:03}", base if i % 2 else main)
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    git(repo, "tag", "origin/equivalent", main)
    for label in ("large inventory", "changed ref", "deleted ref", "changed HEAD", "detached HEAD"):
        if label == "changed ref":
            git(repo, "update-ref", "refs/remotes/origin/bulk-001", diverged)
        elif label == "deleted ref":
            git(repo, "update-ref", "-d", "refs/remotes/origin/bulk-002")
        elif label == "changed HEAD":
            git(repo, "checkout", "-q", "equivalent")
        elif label == "detached HEAD":
            git(repo, "checkout", "-q", "--detach", base)
        prior, faster = refresh(previous, repo), refresh(script, repo)
        assert stable(faster) == stable(prior), label
        assert len(remote_rows(faster)) == len(remote_rows(prior)), label
        print("Full protocol parity:", label)


print("Git refresh merged-ref prefilter: exact-output and patch-equivalence PASS")

# A separate scaled benchmark measures G4a itself (not the earlier remote
# local-branch-index optimization). Timing is evidence, never a flaky gate.
if "--benchmark" in sys.argv:
    import statistics
    import time

    with tempfile.TemporaryDirectory(prefix="pa-git-g4a-bench-") as temp:
        repo = Path(temp) / "fixture"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.name", "Disposable Benchmark")
        git(repo, "config", "user.email", "benchmark@example.invalid")
        commits = 4000
        refs = 1200
        lines = []
        for i in range(1, commits + 1):
            lines.extend([
                "commit refs/heads/main",
                f"mark :{i}",
                f"committer Bench <benchmark@example.invalid> {1700000000+i} +0000",
                "data 1",
                "x",
            ])
            if i > 1:
                lines.append(f"from :{i-1}")
            if i == 1:
                lines.extend(["M 100644 inline tracked.txt", "data 1", "x"])
            lines.append("")
        subprocess.run(["git", "-C", str(repo), "fast-import", "--quiet"],
                       input=("\n".join(lines)+"\n").encode(),
                       check=True, capture_output=True, timeout=60)
        git(repo, "reset", "--hard", "HEAD")
        shas = git(repo, "rev-list", "--reverse", "HEAD").splitlines()
        assert len(shas) == commits
        commands = "".join(
            f"update refs/remotes/origin/bench-{i:04d} {shas[i*(commits-1)//(refs-1)]}\n"
            for i in range(refs)
        )
        subprocess.run(["git", "-C", str(repo), "update-ref", "--stdin"],
                       input=commands.encode(), check=True, capture_output=True, timeout=30)
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/bench-1199")
        # Pack fixture objects for a more realistic repository; no commit graph
        # is generated explicitly, and no operator repository is accessed.
        git(repo, "gc", "--quiet")
        # Warm both variants, then alternate order to limit cache-order bias.
        baseline = stable(refresh(previous, repo))
        assert stable(refresh(script, repo)) == baseline
        assert len(remote_rows(baseline)) == refs
        samples = {"before": [], "after": []}
        for labels in (("before", "after"), ("after", "before"), ("before", "after")):
            for label in labels:
                started = time.monotonic()
                data = refresh(previous if label == "before" else script, repo)
                wall = round((time.monotonic()-started)*1000)
                assert stable(data) == baseline, label
                marks = dict((stage, int(ms)) for stage, ms in
                             re.findall(r"^DIAGTIME\t([a-z_]+)\t(\d+)$", data, re.M))
                assert list(marks) == ["repo_check", "metadata", "status", "upstream",
                    "merged_refs", "cherry", "local_branches", "remote_branches",
                    "history", "finished"], marks
                assert list(marks.values()) == sorted(marks.values()), marks
                samples[label].append({
                    "wall": wall,
                    "shell": marks["finished"],
                    "merged": marks["cherry"]-marks["merged_refs"],
                    "remote": marks["history"]-marks["remote_branches"],
                    "combined": marks["cherry"]-marks["merged_refs"]+
                                marks["history"]-marks["remote_branches"],
                })
        print(f"G4a scaled fixture: {commits} commits / {refs} remote refs / 3 paired samples; full stdout parity PASS")
        for label, rows in samples.items():
            print("G4a", label, "raw ms:", rows)
            print("G4a", label, "median ms:",
                  {key: statistics.median(row[key] for row in rows) for key in rows[0]})
        print("Synthetic warm-cache timing only; no operator-workstation speed claim")
