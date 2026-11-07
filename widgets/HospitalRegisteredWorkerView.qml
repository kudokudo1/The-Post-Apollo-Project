import QtQuick
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalWorkerSessionPolicy.js" as SessionPolicy
import "../services/hospital/HospitalWorkerAttentionPolicy.js" as WorkerAttentionPolicy
import "../services/hospital/HospitalWorkerConnectionPolicy.js" as ConnectionPolicy
import "../services/hospital/HospitalWorkerAttachmentPreviewPolicy.js" as AttachPreviewPolicy

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

    // Explicit PREVIEW selection, never an active worker attachment.
    property var availableDoctors: []
    property var availableProviders: []
    property var allRooms: []
    property var allSessions: []
    property bool roomsSnapshotLoaded: false
    property bool sessionsSnapshotLoaded: false
    property bool doctorDirectoryLoaded: false
    property bool providerDirectoryLoaded: false
    property string attachmentSourceError: ""
    property string previewAssignmentId: ""
    property string previewDoctorId: ""
    property string previewProviderId: ""
    property int previewAssignmentPage: 0
    property int previewDoctorPage: 0
    property int previewProviderPage: 0
    readonly property int previewPageSize: 10
    property string attachmentArmKey: ""
    property string attachmentSessionId: ""
    property string attachmentOutcome: ""
    readonly property string attachmentSelectionKey: JSON.stringify({
        room: root.roomData, assignmentId: root.previewAssignmentId,
        doctorId: root.previewDoctorId, providerId: root.previewProviderId,
        plan: root.attachmentPreview,
        roomsLoaded: root.roomsSnapshotLoaded,
        sessionsLoaded: root.sessionsSnapshotLoaded,
        doctorsLoaded: root.doctorDirectoryLoaded,
        providersLoaded: root.providerDirectoryLoaded,
        error: root.attachmentSourceError || assignmentPreview.lastError,
        sessions: root.allSessions
    })
    readonly property bool attachmentArmed:
        attachmentArmKey.length > 0
        && attachmentArmKey === attachmentSelectionKey
        && attachmentSessionId.length > 0
    readonly property var attachmentPreview: AttachPreviewPolicy.plan({
        room: root.roomData,
        rooms: root.allRooms,
        sessions: root.allSessions,
        assignments: assignmentPreview.assignments,
        doctors: root.availableDoctors,
        providers: root.availableProviders,
        assignmentId: root.previewAssignmentId,
        doctorId: root.previewDoctorId,
        providerId: root.previewProviderId,
        roomsLoaded: root.roomsSnapshotLoaded,
        sessionsLoaded: root.sessionsSnapshotLoaded,
        assignmentsLoaded: assignmentPreview.loaded,
        doctorsLoaded: root.doctorDirectoryLoaded,
        providersLoaded: root.providerDirectoryLoaded,
        loadError: root.attachmentSourceError || assignmentPreview.lastError
    })
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

    function openAttachmentPreview() {
        if (!root.active || !root.roomMatches)
            return false;
        // Fresh operator choices start from the durable Room records.
        // Selecting here cannot update staffing or start a PX Session.
        previewAssignmentId = String(root.roomData.assignmentId || "").trim();
        previewDoctorId = String(root.roomData.roomDoctorId || "").trim();
        previewProviderId = String(root.roomData.roomProviderId || "").trim();
        previewAssignmentPage = 0;
        previewDoctorPage = 0;
        previewProviderPage = 0;
        attachmentArmKey = "";
        attachmentSessionId = "";
        attachmentOutcome = "";
        viewMode = "attachPreview";
        assignmentPreview.refresh();
        refreshRequested();
        return true;
    }

    function armAttachment() {
        if (!root.active || !root.roomMatches
                || root.viewMode !== "attachPreview"
                || !root.attachmentPreview.reviewable
                || attachmentAction.running) {
            attachmentOutcome = "ARM REFUSED // REVIEW CONNECTION BLOCKERS";
            return false;
        }
        attachmentSessionId = root.attachmentPreview.sessionMode
            === "REUSE_SESSION_REVIEW"
            ? String(root.attachmentPreview.sessionId || "")
            : "hospital-attach-" + Date.now().toString(36)
              + "-" + Math.random().toString(36).slice(2, 12);
        attachmentArmKey = root.attachmentSelectionKey;
        attachmentOutcome = "ARMED // CONFIRM THE EXACT SESSION ID BELOW";
        return root.attachmentArmed;
    }

    function confirmAttachment() {
        if (!root.attachmentArmed || !root.active || !root.roomMatches
                || root.viewMode !== "attachPreview"
                || !root.attachmentPreview.reviewable
                || attachmentAction.running) {
            attachmentOutcome = "CONFIRM REFUSED // PREVIEW CHANGED OR BLOCKED";
            attachmentArmKey = "";
            return false;
        }
        const plan = root.attachmentPreview;
        const room = root.roomData || {};
        const candidate = {
            roomId: root.pinnedRoomId,
            sessionId: root.attachmentSessionId,
            assignmentId: root.previewAssignmentId,
            doctorId: root.previewDoctorId,
            providerId: root.previewProviderId,
            repository: String(room.repository || ""),
            branch: String(room.branch || ""),
            bedPath: String(room.bedPath || ""),
            mode: plan.sessionMode === "REUSE_SESSION_REVIEW"
                ? "reuse" : "create"
        };
        root.attachmentArmKey = "";
        root.attachmentOutcome = "SUBMITTING // PX WILL REVALIDATE CURRENT RECORDS";
        if (!attachmentAction.attach(candidate)) {
            root.attachmentOutcome = attachmentAction.lastError
                || "PX ATTACH REQUEST REFUSED";
            return false;
        }
        return true;
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
            previewAssignmentId = "";
            previewDoctorId = "";
            previewProviderId = "";
            attachmentArmKey = "";
            attachmentSessionId = "";
            attachmentOutcome = "";
            reload();
        } else {
            attachmentArmKey = "";
            runtimeStatusVerified = false;
            actionError = "";
        }
    }
    onPreviewAssignmentIdChanged: attachmentArmKey = ""
    onPreviewDoctorIdChanged: attachmentArmKey = ""
    onPreviewProviderIdChanged: attachmentArmKey = ""
    onRoomDataChanged: attachmentArmKey = ""
    onPinnedRoomIdChanged: {
        attachmentArmKey = "";
        runtimeStatusVerified = false;
        if (active)
            transcript.refresh();
    }
    onPinnedSessionIdChanged: {
        runtimeStatusVerified = false;
        if (active && sessionMatches)
            runtime.refresh();
    }

    HospitalWorkerAttachmentActionService {
        id: attachmentAction
        onAttached: function(result) {
            // A registration is not a provider turn or browser connection.
            if (root.active && String(result.roomId || "") === root.pinnedRoomId) {
                root.attachmentOutcome = "PX SESSION REGISTERED // "
                    + String(result.mode || "")
                    + " // " + String(result.sessionId || "")
                    + " // PROVIDER NOT LAUNCHED";
            }
            root.attachmentSessionId = "";
            root.attachmentArmKey = "";
            root.runtimeStatusVerified = false;
            root.refreshRequested();
        }
        onRefused: function(reason) {
            if (root.active)
                root.attachmentOutcome = reason;
            root.attachmentArmKey = "";
        }
    }

    HospitalWorkerAttachmentPreviewService {
        id: assignmentPreview
        roomId: root.active && root.viewMode === "attachPreview"
            ? root.pinnedRoomId : ""
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
                HospitalActionButton {
                    width: parent.width
                    height: 30
                    label: "PREVIEW ATTACHMENT"
                    compactIcon: "LINK"
                    accent: Colors.orange
                    onTriggered: root.openAttachmentPreview()
                }
            }
        }

        NeonScrollBar {
            flickable: connectionsScroll
            handleStyle: "star"
            visible: root.viewMode === "connections" && scrollable
        }

        Flickable {
            id: attachScroll
            visible: root.viewMode === "attachPreview"
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: attachRows.height
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: attachRows
                width: attachScroll.width
                spacing: 7

                GohuText {
                    width: parent.width
                    text: "ATTACHMENT // READ-ONLY PREFLIGHT"
                    color: Colors.orange
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: root.attachmentPreview.headline
                    color: root.attachmentPreview.reviewable
                        ? Colors.green : Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: "Room and Patient are pinned. Choose only existing records below. No attach command is exposed."
                    font.pixelSize: 9
                    color: Colors.blue
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: root.attachmentPreview.facts
                    GohuText {
                        required property var modelData
                        width: attachRows.width
                        text: String(modelData.label || "") + " // "
                            + String(modelData.value || "")
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideMiddle
                    }
                }

                GohuText {
                    width: parent.width
                    text: "ASSIGNMENT // SELECT AN EXISTING CONTRACT"
                    font.pixelSize: 10
                    color: Colors.orange
                }
                GohuText {
                    width: parent.width
                    visible: assignmentPreview.loading || !!assignmentPreview.lastError
                    text: assignmentPreview.lastError
                        || "READING EXACT ROOM ASSIGNMENTS..."
                    font.pixelSize: 9
                    color: assignmentPreview.lastError ? Colors.red : Colors.cyan
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: assignmentPreview.assignments.slice(
                        root.previewAssignmentPage * root.previewPageSize,
                        (root.previewAssignmentPage + 1) * root.previewPageSize)
                    Rectangle {
                        required property var modelData
                        width: attachRows.width
                        height: 31
                        color: Colors.black
                        border.width: 1
                        border.color: String(modelData.id || "") === root.previewAssignmentId
                            ? Colors.orange : Colors.magenta
                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 6
                            text: "#" + String(modelData.id || "")
                                + " // " + String(modelData.status || "")
                                + " // " + String(modelData.title || "")
                            font.pixelSize: 9
                            color: Colors.white
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.previewAssignmentId =
                                String(modelData.id || "")
                        }
                    }
                }
                Row {
                    width: parent.width
                    height: 27
                    spacing: 5
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "PREV"
                        compactIcon: "<"
                        accent: Colors.cyan
                        enabledAction: root.previewAssignmentPage > 0
                        onTriggered: root.previewAssignmentPage--
                    }
                    GohuText {
                        width: parent.width - 157
                        height: parent.height
                        text: "ASSIGNMENTS // " + assignmentPreview.assignments.length
                            + " // PAGE " + (root.previewAssignmentPage + 1)
                        font.pixelSize: 8
                        color: Colors.blue
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "NEXT"
                        compactIcon: ">"
                        accent: Colors.cyan
                        enabledAction: (root.previewAssignmentPage + 1)
                            * root.previewPageSize < assignmentPreview.assignments.length
                        onTriggered: root.previewAssignmentPage++
                    }
                }
                GohuText {
                    width: parent.width
                    text: "DOCTOR // CHOOSE REGISTERED STAFF"
                    font.pixelSize: 10
                    color: Colors.orange
                }
                GohuText {
                    width: parent.width
                    visible: root.availableDoctors.length === 0
                    text: "NO DOCTORS LOADED // REFRESH HOSPITAL DIRECTORY"
                    font.pixelSize: 9
                    color: Colors.orange
                }
                Repeater {
                    model: root.availableDoctors.slice(
                        root.previewDoctorPage * root.previewPageSize,
                        (root.previewDoctorPage + 1) * root.previewPageSize)
                    Rectangle {
                        required property var modelData
                        width: attachRows.width
                        height: 30
                        color: Colors.black
                        border.width: 1
                        border.color: String(modelData.id || "") === root.previewDoctorId
                            ? Colors.orange : Colors.magenta
                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 6
                            text: String(modelData.name || modelData.id || "")
                                + " // " + String(modelData.status || "")
                                + " // " + String(modelData.id || "")
                            color: Colors.white
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.previewDoctorId =
                                String(modelData.id || "")
                        }
                    }
                }
                Row {
                    width: parent.width
                    height: 27
                    spacing: 5
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "PREV"
                        compactIcon: "<"
                        accent: Colors.cyan
                        enabledAction: root.previewDoctorPage > 0
                        onTriggered: root.previewDoctorPage--
                    }
                    GohuText {
                        width: parent.width - 157
                        height: parent.height
                        text: "DOCTORS // " + root.availableDoctors.length
                            + " // PAGE " + (root.previewDoctorPage + 1)
                        font.pixelSize: 8
                        color: Colors.blue
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "NEXT"
                        compactIcon: ">"
                        accent: Colors.cyan
                        enabledAction: (root.previewDoctorPage + 1)
                            * root.previewPageSize < root.availableDoctors.length
                        onTriggered: root.previewDoctorPage++
                    }
                }
                GohuText {
                    width: parent.width
                    text: "PROVIDER // CHOOSE PX RUNTIME"
                    font.pixelSize: 10
                    color: Colors.orange
                }
                GohuText {
                    width: parent.width
                    visible: root.availableProviders.length === 0
                    text: "NO PROVIDERS LOADED // REFRESH PROVIDER DIRECTORY"
                    font.pixelSize: 9
                    color: Colors.orange
                }
                Repeater {
                    model: root.availableProviders.slice(
                        root.previewProviderPage * root.previewPageSize,
                        (root.previewProviderPage + 1) * root.previewPageSize)
                    Rectangle {
                        required property var modelData
                        width: attachRows.width
                        height: 30
                        color: Colors.black
                        border.width: 1
                        border.color: String(modelData.id || "") === root.previewProviderId
                            ? Colors.orange : Colors.magenta
                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 6
                            text: String(modelData.name || modelData.id || "")
                                + " // " + (modelData.available ? "LISTED AVAILABLE"
                                    : "UNAVAILABLE")
                                + " // " + String(modelData.id || "")
                            color: Colors.white
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.previewProviderId =
                                String(modelData.id || "")
                        }
                    }
                }
                Row {
                    width: parent.width
                    height: 27
                    spacing: 5
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "PREV"
                        compactIcon: "<"
                        accent: Colors.cyan
                        enabledAction: root.previewProviderPage > 0
                        onTriggered: root.previewProviderPage--
                    }
                    GohuText {
                        width: parent.width - 157
                        height: parent.height
                        text: "PROVIDERS // " + root.availableProviders.length
                            + " // PAGE " + (root.previewProviderPage + 1)
                        font.pixelSize: 8
                        color: Colors.blue
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    HospitalActionButton {
                        width: 76
                        height: 26
                        label: "NEXT"
                        compactIcon: ">"
                        accent: Colors.cyan
                        enabledAction: (root.previewProviderPage + 1)
                            * root.previewPageSize < root.availableProviders.length
                        onTriggered: root.previewProviderPage++
                    }
                }
                GohuText {
                    width: parent.width
                    text: "VERIFICATION // BED AND SESSION"
                    font.pixelSize: 10
                    color: Colors.orange
                }
                GohuText {
                    width: parent.width
                    text: "No Bed edits here. PX admission can register an IDLE Session only after explicit confirmation and fresh backend checks."
                    color: Colors.blue
                    font.pixelSize: 9
                    wrapMode: Text.Wrap
                }
                Repeater {
                    model: root.attachmentPreview.blockers
                    GohuText {
                        required property string modelData
                        width: attachRows.width
                        text: "! " + modelData
                        color: Colors.red
                        font.pixelSize: 9
                        wrapMode: Text.Wrap
                    }
                }
                Repeater {
                    model: root.attachmentPreview.notes
                    GohuText {
                        required property string modelData
                        width: attachRows.width
                        text: "· " + modelData
                        color: Colors.blue
                        font.pixelSize: 9
                        wrapMode: Text.Wrap
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 48
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange
                    GohuText {
                        anchors.fill: parent
                        anchors.margins: 7
                        text: root.attachmentPreview.reviewable
                            ? "PREVIEW CONSISTENT // NO ATTACHMENT MADE. Operator approval and atomic PX preflight required."
                            : "BLOCKED // NOTHING CHANGED. Resolve listed issues; no connection or registration attempted."
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.Wrap
                    }
                }
                GohuText {
                    width: parent.width
                    text: root.attachmentOutcome || attachmentAction.lastError
                        || (attachmentAction.running
                            ? "PX ATTACH IN PROGRESS // WAITING FOR VERIFICATION"
                            : "NOT ATTACHED // SELECT REVIEW TO ARM")
                    font.pixelSize: 9
                    color: attachmentAction.lastError ? Colors.red : Colors.orange
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    visible: root.attachmentArmed
                    text: "CONFIRM EXACT PX SESSION // " + root.attachmentSessionId
                        + " // " + root.attachmentPreview.sessionMode
                    font.pixelSize: 9
                    color: Colors.cyan
                    wrapMode: Text.Wrap
                }
                HospitalActionButton {
                    width: parent.width
                    height: 31
                    label: attachmentAction.running
                        ? "PX ATTACH IN PROGRESS"
                        : "REVIEW ATTACHMENT"
                    compactIcon: "LINK"
                    accent: Colors.orange
                    enabledAction: root.active && root.roomMatches
                        && root.attachmentPreview.reviewable
                        && !attachmentAction.running
                    onTriggered: root.armAttachment()
                }
                HospitalActionButton {
                    width: parent.width
                    height: 33
                    label: "CONFIRM ATTACH // REGISTER IDLE SESSION"
                    compactIcon: "LINK"
                    accent: Colors.green
                    enabledAction: root.attachmentArmed
                        && root.attachmentPreview.reviewable
                        && !attachmentAction.running
                    onTriggered: root.confirmAttachment()
                }
                GohuText {
                    width: parent.width
                    text: "CONFIRM writes PX Room/Session records only. No AI launch, no browser ChatGPT attachment, no role authorization granted."
                    font.pixelSize: 9
                    color: Colors.blue
                    wrapMode: Text.Wrap
                }
                HospitalActionButton {
                    width: parent.width
                    height: 29
                    label: "BACK TO CONNECTIONS"
                    compactIcon: "LINK"
                    accent: Colors.cyan
                    onTriggered: {
                        if (!attachmentAction.running)
                            root.viewMode = "connections";
                    }
                }
            }
        }

        NeonScrollBar {
            flickable: attachScroll
            handleStyle: "star"
            visible: root.viewMode === "attachPreview" && scrollable
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
            text: "PX ONLY // Not a browser ChatGPT tab. Attachment registers a Session only; provider launch and role authority remain separate."
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.Wrap
        }
    }
}
