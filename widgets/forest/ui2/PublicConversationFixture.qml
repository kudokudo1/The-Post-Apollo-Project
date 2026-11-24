import QtQuick
import "../../../components"
import "PublicSessionDisplay.js" as Display

// Standalone embeddable test content, NOT a Window or an installed Forest host.
// Fixed public samples only; no input property accepts external transcript data.
Item {
    id: root
    readonly property var view: ({requestId: "ui21_fixture_0001", treeKey: "CHERRY", generation: 1})
    readonly property var sample: Display.project({
        schema: "postapollo.forest.public-session-display.v1",
        requestId: view.requestId, treeKey: view.treeKey, generation: view.generation,
        sessions: [{session_id: "public-demo", title: "Public conversation fixture",
            revision: 2, updated_at_ms: 1}]
    }, view, view)
    readonly property bool fixtureReady: sample.state === "STRUCTURALLY_VALID_PUBLIC_FIXTURE"
        && sample.sessions.length === 1

    Text {
        id: label
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 24
        text: "PUBLIC FIXTURE // SEND LOCKED"
        textFormat: Text.PlainText
        color: Colors.orange
        font.pixelSize: 12
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
    }

    ConversationFeed {
        anchors.top: label.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        conversation: root.fixtureReady
            ? ({id: root.sample.sessions[0].session_id,
                displayNameInProfile: root.sample.sessions[0].title}) : null
        scopeId: "forest-ui2-public-fixture"
        messages: root.fixtureReady ? [
            {direction: "outgoing", body: "What is a Tree?"},
            {direction: "incoming", body: "Public sample: a Tree is a Forest agent identity."}
        ] : []
        messageTextFormat: Text.PlainText
        richMessageActions: false
        sendEnabled: false
        sending: false
        sendLabel: "LOCKED"
        composerPlaceholder: "PUBLIC FIXTURE ONLY"
        emptyConversationLabel: "FIXTURE UNAVAILABLE"
        // No sendRequested handler, no transport, no STOP or authority claims.
    }
}
