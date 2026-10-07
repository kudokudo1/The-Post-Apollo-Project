import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: adapter

    property string pythonPath: "/usr/bin/python3"
    readonly property string bridgePath: Quickshell.shellPath("services/messaging/SessionBridge.py")

    property string backendMode: "PROBING"
    property string backendDetail: ""

    property string conversationStderr: ""
    property string messageStderr: ""
    property string sendStderr: ""
    property string healthStderr: ""

    function bridgeCommand(args) {
        return [pythonPath, bridgePath].concat(args || []);
    }

    function compactProcessError(value, context) {
        const detail = String(value || "").trim();

        if (detail === "")
            return context + " failed";

        const lines = detail.split("\n").filter(function (line) {
            return line.trim() !== "";
        });

        const last = lines.length > 0 ? lines[lines.length - 1].trim() : detail;

        return context + ": " + last;
    }

    // ---------------------------------------------------------
    // CONVERSATIONS
    // ---------------------------------------------------------

    property var conversations: []
    property bool loading: false
    property string error: ""

    // ---------------------------------------------------------
    // MESSAGES
    // ---------------------------------------------------------

    property string selectedConversationId: ""
    property var messages: []
    property bool messagesLoading: false
    property string messagesError: ""

    property bool messageRefreshPending: false

    // ---------------------------------------------------------
    // SENDING
    // ---------------------------------------------------------

    property bool sending: false
    property string sendError: ""

    // Incremented after every successful send.
    // ChatFeed uses this to know when it is safe to clear
    // the composer.
    property int sendSuccessSerial: 0

    signal messageSent

    function refresh() {
        if (conversationProcess.running)
            return;

        loading = true;
        error = "";
        conversationStderr = "";

        conversationProcess.command = bridgeCommand(["--json", "list"]);
        conversationProcess.running = true;
    }

    function loadMessages(conversationId) {
        if (!conversationId || conversationId === "")
            return;

        selectedConversationId = conversationId;

        refreshMessages();
    }

    function refreshMessages() {
        if (!selectedConversationId || selectedConversationId === "") {
            return;
        }

        if (messageProcess.running) {
            messageRefreshPending = true;
            return;
        }

        // Only show LOADING on the initial fetch.
        // Background refreshes stay silent.
        if (messages.length === 0)
            messagesLoading = true;

        messagesError = "";
        messageStderr = "";

        messageProcess.command = bridgeCommand([
            "--json",
            "messages",
            "--limit",
            "100",
            selectedConversationId
        ]);

        messageProcess.running = true;
    }

    function sendMessage(conversationId, text) {
        if (!conversationId || conversationId === "")
            return false;

        const trimmed = text.trim();

        if (trimmed === "")
            return false;

        if (sendProcess.running || sending)
            return false;

        sending = true;
        sendError = "";
        sendStderr = "";

        sendProcess.command = bridgeCommand([
            "send",
            conversationId,
            trimmed
        ]);

        sendProcess.running = true;

        return true;
    }

    // ---------------------------------------------------------
    // BACKEND HEALTH
    // ---------------------------------------------------------

    Process {
        id: healthProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(text || "").trim();

                if (body === "")
                    return;

                try {
                    const result = JSON.parse(body);

                    adapter.backendMode = String(result.mode || "READY");
                    adapter.backendDetail = String(result.detail || "");

                    console.log(
                        "SessionAdapter backend:",
                        adapter.backendMode,
                        adapter.backendDetail
                    );
                } catch (e) {
                    adapter.backendMode = "ERROR";
                    adapter.backendDetail = "Session bridge health JSON error: " + e;
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                adapter.healthStderr = String(text || "").trim();

                if (adapter.healthStderr !== "")
                    console.log("Session bridge health:", adapter.healthStderr);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                adapter.backendMode = "ERROR";
                adapter.backendDetail = adapter.compactProcessError(
                    adapter.healthStderr,
                    "SESSION BACKEND"
                );
            }
        }
    }

    // ---------------------------------------------------------
    // CONVERSATION PROCESS
    // ---------------------------------------------------------

    Process {
        id: conversationProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);

                    if (!Array.isArray(result)) {
                        throw new Error("Session returned non-array conversation data");
                    }

                    adapter.conversations = result;
                    adapter.error = "";

                    console.log("SessionAdapter:", result.length, "conversation(s)");
                } catch (e) {
                    adapter.error = "Session conversation JSON error: " + e;

                    console.log(adapter.error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                adapter.conversationStderr = String(text || "").trim();

                if (adapter.conversationStderr !== "")
                    console.log("Session conversation error:", adapter.conversationStderr);
            }
        }

        onExited: function (exitCode, exitStatus) {
            adapter.loading = false;

            if (exitCode !== 0) {
                adapter.error = adapter.compactProcessError(
                    adapter.conversationStderr,
                    "SESSION LIST"
                );
            }
        }
    }

    // ---------------------------------------------------------
    // MESSAGE PROCESS
    // ---------------------------------------------------------

    Process {
        id: messageProcess

        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);

                    if (!Array.isArray(result)) {
                        throw new Error("Session returned non-array message data");
                    }

                    /*
                     * The bridge normalizes direction/type and preserves
                     * session-cli's newest -> oldest ordering.
                     *
                     * The chat UI wants oldest -> newest.
                     */
                    const sorted = result.slice().sort(function (a, b) {
                        const aTime = a.sent_at || a.received_at || a.timestamp || 0;
                        const bTime = b.sent_at || b.received_at || b.timestamp || 0;

                        return aTime - bTime;
                    });

                    adapter.messages = sorted;
                    adapter.messagesError = "";

                    console.log(
                        "SessionAdapter:",
                        sorted.length,
                        "message(s), newest:",
                        sorted.length > 0
                            ? (sorted[sorted.length - 1].sent_at
                               || sorted[sorted.length - 1].timestamp)
                            : "none"
                    );
                } catch (e) {
                    adapter.messagesError = "Session message JSON error: " + e;

                    console.log(adapter.messagesError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                adapter.messageStderr = String(text || "").trim();

                if (adapter.messageStderr !== "")
                    console.log("Session message error:", adapter.messageStderr);
            }
        }

        onExited: function (exitCode, exitStatus) {
            adapter.messagesLoading = false;

            if (exitCode !== 0) {
                adapter.messagesError = adapter.compactProcessError(
                    adapter.messageStderr,
                    "SESSION MESSAGES"
                );
            }

            if (adapter.messageRefreshPending) {
                adapter.messageRefreshPending = false;
                adapter.refreshMessages();
            }
        }
    }

    // ---------------------------------------------------------
    // SEND PROCESS
    // ---------------------------------------------------------

    Process {
        id: sendProcess

        stdout: StdioCollector {
            onStreamFinished: {
                if (String(text || "").trim() !== "") {
                    console.log("Session send:", String(text).trim());
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                adapter.sendStderr = String(text || "").trim();

                if (adapter.sendStderr !== "") {
                    console.log("Session send error:", adapter.sendStderr);
                }
            }
        }

        onExited: function (exitCode, exitStatus) {
            adapter.sending = false;

            if (exitCode === 0) {
                adapter.sendError = "";
                adapter.sendSuccessSerial += 1;

                console.log("SessionAdapter: message sent");

                adapter.messageSent();

                // Don't wait for the normal 3-second poll.
                adapter.refreshMessages();
                adapter.refresh();
            } else {
                adapter.sendError = adapter.compactProcessError(
                    adapter.sendStderr,
                    "SESSION SEND"
                );

                console.log("SessionAdapter:", adapter.sendError);
            }
        }
    }

    // ---------------------------------------------------------
    // POLLING
    // ---------------------------------------------------------

    Timer {
        interval: 5000
        running: true
        repeat: true

        onTriggered: adapter.refresh()
    }

    Timer {
        interval: 3000

        running: adapter.selectedConversationId !== ""

        repeat: true

        onTriggered: adapter.refreshMessages()
    }

    Component.onCompleted: {
        healthStderr = "";
        healthProcess.command = bridgeCommand(["--json", "health"]);
        healthProcess.running = true;

        adapter.refresh();
    }
}
