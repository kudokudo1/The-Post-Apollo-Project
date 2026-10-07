from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "hospital" / "HospitalRoomReportService.qml"
VIEW = ROOT / "widgets" / "HospitalRoomReportsView.qml"
HOSPITAL = ROOT / "widgets" / "HospitalW.qml"
SURGICAL = ROOT / "widgets" / "HospitalReportsView.qml"

for path in (SERVICE, VIEW, HOSPITAL, SURGICAL):
    assert path.is_file(), path

service = SERVICE.read_text()
for needle in (
    'property string roomId: ""',
    'property var reports: []',
    'readonly property var latestReport:',
    'readonly property int reportCount:',
    'function refresh()',
    '"hospital",',
    '"room-reports",',
    '"--limit",',
    '"50",',
    '.local/share/post-apollo-dev-runtime/bin/px',
):
    assert needle in service, needle

assert "Quickshell.execDetached" not in service

view = VIEW.read_text()
for needle in (
    'required property var reportService',
    'readonly property var displayReports:',
    'return source.slice().reverse();',
    'signal closeRequested()',
    'signal chatRequested()',
    '"ROOM REPORTS // "',
    '"GIT EVIDENCE // "',
    '"NO ROOM REPORTS // USE QUICK REPORT"',
    'root.selectedReport.changedFiles',
    'textFormat: Text.MarkdownText',
    'root.selectedReport.body',
):
    assert needle in view, needle

hospital = HOSPITAL.read_text()
for needle in (
    'function openRoomReports()',
    'root.operationsSurface = "roomReports";',
    'HospitalRoomReportService {',
    'id: roomReportService',
    'roomId: root.selectedRoomTeam',
    'roomReportService.refresh();',
    'id: roomReportsButton',
    '"ROOM REPORTS // "',
    'roomReportService.reportCount',
    'HospitalRoomReportsView {',
    'id: roomReportsView',
    'visible: root.operationsSurface === "roomReports"',
    'reportService: roomReportService',
    'onCloseRequested: root.showSurgery()',
    'onChatRequested: root.openRoomChat()',
):
    assert needle in hospital, needle

# Room Reports / Doctor Notes must remain semantically separate from the
# existing certification/surgery Reports surface.
assert 'root.operationsSurface = "reports";' in hospital
assert 'root.operationsSurface = "roomReports";' in hospital
assert "HospitalReportsView" in hospital
assert "HospitalRoomReportsView" in hospital

quick_complete = hospital.index(
    'onQuickCompleted: function(command, result)'
)
quick_complete_end = hospital.index(
    'onTurnCancelled: function(result)',
    quick_complete,
)
quick_refresh = hospital[quick_complete:quick_complete_end]
assert 'roomChatView.refresh();' in quick_refresh
assert 'roomCheckpointService.refresh();' in quick_refresh
assert 'roomReportService.refresh();' in quick_refresh

print("hospital Room Reports / Doctor Notes contracts: PASS")
