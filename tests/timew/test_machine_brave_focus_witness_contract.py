#!/usr/bin/env python3
"""No accidental Brave host activation or window-moving authority."""
import ast
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "services/time/MachineBraveFocusWitness.py").read_text()
review = (root / "services/time/MachineBraveHostPairingReview.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
pilot = (root / "integrations/machine/brave-topology/manifest.json").read_text()
restore = (root / "services/time/MachineRestoreCheckpoint.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()

assert '["swaymsg", "-r", "-t", "get_tree"]' in host
assert 'from MachineSwayRead import _read_json' in host
assert 'same_focused_client_in_two_reads' in host
assert '"sway_window_binding_verified": False' in host
assert '"private_window_exclusion_verified": False' in host
assert '"session_restorable": False' in host
assert '"action_allowed": False' in host
assert '"safe_actions": []' in host
assert '"browser_window_id": None' in host
assert "new_id=uuid.uuid4" in host

for source in (host, review):
    ast.parse(source)
    for forbidden in (
        "gtk-launch", "shell=True", "swaymsg -t command",
        '"-t", "command"', "os.system", "Popen(",
        "connectNative", "sendNativeMessage",
        "chrome.tabs", "chrome.windows.update",
        "window_move", "save_pair(", "sqlite3.connect",
        "document_json", "geometry_json",
        ".write(", ".unlink(", ".rename(", "os.environ",
        "requests.", "urllib.request",
    ):
        assert forbidden not in source, forbidden

assert '"browser_to_sway_identity_verified": False' in review
assert '"operator_confirmation_is_identity_proof": False' in review
assert '"exact_session_match": False' in review
assert '"action_allowed": False' in review
assert '"safe_actions": []' in review
assert '"status": "unverified_focus_candidate"' not in review
assert 'status="unverified_focus_candidate"' in review
assert "PairingReviewError" in review
assert '"temporary_browser_window_id"' in review

# No new runtime surfaces, installed native host manifests, Brave permission
# grants, or database changes. This feature is repository-only.
assert "MachineBraveFocusWitness" not in qml
assert "MachineBraveHostPairingReview" not in qml
assert "MachineBraveFocusWitness" not in restore
assert "MachineBraveFocusWitness" not in legacy
pilot_manifest = json.loads(pilot)
assert pilot_manifest["permissions"] == []
assert pilot_manifest["host_permissions"] == []
assert pilot_manifest["optional_permissions"] == ["nativeMessaging"]
assert pilot_manifest["incognito"] == "not_allowed"
assert "SCHEMA_VERSION = 1" in legacy
assert qml.count("Process {") == 15

print("MACHINE Brave focus // no host binding, move or identity grant PASS")
