import QtQuick
import "../../../components" as Shared
import "PublicSessionDisplay.js" as Display

// Fixed public fixture only. A future explicit, default-off Loader owns
// lifetime; no external transcript, runtime status, session or sender input.
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
    readonly property bool transcriptReady: fixtureReady && history.complete
    readonly property string fixtureState: history.state
    readonly property string fixtureReason: history.reason

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
    Component.onCompleted: _rootCompleted = true
    onCanPopulateChanged: {
        if (canPopulate)
            populateFixture();
    }
    function populateFixture() {
        if (!canPopulate || _populated)
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
        height: implicitHeight
        fixtureVisible: true
        historyState: root.fixtureReady ? history.state : "UNAVAILABLE"
        historyReason: history.reason
    }

    Shared.ConversationFeed {
        id: feed
        objectName: "publicFixtureFeed"
        anchors.top: status.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        conversation: root.transcriptReady
            ? ({id: root.sample.sessions[0].session_id,
                displayNameInProfile: root.sample.sessions[0].title}) : null
        scopeId: "forest-ui2-public-fixture"
        messages: root.transcriptReady ? history.messages : []
        showHeader: false
        showComposer: false
        messageTextFormat: Text.PlainText
        richMessageActions: false
        sendEnabled: false
        sending: false
        emptyConversationLabel: "FIXTURE UNAVAILABLE"
        // No sendRequested handler, no transport, no STOP or authority claims.
    }
}
