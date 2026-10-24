#!/usr/bin/env python3
"""Compact live Fetch/Pull header contract; no Quickshell runtime required."""
from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]
service = (root / "services/git/GitService.qml").read_text()
view = (root / "widgets/GitW.qml").read_text()
header = view.split("id: syncTimingHeader", 1)[1].split(
    "Flickable {\n                                id: syntagmaPane2", 1
)[0]

# No duplicate end-to-end row remains in the scrollable Git output.
assert 'actionOutput += "\\nSYNC TIMELINE' not in service
assert 'text: gitService.actionOutput' in view
assert 'journalProfileLine(' in service
assert 'JOURNAL PROFILE // ' in service
assert 'FINISHED // after snapshot ' in service
assert 'REFRESHED // repository view ' in service

fields = [
    ("Prepare", "syncTimingPrepareMs"),
    ("Git", "syncTimingGitMs"),
    ("Finalize", "syncTimingFinalizeMs"),
    ("Refresh", "syncTimingRefreshMs"),
    ("Total", "syncTimingTotalMs"),
]
for label, name in fields:
    assert f"property int {name}: -1" in service, (label, name)
    assert f"{name} = -1;" in service
    assert f"gitService.{name}" in header, name

# Make each phase available as it finishes, not only at the final DONE event.
started = service.split("function startPendingActionProcess()", 1)[1].split(
    "function finalActionLine()", 1
)[0]
complete = service.split("function finishActionProcess()", 1)[1].split(
    "function runProcessAction(", 1
)[0]
finalize = service.split("function finalizeControlAction(", 1)[1].split(
    "function finishActionProcess()", 1
)[0]
assert "syncTimingPrepareMs = syncCommandStartedMs - syncStartedMs;" in started
assert "syncTimingGitMs = syncCommandFinishedMs - syncCommandStartedMs;" in complete
assert "syncTimingFinalizeMs =" in finalize
assert "syncTimingRefreshMs = refreshMs;" in service
assert "syncTimingTotalMs = end - syncStartedMs;" in service

# Two-line header, with one tighter log window. No new card or window.
assert 'id: syncTimingHeader' in view
assert "syncTimingHeader.visible ? 33 : 24" in view
assert "visible: isSyncOutput" in header
assert 'gitService.actionTitle.toLowerCase()' in header
assert 'font.pixelSize: 9' in header
assert "TOTAL " in header
assert 'elide: Text.ElideRight' in header

# Run the actual QML formatting helper under Node and check pending,
# millisecond, and second values, including exact boundary.
fmt = re.search(
    r"function briefMs\(value\) \{.*?\n                                \}",
    header, re.S
)
assert fmt, "formatter not found"
js = """
const assert = require('node:assert/strict');
const vm = require('node:vm');
vm.runInThisContext(FORMATTER);
assert.equal(briefMs(-1), '…');
assert.equal(briefMs(0), '0ms');
assert.equal(briefMs(999), '999ms');
assert.equal(briefMs(1000), '1.00s');
assert.equal(briefMs(1655), '1.66s');
console.log('Git compact header formatting and pending state: PASS');
""".replace("FORMATTER", json.dumps(fmt.group(0)))
# FORMATTER is source code, not a quoted string.
js = js.replace(json.dumps(fmt.group(0)), fmt.group(0))
run = subprocess.run(
    ["node", "-e", js], cwd=root, capture_output=True, text=True,
    timeout=20, check=False
)
assert run.returncode == 0, run.stdout + "\n" + run.stderr
print(run.stdout.strip())
print("Git compact timing header presentation and journal preservation: PASS")
