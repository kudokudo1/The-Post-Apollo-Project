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
    property var messages: []
    property bool messagesLoading: false
    property string messagesError: ""
    property bool messageRefreshPending: false

    property bool sending: false
    property string sendError: ""
    property int sendSuccessSerial: 0

    property int messageLimit: 100
    property string operatorId: "operator"

    signal messageSent

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];
        return [
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" "$@"',
            "hospital-room-conversation"
        ].concat(suffix);
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
        return refreshMessages();
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

    function sendMessage(conversationId, textValue) {
        const roomId = String(conversationId || "").trim();
        const body = String(textValue || "").trim();

        if (!roomId || !body || sending || sendProcess.running)
            return false;

        sending = true;
        sendError = "";

        const args = [
            "hospital",
            "message-append",
            "--room-id",
            roomId
        ];

        if (activeSessionId) {
            args.push("--session-id");
            args.push(String(activeSessionId));
        }

        args.push("--author-role");
        args.push("operator");
        args.push("--author-id");
        args.push(String(operatorId || "operator"));
        args.push("--direction");
        args.push("outgoing");
        args.push("--body");
        args.push(body);
        args.push("--json");

        sendProcess.exec(pxArgs(args));
        return true;
    }

    function maybeRefreshSelectedRoom() {
        if (selectedConversationId)
            refreshMessages();
        refresh();
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
        id: sendProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    JSON.parse(body);
                } catch (parseError) {
                    adapter.sendError =
                        "HOSPITAL CONVERSATION SEND // "
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

            if (Number(code) === 0 && !adapter.sendError) {
                adapter.sendSuccessSerial += 1;
                adapter.messageSent();
                adapter.maybeRefreshSelectedRoom();
                return;
            }

            if (!adapter.sendError)
                adapter.sendError = "PX HOSPITAL SEND EXIT " + String(code);
        }
    }

    Component.onCompleted: refresh()
}
