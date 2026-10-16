#!/usr/bin/env python3
"""Offline regression for GitHub PULLS large-JSON loading and error semantics.

Extract the actual shell script built by GitHubWorkItemsService.qml and execute
it against a deterministic fake gh response; never touch a real GitHub account.
"""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/github/GitHubWorkItemsService.qml"
SOURCE = SERVICE.read_text(encoding="utf-8")


def embedded_pull_script():
    marker = "pullsProcess.exec(["
    assert SOURCE.count(marker) == 1, "Pull process contract changed"
    block = SOURCE.split(marker, 1)[1].split('].join("\\n")', 1)[0]
    assert '            [\n' in block, "Expected embedded shell argument array"
    block = block.split('            [\n', 1)[1]

    script_lines = []
    for line in block.splitlines():
        line = line.strip().removesuffix(",")
        if not line:
            continue
        assert line.startswith(("'", '"')), "Unexpected QML shell fragment: " + line[:80]
        script_lines.append(ast.literal_eval(line))
    assert script_lines and script_lines[0] == "set -eo pipefail"
    return "\n".join(script_lines)


assert "--argjson rows" not in SOURCE, "Never pass all PRs as a single exec argument"
assert "--argjson details" not in SOURCE, "Never pass enriched PR JSON as an exec argument"
assert '--slurpfile details' in SOURCE, "Enriched details must enter through a file"
assert 'trap ' in SOURCE and ' EXIT' in SOURCE, "Temporary files need an EXIT cleanup"
assert 'set -eo pipefail' in SOURCE, "A failed jq or GraphQL call must fail the load"

assert shutil.which("jq"), "jq is required for the real PR loader and its regression"
SCRIPT = embedded_pull_script()


def run_synthetic(payload, gh_code=0):
    with tempfile.TemporaryDirectory(prefix="apollo-pr-regression-") as tmp:
        root = Path(tmp)
        bindir = root / "bin"
        bindir.mkdir()
        tmpdir = root / "temporary"
        tmpdir.mkdir()
        fixture = root / "mock-graphql.json"
        fixture.write_text(payload, encoding="utf-8")
        shim = bindir / "gh"
        shim.write_text(
            "#!/bin/sh\n"
            'cat "$PA_TEST_GRAPHQL_FIXTURE"\n'
            'exit "$PA_TEST_GH_EXIT"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)

        env = os.environ.copy()
        env.update({
            "PATH": str(bindir) + os.pathsep + env.get("PATH", ""),
            "TMPDIR": str(tmpdir),
            "PA_TEST_GRAPHQL_FIXTURE": str(fixture),
            "PA_TEST_GH_EXIT": str(gh_code),
        })
        # The production service uses bash -lc. Run its identical script with
        # bash -c here, so the test's fake gh PATH is not reset by login files.
        run = subprocess.run(
            ["bash", "-c", SCRIPT, "pa-github-pulls-graphql",
             "kudokudo1/The-Post-Apollo-Project"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        leftovers = list(tmpdir.iterdir())
        assert not leftovers, f"Temporary PR data leaked: {leftovers}"
        return run


rows = []
for index in range(100):
    rows.append({
        "number": index + 1,
        "title": "Synthetic PR " + ("X" * 1600),
        "state": "MERGED",
        "url": f"https://example.invalid/pr/{index + 1}",
        "headRefOid": "a" * 40,
        "reviewDecision": "APPROVED",
        "reviews": {"nodes": [{"state": "APPROVED", "author": {"login": "tester"}}]},
        "commits": {"nodes": [{"commit": {"statusCheckRollup": {
            "state": "SUCCESS",
            "contexts": {"nodes": [{
                "__typename": "CheckRun",
                "name": "check", "status": "COMPLETED", "conclusion": "SUCCESS"
            }]},
        }}}]},
    })

large_payload = json.dumps(rows)
assert len(large_payload.encode()) > 131072
success = run_synthetic(large_payload)
assert success.returncode == 0, success.stderr
output = json.loads(success.stdout)
assert len(output) == 100, f"Expected 100 PRs, got {len(output)}"
assert output[0]["number"] == 1 and output[-1]["number"] == 100
assert output[0]["checkState"] == "SUCCESS"
assert len(output[0]["checkContexts"]) == 1
assert output[0]["checkEvidenceLoaded"] is False
assert output[0]["reviewRequestCount"] == 0

empty = run_synthetic("[]")
assert empty.returncode == 0 and json.loads(empty.stdout) == []

bad_json = run_synthetic("{not valid JSON")
assert bad_json.returncode != 0, "Invalid JSON must not look like READY // 0"

failed_api = run_synthetic("[]", gh_code=42)
assert failed_api.returncode != 0, "Failed GraphQL must not look like READY // 0"

print("GitHub PULLS large-payload and error-propagation regression: PASS")
