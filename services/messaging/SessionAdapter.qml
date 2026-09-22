import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: adapter

    property string cliPath: "/var/home/mapple/.local/share/session-cli-venv/bin/session-cli"

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

        messageProcess.command = [cliPath, "--json", "messages", "--limit", "100", selectedConversationId];

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

        sendProcess.command = [cliPath, "send", conversationId, trimmed];

        sendProcess.running = true;

        return true;
    }

    // ---------------------------------------------------------
    // CONVERSATION PROCESS
    // ---------------------------------------------------------

    Process {
        id: conversationProcess

        command: [adapter.cliPath, "--json", "list"]

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
                if (text.trim() !== "") {
                    console.log("Session conversation error:", text);
                }
            }
        }

        onExited: function (exitCode, exitStatus) {
            adapter.loading = false;

            if (exitCode !== 0 && adapter.error === "") {
                adapter.error = "session-cli list exited with code " + exitCode;
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
                     * session-cli gives us newest -> oldest.
                     *
                     * The chat UI wants oldest -> newest.
                     */
                    const sorted = result.slice().sort(function (a, b) {
                        const aTime = a.sent_at || a.received_at || 0;

                        const bTime = b.sent_at || b.received_at || 0;

                        return aTime - bTime;
                    });

                    adapter.messages = sorted;
                    adapter.messagesError = "";

                    console.log("SessionAdapter:", sorted.length, "message(s), newest:", sorted.length > 0 ? sorted[sorted.length - 1].sent_at : "none");
                } catch (e) {
                    adapter.messagesError = "Session message JSON error: " + e;

                    console.log(adapter.messagesError);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim() !== "") {
                    console.log("Session message error:", text);
                }
            }
        }

        onExited: function (exitCode, exitStatus) {
            adapter.messagesLoading = false;

            if (exitCode !== 0 && adapter.messagesError === "") {
                adapter.messagesError = "session-cli messages exited with code " + exitCode;
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
                if (text.trim() !== "") {
                    console.log("Session send:", text.trim());
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim() !== "") {
                    console.log("Session send error:", text.trim());

                    adapter.sendError = text.trim();
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
                if (adapter.sendError === "") {
                    adapter.sendError = "session-cli send exited with code " + exitCode;
                }

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

    Component.onCompleted: adapter.refresh()
}
