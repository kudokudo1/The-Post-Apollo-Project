#!/usr/bin/env python3
"""MACHINE V2 read-only review UI: explicit click, no restored-authority claim.

Static source contract, not live Qt/SwayPX visual verification.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
qml = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
review = (ROOT / "services/time/MachineRestoreReviewV2.py").read_text(encoding="utf-8")
restore = (ROOT / "services/time/MachineRestoreCheckpoint.py").read_text(encoding="utf-8")

for expected in (
    'property bool machineV2ReviewBusy: false',
    'property string machineV2ReviewKey: ""',
    'function machineInvalidateV2Review()',
    'function machineRequestV2Review()',
    'function machineStepV2ReviewItem(delta)',
    'id: machineV2ReviewProcess',
    'running: false',
    'Quickshell.shellPath("services/time/MachineRestoreReviewV2.py")',
    '"review", machineV2ReviewKey',
    'onLeftClicked: timew.machineRequestV2Review()',
    'label: "RESTORE DESKTOP"',
    'onLeftClicked: timew.machineRestoreSelectedCheckpoint()',
    'Quickshell.shellPath("services/time/MachineRestoreCheckpoint.py")',
    'data.kind === "machine-v2-restore-review-v1"',
    'data.checkpoint_id === timew.machineV2ReviewKey',
    'timew.machineV2ReviewKey !== timew.machineSavedItem.id',
    'data.read_only === true && data.restore_allowed === false',
    'data.browser_tabs_restorable === false',
    'data.exact_geometry_restore_verified === false',
    'data.live_window_identity_verified === false',
    'data.checkpoint_keys_are_live_identity === false',
    'data.requires_fresh_recheck === true',
    'data.safe_actions.length === 0',
    'item.identity_verified === false',
    'item.action_allowed === false',
    'items.length === counts.saved_windows',
    'data.status === "legacy_only"',
    '"AMBIGUOUS_APP_INSTANCES"',
    '"OBSERVED_GEOMETRY_AGREEMENT_UNTRUSTED"',
    '"V2 REVIEW UNAVAILABLE // NO APPROVAL"',
    'textFormat: Text.PlainText',
    'timew.machineV2ReviewItem.classification',
    'machineInvalidateV2Review();',
    'machineV2ReviewBusy',
    'text: "OBSERVATION IS NOT RESTORE AUTHORIZATION // BRAVE TABS NOT RESTORED"',
):
    assert expected in qml, expected

assert qml.count("Process {") == 17
assert "id: machineM5PreviewProcess" in qml
assert "MachineV3LocalPreviewUiRead.py" in qml
assert qml.count("id: machineV2ReviewProcess") == 1
assert qml.count("onLeftClicked: timew.machineRequestV2Review()") == 1
assert qml.count("onLeftClicked: timew.machineRestoreSelectedCheckpoint()") == 1

fn_start = qml.index("function machineRequestV2Review()")
fn_end = qml.index("function machineStepV2ReviewItem(delta)", fn_start)
review_fn = qml[fn_start:fn_end]
assert review_fn.count("machineV2ReviewProcess.exec(") == 1
assert "MachineRestoreReviewV2.py" in review_fn
assert "MachineRestoreCheckpoint.py" not in review_fn
assert "machineApplyOneProcess" not in review_fn
assert "machineAutoRestoreProcess" not in review_fn
assert "Timer" not in review_fn
assert "onMenuOpenChanged: timew.machineRequestV2Review()" not in qml
assert "Component.onCompleted: timew.machineRequestV2Review()" not in qml
assert "onSelectedModeChanged: timew.machineRequestV2Review()" not in qml
assert qml.count("machineV2ReviewProcess.exec(") == 1

# Original V1 RESTORE remains independent.
assert "def restore_checkpoint(" in restore
assert "MoveApprovalGate().review" in restore
assert "apply_one" in restore
assert "no_automatic_retry" in restore

# The V2 backend is still deny-only, not an executable restore command.
for required in ('"read_only": True', '"restore_allowed": False',
                 '"browser_tabs_restorable": False',
                 '"exact_geometry_restore_verified": False',
                 '"live_window_identity_verified": False',
                 '"requires_fresh_recheck": True', '"safe_actions": []'):
    assert required in review, required
assert "def inspect(" in review
assert "live_reader=stable_geometry" in review
assert "subprocess.Popen" not in review
assert "gtk-launch" not in review

print("MACHINE V2 UI // explicit read-only review, stale denial, legacy restore preserved PASS")
