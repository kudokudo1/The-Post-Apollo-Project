import QtQuick
import qs.components
import "../services/hospital"

Item {
    id: root

    property string roomId: ""
    property string activeSessionId: ""
    property string doctorId: ""
    property string providerId: ""

    signal closeRequested()

    readonly property var conversation: {
        const rows =
            Array.isArray(adapter.conversations)
            ? adapter.conversations
            : [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.id || "") === String(root.roomId || ""))
                return row;
        }

        if (!root.roomId)
            return null;

        return {
            id: root.roomId,
            displayNameInProfile: root.roomId,
            nickname:
                root.providerId
                ? String(root.providerId).toUpperCase()
                : ""
        };
    }

    readonly property string statusText: {
        if (adapter.sending)
            return "SENDING";

        if (adapter.messagesLoading || adapter.loading)
            return "LOADING";

        if (adapter.sendError || adapter.messagesError || adapter.error)
            return "ERROR";

        return root.activeSessionId ? "CONNECTED" : "ROOM CHAT";
    }

    function refresh() {
        adapter.refresh();

        if (root.roomId)
            adapter.loadMessages(root.roomId);
    }

    onRoomIdChanged: {
        if (roomId)
            adapter.loadMessages(roomId);
        else {
            adapter.selectedConversationId = "";
            adapter.messages = [];
        }
    }

    HospitalRoomConversationAdapter {
        id: adapter

        activeSessionId: root.activeSessionId
    }

    ConversationFeed {
        id: feed

        anchors.fill: parent

        conversation: root.conversation
        messages: root.roomId ? adapter.messages : []
        loading: adapter.messagesLoading
        error:
            adapter.messagesError
            || (
                root.roomId
                ? ""
                : adapter.error
            )

        sending: adapter.sending
        sendError: adapter.sendError
        sendSuccessSerial: adapter.sendSuccessSerial

        messageTextFormat: Text.MarkdownText
        emptyConversationLabel: "SELECT A ROOM"
        composerPlaceholder:
            root.doctorId
            ? "MESSAGE " + root.doctorId.toUpperCase() + "..."
            : "MESSAGE ROOM..."

        onSendRequested: function(conversationId, text) {
            adapter.sendMessage(conversationId, text);
        }

        onComposerEscapeRequested: root.closeRequested()
    }

    Component.onCompleted: refresh()
}
