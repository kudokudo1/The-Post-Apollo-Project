import QtQuick
import Quickshell
import Quickshell.Io

// Native Telegram adapter, service-owned. No shared UI/router changes.
// Telethon 1.x talks to Telegram's supported personal-client API.
Item {
    id: adapter

    readonly property string serviceId: "telegram"
    property bool active: false
    property string backendMode: "PROBING"
    property string backendDetail: "Select Telegram to check account status"
    // Capability-key naming remains provisional until the shared integration
    // owner freezes it; never interpret this as a cross-service global schema.
    readonly property var capabilities: ({
        listConversations: true,
        readMessages: true,
        sendText: true,
        liveUpdates: false,
        attachments: false,
        calls: false
    })

    property var conversations: []
    property bool loading: false
    property string error: ""

    property string selectedConversationId: ""
    property var messages: []
    property bool messagesLoading: false
    property string messagesError: ""

    property bool sending: false
    property string sendError: ""
    property int sendSuccessSerial: 0

    property int activationSerial: 0
    property int healthRequestSerial: -1
    property int listRequestSerial: -1
    property int messageRequestSerial: -1
    property string requestedConversationId: ""
    property bool queuedMessageRefresh: false
    property string pendingSendText: ""
    property string sendResult: ""
    property string listResult: ""
    property string messageResult: ""
    property string healthResult: ""

    readonly property string bridgePath: Quickshell.shellPath("services/messaging/bridges/telegram/bridge.py")
    property string pythonPath: "/usr/bin/python3"

    function command(args) {
        return [pythonPath, bridgePath].concat(args || []);
    }

    function probe() {
        if (!active || healthProcess.running)
            return;
        backendMode = "PROBING";
        healthResult = "";
        healthRequestSerial = activationSerial;
        healthProcess.command = command(["health"]);
        healthProcess.running = true;
    }

    onActiveChanged: {
        activationSerial++;
        if (active) {
            probe();
        } else {
            // Never leave a selected conversation or private history attached
            // to a deselected service. In-flight reads are generation-guarded.
            selectedConversationId = "";
            conversations = [];
            messages = [];
            queuedMessageRefresh = false;
            loading = false;
            messagesLoading = false;
        }
    }

    function refresh() {
        if (!active || backendMode !== "READY" || listProcess.running)
            return;
        loading = true;
        error = "";
        listResult = "";
        listRequestSerial = activationSerial;
        listProcess.command = command(["list"]);
        listProcess.running = true;
    }

    function loadMessages(conversationId) {
        if (!active || !conversationId)
            return;
        selectedConversationId = String(conversationId);
        messages = [];
        refreshMessages();
    }

    function refreshMessages() {
        if (!active || backendMode !== "READY" || !selectedConversationId)
            return;
        if (messageProcess.running) {
            queuedMessageRefresh = true;
            return;
        }
        messagesLoading = messages.length === 0;
        messagesError = "";
        messageResult = "";
        requestedConversationId = selectedConversationId;
        messageRequestSerial = activationSerial;
        messageProcess.command = command(["messages", requestedConversationId, "--limit", "100"]);
        messageProcess.running = true;
    }

    function sendMessage(conversationId, text) {
        if (!active || backendMode !== "READY" || !capabilities.sendText)
            return false;
        if (sending || sendProcess.running || !conversationId || String(conversationId) !== selectedConversationId)
            return false;
        const body = String(text || "").trim();
        if (!body || body.length > 4096)
            return false;
        sending = true;
        sendError = "";
        sendResult = "";
        pendingSendText = body;
        sendProcess.command = command(["send", String(conversationId)]);
        sendProcess.running = true;
        return true;
    }

    Process {
        id: healthProcess
        stdout: StdioCollector { onStreamFinished: adapter.healthResult = String(text || "") }
        onExited: function(exitCode, exitStatus) {
            if (!adapter.active)
                return;
            if (adapter.healthRequestSerial !== adapter.activationSerial) {
                Qt.callLater(function() { adapter.probe(); });
                return;
            }
            try {
                const result = JSON.parse(adapter.healthResult);
                adapter.backendMode = String(result.mode || "ERROR");
                adapter.backendDetail = String(result.detail || "");
                if (adapter.backendMode === "READY")
                    adapter.refresh();
            } catch (e) {
                adapter.backendMode = "ERROR";
                adapter.backendDetail = "Telegram status unavailable";
            }
        }
    }

    Process {
        id: listProcess
        stdout: StdioCollector { onStreamFinished: adapter.listResult = String(text || "") }
        onExited: function(exitCode, exitStatus) {
            if (!adapter.active || adapter.listRequestSerial !== adapter.activationSerial)
                return;
            adapter.loading = false;
            if (exitCode !== 0) {
                adapter.error = "Telegram conversations unavailable";
                return;
            }
            try {
                const data = JSON.parse(adapter.listResult);
                if (!Array.isArray(data))
                    throw new Error("Invalid conversation list");
                adapter.conversations = data;
            } catch (e) {
                adapter.error = "Telegram returned invalid conversation data";
            }
        }
    }

    Process {
        id: messageProcess
        stdout: StdioCollector { onStreamFinished: adapter.messageResult = String(text || "") }
        onExited: function(exitCode, exitStatus) {
            if (adapter.active && adapter.messageRequestSerial === adapter.activationSerial
                    && adapter.requestedConversationId === adapter.selectedConversationId) {
                adapter.messagesLoading = false;
                if (exitCode !== 0) {
                    adapter.messagesError = "Telegram messages unavailable";
                } else {
                    try {
                        const data = JSON.parse(adapter.messageResult);
                        if (!Array.isArray(data))
                            throw new Error("Invalid messages");
                        adapter.messages = data;
                    } catch (e) {
                        adapter.messagesError = "Telegram returned invalid message data";
                    }
                }
            }
            if (adapter.queuedMessageRefresh) {
                adapter.queuedMessageRefresh = false;
                Qt.callLater(function() { adapter.refreshMessages(); });
            }
        }
    }

    Process {
        id: sendProcess
        stdinEnabled: true
        stdout: StdioCollector { onStreamFinished: adapter.sendResult = String(text || "") }
        onStarted: {
            // The text remains out of argv/process lists and logs.
            write(JSON.stringify({ text: adapter.pendingSendText }) + "\n");
        }
        onExited: function(exitCode, exitStatus) {
            adapter.pendingSendText = "";
            adapter.sending = false;
            if (exitCode !== 0) {
                adapter.sendError = "Telegram send failed; delivery not confirmed";
                return;
            }
            try {
                const ack = JSON.parse(adapter.sendResult);
                if (ack.sent !== true || !ack.messageId)
                    throw new Error("Missing provider acknowledgement");
                adapter.sendError = "";
                adapter.sendSuccessSerial += 1;
                if (adapter.active) {
                    adapter.refreshMessages();
                    adapter.refresh();
                }
            } catch (e) {
                adapter.sendError = "Telegram send was not confirmed";
            }
        }
    }

    Timer {
        interval: 7000
        running: adapter.active && adapter.backendMode === "READY"
        repeat: true
        onTriggered: adapter.refresh()
    }
    Timer {
        interval: 4000
        running: adapter.active && adapter.backendMode === "READY" && adapter.selectedConversationId !== ""
        repeat: true
        onTriggered: adapter.refreshMessages()
    }
}
