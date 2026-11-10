#!/usr/bin/env python3
"""Model-only explicit opt-in draft, no Room/worker/session write by model."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
view = (ROOT / "widgets/HospitalWorkforceManagerView.qml").read_text()
qml = (ROOT / "services/hospital/HospitalAiProposalService.qml").read_text()
client = (ROOT / "services/hospital/hospital_ai_proposal_client.py").read_text()
old = (ROOT / "services/hospital/HospitalConversationIntakePolicy.js").read_text()
issues = []
def check(value, message):
    if not value:
        issues.append(message)

check('HospitalAiProposalService {' in view and 'id: aiIntake' in view
      and 'onFinished: function(result)' in view,
      "Model proposal stays inside existing Surgery workforce manager")
check('label: "BUILD STARTER DRAFT"' in view
      and '"ASK AI // SEND BRIEF"' in view
      and 'root.draftIntake()' in view
      and 'root.requestAiIntake()' in view,
      "Keep local offline starter distinct from explicit ASK AI")
check('ASK AI sends ONLY the entered description to OpenAI' in view
      and 'API access and charges' in view
      and 'NO ROOM, WORKER OR JOB SAVED' in view,
      "Display privacy, potential billing and absence of mutations")
check('onEdited: root.invalidateIntake()' in view
      and 'root.intakeSource !== intakeBriefField.value' in view
      and 'intakeBriefField.value !== aiIntake.pendingBrief' in view,
      "Discard responses for stale/edited briefs")
check('result.permissions !== "READ"' in view
      and 'result.writesHospital !== false' in view
      and 'result.launchesProvider !== false' in view,
      "Never accept privilege or write claims from model output")
check('jobPermissionsField.value = "READ"' in view
      and 'roomCreate.create(p)' in view
      and 'doctorService.saveDoctor(p.id, p.name, p.role, "ACTIVE")' in view
      and 'inlineAssignment.createAssignment(' in view,
      "Original operator-reviewed separate Record writers remain")
check('stdinEnabled: true' in qml and 'onStarted:' in qml
      and 'modelProcess.write(JSON.stringify({' in qml
      and 'brief: root.pendingBrief' in qml
      and 'requestKey: root.pendingKey' in qml,
      "Send only brief via private stdin, never via process arguments")
check('Quickshell.shellDir + "/services/hospital/hospital_ai_proposal_client.py"' in qml
      and 'onStreamFinished:' in qml
      and 'onExited: function(code, status)' in qml
      and 'root.pendingKey' in qml,
      "Process uses verified Quickshell root path and bounded outcome capture")
check('stdoutText.length > 24000' in qml
      and 'data.requestKey' in qml
      and 'data.ready !== true' in qml
      and 'result: ' not in qml,
      "Reject stale, oversize or invalid responses")
check('OPENAI_API_KEY' in client
      and 'ENDPOINT = "https://api.openai.com/v1/responses"' in client
      and '"tools": []' in client
      and '"tool_choice": "none"' in client
      and '"store": False' in client,
      "Only one explicitly requested model-only Responses API call")
check('"permissions"] = {"type": "string", "enum": ["READ"]}' in client
      and 'result.get("permissions") != "READ"' in client
      and '"authorityVerified": False' in client,
      "Schema and local code both prevent write permission promotion")
check('class NoRedirect' in client and 'timeout=20' in client
      and 'MAX_OUTPUT = 65536' in client and 'MAX_INPUT = 8192' in client,
      "Enforce trusted endpoint, bounded request and response")
check('source: "LOCAL STARTER TEMPLATE // NOT AI-GENERATED"' in old
      and 'LOCAL STARTER DRAFT // NOT AI-GENERATED' in view,
      "Offline path must remain truthfully labeled")
for forbidden in ('room-bind', 'doctor-put', 'agent turn', 'session-create',
                  'orchestrate-ready', 'subprocess', 'os.system', 'pickle',
                  'eval(', 'open('):
    check(forbidden not in qml, "Model QML cannot issue PX commands: " + forbidden)
for forbidden in ('subprocess', 'os.system', 'os.popen', 'os.exec', 'PX_HOSPITAL',
                  'session-create', 'assignment-create', 'git checkout',
                  'git commit', 'Authorization: Basic'):
    check(forbidden not in client, "Model subprocess cannot mutate systems: " + forbidden)
if issues:
    print("HOSPITAL MODEL INTAKE // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL MODEL INTAKE // PASS // explicit opt-in, model-only no tools, no authority")
