#!/usr/bin/env python3
"""MACHINE Brave pilot cannot gain hidden permissions, I/O or live activation."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
folder = root / "integrations/machine/brave-topology"
manifest = json.loads((folder / "manifest.json").read_text())
html = (folder / "popup.html").read_text()
popup = (folder / "popup.mjs").read_text()
projection = (folder / "topology.mjs").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
bridge = (root / "services/time/MachineSaveBridgeV2.py").read_text()
restorer = (root / "services/time/MachineRestoreCheckpoint.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()

assert manifest["manifest_version"] == 3
assert manifest["incognito"] == "not_allowed"
assert manifest["permissions"] == []
assert manifest["host_permissions"] == []
assert manifest["action"]["default_popup"] == "popup.html"
assert set(manifest) == {
    "manifest_version", "name", "version", "description",
    "minimum_chrome_version", "incognito", "permissions",
    "host_permissions", "action",
}
for forbidden in (
    "nativeMessaging", "tabs", "history", "cookies", "storage",
    "scripting", "debugger", "activeTab", "background", "content_scripts",
    "externally_connectable", "webRequest", "<all_urls>",
):
    assert forbidden not in json.dumps(manifest), forbidden

assert '<script type="module" src="popup.mjs"></script>' in html
assert '<link rel="stylesheet" href="popup.css">' in html
assert '<script>' not in html and 'onclick=' not in html
assert 'http://' not in html and 'https://' not in html
assert 'chrome.windows.getAll({ populate: true, windowTypes: ["normal"] })' in popup
assert 'chrome.windows.getCurrent({ populate: false })' in popup
assert 'refreshButton.addEventListener("click", inspectOnce)' in popup
assert 'inspectOnce();' in popup   # Only when the user opens the popup
assert "projectBraveTopology(all, currentId)" in popup
assert 'textContent' in popup and 'replaceChildren' in popup
assert 'innerHTML' not in popup and 'document.write' not in popup
assert "source.incognito === true" in projection
assert 'source.type !== "normal"' in projection
assert "temporary_browser_window_id" in projection
assert "sway_window_binding_verified: false" in projection
assert "restart_session_identity_verified: false" in projection
assert "tabs_restorable: false" in projection
assert "safe_restore_actions: []" in projection

for source in (popup, projection):
    for forbidden in (
        "chrome.tabs.", "chrome.sessions.", "chrome.storage.",
        "chrome.debugger.", "chrome.runtime.sendNativeMessage",
        "chrome.runtime.connectNative", "chrome.windows.update",
        "chrome.windows.create", "chrome.windows.remove",
        "fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon",
        "localStorage", "sessionStorage", "indexedDB",
        ".url", ".pendingUrl", ".title", ".favIconUrl",
        ".profilePath", ".cookie", ".sessionId",
        "setInterval(", "setTimeout(", "console.log(",
    ):
        assert forbidden not in source, forbidden

assert "brave-topology" not in qml
assert "brave-topology" not in bridge
assert "brave-topology" not in restorer
assert "brave-topology" not in legacy
assert "SCHEMA_VERSION = 1" in legacy
assert qml.count("Process {") == 15
roots = re.findall(r"^    (?:readonly )?property\s+\w+\s+(\w+)\s*[:=]",
                   qml, flags=re.MULTILINE)
assert roots and len(roots) == len(set(roots))
print("MACHINE Brave // zero permissions, no private data or live host control PASS")
