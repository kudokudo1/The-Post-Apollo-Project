#!/usr/bin/env python3
"""MACHINE M1g: SQLite saves are operator-triggered and isolated from Hospital."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
store = (root / "services/time/MachineCheckpointStore.py").read_text(encoding="utf-8")
for term in (
    'property bool machineStoreBusy: false',
    'property bool machineStoredViewOpen: false',
    'function machineSaveCheckpoint()',
    'function machineShowSavedCheckpoints()',
    'function machineListCheckpoints()',
    'function machineOpenSavedCheckpoint()',
    'function machineStepSavedCheckpoint(delta)',
    'function machineAcceptStoreResponse(data)',
    'machineSelectionValidation.status !== "ready"',
    'selected.schema_version = 1;',
    'selected.captured_at_utc = machineCapturePreview.captured_at_utc;',
    'machineStoreRequest("save", chosen, "")',
    'machineStoreRequest("list", null, "")',
    'machineStoreRequest("load", null, machineSavedItem.id)',
    'id: machineStoreProcess',
    'stdinEnabled: true',
    'machineStoreProcess.write(timew.machineStorePayload + String.fromCharCode(10))',
    'onLeftClicked: timew.machineSaveCheckpoint()',
    'onLeftClicked: timew.machineShowSavedCheckpoints()',
    'onLeftClicked: timew.machineOpenSavedCheckpoint()',
    'label: "OPEN SAVED METADATA"',
    'label: "REFRESH STORED"',
    'read_only === true',
    'NO SCREENSHOTS OR RESTORATION ACTIVE',
    'MARKERS ARE TIMESTAMPS ONLY // LOST ON RESTART',
):
    assert term in qml, f"missing guarded MACHINE storage UI: {term}"

assert 'Quickshell.shellPath("services/time/MachineCheckpointStore.py")' in qml
assert '"python3", "-B", "-I"' in qml
assert 'machineStoredViewOpen = true;' in qml
assert 'function restoreDesktop(' not in qml
assert 'function captureDesktopCheckpoint(' not in qml
assert 'FileView {' not in qml and 'JsonAdapter {' not in qml
assert 'execDetached(' not in qml
assert 'swaymsg' not in qml
assert 'post-apollo" / "machine" / "machine.db"' in store
assert 'post-apollo" / "hospital"' not in store
assert 'O_NOFOLLOW' in store
assert '0o700' in store and '0o600' in store
assert 'journal_mode=WAL' in store and 'synchronous=FULL' in store
assert 'readline(MAX_INPUT_BYTES + 1)' in store
assert 'function restoreDesktop(' not in store
assert 'subprocess' not in store
print("TIMEW MACHINE SQLITE UI CONTRACT: PASS / EXPLICIT SAVE-LOAD / NO RESTORE")
