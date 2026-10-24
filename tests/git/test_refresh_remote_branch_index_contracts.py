#!/usr/bin/env python3
"""Compare actual Git refresh Bash against previous per-remote show-ref behavior.

Only disposable Git repositories. No live Qt, journal, network or user repo.
"""
from pathlib import Path
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "services/git/GitService.qml").read_text()
a = SOURCE.index("        refreshProcess.exec([")
b = SOURCE.index("        ]);", a) + len("        ]")
expression = SOURCE[a + len("        refreshProcess.exec("):b]
assert "declare -A local_branch_refs=()" in expression
assert "%(refname:lstrip=2)" in expression
assert "%09u%(upstream:short)" in expression
assert "GIT_REFRESH_STAGE_TRACE" in SOURCE
assert "JOURNAL PROFILE // " in SOURCE
assert "JOURNAL NOT RECORDED" in SOURCE

# Derive the old exact Bash from the actual new command by reversing
# only the three scoped changes, then compare their full protocol bytes.
def baseline(script):
    replacements = [
        ('declare -A local_branch_refs=()\n'
         'while IFS="$(printf "\\t")" read -r ref ref_head encoded_upstream local_ref; do\n'
         '  [ -z "$ref" ] && continue\n'
         '  local_branch_refs["$local_ref"]=1\n'
         '  ref_upstream="${encoded_upstream#u}"\n'
         '  compare="$ref_upstream"',
         'while IFS="$(printf "\\t")" read -r ref ref_head ref_upstream; do\n'
         '  [ -z "$ref" ] && continue\n'
         '  compare="$ref_upstream"'),
        ('for-each-ref --format="%(refname:short)%09%(objectname:short=10)%09u%(upstream:short)%09%(refname:lstrip=2)" refs/heads',
         'for-each-ref --format="%(refname:short)%09%(objectname:short=10)%09%(upstream:short)" refs/heads'),
        ('if [ -z "${local_branch_refs["$local_branch"]+present}" ]; then remote_only=1; fi',
         'if ! git -C "$root" show-ref --verify --quiet "refs/heads/$local_branch"; then remote_only=1; fi')
    ]
    for new, old in replacements:
        assert script.count(new) == 1, new
        script = script.replace(new, old, 1)
    assert "local_branch_refs" not in script
    return script

NODE = r"""
const vm = require('node:vm');
const result = vm.runInNewContext(process.argv[1], {
  refreshRepoPath: process.argv[2],
  refreshStageTraceEnabled: process.argv[3] === '1'
});
if (!Array.isArray(result) || result.length !== 6
    || result[0] !== 'bash' || result[1] !== '-lc')
  throw Error('changed refresh process argv');
process.stdout.write(JSON.stringify(result));
"""

def get_cmd(path, trace):
    p = subprocess.run(["node", "-e", NODE, expression, str(path),
                        "1" if trace else "0"],
                       check=True, capture_output=True, text=True, timeout=20)
    return json.loads(p.stdout)

def git(*args, data=None):
    return subprocess.run(["git", *map(str, args)], input=data,
                          check=True, capture_output=True, timeout=20).stdout.decode().strip()

def execute(args):
    return subprocess.run(args, check=True, capture_output=True, timeout=35).stdout

def strip_profiles(raw):
    return b"".join(line for line in raw.splitlines(keepends=True)
                    if not line.startswith(b"PROFILE\t"))

with tempfile.TemporaryDirectory(prefix="git-remote-index-") as folder:
    repo = Path(folder) / "repo"
    git("init", "--quiet", "--initial-branch=main", repo)
    git("-C", repo, "config", "user.name", "Synthetic CI")
    git("-C", repo, "config", "user.email", "test@example.invalid")
    (repo / "README").write_text("initial\n")
    git("-C", repo, "add", "README")
    git("-C", repo, "commit", "--quiet", "-m", "synthetic commit")
    sha = git("-C", repo, "rev-parse", "HEAD")
    git("-C", repo, "remote", "add", "origin", str(Path(folder) / "origin.git"))

    remotes = ["main", "feature/with-slash", "duplicate"]
    remotes += [f"bulk-{n:03d}" for n in range(85)]
    commands = "".join(f"update refs/remotes/origin/{name} {sha}\n"
                       for name in remotes)
    git("-C", repo, "update-ref", "--stdin", data=commands.encode())
    locals_ = ["feature/with-slash", "duplicate", "local-only"]
    locals_ += [f"bulk-{n:03d}" for n in range(0, 85, 7)]
    for name in locals_:
        git("-C", repo, "branch", name)
    git("-C", repo, "tag", "duplicate")

    optimized = get_cmd(repo, False)
    previous = optimized.copy()
    previous[2] = baseline(optimized[2])
    before, after = execute(previous), execute(optimized)
    assert before == after, "Git refresh stdout differs from previous behavior"
    assert before.count(b"DONE\t") == 1
    assert sum(line.startswith(b"REMOTEBRANCH\t")
               for line in before.splitlines()) == len(remotes)
    assert b"REMOTEBRANCH\torigin/feature/with-slash\t0\t0\t0" in after
    assert b"REMOTEBRANCH\torigin/bulk-001\t0\t1\t0" in after
    assert b"REMOTEBRANCH\torigin/bulk-000\t0\t0\t0" in after

    optimized_trace = get_cmd(repo, True)
    previous_trace = optimized_trace.copy()
    previous_trace[2] = baseline(optimized_trace[2])
    old_profile, new_profile = execute(previous_trace), execute(optimized_trace)
    assert strip_profiles(old_profile) == strip_profiles(new_profile) == before
    measured = {}
    for label, raw in (("baseline", old_profile), ("optimized", new_profile)):
        rows = [line.decode().strip().split("\t") for line in raw.splitlines()
                if line.startswith(b"PROFILE\t")]
        assert len(rows) == 9, rows
        assert all(len(row) == 3 and re.fullmatch(r"\d+", row[2])
                   for row in rows), rows
        measured[label] = {stage: int(duration) for _, stage, duration in rows}
    print(f"Real Git subprocess protocol parity: PASS ({len(remotes)} remote refs)")
    print("Mixed local/remote, nested refs and tag-name collisions: PASS")
    print("Diagnostic synthetic remote stage: "
          f"baseline={measured['baseline']['remote_branches']}ms "
          f"optimized={measured['optimized']['remote_branches']}ms")
print("Journal and snapshot source boundaries unchanged: PASS")
