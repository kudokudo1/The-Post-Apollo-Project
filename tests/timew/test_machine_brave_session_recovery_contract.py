#!/usr/bin/env python3
"""MACHINE // synthetic browser restart plan must not widen live scope."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
ext = root / "integrations/machine/brave-topology"
plan = (ext / "session-recovery-plan.mjs").read_text()
manifest = json.loads((ext / "manifest.json").read_text())
popup = (ext / "popup.mjs").read_text()
marker = (ext / "marker.mjs").read_text()
bridge = (root / "services/time/MachineSaveBridgeV2.py").read_text()
restorer = (root / "services/time/MachineRestoreCheckpoint.py").read_text()
test = (root / "tests/timew/test_machine_brave_session_recovery_plan.mjs").read_text()

assert manifest["permissions"] == []
assert manifest["optional_permissions"] == ["nativeMessaging"]
assert manifest["host_permissions"] == []
assert manifest["incognito"] == "not_allowed"
assert manifest["version"] == "0.3.1"

# The pure model is intentionally not imported from live browser/TimeW code.
assert "session-recovery-plan" not in popup
assert "session-recovery-plan" not in marker
assert "session-recovery-plan" not in bridge
assert "session-recovery-plan" not in restorer
assert "projectBraveTopology(all, currentId)" in popup
assert 'status: "synthetic_preview_only"' in plan
assert "restore_allowed: false" in plan
assert "persisted: false" in plan
assert "browser_permission_requested: false" in plan
assert "user_tab_urls_exported: false" in plan
assert "persistent_session_identity_verified: false" in plan
assert "browser_sway_binding_verified: false" in plan
assert "safe_actions: []" in plan
assert "privateSkipped++" in plan
assert "requires_sensitive_review" in plan
assert "manual_pairing_required" in plan
assert "freezeDeep" in plan
assert "SESSION RECOVERY PREVIEW REFUSED" in plan

# Privacy: no filesystem, Chromium API, native IPC, storage, clipboard,
# logging or browser actuation. A subsequent opt-in capture is separate.
executable = "\n".join(
    line for line in plan.splitlines()
    if not line.strip().startswith(("*", "//", "/*"))
)
for forbidden in (
    "chrome.", "browser.", "globalThis", "window.", "document.",
    "localStorage", "sessionStorage", "indexedDB",
    "navigator.clipboard", "fetch(", "XMLHttpRequest",
    "WebSocket", "sendNativeMessage", "connectNative",
    "console.log", "console.error", "process.", "fs.",
    "require(", "import ", "setInterval(", "setTimeout(",
    "writeFile", "readFile", "restore(", "tabs.create", "windows.create",
    "swaymsg", "child_process", "Date.now", "performance.now",
):
    assert forbidden not in executable, forbidden

# Source fixture exercises 2//5//6, query/fragment token redaction,
# private-window accessors, malformed inputs, and no inferred pairing.
for required in (
    'win("WORK",2', 'win("MEDIA",5', 'win("PERSONAL",6',
    "PRIVATE TAB URL: NEVER READ",
    "SESSION RECOVERY PREVIEW REFUSED",
    "manual_pairing_required",
    '"restorable"',  # marker below replaces this assertion if not a literal
):
    if required == '"restorable"':
        assert 'session_restorable' in test
    else:
        assert required in test, required

print("MACHINE Brave synthetic restart eligibility // no new permissions or I/O PASS")
