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
    # The service may wrap the same Bash payload with a single Toolbox
    # session to prevent one Podman execution per gh fallback.
    marker = ("pullsProcess.exec(GitHubBatch.wrap("
              if "pullsProcess.exec(GitHubBatch.wrap(" in SOURCE
              else "pullsProcess.exec([")
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


def run_synthetic(payload, gh_code=0, raw=False, target=0):
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
            """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if "graphql" in args:
    raw = open(os.environ["PA_TEST_GRAPHQL_FIXTURE"]).read()
    code = int(os.environ["PA_TEST_GH_EXIT"])
    if os.environ.get("PA_TEST_RAW") == "1":
        sys.stdout.write(raw)
        sys.exit(code)
    try:
        rows = json.loads(raw)
    except ValueError:
        sys.stdout.write("HTTP/2.0 200 OK\\r\\nContent-Type: application/json\\r\\n\\r\\n" + raw)
        sys.exit(code)
    target = next((int(arg.split("=", 1)[1]) for arg in args if arg.startswith("number=")), 0)
    if target:
        body = {"data":{"repository":{"pullRequest":next((r for r in rows if r["number"] == target), None)}}}
        sys.stdout.write("HTTP/2.0 200 OK\\r\\nContent-Type: application/json\\r\\n\\r\\n")
        json.dump(body, sys.stdout)
        sys.exit(code)
    page = 0
    for arg in args:
        if arg.startswith("cursor="):
            page = int(arg.split("=", 1)[1])
    size = next(int(arg.split("=", 1)[1]) for arg in args if arg.startswith("size="))
    assert size == (25 if page == 0 else 75), size
    start = 0 if page == 0 else 25
    chunk = json.loads(json.dumps(rows[start:start + size]))
    # Simulate the actual lightweight selection: no nested review/check lists.
    for row in chunk:
        row.pop("reviews", None)
        for node in row.get("commits", {}).get("nodes", []):
            rollup = node.get("commit", {}).get("statusCheckRollup", {})
            rollup.pop("contexts", None)
    more = len(rows) > start + size
    body = {"data":{"repository":{"pullRequests":{"nodes":chunk,"pageInfo":{
        "hasNextPage":more,"endCursor":str(page + 1) if more else None}}}}}
    sys.stdout.write("HTTP/2.0 200 OK\\r\\nContent-Type: application/json; charset=utf-8\\r\\n\\r\\n")
    json.dump(body, sys.stdout)
    sys.exit(code)
with open(os.environ["PA_TEST_CALLS"], "a") as calls:
    calls.write("REST\\n")
if any("requested_reviewers" in arg for arg in args):
    print("0")
else:
    print("[]")
""",
            encoding="utf-8",
        )
        shim.chmod(0o755)

        env = os.environ.copy()
        env.update({
            "PATH": str(bindir) + os.pathsep + env.get("PATH", ""),
            "TMPDIR": str(tmpdir),
            "PA_TEST_GRAPHQL_FIXTURE": str(fixture),
            "PA_TEST_GH_EXIT": str(gh_code),
            "PA_TEST_RAW": "1" if raw else "0",
            "PA_TEST_CALLS": str(root / "calls"),
        })
        # The production service uses bash -lc. Run its identical script with
        # bash -c here, so the test's fake gh PATH is not reset by login files.
        run = subprocess.run(
            ["bash", "-c", SCRIPT, "pa-github-pulls-graphql",
             "kudokudo1/The-Post-Apollo-Project", str(target)],
            env=env, capture_output=True, text=True, timeout=30,
        )
        leftovers = list(tmpdir.iterdir())
        assert not leftovers, f"Temporary PR data leaked: {leftovers}"
        run.rest_calls = (root / "calls").read_text().count("REST") if (root / "calls").exists() else 0
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
frames = [json.loads(line) for line in success.stdout.splitlines()]
assert len(frames) == 3, frames
assert [len(f["page"]) for f in frames[:-1]] == [25, 75]
output = frames[-1]
assert [r for f in frames[:-1] for r in f["page"]] == output
assert len(output) == 100, f"Expected 100 PRs, got {len(output)}"
assert output[0]["number"] == 1 and output[-1]["number"] == 100
assert output[0]["checkState"] == "SUCCESS"
assert output[0]["checkContexts"] == []
assert output[0]["checkDetailsDeferred"] is True
assert output[0]["reviewDetailsDeferred"] is True
assert success.rest_calls == 0

# A sparse open PR must exercise the review/CI evidence fallback. The
# fallback may be empty, but it must still produce the original PR record.
fallback_row = dict(rows[0])
fallback_row["state"] = "OPEN"
fallback_row["reviewDecision"] = ""
fallback_row["reviews"] = {"nodes": []}
fallback_row["commits"] = {"nodes": [{"commit": {
    "statusCheckRollup": {"state": "", "contexts": {"nodes": []}}
}}]}
fallback = run_synthetic(json.dumps([fallback_row]))
assert fallback.returncode == 0, fallback.stderr
fallback_frames = [json.loads(line) for line in fallback.stdout.splitlines()]
assert len(fallback_frames) == 2 and fallback_frames[0]["page"] == fallback_frames[1]
fallback_rows = fallback_frames[-1]
assert len(fallback_rows) == 1 and fallback_rows[0]["number"] == 1
assert fallback_rows[0]["checkDetailsDeferred"] is True
assert fallback_rows[0]["reviewDetailsDeferred"] is True
assert fallback.rest_calls == 0
selected = run_synthetic(json.dumps([fallback_row]), target=1)
assert selected.returncode == 0, selected.stderr
selected_rows = json.loads(selected.stdout)
assert len(selected_rows) == 1 and selected_rows[0]["number"] == 1
assert selected_rows[0]["checkEvidenceLoaded"] is True
assert selected_rows[0]["reviewEvidenceLoaded"] is True
assert selected_rows[0]["reviewRequestCount"] == 0
assert selected.rest_calls == 5

empty = run_synthetic("[]")
assert empty.returncode == 0
assert [json.loads(line) for line in empty.stdout.splitlines()] == [{"page": [], "kind": "page"}, []]

bad_json = run_synthetic("{not valid JSON")
assert bad_json.returncode != 0, "Invalid JSON must not look like READY // 0"

failed_api = run_synthetic("[]", gh_code=42)
assert failed_api.returncode != 0, "Failed GraphQL must not look like READY // 0"


# Preserve transport vs parse vs GraphQL errors without exposing body or credentials.
for response, diagnostic in [
    ("HTTP/2.0 502 Bad Gateway\r\nContent-Type: text/html\r\n\r\n<html>private</html>", "HTTP 502"),
    ("HTTP/2.0 200 OK\r\nContent-Type: text/html\r\n\r\n<html>private</html>", "NON-JSON CONTENT TYPE"),
    ("HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n", "EMPTY OR INVALID JSON"),
    ("HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"data\":", "EMPTY OR INVALID JSON"),
    ("HTTP/2.0 401 Unauthorized\r\nContent-Type: application/json\r\n\r\n{}", "AUTHENTICATION REQUIRED"),
    ("HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"errors\":[{\"message\":\"private\"}]}", "PROVIDER REPORTED ERRORS"),
    ("HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"data\":{\"repository\":null}}", "INVALID RESULT SHAPE"),
    ("", "NO COMPLETE HTTP HEADERS"),
]:
    failure = run_synthetic(response, raw=True)
    assert failure.returncode != 0, diagnostic
    assert diagnostic in failure.stderr, failure.stderr
    assert "private" not in failure.stderr and not failure.stdout

assert 'JSON.parse(output);' in SOURCE
assert 'throw new Error("EMPTY RESPONSE")' in SOURCE
assert 'throw new Error("EXPECTED PR ARRAY")' in SOURCE

# Source contract: consume complete frames before the process exits.
assert "waitForEnd: false" in SOURCE
assert "root.consumePullsOutput(this.text)" in SOURCE
assert "pullsRequestEpoch !== pullsRepoEpoch" in SOURCE
assert "FINAL RESPONSE DOES NOT MATCH VALIDATED PAGES" in SOURCE
assert "pullsCacheMaxAgeMs: 30000" in SOURCE
assert "pullsFirstPageMs = Math.max" in SOURCE
assert "pullsFullLoadMs = Math.max" in SOURCE
print("GitHub PULLS lightweight progressive pages, large payload and error propagation: PASS")

# Remote-view prewarm is bounded, visibility-gated and cannot displace details.
widget = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
prewarm = widget.split("id: pullsPrewarmTimer", 1)[1].split("function showGithubPage()", 1)[0]
assert "repeat: false" in prewarm
assert "!root.menuOpen" in prewarm and 'root.activePage !== "github"' in prewarm
assert "root.pullRequestControlOpen" in prewarm
assert "repository !== gitService.repoRemoteSlug" in prewarm
assert "githubWorkItemsService.pullsBusy" in prewarm
assert "githubWorkItemsService.ensurePulls(repository)" in prewarm
assert "pullsPrewarmTimer.stop();" in widget.split("function showGithubPulls()", 1)[1].split("function openPullRequestControl", 1)[0]
print("GitW bounded remote-view PULLS prewarm contracts: PASS")
