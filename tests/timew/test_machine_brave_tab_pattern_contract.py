#!/usr/bin/env python3
"""MACHINE // tab-count color grammar is read-only and never a Sway pairing."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
ext = root / "integrations/machine/brave-topology"
qml = (root / "widgets/TimeW.qml").read_text()
part = (root / "widgets/MachineBraveTabPattern.qml").read_text()
js = (ext / "popup.mjs").read_text()
html = (ext / "popup.html").read_text()
css = (ext / "popup.css").read_text()
manifest = json.loads((ext / "manifest.json").read_text())

# The live Brave inventory already uses the projection which excludes incognito
# and exposes counts only. The signature uses that already redacted data.
assert 'for (const entry of topology.windows)' in js
assert 'String(entry.tab_count)' in js
assert 'tabPattern.append(separator, number)' in js
assert 'tabPattern.replaceChildren();' in js
assert 'projectBraveTopology(all, currentId)' in js
assert 'tab-pattern' in html
assert 'BROWSER LIST ORDER // NOT LINKED TO SWAY' in html
for token in ('pattern-label', 'pattern-separator', 'pattern-number'):
    assert token in js and token in css
assert '.pattern-label { color: #55cfca; }' in css
assert '.pattern-separator { color: #ffffff; }' in css
assert '.pattern-number { color: #ed981a; }' in css
assert 'gap: 7px' in css
assert manifest["permissions"] == []
assert manifest["host_permissions"] == []
assert manifest["incognito"] == "not_allowed"
assert manifest["optional_permissions"] == ["nativeMessaging"]

# Shared widget presentation: labels cyan, // white, numbers orange.
assert 'text: "TABS"' in part
assert 'text: "//"' in part
assert 'text: String(pattern.counts[index])' in part
assert 'spacing: 7' in part
assert 'property color labelColor: Colors.cyan' in part
assert 'property color separatorColor: Colors.white' in part
assert 'property color numberColor: Colors.orange' in part
assert 'Repeater {' in part

# TimeW accepts a manually pasted sequence only, never a claimed or inferred
# per-window browser-to-Sway mapping. Preview remains out of checkpoints.
assert 'property string machineBraveTabDraft: ""' in qml
assert 'machineParseBraveTabCounts(machineBraveTabDraft)' in qml
assert 'id: machineBraveTabInput' in qml
assert 'onTextEdited: timew.machineBraveTabDraft = text' in qml
assert 'MachineBraveTabPattern {' in qml
assert 'counts: timew.machineBraveTabCountsPreview || []' in qml
assert 'labelColor: Colors.cyan' in qml
assert 'separatorColor: Colors.white' in qml
assert 'numberColor: Colors.orange' in qml
assert 'BROWSER LIST ORDER // UNLINKED // NOT SAVED' in qml
assert 'NO BRAVE COUNTS ENTERED // UNLINKED' in qml
assert 'INVALID COUNTS // USE 2 // 5 // 6' in qml
assert 'BROWSER TABS + EXACT RESTORE STILL IN DEVELOPMENT' in qml
assert qml.count('Process {') == 15  # no new process or bridge
assert qml.count("machineBraveTabDraft") == 4  # source + property + display input + edit
assert "brave-topology" not in qml  # no direct browser module connection

# No extension secret, storage, browser acts, nor stealth transport.
for forbidden in (
    "chrome.storage.", "chrome.tabs.", "chrome.sessions.", "fetch(",
    "sendNativeMessage", "navigator.clipboard", "window.localStorage",
    "innerHTML", "setInterval(", "setTimeout(",
):
    assert forbidden not in js, forbidden

print("MACHINE tab-count colors and unlinked manual preview // PASS")
