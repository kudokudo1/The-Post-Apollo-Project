#!/usr/bin/env python3
"""STORED editing source contract, including old SAVE and RESTORE seams."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/TimeW.qml").read_text()
bridge = (root / "services/time/MachineSaveBridgeV2.py").read_text()
owner = (root / "services/time/MachineCheckpointAnnotations.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()

for token in (
    'machineNotesEditorOpen', 'machineNotesCheckpointId',
    'machineNotesLoaded', 'machineNotesDraftName', 'machineNotesDraftText',
    'machineNotesDirty', 'machineNotesInputValid',
    'machineNotesNameOverlay', 'machineRequestNotesList()',
    'machineRequestNotesRead()', 'machineSaveNotes()',
    'machineAcceptNotesResponse(data)', 'machineNotesDiscard()',
    'machineNotesNameForItem(timew.machineSavedItem)',
    'label: "SAVE NOTES"', 'label: "CANCEL // CLOSE"',
    'onLeftClicked: timew.machineSaveNotes()',
    'onLeftClicked: timew.machineNotesDiscard()',
    '"notes-update"', '"notes-list"', '"notes-read"',
    'machineSaveBridgeProcess.write(', 'machineSaveBridgePayload',
    '"CHECKPOINT NOTES STALE"', 'NOTES STALE // REFRESH BEFORE EDITING',
    'UNSAVED NOTES // SAVE OR CANCEL FIRST',
    'ORIGINAL CAPTURE AND GEOMETRY STAY UNTOUCHED',
    'id: machineStoredNotesEditor', 'TextArea {',
    'onTextEdited: timew.machineNotesDraftName = text',
    'onTextChanged: timew.machineNotesDraftText = text',
    'maximumLength: 48', 'textFormat: TextEdit.PlainText',
):
    assert token in qml, token

for token in (
    'from MachineCheckpointAnnotations import (',
    'list_annotation_names()', 'get_annotation(argv[1])',
    'set_annotation(', '_decode_notes_input()',
    '"CHECKPOINT NOTES STALE"', '"notes-update"',
):
    assert token in bridge, token

assert 'legacy.connect(writable=False)' in owner
assert 'BEGIN IMMEDIATE' in owner
assert 'WHERE a.checkpoint_id IN' in owner
assert 'SELECT a.checkpoint_id, a.display_name, a.revision' in owner
sql = owner.split('def list_annotation_names():', 1)[1].split(
    'def set_annotation(', 1)[0]
assert 'SELECT a.checkpoint_id, a.display_name, a.revision' in sql
assert 'a.note' not in sql
assert 'MachineCheckpointAnnotations' not in legacy
assert 'SCHEMA_VERSION = 1' in legacy
assert 'id: machineSaveBridgeProcess' in qml
assert qml.count('Process {') == 15, "No new Quickshell process is authorized"
assert qml.count('onTextEdited:') == 19  # Includes durable MARK name field
assert 'SAVE DESKTOP' in qml and 'VERIFY SAVED GEOMETRY' in qml
assert 'RESTORE DESKTOP' in qml and 'machineAdvancedOpen' in qml
assert 'MachineCheckpointNotesCLI.py' not in qml

# Basic lexical QML delimiter check; full native Quickshell still requires
# operator's local runtime acceptance.
pairs = {')': '(', '}': '{', ']': '['}
stack = []
mode = 'code'
i = 0
while i < len(qml):
    ch = qml[i]
    nxt = qml[i + 1] if i + 1 < len(qml) else ''
    if mode == 'line':
        if ch == '\n':
            mode = 'code'
    elif mode == 'block':
        if ch == '*' and nxt == '/':
            mode = 'code'
            i += 1
    elif mode in ('"', "'"):
        if ch == '\\':
            i += 1
        elif ch == mode:
            mode = 'code'
    elif ch == '/' and nxt == '/':
        mode = 'line'
        i += 1
    elif ch == '/' and nxt == '*':
        mode = 'block'
        i += 1
    elif ch in ('"', "'"):
        mode = ch
    elif ch in '({[':
        stack.append(ch)
    elif ch in ')}]':
        assert stack and stack.pop() == pairs[ch], 'QML delimiters mismatched'
    i += 1
assert not stack, "QML delimiters unmatched"

properties = re.findall(
    r"^    (?:readonly )?property\s+\w+\s+(\w+)\s*[:=]",
    qml, flags=re.MULTILINE)
assert properties, "Root properties unavailable"
assert len(properties) == len(set(properties)), "Duplicate TimeW root property"
print("MACHINE STORED // notes UI, preserved processes, unique QML props PASS")
