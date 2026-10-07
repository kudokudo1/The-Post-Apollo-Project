import QtQuick
import qs.components
import "../services/hospital"

Item {
    id: root

    property string roomId: ""
    property string repository: ""
    property string patientId: ""
    property string patientLabel: ""
    property string team: ""
    property string branch: ""
    property string bedPath: ""
    property string doctorId: ""
    property string providerId: ""
    property string assignmentId: ""

    readonly property string activeSessionId: adapter.activeSessionId

    readonly property string storedProviderId: {
        const rows =
            Array.isArray(adapter.conversations)
            ? adapter.conversations
            : [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.id || "") === String(root.roomId || ""))
                return String(row.providerId || "").trim();
        }

        return "";
    }

    readonly property string effectiveProviderId:
        String(root.providerId || root.storedProviderId || "").trim()

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
                root.effectiveProviderId
                ? root.effectiveProviderId.toUpperCase()
                : ""
        };
    }

    readonly property string statusText: {
        if (adapter.bindingRoom)
            return "BINDING";

        if (adapter.sending)
            return "SENDING";

        if (adapter.messagesLoading || adapter.loading)
            return "LOADING";

        if (adapter.bindError
                || adapter.sendError
                || adapter.messagesError
                || adapter.error)
            return "ERROR";

        if (adapter.creatingSession || adapter.sessionsLoading)
            return "CONNECTING";

        if (root.activeSessionId)
            return "CONNECTED";

        return root.effectiveProviderId
            ? "READY TO CONNECT"
            : "ROOM CHAT";
    }

    function roomBinding() {
        return {
            id: root.roomId,
            repository: root.repository,
            patientId: root.patientId,
            patientLabel: root.patientLabel,
            team: root.team || root.roomId,
            branch: root.branch,
            bedPath: root.bedPath,
            doctorId: root.doctorId,
            providerId: root.effectiveProviderId,
            assignmentId: root.assignmentId
        };
    }

    function syncRoomBinding() {
        if (!root.roomId) {
            adapter.selectedConversationId = "";
            adapter.messages = [];
            return;
        }

        if (root.repository) {
            adapter.bindRoom(root.roomBinding());
            return;
        }

        adapter.loadMessages(root.roomId);
    }

    function scheduleRoomBinding() {
        bindTimer.restart();
    }

    function refresh() {
        adapter.refresh();
        scheduleRoomBinding();
    }

    onRoomIdChanged: scheduleRoomBinding()
    onRepositoryChanged: scheduleRoomBinding()
    onPatientIdChanged: scheduleRoomBinding()
    onPatientLabelChanged: scheduleRoomBinding()
    onTeamChanged: scheduleRoomBinding()
    onBranchChanged: scheduleRoomBinding()
    onBedPathChanged: scheduleRoomBinding()
    onDoctorIdChanged: scheduleRoomBinding()
    onProviderIdChanged: scheduleRoomBinding()
    onAssignmentIdChanged: scheduleRoomBinding()

    HospitalRoomConversationAdapter {
        id: adapter

        doctorId: root.doctorId
        providerId: root.effectiveProviderId
        workingDirectory: root.bedPath
    }

    Timer {
        id: bindTimer

        interval: 0
        repeat: false

        onTriggered: root.syncRoomBinding()
    }

    ConversationFeed {
        id: feed

        anchors.fill: parent

        conversation: root.conversation
        messages: root.roomId ? adapter.messages : []
        loading: adapter.messagesLoading
        error:
            adapter.bindError
            || adapter.sessionError
            || adapter.sessionsError
            || adapter.messagesError
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
