import QtQuick
import "../../widgets/forest/ui2" as UI2

Item {
    id: root
    width: 300
    height: 160
    property string inputJson: "null"
    property string historyJson: "[]"
    readonly property string labelText: status.statusText
    readonly property string viewState: status.state
    readonly property bool labelVisible: status.visible
    readonly property real labelHeight: status.height
    readonly property bool authority: status.sourceAuthenticated || status.permissionGranted
        || status.productionAuthority || status.modelExecutionPermitted || status.sendEnabled || status.stopEnabled
    readonly property string historyLabel: historyStatus.statusText
    readonly property int historyCount: history.messages.length

    UI2.PublicHistoryViewState { id: history }
    UI2.PublicHistoryStatus {
        id: historyStatus
        width: parent.width
        fixtureVisible: history.attached
        historyState: history.state
        historyReason: history.reason
    }
    UI2.PublicRuntimeStatusView {
        id: status
        anchors.top: historyStatus.bottom
        width: parent.width
    }

    function setupHistory() {
        const pages = JSON.parse(historyJson);
        const r = pages[0].ref;
        history.treeKey = r.treeKey;
        history.generation = r.generation;
        history.sessionId = r.sessionId;
        history.revision = r.revision;
        history.viewKey = "ui22b-history-fixture";
        history.attached = true;
        history.openPage(r.requestId, r.limit);
        history.receivePublicPage(pages[0].frame);
        history.nextPage(pages[1].ref.requestId, pages[1].ref.limit);
        history.receivePublicPage(pages[1].frame);
    }
    function setCurrent() { status.currentCorrelation = JSON.parse(inputJson); }
    function openView() { status.viewOpen = true; status.treeKey = "CHERRY"; }
    function openLifetime() { status.openLifetime(JSON.parse(inputJson)); }
    function receiveUnit() { status.receiveUnit(JSON.parse(inputJson)); }
    function invalidateLifetime() { status.invalidateLifetime(JSON.parse(inputJson)); }
    function closeView() { status.viewOpen = false; }
    function switchTree() { status.treeKey = "MAPLE"; }
    function detach() { status.currentCorrelation = null; }
}
