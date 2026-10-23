#!/usr/bin/env python3
"""Contract-only MACHINE checkpoint proposal; no runtime activation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = (ROOT / "docs/timew-machine-checkpoint-contract.md").read_text(
    encoding="utf-8")
timew = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
marker = (ROOT / "services/time/MachineTimelinePolicy.js").read_text(
    encoding="utf-8")

required = [
    "State:** DRAFT for operator review",
    "Not approved",
    "metadata-only",
    "## 1 // Identity",
    "## 2 // Consent and authority",
    "## 3 // Read scope and privacy boundary",
    "## 4 // Proposed versioned record",
    "## 5 // Conservative restore matching",
    "## 6 // Allowed *candidate* restoration actions",
    "## 7 // Preview, apply, failure, rollback",
    "## 8 // Acceptance gates before any implementation",
    "## 9 // Open decisions for operator review",
    "CAPTURE PREVIEW",
    "SAVE CHECKPOINT",
    "RESTORE PREVIEW",
    "APPLY SELECTED ACTIONS",
    "user-requested",
    "No automatic",
    "NO",
    "Hospital Room checkpoint",
    "Git's repository snapshot",
    "TimeW window-instance",
    "desktop-layout",
    "window titles",
    "passwords",
    "ambiguous",
    "SKIP / REVIEW",
    "previewed and explicitly authorized",
    "No capture, persistence, Sway control",
]
for term in required:
    assert term in spec, f"Missing checkpoint boundary: {term}"

# The documentation stage must not introduce a new runtime capability.
assert 'MACHINE // SESSION TIMELINE' in timew
assert 'NO SCREENSHOTS OR RESTORATION ACTIVE' in timew
assert 'MARKERS ARE TIMESTAMPS ONLY // LOST ON RESTART' in timew
assert "function addMachineMarker()" in timew
assert "function removeMachineMarker(id)" in timew
assert "function createMarker(" in marker
assert "function appendMarker(" in marker
assert "function removeMarker(" in marker
for forbidden in ('swaymsg', 'grim ', 'JsonAdapter {', 'FileView {',
                  'execDetached(', 'onTriggered: capture',
                  'function captureDesktopCheckpoint(', 'function restoreDesktop('):
    assert forbidden not in timew, f"Unexpected MACHINE runtime capability: {forbidden}"

print("TIMEW MACHINE CHECKPOINT CONTRACT: DRAFT ONLY / NO CAPTURE / NO RESTORE")
