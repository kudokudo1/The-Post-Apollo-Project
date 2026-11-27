import QtQuick
import "../../../components" as Shared
import "PublicSessionDisplay.js" as Display
import "PublicHistoryDisplay.js" as History

// Default literal transcript; explicit connected public history mode is one-way
// for this Loader lifetime. Presentation only, no sender or authority.
// Owner must independently establish fixture provenance/currentness; no
// status input opens the view or derives the current correlation.
Item {
    id: root
    clip: true
    readonly property var view: ({requestId: "ui21_fixture_0001", treeKey: "CHERRY", generation: 1})
    readonly property var sample: Display.project({
        schema: "postapollo.forest.public-session-display.v1",
        requestId: view.requestId, treeKey: view.treeKey, generation: view.generation,
        sessions: [{session_id: "public-demo", title: "Public conversation fixture",
            revision: 2, updated_at_ms: 1}]
    }, view, view)
    readonly property bool fixtureReady: sample.state === "STRUCTURALLY_VALID_PUBLIC_FIXTURE"
        && sample.sessions.length === 1
    property bool _rootCompleted: false
    property bool _populated: false
    readonly property bool canPopulate: _rootCompleted && history.initialized
    readonly property bool transcriptReady: !_demoSelected && !connectedHistoryMode && fixtureReady && history.complete

    // Explicit development-only, process-free presentation. The host opts in
    // on this Loader, not by setting chatHostTrusted or forwarding the draft.
    // One fixed operation per view; no model, I/O, history or automatic retry.
    property bool developmentDemoMode: false
    property bool _demoSelected: false
    property bool _demoSeenVisible: false
    property string _demoState: "READY"
    property int _demoStep: 0
    property var _demoRows: []
    readonly property string demoState: _demoSelected ? _demoState : "OFF"
    readonly property bool demoAvailable: _demoSelected && developmentDemoMode
        && visible && _rootCompleted && !connectedHistoryMode && !runtimeViewOpen
        && _demoState === "READY"
    readonly property string demoPrompt: "Reply with READY."
    readonly property var demoConversation: ({id:"public-dev-demo", displayNameInProfile:"Fixed development mock"})
    readonly property string demoStatusText: {
        switch (demoState) {
        case "READY": return "DEV MOCK // FIXED TEST READY";
        case "STREAMING": return "DEV MOCK // SIMULATED RESPONSE";
        case "COMPLETE": return "DEV MOCK // COMPLETE (NOT SAVED)";
        case "STOPPED": return "DEV MOCK // STOPPED (NOT SAVED)";
        default: return "DEV MOCK // CLOSED";
        }
    }
    function selectDemoMode() {
        if (_demoSelected) return;
        _demoSelected = true;
        _demoSeenVisible = visible;
        if (connectedHistoryMode || runtimeViewOpen) {
            withdrawDemo();
            clearConnectedHistory();
            return;
        }
        clearConnectedHistory();
    }
    onDevelopmentDemoModeChanged: {
        if (developmentDemoMode && _rootCompleted)
            selectDemoMode();
        else if (!developmentDemoMode && _demoSelected)
            withdrawDemo();
    }
    onRuntimeViewOpenChanged: if (_demoSelected && runtimeViewOpen) withdrawDemo()
    function beginDemo() {
        if (!demoAvailable || arguments.length !== 0)
            return false;
        _demoRows = [
            {turnId:"demo-user", ordinal:1, direction:"outgoing", body:demoPrompt},
            {turnId:"demo-assistant", ordinal:2, direction:"incoming", body:"Simulated reply:"}
        ];
        _demoStep = 0;
        _demoState = "STREAMING";
        demoTimer.start();
        return true;
    }
    function stopDemo() {
        if (!_demoSelected || _demoState !== "STREAMING")
            return false;
        demoTimer.stop();
        _demoState = "STOPPED";
        _demoRows = [{turnId:"demo-user", ordinal:1, direction:"outgoing", body:demoPrompt}];
        feed.clearStreamingTail();
        return true;
    }
    function withdrawDemo() {
        if (!_demoSelected) return;
        demoTimer.stop();
        _demoState = "WITHDRAWN";
        _demoRows = [];
        feed.clearStreamingTail();
    }
    Timer {
        id: demoTimer
        interval: 650
        repeat: false
        onTriggered: {
            if (!root.developmentDemoMode || !root.visible
                    || root._demoState !== "STREAMING" || root.runtimeViewOpen) {
                root.withdrawDemo();
                return;
            }
            const finalStep = root._demoStep === 1;
            if (!feed.updateStreamingTail(feed.effectiveScope,
                    finalStep ? "Simulated reply: READY." : "Simulated reply: RE")) {
                root.withdrawDemo();
                return;
            }
            if (finalStep)
                root._demoState = "COMPLETE";
            else {
                root._demoStep = 1;
                restart();
            }
        }
    }

    // Independently observed owner scope, never derived from a PAGE response.
    // The owner must replace the whole object and fence its Process/Loader.
    property var historyCurrentScope: null
    property bool _connectedHistoryMode: false
    readonly property bool connectedHistoryMode: _connectedHistoryMode
    property var _acceptedHistoryScope: null
    property var _usedHistoryViews: ({})
    property int _historyViewCount: 0
    readonly property bool historyInitialized: history.initialized
    readonly property bool historyScopeActive: !_demoSelected && connectedHistoryMode && visible
        && history.attached && sameHistoryScope(_acceptedHistoryScope, historyCurrentScope)
    readonly property var historyPendingRequest: historyScopeActive ? history.pendingRequest : null
    readonly property var historyNextAfter: historyScopeActive ? history.nextAfter : null

    function publicToken(v) {
        return typeof v === "string" && v.length === 32 && /^[0-9a-f]{32}$/.test(v);
    }
    function validHistoryScope(s) {
        return History.exact(s, ["treeKey","generation","sessionId","revision","viewKey"])
            && s.treeKey === "CHERRY" && History.integer(s.generation, 1)
            && History.integer(s.revision, 0) && publicToken(s.sessionId)
            && publicToken(s.viewKey) && s.sessionId !== s.viewKey;
    }
    function sameHistoryScope(a, b) {
        return validHistoryScope(a) && validHistoryScope(b)
            && a.treeKey === b.treeKey && a.generation === b.generation
            && a.sessionId === b.sessionId && a.revision === b.revision && a.viewKey === b.viewKey;
    }
    function clearConnectedHistory() {
        history.attached = false;
        history.closeHistory();
        _acceptedHistoryScope = null;
    }
    // Only an explicit owner action may leave the literal preview. No fallback
    // on refusal, detach, or missing history. Recreate Loader for a new sample.
    function beginConnectedHistory() {
        if (_demoSelected || developmentDemoMode || !_rootCompleted || !history.initialized || !visible || connectedHistoryMode)
            return false;
        clearConnectedHistory();
        _connectedHistoryMode = true;
        return true;
    }
    function observeHistoryScope() {
        if (connectedHistoryMode && (!visible
                || !sameHistoryScope(_acceptedHistoryScope, historyCurrentScope)))
            clearConnectedHistory();
    }
    onHistoryCurrentScopeChanged: observeHistoryScope()
    onVisibleChanged: {
        observeHistoryScope();
        if (_demoSelected) {
            if (visible) _demoSeenVisible = true;
            else if (_demoSeenVisible) withdrawDemo();
        }
    }

    function attachHistoryScope(ref) {
        if (!connectedHistoryMode || !visible || !history.initialized
                || !sameHistoryScope(ref, historyCurrentScope))
            return false;
        // Never let a delayed open clear a different accepted scope.
        if (_usedHistoryViews[ref.viewKey] || _historyViewCount >= 64)
            return false;
        clearConnectedHistory();
        _usedHistoryViews[ref.viewKey] = true;
        _historyViewCount++;
        _acceptedHistoryScope = {treeKey: ref.treeKey, generation: ref.generation,
            sessionId: ref.sessionId, revision: ref.revision, viewKey: ref.viewKey};
        history.treeKey = ref.treeKey;
        history.generation = ref.generation;
        history.sessionId = ref.sessionId;
        history.revision = ref.revision;
        history.viewKey = ref.viewKey;
        history.attached = true;
        return historyScopeActive;
    }
    function openHistoryPage(ref, requestId, limit) {
        if (!historyScopeActive || !sameHistoryScope(ref, _acceptedHistoryScope)
                || !publicToken(requestId) || (limit !== 1 && limit !== 2)
                || history.state !== "CLOSED")
            return false;
        return history.openPage(requestId, limit);
    }
    function nextHistoryPage(ref, requestId, limit) {
        if (!historyScopeActive || !sameHistoryScope(ref, _acceptedHistoryScope)
                || !publicToken(requestId) || (limit !== 1 && limit !== 2)
                || history.state !== "PARTIAL")
            return false;
        return history.nextPage(requestId, limit);
    }
    function receiveHistoryPage(ref, frame) {
        // Caller fences original child/action before invoking this method.
        // Old view packets must not reach the fail-closed history controller.
        if (!historyScopeActive || !sameHistoryScope(ref, _acceptedHistoryScope))
            return false;
        if (!frame || !Array.isArray(frame.messages) || frame.messages.length > 2
                || frame.messages.some(row => !row || !publicToken(row.turn_id))) {
            history.rejectPage();
            return false;
        }
        return history.receivePublicPage(frame);
    }
    function refuseHistoryScope(ref) {
        if (historyScopeActive && sameHistoryScope(ref, _acceptedHistoryScope))
            history.rejectPage();
    }

    readonly property string fixtureState: history.state
    readonly property string fixtureReason: history.reason

    // Host-owned, independent inputs. Replace the whole correlation; never
    // populate these fields from a received unit. Defaults are disconnected.
    property bool runtimeViewOpen: false
    property string runtimeTreeKey: ""
    property var runtimeCurrentCorrelation: null
    readonly property bool runtimeInitialized: operationStatus.initialized
    readonly property string runtimeState: operationStatus.state
    readonly property string runtimeStatusText: operationStatus.statusText
    readonly property bool runtimeEligible: operationStatus.eligible

    function openRuntimeLifetime(ref) {
        return operationStatus.openLifetime(ref);
    }
    function receiveRuntimeUnit(unit) {
        operationStatus.receiveUnit(unit);
    }
    // Connected disposable mode only. No transport or raw result decoding.
    function recordRuntimeLocalAbort(ref, code, finalSequence) {
        return connectedHistoryMode && visible
            && operationStatus.recordLocalAbort(ref,code,finalSequence);
    }
    function invalidateRuntimeLifetime(ref) {
        operationStatus.invalidateLifetime(ref);
    }
    // Only the owner of the current lifecycle may close it by changing
    // runtimeViewOpen/currentCorrelation. No unscoped delayed-close method.

    PublicHistoryViewState {
        id: history
        treeKey: root.view.treeKey
        generation: root.view.generation
        sessionId: root.fixtureReady ? root.sample.sessions[0].session_id : ""
        revision: root.fixtureReady ? root.sample.sessions[0].revision : -1
        viewKey: "public-fixture-view"
    }

    // Instantiation is the opt-in fixture action. This local literal page
    // is not an M4 database read or model execution. Child and parent
    // completion order is unspecified; wait for both, with no queued work.
    Component.onCompleted: {
        _rootCompleted = true;
        if (developmentDemoMode) selectDemoMode();
    }
    onCanPopulateChanged: {
        if (canPopulate)
            populateFixture();
    }
    function populateFixture() {
        if (!canPopulate || _populated || connectedHistoryMode || developmentDemoMode || _demoSelected)
            return;
        _populated = true;
        if (!fixtureReady)
            return;
        history.attached = true;
        const request = "ui21_history_0001";
        if (!history.openPage(request, 2))
            return;
        history.receivePublicPage({
            schema: "postapollo.forest.public-history-display.v1",
            requestId: request, treeKey: view.treeKey, generation: view.generation,
            sessionId: history.sessionId, revision: history.revision,
            messages: [
                {turn_id: "public-turn-1", ordinal: 1, role: "user", text: "What is a Tree?"},
                {turn_id: "public-turn-2", ordinal: 2, role: "assistant",
                    text: "Public sample: a Tree is a Forest agent identity."}
            ],
            complete: true
        });
    }

    PublicHistoryStatus {
        id: status
        objectName: "publicFixtureStatus"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root._demoSelected ? 0 : implicitHeight
        fixtureVisible: !root._demoSelected
        historyState: root.connectedHistoryMode ? (root.historyScopeActive ? history.state : "CLOSED")
            : (root.fixtureReady ? history.state : "UNAVAILABLE")
        historyReason: history.reason
    }

    Text {
        id: demoStatus
        objectName: "publicDemoStatus"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root._demoSelected
        height: visible ? implicitHeight : 0
        text: root.demoStatusText + " // NO MODEL"
        textFormat: Text.PlainText
        color: "#ED981A"
        font.pixelSize: 12
        elide: Text.ElideRight
    }

    // One operation label below the independent history snapshot label.
    // No label reserves space or changes the transcript when disconnected.
    PublicRuntimeStatusView {
        id: operationStatus
        objectName: "publicFixtureRuntimeStatus"
        anchors.top: root._demoSelected ? demoStatus.bottom : status.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        viewOpen: !root._demoSelected && root.runtimeViewOpen && root.visible && (root.connectedHistoryMode || root.transcriptReady)
        treeKey: root.runtimeTreeKey
        currentCorrelation: root.runtimeCurrentCorrelation
    }

    Shared.ConversationFeed {
        id: feed
        objectName: "publicFixtureFeed"
        anchors.top: operationStatus.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        conversation: root._demoSelected ? (root.demoState === "WITHDRAWN" ? null : root.demoConversation) : root.connectedHistoryMode
            ? (root.historyScopeActive ? ({id: root._acceptedHistoryScope.sessionId,
                displayNameInProfile: "Public conversation"}) : null)
            : (root.transcriptReady ? ({id: root.sample.sessions[0].session_id,
                displayNameInProfile: root.sample.sessions[0].title}) : null)
        scopeId: root._demoSelected ? "forest-ui2-dev-demo" : "forest-ui2-public-fixture"
        messages: root._demoSelected ? root._demoRows : (root.connectedHistoryMode ? root.historyScopeActive : root.transcriptReady)
            ? history.messages : []
        streamingTailEnabled: root._demoSelected && root.demoState !== "WITHDRAWN"
        showHeader: false
        showComposer: false
        messageTextFormat: Text.PlainText
        richMessageActions: false
        sendEnabled: false
        sending: false
        emptyConversationLabel: root._demoSelected
            ? (root.demoState === "READY" ? "FIXED PUBLIC TEST // NO MODEL" : "DEVELOPMENT VIEW CLOSED")
            : root.connectedHistoryMode ? "PUBLIC HISTORY NOT AVAILABLE" : "FIXTURE UNAVAILABLE"
        // No sendRequested handler, no transport, no STOP or authority claims.
    }
}
