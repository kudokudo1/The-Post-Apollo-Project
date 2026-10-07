from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "hospital" / "HospitalDoctorRuntimeService.qml"
HOSPITAL = ROOT / "widgets" / "HospitalW.qml"

assert SERVICE.is_file(), SERVICE
assert HOSPITAL.is_file(), HOSPITAL

service = SERVICE.read_text()
for needle in (
    'property string sessionId: ""',
    'property string status: "IDLE"',
    'property int activePid: 0',
    'property int elapsedSeconds: 0',
    'property bool operating: false',
    'property bool cancelling: false',
    'readonly property string displayStatus:',
    'readonly property string elapsedLabel:',
    'function refresh()',
    'function cancel(reasonValue)',
    '"agent",',
    '"status",',
    '"cancel",',
    'interval: root.operating ? 1000 : 3000',
    '.local/share/post-apollo-dev-runtime/bin/px',
):
    assert needle in service, needle

assert "Quickshell.execDetached" not in service
assert 'root.turnCancelled(root.lastCancelResult);' in service

hospital = HOSPITAL.read_text()
for needle in (
    'function openRoomQuick()',
    'root.operationsSurface = "quick";',
    'HospitalDoctorRuntimeService {',
    'id: doctorRuntimeService',
    'sessionId: roomChatView.activeSessionId',
    'readonly property bool stopVisible:',
    'model: ["QUICK", "CHAT", "DOCTOR"]',
    'id: roomStopButton',
    'root.openRoomQuick();',
    'doctorRuntimeService.cancel("OPERATOR");',
    'id: roomQuickView',
    'visible: root.operationsSurface === "quick"',
    'id: roomChatRuntimeHud',
    'doctorRuntimeService.elapsedLabel',
    'doctorRuntimeService.displayStatus',
):
    assert needle in hospital, needle

dock_start = hospital.index("id: roomAiDock")
inspect_start = hospital.index("id: roomInspectActions")
dock = hospital[dock_start:inspect_start]
assert '"STOP"' in dock
assert 'doctorRuntimeService.operating' in dock
assert 'doctorRuntimeService.cancelling' in dock

quick_start = hospital.index("id: roomQuickView")
chat_start = hospital.index("id: roomChatView")
quick = hospital[quick_start:chat_start]
assert 'model: ["STATUS", "CHAT", "STOP"]' in quick
assert 'doctorRuntimeService.refresh();' in quick
assert 'doctorRuntimeService.cancel("OPERATOR")' in quick

print("hospital Doctor runtime supervision contracts: PASS")
