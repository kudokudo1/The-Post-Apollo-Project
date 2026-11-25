import QtQml
import "PublicHistoryDisplay.js" as History

// UI2-owned public-fixture view state. No transport, storage or sender.
// The future host must establish provenance and actual currentness separately.
QtObject {
    id: root
    property bool attached: false
    property string treeKey: ""
    property real generation: 0
    property string sessionId: ""
    property real revision: -1
    property string viewKey: ""

    readonly property var _controller: History.createController()
    property var _snapshot: null
    property bool _initialized: false
    readonly property bool initialized: _initialized
    readonly property string state: attached && _snapshot ? _snapshot.state : "CLOSED"
    readonly property string reason: attached && _snapshot ? _snapshot.reason : ""
    readonly property var messages: attached && _snapshot ? _snapshot.messages : []
    readonly property var pendingRequest: attached && _snapshot ? _snapshot.request : null
    readonly property var nextAfter: attached && _snapshot ? _snapshot.nextAfter : null
    readonly property bool complete: attached && _snapshot ? _snapshot.complete : false
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false
    readonly property bool sendEnabled: false

    function currentScope() {
        return {treeKey: treeKey, generation: generation, sessionId: sessionId,
            revision: revision, viewKey: viewKey};
    }
    function observeScope() {
        if (_controller && attached)
            _snapshot = _controller.observe(currentScope());
    }
    function resetAttachment() {
        if (_controller)
            _snapshot = _controller.close();
    }
    onAttachedChanged: resetAttachment()
    onTreeKeyChanged: observeScope()
    onGenerationChanged: observeScope()
    onSessionIdChanged: observeScope()
    onRevisionChanged: observeScope()
    onViewKeyChanged: observeScope()
    Component.onCompleted: {
        resetAttachment();
        _initialized = true;
    }

    // Explicit presentation requests only. Nothing dispatches pendingRequest.
    function openPage(requestId, limit) {
        if (!attached)
            return false;
        _snapshot = _controller.open(currentScope(), requestId, limit);
        return state === "PENDING";
    }
    function nextPage(requestId, limit) {
        if (!attached)
            return false;
        _snapshot = _controller.next(currentScope(), requestId, limit);
        return state === "PENDING";
    }
    function receivePublicPage(frame) {
        if (!attached)
            return false;
        _snapshot = _controller.receive(frame, currentScope());
        return state === "PARTIAL" || state === "COMPLETE";
    }
    function rejectPage() {
        if (attached)
            _snapshot = _controller.reject();
    }
    function closeHistory() {
        resetAttachment();
    }
}
