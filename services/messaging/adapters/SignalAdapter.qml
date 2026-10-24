import QtQuick

Item {
    id: adapter

    // Research gate: no supported personal-account integration was verified
    // for this provider. Keep the required adapter surface inert and explicit
    // rather than falling back to scraping, password automation, or bot /
    // business APIs that do not represent the operator's personal inbox.
    readonly property string serviceId: "signal"
    property bool active: false

    readonly property string backendMode: "UNSUPPORTED"
    readonly property string backendDetail: "No supported Signal personal-account automation interface was verified; Signal prohibits auto-messaging and unauthorized service access."

    // Shared capability keys are intentionally not frozen in contract v1.0.
    // Do not invent cross-adapter names here; integration owner will define them.
    readonly property var capabilities: ({})

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

    function refresh() {
        loading = false;
        conversations = [];
        error = backendDetail;
        return false;
    }

    function loadMessages(conversationId) {
        selectedConversationId = String(conversationId || "");
        messagesLoading = false;
        messages = [];
        messagesError = backendDetail;
        return false;
    }

    function refreshMessages() {
        messagesLoading = false;
        messages = [];
        messagesError = backendDetail;
        return false;
    }

    function sendMessage(conversationId, text) {
        sending = false;
        sendError = backendDetail;
        return false;
    }
}
