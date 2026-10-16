#!/usr/bin/env python3
"""Hospital audit launcher preference and truthful Reports empty-state contract."""
from pathlib import Path
import json
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
audit = (root / "services/hospital/HospitalAuditService.qml").read_text()
catalog = (root / "services/hospital/HospitalRoomReportCatalogService.qml").read_text()
view = (root / "widgets/HospitalReportsView.qml").read_text()

for literal in (
    'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"',
    '[ -x "$px" ] || px="$HOME/.local/bin/px"',
    'exec "$px" audit "$1"',
):
    assert literal in audit, literal
for literal in ("property bool loaded: false", "loaded = false;", "root.loaded = true;"):
    assert literal in catalog, literal
for literal in (
    "NO PERSISTENT PX ROOMS REGISTERED",
    "NO STORED ROOM REPORTS OR CERTIFICATION EVENTS",
    "NO REPORTS MATCH THE SELECTED FILTER",
    "PX ROOM REPORT CATALOG HAS NOT LOADED",
):
    assert literal in view, literal

match = re.search(r"auditProcess\.exec\(\[(.*?)\]\);", audit, re.S)
assert match, "Audit command builder missing"
node_script = (
    'const target = "example/fixture";\n'
    "process.stdout.write(JSON.stringify([" + match.group(1) + "]));"
)
result = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
argv = json.loads(result.stdout)
assert argv[:2] == ["bash", "-lc"]
assert argv[3] == "px-audit"
assert argv[4] == "example/fixture"
with tempfile.TemporaryDirectory(prefix="hospital-px-audit-select-") as tmp:
    home = Path(tmp)
    runtime = home / ".local/share/post-apollo-dev-runtime/bin/px"
    fallback = home / ".local/bin/px"
    for target, name in ((runtime, "runtime"), (fallback, "fallback")):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('#!/bin/sh\nprintf "' + name + ' %s\\n" "$2"\n')
        target.chmod(0o755)
    env = dict(os.environ, HOME=str(home))
    chosen = subprocess.run(argv, env=env, text=True, capture_output=True, check=True)
    assert chosen.stdout.strip() == "runtime example/fixture", chosen.stdout
    runtime.unlink()
    chosen = subprocess.run(argv, env=env, text=True, capture_output=True, check=True)
    assert chosen.stdout.strip() == "fallback example/fixture", chosen.stdout

print("HOSPITAL AUDIT // PREFERRED PX RUNTIME AND REPORT SOURCE STATUS PASS")
