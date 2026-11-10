#!/usr/bin/env python3
"""Conversation-style Surgery onboarding is a safe local draft, not a model or PX launch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
view = (ROOT / "widgets/HospitalWorkforceManagerView.qml").read_text()
policy = (ROOT / "services/hospital/HospitalConversationIntakePolicy.js").read_text()
host = (ROOT / "widgets/HospitalW.qml").read_text()
errors = []
def check(ok, msg):
    if not ok: errors.append(msg)

check('HospitalWorkforceManagerView {' in host and 'id: inlineWorkforceManager' in host,
      "Must remain in existing Surgery roster, not a new window")
check('import "../services/hospital/HospitalConversationIntakePolicy.js" as ConversationIntakePolicy' in view,
      "Exact pure policy imported as a local starter template")
check('root.selectMode("SETUP")' in view
      and 'root.mode === "SETUP"' in view
      and 'START HERE // DESCRIBE A NEW AI JOB' in view
      and 'NEW AI // TELL HOSPITAL WHAT YOU WANT TO WORK ON' in view,
      "Operator can open the new natural-language intake inside Surgery")
check('id: intakeBriefField' in view
      and 'editHeight: 156' in view
      and 'onEdited: root.invalidateIntake()' in view
      and 'onTextChanged: managerArea.edited()' in view,
      "Brief edits invalidate the preview and have a dedicated larger editor")
check('ConversationIntakePolicy.proposal(intakeBriefField.value)' in view
      and 'root.intakeSource !== intakeBriefField.value' in view
      and 'LOCAL STARTER DRAFT // NOT AI-GENERATED' in view,
      "Snapshot-based draft requires exact current brief and honest model status")
check('function applyIntake(section)' in view
      and 'roomNameField.value = p.roomName' in view
      and 'workerNameField.value = p.workerName' in view
      and 'root.workerRole = p.role' in view
      and 'jobGoalField.value = p.goal' in view
      and 'jobPermissionsField.value = "READ"' in view,
      "Draft transfers only to existing editable Room / worker / job fields")
check('label: "EDIT ROOM"' in view
      and 'label: "EDIT WORKER"' in view
      and 'label: "EDIT JOB"' in view,
      "Each record can be individually inspected before saving")
check('function confirm(kind)' in view
      and 'armedKey !== signature(kind)' in view
      and 'roomCreate.create(p)' in view
      and 'inlineAssignment.createAssignment(' in view
      and 'doctorService.saveDoctor(p.id, p.name, p.role, "ACTIVE")' in view,
      "Original separate PX REVIEW and CONFIRM gates retained")
check('ROOM // ' in view and 'root.selectedRoomId' in view
      and 'The JOB needs a saved Room.' in view,
      "Onboarding does not create an Assignment before a saved Room is selected")
check('permissions: "READ"' in policy
      and 'launchesProvider: false' in policy
      and 'writesHospital: false' in policy
      and 'authorityVerified: false' in policy
      and 'activatesAssignment: false' in policy,
      "Proposals may never silently start models, write records or escalate permission")
check('NOT AI-GENERATED' in view
      and 'NOT AI-GENERATED' in policy
      and 'LOCAL STARTER TEMPLATE' in policy,
      "A rule-based draft must never be presented as an AI model response")
for bad in ('...', 'eval(', 'Function(', 'import(', 'session-create',
            'orchestrate-ready', 'provider.launch', 'gh auth'):
    check(bad not in policy, "Pure QML-imported JS must not contain unsafe action/syntax: " + bad)
if errors:
    print("HOSPITAL CONVERSATIONAL INTAKE // FAIL")
    for issue in errors: print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL CONVERSATIONAL INTAKE // PASS // review-only local draft, no auto-execution")
