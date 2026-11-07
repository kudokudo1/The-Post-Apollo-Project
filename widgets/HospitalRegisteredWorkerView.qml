import QtQuick
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalWorkerSessionPolicy.js" as SessionPolicy
import "../services/hospital/HospitalWorkerAttentionPolicy.js" as WorkerAttentionPolicy
import "../services/hospital/HospitalWorkerConnectionPolicy.js" as ConnectionPolicy

// Exact durable Room / pinned PX Session inspection. No room-bind,
// no session-create, no browser-chat access and no automatic agent turns.
Item {
    id: root

    property bool active: false
    property var roomData: ({})
    property string pinnedRoomId: ""
    property string pinnedSessionId: ""
    property string initialMode: "chat"
    property string viewMode: "chat"
    property bool runtimeStatusVerified: false
    property string actionError: ""
    readonly property var recordedAttention:
        WorkerAttentionPolicy.describe(root.roomData)
    readonly property var connectionPlan:
        ConnectionPolicy.inspect(root.roomData)
    readonly property color connectionColor:
        connectionPlan.canRequestTurn ? Colors.cyan
        : connectionPlan.code === "DOCTOR_MISMATCH"
          || connectionPlan.code === "PROVIDER_MISMATCH"
          || connectionPlan.code === "BED_MISMATCH" ? Colors.red
        : Colors.orange
    readonly property color recordedAttentionColor:
        recordedAttention.severity >= 3 ? Colors.red
        : recordedAttention.severity === 2 ? Colors.orange
        : recordedAttention.severity === 1 ? Colors.yellow
        : Colors.cyan

    readonly property bool roomMatches:
        SessionPolicy.roomMatches(roomData, pinnedRoomId)
    readonly property bool sessionMatches:
        SessionPolicy.sessionMatches(roomData, pinnedRoomId, pinnedSessionId)
    readonly property bool runtimeSessionMatches:
        SessionPolicy.statusMatches(runtime.lastStatusPayload, pinnedSessionId)
    readonly property bool canCommand:
        active && sessionMatches && runtimeStatusVerified
        && runtimeSessionMatches && !runtime.lastError
        && !runtime.refreshing && !runtime.cancelling
        && !runtime.quickRunning && !runtime.feedbackRunning

    signal closeRequested()
    signal refreshRequested()

    function reload() {
        if (!active)
            return;
        runtimeStatusVerified = false;
        actionError = "";
        if (pinnedRoomId)
            transcript.refresh();
        if (sessionMatches)
            runtime.refresh();
        refreshRequested();
    }

    function runQuick(commandValue) {
        const command = String(commandValue || "").trim().toUpperCase();
        const allowed = ConnectionPolicy.allowsCommand(root.roomData, command)
            && SessionPolicy.canIssueQuick({
            command: command,
            active: root.active,
            sessionMatches: root.sessionMatches,
            runtimeStatusVerified: root.runtimeStatusVerified,
            runtimeSessionMatches: root.runtimeSessionMatches,
            hasError: !!runtime.lastError,
            busy: runtime.refreshing || runtime.cancelling
                || runtime.quickRunning || runtime.feedbackRunning,
            operating: runtime.operating
        });
        if (!allowed) {
            actionError = "QUICK REFUSED // " + root.connectionPlan.label
                + " // CHECK CONNECTIONS OR PX AUTHORITY";
            return false;
        }
        actionError = "";
        return runtime.quick(command);
    }

    onActiveChanged: {
        if (active) {
            viewMode = initialMode === "connections" ? "connections"
                : initialMode === "quick" ? "quick" : "chat";
            reload();
        } else {
            runtimeStatusVerified = false;
            actionError = "";
        }
    }
    onPinnedRoomIdChanged: {
        runtimeStatusVerified = false;
        if (active)
            transcript.refresh();
    }
    onPinnedSessionIdChanged: {
        runtimeStatusVerified = false;
        if (active && sessionMatches)
            runtime.refresh();
    }

    HospitalWorkerTranscriptService {
        id: transcript
        roomId: root.active ? root.pinnedRoomId : ""
    }

    HospitalDoctorRuntimeService {
        id: runtime
        sessionId: root.active && root.sessionMatches
            ? root.pinnedSessionId : ""

        onStatusRefreshed: {
            root.runtimeStatusVerified =
                !runtime.lastError && root.sessionMatches
                && root.runtimeSessionMatches;
        }
        onQuickCompleted: function(command, result) {
            root.actionError = "";
            transcript.refresh();
            root.runtimeStatusVerified = false;
            runtime.refresh();
            root.refreshRequested();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta
    }

    Row {
        id: heading
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 10
        }
        height: 30
        spacing: 8
        GohuText {
            width: parent.width - 170
            height: parent.height
            text: "WORKER // " + String(root.roomData.name || root.pinnedRoomId || "UNKNOWN")
            font.pixelSize: 13
            color: Colors.orange
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        HospitalActionButton {
            width: 78
            height: 27
            label: "REFRESH"
            compactIcon: "↻"
            accent: Colors.cyan
            onTriggered: root.reload()
        }
        HospitalActionButton {
            width: 76
            height: 27
            label: "BACK"
            compactIcon: "X"
            accent: Colors.magenta
            onTriggered: root.closeRequested()
        }
    }

    Column {
        id: identity
        anchors {
            top: heading.bottom
            topMargin: 8
            left: parent.left
            right: parent.right
            leftMargin: 11
            rightMargin: 11
        }
        spacing: 5
        GohuText {
            width: parent.width
            text: "ROOM ID // " + root.pinnedRoomId
                + "  |  DOCTOR // " + String(root.roomData.doctorName || "UNASSIGNED")
            color: Colors.cyan
            font.pixelSize: 10
            elide: Text.ElideMiddle
        }
        GohuText {
            width: parent.width
            text: "ASSIGNMENT // "
                + String(root.roomData.assignmentTitle
                         || root.roomData.assignmentId || "NONE")
            color: Colors.white
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "CONNECTION // " + root.connectionPlan.label
                + " // " + root.connectionPlan.next
            color: root.connectionColor
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "PX SESSION // " + (root.pinnedSessionId || "NONE")
                + "  |  RECORDED // "
                + String(root.roomData.sessionStatus || "NO SESSION")
            color: Colors.blue
            font.pixelSize: 9
            elide: Text.ElideMiddle
        }
        GohuText {
            width: parent.width
            text: "RECORDED ATTENTION // "
                + root.recordedAttention.label + " // "
                + root.recordedAttention.reason
            color: root.recordedAttentionColor
            font.pixelSize: 10
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "SOURCE // " + root.recordedAttention.source
                + "  //  UPDATED // "
                + (root.recordedAttention.recordedAt || "UNKNOWN")
            color: Colors.blue
            font.pixelSize: 8
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: root.runtimeStatusVerified
                ? "PX STATUS READ // " + runtime.displayStatus
                  + "  |  " + String(runtime.lastActivityText || "NO ACTIVITY TEXT")
                : root.sessionMatches
                  ? "PX STATUS READ // UNVERIFIED OR REFRESHING"
                  : "SESSION UNAVAILABLE // VIEW DURABLE ROOM TRANSCRIPT ONLY"
            color: root.runtimeStatusVerified ? Colors.green : Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
        }
    }

    Row {
        id: modes
        anchors {
            top: identity.bottom
            topMargin: 8
            left: parent.left
            right: parent.right
            leftMargin: 11
            rightMargin: 11
        }
        height: 30
        spacing: 7
        HospitalActionButton {
            width: (parent.width - 14) / 3
            height: parent.height
            label: "CHAT // SAVED" 
            compactIcon: "CHAT"
            selectedAction: root.viewMode === "chat"
            accent: Colors.cyan
            onTriggered: root.viewMode = "chat"
        }
        HospitalActionButton {
            width: (parent.width - 14) / 3
            height: parent.height
            label: "QUICK // PX" 
            compactIcon: "QUICK"
            selectedAction: root.viewMode === "quick"
            accent: Colors.orange
            onTriggered: root.viewMode = "quick"
        }
        HospitalActionButton {
            width: (parent.width - 14) / 3
            height: parent.height
            label: "CONNECTIONS"
            compactIcon: "LINK"
            selectedAction: root.viewMode === "connections"
            accent: root.connectionColor
            onTriggered: root.viewMode = "connections"
        }
    }

    Item {
        id: contentArea
        anchors {
            top: modes.bottom
            topMargin: 8
            bottom: noteArea.top
            bottomMargin: 7
            left: parent.left
            right: parent.right
            leftMargin: 11
            rightMargin: 11
        }

        Flickable {
            id: transcriptScroll
            visible: root.viewMode === "chat"
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: transcriptRows.height
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: transcriptRows
                width: transcriptScroll.width
                spacing: 6

                GohuText {
                    width: parent.width
                    text: transcript.lastError
                        || (transcript.loading ? "LOADING PX ROOM MESSAGES..."
                            : transcript.messages.length === 0
                              ? "NO SAVED ROOM MESSAGES" : "ROOM HISTORY // ALL ATTACHMENTS")
                    color: transcript.lastError ? Colors.red : Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: transcript.messages
                    Rectangle {
                        required property var modelData
                        width: transcriptRows.width
                        height: Math.max(48, Math.min(250, messageBody.implicitHeight + 32))
                        color: Colors.black
                        border.width: 1
                        border.color: String(modelData.direction || "").toLowerCase()
                            === "outgoing" ? Colors.magenta : Colors.cyan
                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 4
                            GohuText {
                                width: parent.width
                                font.pixelSize: 9
                                color: Colors.orange
                                text: String(modelData.authorId || modelData.authorRole
                                    || modelData.direction || "MESSAGE").toUpperCase()
                                    + " // " + String(modelData.createdAt || "")
                                elide: Text.ElideRight
                            }
                            GohuText {
                                id: messageBody
                                width: parent.width
                                font.pixelSize: 10
                                color: Colors.white
                                text: String(modelData.body || modelData.bodyMd || "")
                                wrapMode: Text.WrapAnywhere
                                maximumLineCount: 16
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        NeonScrollBar {
            flickable: transcriptScroll
            handleStyle: "star"
            visible: root.viewMode === "chat" && scrollable
        }

        Flickable {
            id: connectionsScroll
            visible: root.viewMode === "connections"
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: connectionsRows.height
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: connectionsRows
                width: connectionsScroll.width
                spacing: 7

                GohuText {
                    width: parent.width
                    text: "PX BINDINGS // " + root.connectionPlan.label
                    font.pixelSize: 12
                    color: root.connectionColor
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: root.connectionPlan.next
                    font.pixelSize: 10
                    color: Colors.orange
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: root.connectionPlan.checks
                    Rectangle {
                        required property var modelData
                        width: connectionsRows.width
                        height: 42
                        color: Colors.black
                        border.width: 1
                        border.color: modelData.ok ? Colors.cyan : Colors.orange
                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 4
                            GohuText {
                                width: parent.width
                                text: (modelData.ok ? "✓  " : "!  ")
                                    + String(modelData.label || "")
                                font.pixelSize: 9
                                color: modelData.ok ? Colors.green : Colors.orange
                            }
                            GohuText {
                                width: parent.width
                                text: String(modelData.detail || "")
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: root.runtimeStatusVerified
                        ? "PX STATUS RECORD // EXACT SESSION ID CHECKED"
                        : "PX STATUS RECORD // NOT YET VERIFIED"
                    font.pixelSize: 9
                    color: root.runtimeStatusVerified ? Colors.green : Colors.orange
                }
                GohuText {
                    width: parent.width
                    text: "A status read proves the PX record was accessible, not that the Provider can answer a turn. No connection is created here."
                    font.pixelSize: 9
                    color: Colors.blue
                    wrapMode: Text.Wrap
                }
            }
        }

        NeonScrollBar {
            flickable: connectionsScroll
            handleStyle: "star"
            visible: root.viewMode === "connections" && scrollable
        }

        Column {
            visible: root.viewMode === "quick"
            anchors.fill: parent
            spacing: 10

            GohuText {
                width: parent.width
                text: !root.canCommand
                    ? "QUICK LOCKED // EXACT PX SESSION NOT VERIFIED"
                    : root.connectionPlan.canRequestTurn
                      ? "PX SESSION VERIFIED // REQUEST SUBJECT TO BACKEND PREFLIGHT"
                      : "WORKER NOT READY // STATUS ONLY; SEE CONNECTIONS"
                font.pixelSize: 10
                color: root.canCommand ? Colors.green : Colors.orange
                wrapMode: Text.Wrap
            }

            Grid {
                id: quickGrid
                width: parent.width
                columns: 4
                columnSpacing: 6
                rowSpacing: 7
                Repeater {
                    model: ["GO", "CONTINUE", "STATUS", "REPORT",
                            "CHECKLIST", "NEXT", "SUGGEST", "PAUSE"]
                    HospitalActionButton {
                        required property string modelData
                        width: (quickGrid.width - 18) / 4
                        height: 34
                        label: modelData
                        compactIcon: modelData === "CONTINUE" ? "GO" : modelData
                        accent: modelData === "PAUSE" ? Colors.orange : Colors.cyan
                        enabledAction: root.canCommand
                            && ConnectionPolicy.allowsCommand(
                                root.roomData, modelData)
                            && (!runtime.operating || modelData === "STATUS"
                                || modelData === "PAUSE")
                        onTriggered: root.runQuick(modelData)
                    }
                }
            }
            GohuText {
                width: parent.width
                text: root.actionError || runtime.lastError
                    || (runtime.quickRunning
                        ? "SENDING // " + runtime.quickCommand
                        : "No command is sent by opening this panel.")
                font.pixelSize: 10
                color: root.actionError || runtime.lastError
                    ? Colors.red : Colors.blue
                wrapMode: Text.Wrap
            }
        }
    }

    Rectangle {
        id: noteArea
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            margins: 11
        }
        height: 42
        color: Colors.black
        border.width: 1
        border.color: Colors.blue
        GohuText {
            anchors.fill: parent
            anchors.margins: 7
            text: "PX ONLY // Not a ChatGPT browser tab. CONNECTIONS reports saved links; Quick turns require exact Session and PX authority."
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.Wrap
        }
    }
}
