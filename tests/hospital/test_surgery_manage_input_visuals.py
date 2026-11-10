#!/usr/bin/env python3
"""Manage input palette, Reception-style microphone, and active Floor repo autofill."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
view = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
reception = (root / "widgets/HospitalReceptionistView.qml").read_text()
policy = (root / "services/hospital/HospitalGitHubOwnerPolicy.js").read_text()
errors = []

def check(ok, msg):
    if not ok:
        errors.append(msg)

short = view.split("    component ManagerField: Column {", 1)[1].split(
    "    component ManagerArea: Column {", 1)[0]
long = view.split("    component ManagerArea: Column {", 1)[1]

for label, fragment in (("single-line", short), ("multiline", long)):
    check('color: Colors.magenta' in fragment,
          label + " operator text must be magenta")
    check('selectionColor: Colors.magenta' in fragment
          and 'selectedTextColor: Colors.black' in fragment,
          label + " selection must remain readable")
    check('cursorDelegate: Rectangle {' in fragment
          and 'width: 2' in fragment
          and 'color: Colors.orange' in fragment,
          label + " must have an orange insertion cursor")
    check('border.color: Colors.orange' in fragment,
          label + " text box must have an orange border")
    check('color: Colors.black' in fragment,
          label + " input background must remain black")
check('import QtQuick.Effects' in view
      and 'import Qt5Compat.GraphicalEffects' in view,
      "Use existing Reception shadow components")
check('text: "🗣︎"' in reception
      and 'text: "🗣︎"' in long
      and 'Colors.omnitrix' in long
      and 'RectangularShadow {' in long
      and 'layer.effect: DropShadow {' in long
      and 'micMouse.containsMouse' in long,
      "Match Reception talking-person glyph, green glow and orange hover")
check('onClicked: root.toggleDictation(managerArea.voiceKey)' in long
      and 'root.speechInputService.stopRecording(false)' not in long
      and 'root.toggleDictation(managerArea.voiceKey)' in view,
      "Mic must toggle the established field-specific STOP without submission")
check('label: "CANCEL"' in long
      and 'root.cancelDictation()' in long,
      "Maintain explicit red microphone cancellation")
check('suggestedRepository: githubService.repoSlug' in host
      and '|| patientService.repository' in host,
      "Autofill from active Floor GitHub origin, fall back to Patient")
check('id: roomOwnerField' in view
      and 'id: roomRepoField' in view
      and 'label: "USE CURRENT REPO"' in view
      and 'onTriggered: root.useCurrentPatient()' in view,
      "Keep owner/repository separately editable and allow explicit current repo selection")
check('CURRENT FLOOR REPOSITORY //' in view
      and 'root.suggestedRepository' in view,
      "Show provenance of the repo that will be used for the new Room")
check('if (!root.roomOwnerManuallyEdited)' in view
      and 'if (!root.roomRepositoryManuallyEdited)' in view
      and 'onSuggestedRepositoryChanged:' in view,
      "Automatic updates must not clobber unsaved manual owner or repo edits")
check('root.roomOwnerManuallyEdited = false;' in view
      and 'root.roomRepositoryManuallyEdited = false;' in view
      and 'root.applyRoomSuggestions();' in view
      and 'onCreated: function(room)' in view,
      "Confirmed Room save should prepare a fresh current-Floor default")
check('function suggestion(currentPatient, githubLogin)' in policy
      and 'if (patient.owner) return {owner: patient.owner, repository: patient.repository,' in policy,
      "An active foreign repository must keep its original GitHub owner")
for bad in ('session-create', 'git switch', 'git checkout', 'gh auth login'):
    check(bad not in short + long,
          "Field styling must not gain executable capabilities: " + bad)
if errors:
    print("HOSPITAL MANAGE INPUT VISUALS // FAIL")
    for msg in errors:
        print(" - " + msg)
    raise SystemExit(1)
print("HOSPITAL MANAGE INPUT VISUALS // PASS // Reception mic, orange boxes/cursor, live Floor repo default")
