from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "components" / "ConversationFeed.qml"
CHAT = ROOT / "widgets" / "HospitalRoomChatView.qml"
ACTIONS = ROOT / "services" / "hospital" / "HospitalChatActionService.qml"
HOSPITAL = ROOT / "widgets" / "HospitalW.qml"

for path in (FEED, CHAT, ACTIONS, HOSPITAL):
    assert path.is_file(), path

feed = FEED.read_text()
for needle in (
    'property bool richMessageActions: false',
    'signal messageActionRequested(string action, var message, string value)',
    'function firstCodeBlock(value)',
    'function firstFileReference(value)',
    'function actionModel(message)',
    '{ label: "COPY", action: "COPY", value: body }',
    '{ label: "COPY CODE", action: "COPY_CODE", value: code }',
    '{ label: "OPEN FILE", action: "OPEN_FILE", value: file }',
    '{ label: "OPEN DIFF", action: "OPEN_DIFF", value: "" }',
    'onLinkActivated: function(link)',
):
    assert needle in feed, needle

chat = CHAT.read_text()
for needle in (
    'signal richActionRequested(string action, string value, var message)',
    'HospitalChatActionService {',
    'richMessageActions: true',
    'chatActionService.classifyLink(resolvedValue)',
    'chatActionService.handleLocal(',
    'root.richActionRequested(',
):
    assert needle in chat, needle

actions = ACTIONS.read_text()
for needle in (
    'function copyText(value)',
    'wl-copy',
    'function openFile(referenceValue)',
    'realpath -e',
    'exec xdg-open "$target"',
    'function classifyLink(value)',
    'hospital:file:',
    'hospital:diff',
    'hospital:room:',
    'hospital:report:',
    'function openExternal(urlValue)',
):
    assert needle in actions, needle

hospital = HOSPITAL.read_text()
for needle in (
    'assignmentId:',
    'onRichActionRequested: function(action, value, message)',
    'roomService.runInspection("diff");',
    'root.openRoomReports();',
    'const roomIndex = root.roomIndexOfTeam(target);',
    'Qt.callLater(root.openRoomChat);',
):
    assert needle in hospital, needle

print("hospital rich chat contracts: PASS")
