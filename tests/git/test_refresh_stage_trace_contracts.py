#!/usr/bin/env python3
"""Exercise actual GitService refresh Bash with profiling off and on.

Disposable temporary repositories only; no user's repo, network, journal,
Quickshell process, or local Git worktree is accessed.
"""
from pathlib import Path
import json
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
service = (root / "services/git/GitService.qml").read_text()

assert 'Quickshell.env("POST_APOLLO_GIT_REFRESH_STAGE_TRACE")' in service
assert 'refreshStageTraceEnabled ? "1" : "0"' in service
assert 'else if (key === "PROFILE")' in service
assert 'if (!refreshStageTraceEnabled)' in service
assert 'GIT_REFRESH_STAGE_TRACE // stage=' in service
assert "JOURNAL PROFILE // " in service
assert "JOURNAL NOT RECORDED // " in service
assert 'REFRESHED // repository view ' in service

start = service.index('        refreshProcess.exec([')
end = service.index('        ]);', start) + len('        ]')
command = service[start + len('        refreshProcess.exec('):end]
assert command.startswith("[") and command.endswith("]")
assert "trace_refresh_stage" in command
assert "trace_refresh_total" in command

# Extract the same array expression that QML evaluates, without rewriting
# the Bash or reproducing it in a separate Python implementation.
extract = r"""
const vm = require('node:vm');
const source = process.argv[1];
const repo = process.argv[2];
const enabled = process.argv[3] === '1';
const command = vm.runInNewContext(source, {
  refreshRepoPath: repo,
  refreshStageTraceEnabled: enabled
});
if (!Array.isArray(command) || command[0] !== 'bash' || command[1] !== '-lc')
  throw new Error('unexpected Git refresh command shape');
process.stdout.write(JSON.stringify(command));
"""
def actual_command(repo_path: str, enabled: bool):
    p = subprocess.run(
        ["node", "-e", extract, command, repo_path, "1" if enabled else "0"],
        cwd=root, capture_output=True, text=True, timeout=15, check=True
    )
    return json.loads(p.stdout)

def run_git(*args, cwd=None):
    subprocess.run(["git", *map(str, args)], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                   timeout=20)

def execute(script):
    return subprocess.run(script, cwd=root, capture_output=True,
                          timeout=30, check=True).stdout

expected_stages = [
    "metadata", "status", "upstream", "merged_refs", "cherry",
    "local_branches", "remote_branches", "history", "total"
]
with tempfile.TemporaryDirectory(prefix="pa-git-refresh-stage-") as td:
    temp = Path(td)
    bed = temp / "bed"
    remote = temp / "origin.git"
    run_git("init", "--quiet", "--bare", "--initial-branch=main", remote)
    run_git("init", "--quiet", "--initial-branch=main", bed)
    run_git("-C", bed, "config", "user.name", "Synthetic CI")
    run_git("-C", bed, "config", "user.email", "synthetic@example.invalid")
    (bed / "README.txt").write_text("initial\n")
    run_git("-C", bed, "add", "README.txt")
    run_git("-C", bed, "commit", "--quiet", "-m", "synthetic main")
    run_git("-C", bed, "remote", "add", "origin", remote)
    run_git("-C", bed, "push", "--quiet", "-u", "origin", "main")
    run_git("-C", bed, "checkout", "--quiet", "-b", "feature")
    (bed / "README.txt").write_text("branch\n")
    run_git("-C", bed, "commit", "--quiet", "-am", "synthetic feature")
    run_git("-C", bed, "push", "--quiet", "-u", "origin", "feature")
    run_git("-C", bed, "checkout", "--quiet", "main")

    off_cmd = actual_command(str(bed), False)
    on_cmd = actual_command(str(bed), True)
    assert off_cmd[:-1] == on_cmd[:-1]
    assert off_cmd[-1] == "0" and on_cmd[-1] == "1"
    assert 'EPOCHREALTIME' in off_cmd[2]
    baseline = execute(off_cmd)
    profiled = execute(on_cmd)
    profile_lines = [line for line in profiled.splitlines(keepends=True)
                     if line.startswith(b"PROFILE\t")]
    actual_stages = [line.decode().strip().split("\t")[1]
                     for line in profile_lines]
    assert actual_stages == expected_stages, actual_stages
    for line in profile_lines:
        parts = line.decode().strip().split("\t")
        assert len(parts) == 3 and re.fullmatch(r"\d{1,9}", parts[2]), parts

    # Every ordinary stdout byte is preserved, including COMMIT protocol,
    # error wording, branch identities, and exactly one DONE sentinel.
    stripped = b"".join(line for line in profiled.splitlines(keepends=True)
                        if not line.startswith(b"PROFILE\t"))
    assert baseline == stripped, (
        "diagnostic mode must not change the refresh data protocol\n"
        + repr(baseline[-700:]) + "\n" + repr(stripped[-700:])
    )
    assert baseline.count(b"DONE\t") == 1
    assert b"REMOTEBRANCH\torigin/feature" in baseline
    assert b"LOCALBRANCH\tmain" in baseline
    assert b"COMMIT\t" in baseline
    assert not any(line.startswith(b"PROFILE\t")
                   for line in baseline.splitlines())
    print("Actual Git refresh Bash: off/on exact protocol parity PASS")
    print("Nine stage durations, synthetic origin branches/history: PASS")

print("Git refresh stage diagnostics dormant by default: PASS")
