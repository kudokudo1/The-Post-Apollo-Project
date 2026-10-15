#!/usr/bin/env python3
"""Projects editable table: source/authority contract.

This is deliberately not a claim that the user's live Quickshell UI was
rendered or that any real GitHub Project item was modified.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
service = (root / "services/github/GitHubProjectsService.qml").read_text()
table = (root / "widgets/GitHubProjectsTableView.qml").read_text()
editor = (root / "widgets/GitHubProjectsFieldEditor.qml").read_text()
owner = (root / "widgets/GitHubProjectsView.qml").read_text()

# Expose actual edit affordances for eligible project fields, not empty
# decorative controls. Only draft titles may be changed inside the project.
for kind in ("status", "priority", "iteration", "start", "target", "title"):
    assert f'root.beginEdit(tableRow.modelData, "{kind}")' in table, kind
assert 'root.projectService.isDraftItem(tableRow.modelData)' in table
assert 'visible: !root.projectService.isDraftItem(tableRow.modelData)' in table
assert "component EditableCell: Item {" in table
assert "Components.ActionButton {" in table
assert "property bool editOpen: false" in table
assert "GitHubProjectsFieldEditor {" in table
assert "onDismissRequested: root.closeEditor()" in table
assert "keyboardHost: root.keyboardHost" in owner
assert "onSelectedProjectIndexChanged()" in table
assert 'if (success && (operation === "edit-field"' in table

# Field identities and option IDs must come from the selected project's
# authoritative schema, never a color/column name or arbitrary typed ID.
assert "function editableFieldName(kind)" in service
assert "function editableField(kind)" in service
assert "function editableChoices(kind)" in service
assert "function editItemField(item, kind, value, clearValue)" in service
assert 'option.id || option.iterationId' in service
assert 'id && label' in service
assert 'return type === "DRAFTISSUE"' in service
assert 'items.some(function(row) { return itemId(row) === targetId; })' in service
assert 'if (busy || !selectedNumber() || !targetId || !projectId' in service
assert 'match.length !== 1' in service
assert '--single-select-option-id' in service
assert '--iteration-id' in service
assert '--date' in service
assert '--clear' in service
assert '--title' in service
assert '"PROJECTV2FIELD"' in service

# A source-level fixture catches accidental conversion to a literal \\d
# matcher. Real date parsing still happens at runtime before invoking gh.
assert r'/^\d{4}-\d{2}-\d{2}$/' in service
assert r'/^\\d{4}' not in service
assert 'parsed.toISOString().slice(0, 10) === text' in service

# Fixed shell command with positional argument quoting; no user text is
# concatenated into the shell source.
command = service.split('function editItemField(', 1)[1].split(
    'function parseProjects(', 1
)[0]
assert 'targetId, projectId, fieldId, editFlag, clean' in command
assert 'exec gh project item-edit --id "$1" --project-id "$2" --title "$3" --format json' in command
assert 'exec gh project item-edit --id "$1" --project-id "$2" --field-id "$3"' in command
assert 'if [ "$4" = "--clear" ]' in command
assert 'if (clearValue)' in command

# UI intent and Syntagma default input grammar.
for needle in (
    "signal dismissRequested()", "onVisibleChanged",
    'text: "EDIT // " + root.fieldLabel',
    "font.family: \"GohuFont 11 Nerd Font Mono\"",
    "color: Colors.magenta",
    "cursorDelegate: Rectangle {",
    "color: Colors.orange",
    "Keys.onEscapePressed:",
    "label: root.clearArmed ? \"CLEAR?\" : \"CLEAR\"",
    "destructive: true",
    "root.save(modelData.id, false)",
    'root.save(valueEditor.text, false)',
    "mountingParent: panel",
    'NO ITERATION IDS EXPOSED',
):
    assert needle in editor, needle

# Keep the new popup outside the horizontally clipped Flickable.
assert table.index("GitHubProjectsFieldEditor {") > table.index(
    "NeonScrollBar { flickable: tableScroll; handleStyle: \"star\""
)

print("PROJECTS EDITABLE TABLE // CONTRACT PASS")
