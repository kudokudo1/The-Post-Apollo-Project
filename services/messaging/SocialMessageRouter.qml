import QtQuick
import "adapters"

// One shared owner for Social's native message backends.
// The UI only sees the selected adapter; browser modes stay independent.
Item {
    id: router

    property int appIndex: 0
    // Empty until the operator explicitly opts into private Telegram sessions.
    property string telegramIdentityId: ""
    readonly property bool nativeSelected: appIndex === 0 || appIndex === 2
    readonly property var selectedBackend: appIndex === 0 ? sessions
                                            : appIndex === 2 ? telegram : null
    readonly property string serviceId: appIndex === 0 ? "session"
                                              : appIndex === 2 ? "telegram" : ""
    readonly property var conversations: selectedBackend ? selectedBackend.conversations : []
    readonly property var messages: selectedBackend ? selectedBackend.messages : []
    readonly property string selectedConversationId: selectedBackend
        ? String(selectedBackend.selectedConversationId || "") : ""
    readonly property bool messagesLoading: selectedBackend
        ? selectedBackend.messagesLoading : false
    readonly property string messagesError: selectedBackend
        ? selectedBackend.messagesError : ""
    readonly property bool sending: selectedBackend ? selectedBackend.sending : false
    readonly property string sendError: selectedBackend ? selectedBackend.sendError : ""
    // Provider success counters are global per adapter, but the feed must
    // receive confirmations only for its own service and conversation.
    property var confirmedByScope: ({})
    property string pendingSessionConversationId: ""
    property string pendingTelegramConversationId: ""
    property string pendingTelegramScope: ""
    readonly property string telegramScopedServiceId: telegram.identityId !== ""
        ? "telegram@" + telegram.identityId : "telegram"
    readonly property string selectedScope: selectedConversationId !== ""
        ? (appIndex === 2 ? telegramScopedServiceId : serviceId)
          + ":" + selectedConversationId : ""
    readonly property int sendSuccessSerial: selectedScope !== ""
        ? Number(confirmedByScope[selectedScope] || 0) : 0

    function confirmSend(service, conversationId) {
        if (!conversationId)
            return;
        const key = service + ":" + String(conversationId);
        const next = Object.assign({}, confirmedByScope);
        next[key] = Number(next[key] || 0) + 1;
        confirmedByScope = next;
    }

    // Existing Sessions supports text messages but predates capability flags.
    // Telegram's supported feature map is explicitly declared by its adapter.
    readonly property bool sendEnabled: appIndex === 0
        || (appIndex === 2 && telegram.backendMode === "READY"
            && telegram.capabilities.sendText === true)

    // Adapter B's inert sentinel states are surfaced without routing native
    // messages or allowing unsupported send controls.
    readonly property string accessBackendMode:
        appIndex === 15 ? messenger.backendMode :
        appIndex === 26 ? signal.backendMode :
        appIndex === 29 ? viber.backendMode : "UNSUPPORTED"
    readonly property string accessBackendDetail:
        appIndex === 15 ? messenger.backendDetail :
        appIndex === 26 ? signal.backendDetail :
        appIndex === 29 ? viber.backendDetail :
        appIndex === 14 ? "WhatsApp personal inbox is not exposed through an approved native API. WhatsApp Web is a separate provider interface." :
        appIndex === 27 ? "WeChat personal message history is not exposed through an approved native adapter. The provider's desktop app is separate." :
        appIndex === 28 ? "LINE Official Account APIs are not personal inbox access. The provider's Chrome extension is separate." :
        appIndex === 30 ? "No supported KakaoTalk personal inbox adapter is available." :
        appIndex === 31 ? "No supported BeReal desktop/personal-message adapter is available." : ""

    readonly property var telegramBackend: telegram
    readonly property bool telegramNeedsSetup: appIndex === 2
        && (telegram.backendMode !== "READY" || telegram.loginInProgress)

    readonly property string telegramStatus: appIndex === 2
        && telegram.backendMode !== "READY"
        ? "TELEGRAM // " + telegram.backendMode + " // " + telegram.backendDetail
        : ""

    function loadMessages(conversationId) {
        if (!nativeSelected || !selectedBackend || !conversationId)
            return false;
        selectedBackend.loadMessages(String(conversationId));
        return true;
    }

    function sendMessage(conversationId, body) {
        if (!nativeSelected || !selectedBackend || !sendEnabled || !conversationId
                || String(conversationId) !== selectedConversationId)
            return false;
        const accepted = selectedBackend.sendMessage(String(conversationId), body);
        if (accepted) {
            if (appIndex === 0)
                pendingSessionConversationId = String(conversationId);
            else if (appIndex === 2) {
                pendingTelegramConversationId = String(conversationId);
                pendingTelegramScope = telegramScopedServiceId;
            }
        }
        return accepted;
    }

    SessionAdapter {
        id: sessions
        active: router.appIndex === 0
    }

    Connections {
        target: sessions
        function onSendSuccessSerialChanged() {
            if (router.pendingSessionConversationId === "")
                return;
            router.confirmSend("session", router.pendingSessionConversationId);
            router.pendingSessionConversationId = "";
        }
    }

    Connections {
        target: telegram
        function onSendSuccessSerialChanged() {
            if (router.pendingTelegramConversationId === "")
                return;
            router.confirmSend(router.pendingTelegramScope, router.pendingTelegramConversationId);
            router.pendingTelegramConversationId = "";
            router.pendingTelegramScope = "";
        }
    }

    TelegramAdapter {
        id: telegram
        identityId: router.telegramIdentityId
        active: router.appIndex === 2
        onIdentityIdChanged: {
            router.pendingTelegramConversationId = "";
            router.pendingTelegramScope = "";
        }
    }

    SignalAdapter {
        id: signal
        active: router.appIndex === 26
    }
    MessengerAdapter {
        id: messenger
        active: router.appIndex === 15
    }
    ViberAdapter {
        id: viber
        active: router.appIndex === 29
    }
}
