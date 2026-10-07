import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: adapter

    property var conversations: []
    property bool loading: false
    property string error: ""

    property string selectedConversationId: ""
    property string activeSessionId: ""
    property string doctorId: ""
    property string providerId: ""
    property string workingDirectory: ""

    property var roomSessions: []
    property bool sessionsLoading: false
    property string sessionsError: ""
    property string sessionLookupRoomId: ""
    property bool continueAfterSessionDiscovery: false
    property string queuedSessionDiscoveryRoomId: ""
    property bool queuedSessionContinue: false

    property var messages: []
    property bool messagesLoading: false
    property string messagesError: ""
    property bool messageRefreshPending: false

    property bool sending: false
    property string sendError: ""
    property int sendSuccessSerial: 0

    property bool creatingSession: false
    property string sessionError: ""
    property var createdSessionResult: null
    property string pendingTurnBody: ""
    property string pendingTurnRoomId: ""
    property string turnBody: ""
    property var lastTurnResult: null

    property int messageLimit: 100
    property string operatorId: "operator"

    property bool bindingRoom: false
    property string bindError: ""
    property string bindingRoomId: ""
    property var boundRoomResult: null
    property var queuedRoomBinding: null

    signal messageSent
    signal roomBound(var room)
    signal sessionResolved(string sessionId)
    signal turnCompleted(var result)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];
        return [
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" "$@"',
            "hospital-room-conversation"
        ].concat(suffix);
    }

    function bindRoom(roomValue) {
        const room = roomValue || {};
        const roomId = String(room.id || room.roomId || "").trim();
        const repository = String(room.repository || "").trim();

        if (!roomId || !repository) {
            bindError = "HOSPITAL ROOM BIND // ROOM AND REPOSITORY REQUIRED";
            return false;
        }

        if (bindProcess.running || bindingRoom) {
            queuedRoomBinding = Object.assign({}, room);
            return false;
        }

        selectedConversationId = roomId;
        bindingRoom = true;
        bindingRoomId = roomId;
        boundRoomResult = null;
        bindError = "";

        const args = [
            "hospital",
            "room-bind",
            roomId,
            "--repository",
            repository
        ];

        const patientId = String(room.patientId || "").trim();
        const patientLabel = String(room.patientLabel || "").trim();
        const team = String(room.team || roomId).trim();
        const branch = String(room.branch || "").trim();
        const bedPath = String(room.bedPath || "").trim();
        const roomDoctorId = String(room.doctorId || "").trim();
        const assignmentId = String(room.assignmentId || "").trim();

        if (patientId) {
            args.push("--patient-id");
            args.push(patientId);
        }

        if (patientLabel) {
            args.push("--patient-label");
            args.push(patientLabel);
        }

        if (team) {
            args.push("--team");
            args.push(team);
        }

        if (branch) {
            args.push("--branch");
            args.push(branch);
        }

        if (bedPath) {
            args.push("--bed-path");
            args.push(bedPath);
        }

        if (roomDoctorId) {
            args.push("--doctor-id");
            args.push(roomDoctorId);
        }

        if (assignmentId) {
            args.push("--assignment-id");
            args.push(assignmentId);
        }

        args.push("--json");
        bindProcess.exec(pxArgs(args));
        return true;
    }

    function runQueuedRoomBind() {
        const next = queuedRoomBinding;

        if (!next)
            return;

        queuedRoomBinding = null;
        Qt.callLater(function() {
            adapter.bindRoom(next);
        });
    }

    function refresh() {
        if (roomsProcess.running)
            return false;

        loading = true;
        error = "";
        roomsProcess.exec(pxArgs([
            "hospital",
            "rooms",
            "--json"
        ]));
        return true;
    }

    function loadMessages(conversationId) {
        const roomId = String(conversationId || "").trim();

        if (!roomId)
            return false;

        selectedConversationId = roomId;
        messages = [];
        refreshMessages();
        discoverSession(roomId, false);
        return true;
    }

    function refreshMessages() {
        const roomId = String(selectedConversationId || "").trim();

        if (!roomId)
            return false;

        if (messagesProcess.running) {
            messageRefreshPending = true;
            return false;
        }

        if (messages.length === 0)
            messagesLoading = true;

        messagesError = "";
        messagesProcess.exec(pxArgs([
            "hospital",
            "messages",
            roomId,
            "--limit",
            String(Math.max(1, Math.min(500, messageLimit))),
            "--json"
        ]));
        return true;
    }

    function compatibleSession(rows) {
        const source = Array.isArray(rows) ? rows : [];
        const wantedProvider = String(providerId || "").trim();
        const wantedDoctor = String(doctorId || "").trim();

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const status = String(row.status || "").toUpperCase();

            if (status === "COMPLETE" || status === "FAILED")
                continue;

            if (wantedProvider
                    && String(row.providerId || "") !== wantedProvider)
                continue;

            if (wantedDoctor
                    && String(row.doctorId || "") !== wantedDoctor)
                continue;

            return row;
        }

        return null;
    }

    function discoverSession(roomIdValue, continueAfter) {
        const roomId = String(roomIdValue || "").trim();

        if (!roomId)
            return false;

        if (sessionsProcess.running || sessionsLoading) {
            queuedSessionDiscoveryRoomId = roomId;
            queuedSessionContinue =
                queuedSessionContinue || !!continueAfter;
            return false;
        }

        sessionsLoading = true;
        sessionsError = "";
        sessionLookupRoomId = roomId;
        continueAfterSessionDiscovery = !!continueAfter;

        sessionsProcess.exec(pxArgs([
            "hospital",
            "sessions",
            "--room-id",
            roomId,
            "--json"
        ]));
        return true;
    }

    function runQueuedSessionDiscovery() {
        const roomId = queuedSessionDiscoveryRoomId;
        const shouldContinue = queuedSessionContinue;

        queuedSessionDiscoveryRoomId = "";
        queuedSessionContinue = false;

        if (!roomId)
            return;

        Qt.callLater(function() {
            adapter.discoverSession(roomId, shouldContinue);
        });
    }

    function createSessionForPendingTurn() {
        const roomId = String(pendingTurnRoomId || selectedConversationId || "").trim();
        const provider = String(providerId || "").trim();
        const doctor = String(doctorId || "").trim();
        const cwd = String(workingDirectory || "").trim();

        if (!roomId || !provider || !doctor || !cwd) {
            sending = false;
            sessionError =
                "HOSPITAL DOCTOR SESSION // ROOM, DOCTOR, PROVIDER, AND BED REQUIRED";
            sendError = sessionError;
            pendingTurnBody = "";
            pendingTurnRoomId = "";
            return false;
        }

        if (sessionCreateProcess.running || creatingSession)
            return false;

        creatingSession = true;
        sessionError = "";
        createdSessionResult = null;

        sessionCreateProcess.exec(pxArgs([
            "agent",
            "session-create",
            "--room-id",
            roomId,
            "--doctor-id",
            doctor,
            "--provider-id",
            provider,
            "--working-directory",
            cwd,
            "--json"
        ]));
        return true;
    }

    function runPendingTurn() {
        const sessionId = String(activeSessionId || "").trim();
        const body = String(pendingTurnBody || "");
        const cwd = String(workingDirectory || "").trim();

        if (!sessionId || !body) {
            sending = false;
            sendError = "HOSPITAL DOCTOR TURN // SESSION OR MESSAGE MISSING";
            return false;
        }

        if (turnProcess.running)
            return false;

        turnBody = body;
        lastTurnResult = null;
        sendError = "";

        const args = [
            "agent",
            "turn",
            sessionId,
            "--prompt-json-stdin",
            "--author-id",
            String(operatorId || "operator"),
            "--message-type",
            "chat"
        ];

        if (cwd) {
            args.push("--working-directory");
            args.push(cwd);
        }

        args.push("--json");
        turnProcess.exec(pxArgs(args));
        return true;
    }

    function sendMessage(conversationId, textValue) {
        const roomId = String(conversationId || "").trim();
        const body = String(textValue || "").trim();

        if (!roomId || !body || sending || turnProcess.running)
            return false;

        sending = true;
        sendError = "";
        sessionError = "";
        pendingTurnRoomId = roomId;
        pendingTurnBody = body;

        if (activeSessionId)
            return runPendingTurn();

        discoverSession(roomId, true);
        return true;
    }

    function maybeRefreshSelectedRoom() {
        if (selectedConversationId)
            refreshMessages();
        refresh();
    }

    function resetResolvedSession() {
        activeSessionId = "";
        roomSessions = [];

        if (selectedConversationId)
            discoverSession(selectedConversationId, false);
    }

    onProviderIdChanged: resetResolvedSession()
    onDoctorIdChanged: resetResolvedSession()

    Process {
        id: bindProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    adapter.boundRoomResult = JSON.parse(body);
                } catch (parseError) {
                    adapter.bindError =
                        "HOSPITAL ROOM BIND // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.bindError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            const roomId = adapter.bindingRoomId;
            adapter.bindingRoom = false;
            adapter.bindingRoomId = "";

            if (Number(code) === 0
                    && !adapter.bindError
                    && adapter.boundRoomResult) {
                adapter.roomBound(adapter.boundRoomResult);
                adapter.refresh();

                if (adapter.selectedConversationId === roomId) {
                    adapter.refreshMessages();
                    adapter.discoverSession(roomId, false);
                }
            } else if (!adapter.bindError) {
                adapter.bindError = "PX HOSPITAL ROOM BIND EXIT " + String(code);
            }

            adapter.runQueuedRoomBind();
        }
    }

    Process {
        id: roomsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(String(this.text || "[]"));

                    if (!Array.isArray(result))
                        throw new Error("PX Hospital rooms returned non-array data");

                    adapter.conversations = result;
                    adapter.error = "";
                } catch (parseError) {
                    adapter.error =
                        "HOSPITAL CONVERSATION ROOMS // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.error = detail;
            }
        }

        onExited: function(code, exitStatus) {
            adapter.loading = false;

            if (Number(code) !== 0 && !adapter.error)
                adapter.error = "PX HOSPITAL ROOMS EXIT " + String(code);
        }
    }

    Process {
        id: sessionsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(String(this.text || "[]"));

                    if (!Array.isArray(result))
                        throw new Error("PX Hospital sessions returned non-array data");

                    adapter.roomSessions = result;
                    adapter.sessionsError = "";

                    if (adapter.sessionLookupRoomId
                            === adapter.selectedConversationId) {
                        const matched = adapter.compatibleSession(result);
                        adapter.activeSessionId =
                            matched ? String(matched.id || "") : "";

                        if (adapter.activeSessionId)
                            adapter.sessionResolved(adapter.activeSessionId);
                    }
                } catch (parseError) {
                    adapter.sessionsError =
                        "HOSPITAL DOCTOR SESSIONS // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.sessionsError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            const shouldContinue = adapter.continueAfterSessionDiscovery;
            adapter.sessionsLoading = false;
            adapter.continueAfterSessionDiscovery = false;

            if (Number(code) !== 0 && !adapter.sessionsError)
                adapter.sessionsError =
                    "PX HOSPITAL SESSIONS EXIT " + String(code);

            if (Number(code) === 0
                    && !adapter.sessionsError
                    && shouldContinue
                    && adapter.pendingTurnBody) {
                if (adapter.activeSessionId)
                    adapter.runPendingTurn();
                else
                    adapter.createSessionForPendingTurn();
            } else if (shouldContinue && adapter.sessionsError) {
                adapter.sending = false;
                adapter.sendError = adapter.sessionsError;
                adapter.pendingTurnBody = "";
                adapter.pendingTurnRoomId = "";
            }

            adapter.runQueuedSessionDiscovery();
        }
    }

    Process {
        id: sessionCreateProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    adapter.createdSessionResult = JSON.parse(body);
                } catch (parseError) {
                    adapter.sessionError =
                        "HOSPITAL DOCTOR SESSION CREATE // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.sessionError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            adapter.creatingSession = false;

            if (Number(code) === 0
                    && !adapter.sessionError
                    && adapter.createdSessionResult) {
                adapter.activeSessionId =
                    String(adapter.createdSessionResult.id || "");

                if (!adapter.activeSessionId) {
                    adapter.sessionError =
                        "HOSPITAL DOCTOR SESSION CREATE // SESSION ID MISSING";
                } else {
                    adapter.sessionResolved(adapter.activeSessionId);
                    adapter.runPendingTurn();
                    return;
                }
            }

            adapter.sending = false;

            if (!adapter.sessionError)
                adapter.sessionError =
                    "PX HOSPITAL AGENT SESSION CREATE EXIT " + String(code);

            adapter.sendError = adapter.sessionError;
            adapter.pendingTurnBody = "";
            adapter.pendingTurnRoomId = "";
        }
    }

    Process {
        id: messagesProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(String(this.text || "[]"));

                    if (!Array.isArray(result))
                        throw new Error("PX Hospital messages returned non-array data");

                    adapter.messages = result;
                    adapter.messagesError = "";
                } catch (parseError) {
                    adapter.messagesError =
                        "HOSPITAL CONVERSATION MESSAGES // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.messagesError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            adapter.messagesLoading = false;

            if (Number(code) !== 0 && !adapter.messagesError)
                adapter.messagesError =
                    "PX HOSPITAL MESSAGES EXIT " + String(code);

            if (adapter.messageRefreshPending) {
                adapter.messageRefreshPending = false;
                adapter.refreshMessages();
            }
        }
    }

    Process {
        id: turnProcess

        stdinEnabled: true

        onStarted: {
            turnProcess.write(
                JSON.stringify({
                    prompt: adapter.turnBody
                }) + "\n"
            );
        }

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    adapter.lastTurnResult = JSON.parse(body);
                } catch (parseError) {
                    adapter.sendError =
                        "HOSPITAL DOCTOR TURN // "
                        + String(parseError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    adapter.sendError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            adapter.sending = false;

            if (Number(code) === 0
                    && !adapter.sendError
                    && adapter.lastTurnResult) {
                adapter.sendSuccessSerial += 1;
                adapter.messageSent();
                adapter.turnCompleted(adapter.lastTurnResult);
                adapter.pendingTurnBody = "";
                adapter.pendingTurnRoomId = "";
                adapter.turnBody = "";
                adapter.maybeRefreshSelectedRoom();
                adapter.discoverSession(
                    adapter.selectedConversationId,
                    false
                );
                return;
            }

            if (!adapter.sendError)
                adapter.sendError =
                    "PX HOSPITAL AGENT TURN EXIT " + String(code);

            adapter.pendingTurnBody = "";
            adapter.pendingTurnRoomId = "";
            adapter.turnBody = "";
            adapter.refreshMessages();
            adapter.discoverSession(
                adapter.selectedConversationId,
                false
            );
        }
    }

    Component.onCompleted: refresh()
}
