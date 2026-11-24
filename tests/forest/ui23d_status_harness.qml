import QtQuick
import "../../widgets/forest/ui2" as UI2

Item {
    id: root
    width: 240
    height: 80
    property string fixtureJson: "[]"
    readonly property var pages: JSON.parse(fixtureJson)
    readonly property string labelText: status.statusText
    readonly property string executionText: status.executionText
    readonly property bool statusVisible: status.visible
    readonly property bool anyAuthority: status.sendEnabled || status.stopEnabled
        || status.sourceAuthenticated || status.permissionGranted
    readonly property int messageCount: history.messages.length

    UI2.PublicHistoryViewState { id: history }

    UI2.PublicHistoryStatus {
        id: status
        width: parent.width
        fixtureVisible: history.attached
        historyState: history.state
        historyReason: history.reason
    }

    function attach() {
        const r = pages[0].ref;
        history.treeKey = r.treeKey;
        history.generation = r.generation;
        history.sessionId = r.sessionId;
        history.revision = r.revision;
        history.viewKey = "status-fixture-view";
        history.attached = true;
    }
    function openFirst() { history.openPage(pages[0].ref.requestId, pages[0].ref.limit); }
    function receiveFirst() { history.receivePublicPage(pages[0].frame); }
    function nextPage() { history.nextPage(pages[1].ref.requestId, pages[1].ref.limit); }
    function receiveSecond() { history.receivePublicPage(pages[1].frame); }
    function refuse() { history.rejectPage(); }
    function changeTree() { history.treeKey = "MAPLE"; }
    function detach() { history.attached = false; }
    function arbitraryReason() {
        status.historyState = "UNAVAILABLE";
        status.historyReason = "<b>private-error-text</b>";
    }
    function unknownState() {
        status.historyState = "<b>raw-event</b>";
    }
    function displayLimit() {
        status.historyState = "UNAVAILABLE";
        status.historyReason = "DISPLAY_LIMIT";
    }
    function requestExhaustion() {
        status.historyState = "UNAVAILABLE";
        status.historyReason = "INVALID_OR_EXHAUSTED_REQUEST";
    }
}
