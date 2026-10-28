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
date_input = (root / "widgets/GitHubProjectsDateInput.qml").read_text()

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
    'onAccepted: root.save(text, false)',
    'NO ITERATION IDS EXPOSED',
):
    assert needle in editor, needle

# Keep the new popup outside the horizontally clipped Flickable.
assert table.index("GitHubProjectsFieldEditor {") > table.index(
    "NeonScrollBar { flickable: tableScroll; handleStyle: \"star\""
)

# UI must show the pencil yellow independently of the value text.
assert 'label: editCell.value || "—"' in table
assert 'text: "✎"' in table
assert 'color: Colors.yellow' in table

# Popup belongs to the whole Projects shell, not the Table's short height.
assert 'property Item editorHost: null' in table
assert 'parent: root.editorHost ? root.editorHost : root' in table
assert 'editorHost: root' in owner
assert 'onVisibleChanged: { if (!visible) closeEditor(); }' in table
assert 'height: Math.max(150, Math.min(root.isDate ? 225 : 228, root.height - 10))' in editor
assert 'height: Math.max(25, panel.height - 101)' in editor

# Status/Progress uses the project's actual three (or operator-customized)
# single-select options. Never fake IDs just to show 3 buttons.
assert 'root.projectService.editableChoices(fieldKind)' not in editor  # root binds through projectService
assert 'projectService.editableChoices(fieldKind)' in editor
assert 'root.save(modelData.id, false)' in editor
assert '"Todo,In Progress,Done"' in service

# The date picker owns THREE independently typed fields and step controls.
for part in ('caption: "DAY"', 'caption: "MONTH"', 'caption: "YEAR"'):
    assert part in date_input
assert 'id: dayPart' in date_input
assert 'id: monthPart' in date_input
assert 'id: yearPart' in date_input
assert 'validator: RegularExpressionValidator {' in date_input
assert 'cursorDelegate: Rectangle {' in date_input
assert 'color: Colors.orange' in date_input
assert 'label: "↑"' in date_input
assert 'label: "↓"' in date_input
assert 'function isoValue()' in date_input
assert 'year.padStart(4, "0") + "-"' in date_input
assert 'month.padStart(2, "0") + "-"' in date_input
assert 'day.padStart(2, "0")' in date_input
assert 'onSubmitted: function(isoDate) { root.save(isoDate, false); }' in editor
assert 'root.isDate ? dateInput.isoValue() : valueEditor.text' in editor

# Item already owns the auto-generated focusChanged signal for its inherited
# focus property. Do not declare a root method with the same name.
assert "function handleEditorFocusChanged(editor, active)" in date_input
assert "part.focusOwner.handleEditorFocusChanged(entry, activeFocus);" in date_input
assert "function focusChanged(" not in date_input

# Missing fields require a second explicit click before any schema mutation,
# and iteration is never synthesized from guessed IDs.
assert 'property bool setupArmed: false' in editor
assert 'if (root.setupArmed)' in editor
assert 'root.projectService.setupMissingField(root.fieldKind)' in editor
assert 'function setupMissingField(kind)' in service
assert 'if (busy || !number || fields.length === 0' in service
assert '|| editableField(kind)' in service
assert 'exec gh project field-create "$1"' in service
assert '"High,Medium,Low"' in service
assert '"SINGLE_SELECT"' in service
assert '"DATE"' in service
assert 'FIELD SETUP UNAVAILABLE // CREATE ITERATIONS IN GITHUB' in service
assert 'label: "OPEN GITHUB PROJECT FIELDS"' in editor

# Editor option rows now fill their entire area, without a reserved star
# scrollbar lane. Scrolling continues through the Flickable itself.
assert "width: choiceScroll.width" in editor
assert "width: Math.max(0, choiceScroll.width - 20)" not in editor
option_area = editor.split('id: choiceScroll', 1)[1].split('id: missingInfo', 1)[0]
# The shared structural contract still sees a scrollbar instance, but the
# operator-facing menu reserves zero pixels and never shows or captures it.
assert "NeonScrollBar {" in option_area
assert "flickable: choiceScroll" in option_area
assert "reserveSpace: false" in option_area
assert "visible: false" in option_area
assert "interactive: false" in option_area
assert "wheelEnabled: false" in option_area
for kind, color in (
    ("status", "yellow"),
    ("priority", "magenta"),
    ("iteration", "orange"),
):
    assert f'fieldKind === "{kind}" ? Colors.{color}' in editor
    assert f'accent: Colors.{color}' in table
    assert f'value: "{kind.upper()}"' in table
assert "accentColor: root.optionAccent" in editor
assert "idleBorderColor: root.optionAccent" in editor
assert "hoverBorderColor: root.optionAccent" in editor
assert "selectedBorderColor: root.optionAccent" in editor
assert "hoverBorderColor: editCell.accent" in table

# Archive shares one explicit interaction grammar in all four places.
roadmap = (root / "widgets/GitHubProjectsRoadmapView.qml").read_text()
archive = (root / "widgets/GitHubProjectsArchiveButton.qml").read_text()
for view, count in ((owner, 1), (table, 1), (roadmap, 2)):
    assert view.count("GitHubProjectsArchiveButton {") == count
    assert view.count('label: "OPEN"') == count
    assert view.count('root.armOrRunItem(') >= count
    assert view.count('root.projectService.archiveItem(') == count
    # Never let replacement of Archive swallow its neighboring OPEN button.
    assert view.count('root.openProjectItem(') >= count
for rule in (
    'label: root.armed ? "CONFIRM" : "ARCHIVE"',
    "idleForegroundColor: Colors.white",
    "hoverForegroundColor: Colors.white",
    "pressedForegroundColor: Colors.white",
    "selectedForegroundColor: Colors.white",
    "keyboardSelectedForegroundColor: Colors.white",
    "idleBorderColor: Colors.orange",
    "selectedBorderColor: Colors.orange",
    "height: 26",
    "onTriggered: root.triggered()",
):
    assert rule in archive, rule
assert "GitHubProjectsArchiveButton {\n                                                            width: 70\n                                                            height: 20" in owner
assert "GitHubProjectsArchiveButton {\n                                        width: 76" in table
assert roadmap.count('GitHubProjectsArchiveButton {') == 2
assert roadmap.count('height: 24\n                                        anchors.verticalCenter: parent.verticalCenter\n                                        armed: root.itemActionArmed("archive"') == 2

print("PROJECTS EDITABLE TABLE // CONTRACT PASS")
