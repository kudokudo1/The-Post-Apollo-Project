import QtQml
import "../../widgets/forest/ui2" as UI2

QtObject {
    id: root
    property string fixtureJson: "[]"
    readonly property var pages: JSON.parse(fixtureJson)
    property UI2.PublicHistoryViewState history: UI2.PublicHistoryViewState {}
    readonly property string state: history.state
    readonly property int messageCount: history.messages.length
    readonly property string lastBody: messageCount ? history.messages[messageCount - 1].body : ""
    readonly property string lastDirection: messageCount ? history.messages[messageCount - 1].direction : ""
    readonly property bool hasRequest: history.pendingRequest !== null
    readonly property int cursor: hasRequest ? history.pendingRequest.after : -1
    readonly property bool complete: history.complete
    readonly property bool authority: history.sourceAuthenticated || history.permissionGranted || history.sendEnabled

    function setupView() {
        const r = pages[0].ref;
        history.treeKey = r.treeKey;
        history.generation = r.generation;
        history.sessionId = r.sessionId;
        history.revision = r.revision;
        history.viewKey = "local-fixture-view";
        history.attached = true;
    }
    function openFirst() { history.openPage(pages[0].ref.requestId, pages[0].ref.limit); }
    function receiveFirst() { history.receivePublicPage(pages[0].frame); }
    function nextPage() { history.nextPage(pages[1].ref.requestId, pages[1].ref.limit); }
    function receiveSecond() { history.receivePublicPage(pages[1].frame); }
    function changeTree() { history.treeKey = "MAPLE"; }
    function changeRevision() { history.revision += 1; }
    function changeGeneration() { history.generation += 1; }
    function changeSession() { history.sessionId = "other-public-session"; }
    function changeView() { history.viewKey = "local-fixture-view-b"; }
    function detach() { history.attached = false; }
    function reattach() { history.attached = true; }
    function reject() { history.rejectPage(); }
    function close() { history.closeHistory(); }
}
