from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "hospital" / "HospitalChartService.qml"
VIEW = ROOT / "widgets" / "HospitalChartsView.qml"
SUGGESTIONS = ROOT / "widgets" / "HospitalChartSuggestionsView.qml"
HOSPITAL = ROOT / "widgets" / "HospitalW.qml"
RUNTIME = ROOT / "services" / "hospital" / "HospitalDoctorRuntimeService.qml"

for path in (SERVICE, VIEW, SUGGESTIONS, HOSPITAL, RUNTIME):
    assert path.is_file(), path

service = SERVICE.read_text()
for needle in (
    'property string patientId: ""',
    'property string roomId: ""',
    'property string sourceSessionId: ""',
    'property var patientEntries: []',
    'property var roomEntries: []',
    'readonly property int patientActiveCount:',
    'readonly property int roomActiveCount:',
    'function refreshAll()',
    'function addEntry(',
    'function setEntryStatus(entryIdValue, statusValue)',
    '"chart-entries"',
    '"chart-entry-add"',
    '"chart-entry-status"',
    '"--supersedes-id"',
    '"--source-session-id"',
    '"HOSPITAL_UI"',
    'property var patientSuggestions: []',
    'property var roomSuggestions: []',
    'readonly property int pendingSuggestionCount:',
    'function refreshSuggestions()',
    'function promoteSuggestion(suggestionIdValue)',
    'function rejectSuggestion(suggestionIdValue, noteValue)',
    '"chart-suggestions"',
    '"chart-suggestion-promote"',
    '"chart-suggestion-reject"',
):
    assert needle in service, needle

assert "Quickshell.execDetached" not in service

view = VIEW.read_text()
for needle in (
    'required property var chartService',
    'property string scopeMode: "ROOM"',
    'property string statusFilter: "ACTIVE"',
    '"PATIENT"',
    '"ROOM"',
    '"ACTIVE"',
    '"ALL"',
    '"NEW"',
    '"REPLACE"',
    '"RESOLVE"',
    '"ARCHIVE"',
    '"RESTORE"',
    'root.openEditor("REPLACE")',
    'chartService.addEntry(',
    'chartService.setEntryStatus(',
    'root.selectedEntry.supersedesId',
    'root.selectedEntry.supersededById',
    'textFormat: Text.MarkdownText',
):
    assert needle in view, needle

suggestions = SUGGESTIONS.read_text()
for needle in (
    'required property var chartService',
    'DOCTORS PROPOSE // OPERATOR PROMOTES',
    '"PROMOTE TO CHART"',
    'label: "REJECT"',
    'chartService.promoteSuggestion(',
    'chartService.rejectSuggestion(',
    'sourceMessageId',
):
    assert needle in suggestions, needle

runtime = RUNTIME.read_text()
assert '"SUGGEST"' in runtime
assert '"chart-entry-add"' not in runtime

hospital = HOSPITAL.read_text()
for needle in (
    'function openRoomCharts()',
    'root.operationsSurface = "charts";',
    'HospitalChartService {',
    'id: chartService',
    'patientId: floorService.floorId',
    'roomId: root.selectedRoomTeam',
    'sourceSessionId: roomChatView.activeSessionId',
    'id: roomChartButton',
    '"CHART // "',
    'chartService.roomActiveCount',
    'chartService.patientActiveCount',
    'HospitalChartsView {',
    'id: chartsView',
    'visible: root.operationsSurface === "charts"',
    'chartService: chartService',
    'onCloseRequested: root.showSurgery()',
    'function openRoomChartSuggestions()',
    'root.operationsSurface = "chartSuggestions";',
    'id: chartSuggestionsButton',
    '"SUGGEST // "',
    'chartService.pendingSuggestionCount',
    'HospitalChartSuggestionsView {',
    'id: chartSuggestionsView',
):
    assert needle in hospital, needle

assert 'root.operationsSurface = "reports";' in hospital
assert 'root.operationsSurface = "roomReports";' in hospital
assert 'root.operationsSurface = "charts";' in hospital

print("hospital Patient/Room Chart manager contracts: PASS")
