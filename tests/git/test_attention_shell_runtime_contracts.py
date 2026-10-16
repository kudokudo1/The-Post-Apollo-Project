#!/usr/bin/env python3
"""Execute the actual Attention shell builder against a fake GitHub CLI.

A static substring check missed a doubled-backslash newline that made the
entire generated Bash script a malformed single line.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
provider = (ROOT / "services/github/GitHubAttentionProvider.qml").read_text()
start = provider.index("        const args = [", provider.index("    function refresh(values)"))
end = provider.index("        refreshProcess.exec(args);", start)
js_body = provider[start:end] + "\n        return args;\n"
node = (
    "const fn = new Function('targets', 'maxPullRequestsPerRepository', "
    + json.dumps(js_body) + ");\n"
    + "process.stdout.write(JSON.stringify(fn(['kudokudo1/fixture'], 10)));\n"
)
built = subprocess.run(["node", "-e", node], capture_output=True, text=True, check=True)
args = json.loads(built.stdout)
assert args[:2] == ["bash", "-lc"], args[:2]
assert args[3] == "pa-github-attention"
assert args[5] == "kudokudo1/fixture"
script = args[2]
assert "\nfor repo in \"$@\"; do\n" in script, "shell commands must be separated by actual newlines"
subprocess.run(["bash", "-n", "-c", script], check=True, capture_output=True, text=True)

fixture = {
    "data": {"repository": {"pullRequests": {"nodes": [{
        "number": 7,
        "title": "Fixture PR",
        "state": "OPEN",
        "url": "https://github.com/kudokudo1/fixture/pull/7",
        "isDraft": False,
        "updatedAt": "2026-10-16T08:00:00Z",
        "author": {"login": "fixture-author"},
        "headRefName": "fix/fixture",
        "baseRefName": "main",
        "headRefOid": "abcdef123456",
        "reviewDecision": "",
        "mergeStateStatus": "CLEAN",
        "mergeable": "MERGEABLE",
        "reviewRequests": {"totalCount": 0, "nodes": []},
        "commits": {"nodes": [{"commit": {"statusCheckRollup": {
            "state": "SUCCESS", "contexts": {"nodes": [{
                "__typename": "CheckRun", "name": "fixture-ci",
                "status": "COMPLETED", "conclusion": "SUCCESS"
            }]}
        }}}]}
    }]}}}
}
with tempfile.TemporaryDirectory(prefix="attention-shell-test-") as temp:
    gh = Path(temp) / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = api ] && [ \"$2\" = user ]; then printf 'fixture-viewer\\n'; exit 0; fi\n"
        "if [ \"$1\" = api ] && [ \"$2\" = graphql ]; then printf '%s\\n' \"$FAKE_GRAPHQL\"; exit 0; fi\n"
        "printf 'unexpected gh invocation: %s\\n' \"$*\" >&2\nexit 30\n"
    )
    gh.chmod(0o755)
    env = dict(os.environ, PATH=temp + os.pathsep + os.environ["PATH"],
               FAKE_GRAPHQL=json.dumps(fixture))
    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, (result.returncode, result.stderr, result.stdout)
    parsed = json.loads(result.stdout)
    assert parsed["viewerLogin"] == "fixture-viewer", parsed
    assert len(parsed["pullRequests"]) == 1, parsed
    assert parsed["pullRequests"][0]["number"] == 7, parsed
    assert parsed["repositories"][0]["state"] == "OK", parsed

print("ATTENTION GENERATED BASH // SYNTAX + FAKE GITHUB DATA PASS")
