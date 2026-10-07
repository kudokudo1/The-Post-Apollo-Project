from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "hospital" / "HospitalAssignmentService.qml"
VIEW = ROOT / "widgets" / "HospitalAssignmentsView.qml"
HOSPITAL = ROOT / "widgets" / "HospitalW.qml"

for path in (SERVICE, VIEW, HOSPITAL):
    assert path.is_file(), path

service = SERVICE.read_text()
for needle in (
    'property string roomId: ""',
    'property var assignments: []',
    'readonly property var activeAssignment:',
    'function refresh()',
    'function createAssignment(',
    'function updateAssignment(',
    'function activateAssignment(assignmentIdValue)',
    'function startAllReady()',
    'function setAssignmentStatus(assignmentIdValue, statusValue)',
    '"assignments"',
    '"assignment-create"',
    '"assignment-update"',
    '"assignment-activate"',
    '"orchestrate-ready"',
    '"assignment-status"',
    '"READ"',
    '"EDIT"',
    '"TEST"',
    '"COMMIT"',
    '"PUSH"',
    '"OPEN_PR"',
    '"INTEGRATE"',
):
    assert needle in service, needle

assert "Quickshell.execDetached" not in service

view = VIEW.read_text()
for needle in (
    'required property var assignmentService',
    'HOSPITAL // ORDERS // ROOM ASSIGNMENTS',
    '## GOAL',
    '## CONSTRAINTS',
    '## DEFINITION OF DONE',
    '## CHECKLIST',
    '## OPEN QUESTIONS',
    '"READY"',
    '"ACTIVATE"',
    '"PAUSE"',
    '"COMPLETE"',
    '"CANCEL"',
    'assignmentService.createAssignment(',
    'assignmentService.updateAssignment(',
    'assignmentService.activateAssignment(',
    'assignmentService.startAllReady()',
    'assignmentService.setAssignmentStatus(',
    'permissionsInput.text',
    'phaseInput.text',
    '"START READY"',
    'assignmentService.orchestrating',
):
    assert needle in view, needle

hospital = HOSPITAL.read_text()
for needle in (
    'function openRoomAssignments()',
    'root.operationsSurface = "assignments";',
    'HospitalAssignmentService {',
    'id: assignmentService',
    'roomId: root.selectedRoomTeam',
    'id: roomOrdersButton',
    '"ORDERS // "',
    'assignmentService.assignmentCount',
    'assignmentService.activeAssignment',
    'HospitalAssignmentsView {',
    'id: assignmentsView',
    'assignmentService: assignmentService',
):
    assert needle in hospital, needle

# Provider staffing persistence remains owned by PR #53. Orders integration
# must not invade the conversation/provider adapter while that work is open.
for forbidden in (
    "HospitalRoomConversationAdapter.qml",
    "providerSessionId =",
):
    assert forbidden not in view, forbidden
    assert forbidden not in service, forbidden

print("hospital durable Assignment/Orders contracts: PASS")
