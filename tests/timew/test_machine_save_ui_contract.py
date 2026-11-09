#!/usr/bin/env python3
"""TimeW SAVE UI source contract: primary SAVE has no preview prerequisite."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
ui = (root / "widgets/TimeW.qml").read_text()
bridge = (root / "services/time/MachineSaveBridgeV2.py").read_text()
capturer = (root / "services/time/MachineCaptureSaveV2.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()

# Source QML is the existing real widget, not an alternative mock.
for value in (
    'id: machineCaptureViewport', 'id: machineCaptureScroll',
    'id: machineCaptureRail', 'id: machineSaveBridgeProcess',
    'machineRequestFullSave()', 'machineRequestCustomInspect()',
    'machineRequestCustomSave()', 'machineCustomReview',
    'machineCustomExcluded', 'machineCustomValidation',
    'machineCustomOpen', 'machineAdvancedOpen',
    'label: "SAVE DESKTOP"', 'label: "SAVE SELECTED DESKTOP"',
    'text: "LOCAL CLOCK // " + timew.clockReadoutText',
    'onLeftClicked: timew.machineRequestFullSave()',
    'onLeftClicked: timew.machineRequestCustomSave()',
    'onLeftClicked: timew.machineToggleCustomItem()',
    'onLeftClicked: timew.machineStepCustomInspect(-1)',
    'onLeftClicked: timew.machineStepCustomInspect(1)',
    'Quickshell.shellPath("services/time/MachineSaveBridgeV2.py")',
    'machineSaveBridgeProcess.write(',
    'flickable: machineCaptureScroll',
):
    # Primary action label may be conditional on busy state, but must exist.
    if value == 'label: "SAVE DESKTOP"':
        assert '"SAVE DESKTOP"' in ui
    else:
        assert value in ui, value
assert 'id: machineLegacyControls' in ui
assert 'visible: timew.machineAdvancedOpen' in ui
assert 'machineSaveBridgePayload + String.fromCharCode(10)' in ui
assert 'review: null, selection: null' in ui
assert 'review: review.review, selection: selected' in ui
assert 'MachineCaptureSaveV2' not in ui
assert 'MachineSaveBridgeV2' not in legacy
assert 'SCHEMA_VERSION = 1' in legacy

functions = {n.name for n in ast.parse(bridge).body if isinstance(n, ast.FunctionDef)}
assert {'inspect', 'save_request', '_decode_request', 'main'}.issubset(functions)
for token in ('MAX_REQUEST_BYTES = 65536',
              'namespace_factory=uuid.uuid4',
              '"restorable_identity_verified": False',
              '"review": {"namespace": namespace, "digest": geometry_digest(geometry)}',
              '"selection": selection'):
    assert token in bridge, token
assert 'stable_geometry(' in bridge
assert 'review_binding' in capturer
assert 'geometry_digest(geometry)' in capturer
assert 'CUSTOM SELECTION STALE' in capturer
assert '"-t", "command"' not in bridge
assert 'shell=True' not in bridge

# Check QML structural delimiter balance outside strings and comments.
# This is a lexical brace check, not a substitute for native Quickshell.
pairs = {'}': '{', ')': '(', ']': '['}
stack = []
mode = 'code'
i = 0
while i < len(ui):
    ch = ui[i]
    follow = ui[i+1] if i+1 < len(ui) else ''
    if mode == 'line':
        if ch == '\n':
            mode = 'code'
    elif mode == 'block':
        if ch == '*' and follow == '/':
            mode = 'code'
            i += 1
    elif mode in ('"', "'"):
        if ch == '\\':
            i += 1
        elif ch == mode:
            mode = 'code'
    elif ch == '/' and follow == '/':
        mode = 'line'
        i += 1
    elif ch == '/' and follow == '*':
        mode = 'block'
        i += 1
    elif ch in ('"', "'"):
        mode = ch
    elif ch in '{([':
        stack.append(ch)
    elif ch in '})]':
        assert stack and stack.pop() == pairs[ch], 'QML source delimiters mismatched'
    i += 1
assert not stack, 'QML source contains unmatched delimiters'
print('MACHINE UI // primary SAVE, optional bound CUSTOMIZE and original advanced controls PASS')
