import QtQuick
import "BlueFerryProjectionView.js" as Projection

// P18e // Dormant, service-owned read-only display adapter.
//
// Not an authentication mechanism or a trusted content endpoint. A future
// approved Identity/Phone host must own grant checks, private IPC, revocation
// and reliable purge before feeding data to this adapter. These public QML
// methods accept caller-supplied values and CANNOT prove their provenance.
//
// No Process, network, D-Bus, polling, local store, login or sending.
// Not wired into the shared router or current Social PHONE surface.
Item {
    id: adapter

    readonly property string serviceId: "blueferry"
    property bool active: false

    // "DEGRADED" means *cached, read-only display*, never live sync.
    // The QML state itself is not evidence of a verified host or grant.
    readonly property string backendMode: active && (_hasThreads || _hasContacts)
                                          ? "DEGRADED" : "AUTH_REQUIRED"
    readonly property string backendDetail: active && (_hasThreads || _hasContacts)
        ? "Read-only phone snapshot in memory. Live updates and sending are not connected."
        : "Trusted phone-data host not connected. Pairing or audio alone does not grant access."

    // Key names follow the existing Telegram adapter's service-owned convention;
    // the shared integration owner has not frozen a universal capability shape.
    readonly property var capabilities: ({
        listConversations: adapter.active && adapter._hasThreads,
        readMessages: adapter.active && adapter._hasThreads,
        sendText: false,
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

    // Phone contact cards are NOT chat conversations.
    property var contactCards: []

    property string _contextKey: ""
    property string _profileId: ""
    property int _contextEpoch: 0
    property int _lastEpoch: 0
    property int _messagesSerial: 0
    property int _contactsSerial: 0
    property bool _hasThreads: false
    property bool _hasContacts: false
    property var _messagesById: ({})

    function forgetHostView() {
        // Local in-memory reset only. This is NOT an acknowledged wipe of
        // all rendering, clipboard, plugin copies or a different process.
        _contextKey = "";
        _profileId = "";
        _contextEpoch = 0;
        _messagesSerial = 0;
        _contactsSerial = 0;
        _hasThreads = false;
        _hasContacts = false;
        _messagesById = ({});
        conversations = [];
        contactCards = [];
        selectedConversationId = "";
        messages = [];
        loading = false;
        error = "";
        messagesLoading = false;
        messagesError = "";
        sending = false;
        sendError = "";
    }

    onActiveChanged: {
        if (!active)
            forgetHostView();
    }

    function beginHostView(contextKey, profileId, epoch) {
        // Caller values are untrusted selectors; host ownership of the IPC
        // and verified context is a separate, currently missing prerequisite.
        if (!active || _contextKey !== ""
                || !Projection.validOpaqueContext(contextKey)
                || !Projection.validProfile(profileId)
                || !Projection.validDeliveryEpoch(epoch)
                || epoch <= _lastEpoch)
            return false;
        forgetHostView();
        _contextKey = contextKey;
        _profileId = profileId;
        _contextEpoch = epoch;
        _lastEpoch = epoch;
        return true;
    }

    function dropHostView(contextKey, epoch) {
        // An old revoke or stale async result must not wipe a new context.
        if (!active || _contextKey === ""
                || contextKey !== _contextKey || epoch !== _contextEpoch)
            return false;
        forgetHostView();
        // This is a QML array reset, not a durable host purge ACK.
        return true;
    }

    function applyHostProjection(contextKey, epoch, sequence, operation, payload) {
        if (!active || _contextKey === ""
                || contextKey !== _contextKey || epoch !== _contextEpoch)
            return false;
        if (!Projection.validDeliveryEpoch(sequence)
                || (operation !== "messages.read" && operation !== "contacts.read")) {
            forgetHostView();
            return false;
        }
        if (operation === "messages.read" && sequence <= _messagesSerial)
            return false;
        if (operation === "contacts.read" && sequence <= _contactsSerial)
            return false;

        try {
            if (operation === "messages.read") {
                var next = Projection.messagesView(payload, _profileId);
                if (next === null) {
                    forgetHostView();
                    return false;
                }
                // Commit only after the full snapshot validates.
                _messagesById = next.messagesById;
                conversations = next.conversations;
                _hasThreads = true;
                _messagesSerial = sequence;
                var current = selectedConversationId;
                if (current !== "" && Object.prototype.hasOwnProperty.call(
                        _messagesById, current)) {
                    messages = _messagesById[current].slice(0);
                } else {
                    selectedConversationId = "";
                    messages = [];
                }
            } else {
                var cards = Projection.contactsView(payload, _profileId);
                if (cards === null) {
                    forgetHostView();
                    return false;
                }
                // Contacts stay separate; do not manufacture SMS threads.
                contactCards = cards;
                _hasContacts = true;
                _contactsSerial = sequence;
            }
            return true;
        } catch (error) {
            // Never surface provider exceptions with private message contents.
            forgetHostView();
            return false;
        }
    }

    function refresh() {
        // No call to a provider and no implicit permission request.
        loading = false;
        error = "Trusted phone refresh is not connected.";
        return false;
    }

    function loadMessages(conversationId) {
        messagesLoading = false;
        if (!active || !_hasThreads || typeof conversationId !== "string"
                || !Object.prototype.hasOwnProperty.call(
                    _messagesById, conversationId)) {
            selectedConversationId = "";
            messages = [];
            messagesError = "No current authorized phone snapshot for this conversation.";
            return false;
        }
        selectedConversationId = conversationId;
        messages = _messagesById[conversationId].slice(0);
        messagesError = "";
        return true;
    }

    function refreshMessages() {
        messagesLoading = false;
        messagesError = "Live phone message refresh is not connected.";
        return false;
    }

    function sendMessage(conversationId, text) {
        sending = false;
        sendError = "Sending messages from Social PHONE is not enabled.";
        return false;
    }
}
