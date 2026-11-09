#!/usr/bin/env python3
"""MACHINE MARK NOW must use existing durable v2 SAVE, not session markers."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
qml = (ROOT / "widgets/TimeW.qml").read_text()
bridge = (ROOT / "services/time/MachineSaveBridgeV2.py").read_text()
timeline = (ROOT / "services/time/MachineTimelinePolicy.js").read_text()
legacy = (ROOT / "services/time/MachineCheckpointStore.py").read_text()
geometry = (ROOT / "services/time/MachineGeometryStoreV2.py").read_text()

for item in (
    'property string machinePersistentMarkDraft',
    'property string machinePersistentMarkStatus',
    'property string machineSaveBridgeOrigin',
    'function machineRequestPersistentMark()',
    'machineSaveBridgeOrigin = origin || action',
    'machineBeginSaveBridge("save", {',
    'label: label, review: null, selection: null',
    'const label = "MARK // " +',
    'clockReadoutText',
    'machinePersistentMarkStatus = "MARK SAVED + VERIFIED // "',
    'machinePersistentMarkDraft = "";',
    'MARK MAY BE STORED // CHECK STORED BEFORE RETRY',
    'MARK OUTCOME UNKNOWN // CHECK STORED BEFORE RETRY',
    'MARK BLOCKED // ',
    'id: machinePersistentMarkRow',
    'id: machinePersistentMarkInput',
    'id: machinePersistentMarkButton',
    '"MARK NOW"',  # ActionButton label is conditional on saving state
    'maximumLength: 40',
    'onTextEdited: timew.machinePersistentMarkDraft = text',
    'onAccepted: timew.machineRequestPersistentMark()',
    'onLeftClicked: timew.machineRequestPersistentMark()',
    'MARK SAVES GEOMETRY IN STORED',
    'machineStoreStatus = "SAVED // GEOMETRY READBACK VERIFIED"',
    'data.verification.status === "readback_verified"',
    'label: "TIME ONLY"',
    'LEGACY MARKERS // MEMORY ONLY // NOT RESTORABLE',
    'onLeftClicked: timew.addMachineMarker()',
    'model: timew.machineMarkers',
    'onLeftClicked: timew.machineRequestFullSave()',
    'onLeftClicked: timew.machineRequestCustomSave()',
    'label: "SAVE NOTES"',
    'RESTORE DESKTOP',
):
    assert item in qml, item

mark_fn = qml.split('function machineRequestPersistentMark()', 1)[1].split(
    'function machineRequestCustomInspect()', 1)[0]
assert 'machineBeginSaveBridge("save"' in mark_fn
assert 'addMachineMarker(' not in mark_fn
assert 'machineMarkers =' not in mark_fn
assert 'machineMarkerNextId' not in mark_fn
assert 'machinePersistentMarkDraft.trim()' in mark_fn
assert 'typed.length > 40' in mark_fn

# The normal marker must be a full geometry checkpoint and can be reopened
# through exactly the same atomic reader; no standalone MARK database writer.
assert 'return _verified_receipt(saved' in bridge
assert 'result = save_request(_decode_request())' in bridge
assert 'load_geometry' in bridge
assert 'save_pair' in geometry
assert 'SCHEMA_VERSION = 1' in legacy
assert 'function createMarker' in timeline  # old session-only state preserved

assert qml.count('Process {') == 15
assert qml.count('onTextEdited:') == 19
roots = re.findall(r'^    (?:readonly )?property\s+\w+\s+(\w+)\s*[:=]',
                   qml, flags=re.MULTILINE)
assert roots and len(roots) == len(set(roots)), 'Duplicate QML root property'

# Basic QML delimiter balance cannot replace actual Quickshell runtime tests.
pairs = {')': '(', '}': '{', ']': '['}
stack, mode, i = [], 'code', 0
while i < len(qml):
    c = qml[i]
    n = qml[i + 1] if i + 1 < len(qml) else ''
    if mode == 'line':
        if c == '\n':
            mode = 'code'
    elif mode == 'block':
        if c == '*' and n == '/':
            mode = 'code'
            i += 1
    elif mode in ('"', "'"):
        if c == '\\':
            i += 1
        elif c == mode:
            mode = 'code'
    elif c == '/' and n == '/':
        mode = 'line'
        i += 1
    elif c == '/' and n == '*':
        mode = 'block'
        i += 1
    elif c in ('"', "'"):
        mode = c
    elif c == '/' and n == '/':
        mode = 'line'
        i += 1
    elif c == '/' and n == '*':
        mode = 'block'
        i += 1
    elif c in '({[':
        stack.append(c)
    elif c in ')}]':
        assert stack and stack.pop() == pairs[c], 'Unbalanced QML punctuation'
    i += 1
assert not stack
print('MACHINE MARK NOW // durable SAVE wiring, legacy isolation and QML guards PASS')
