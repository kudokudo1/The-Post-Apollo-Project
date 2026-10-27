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
    readonly property string loginBridgePath: Quickshell.shellPath("services/messaging/bridges/telegram/login_ui.py")

    // Explicit, user-initiated account connection. No automatic login.
    property string loginState: "IDLE"
    property string loginDetail: ""
    property var qrModules: []
    property string loginMode: ""
    property string requestedLoginMode: ""
    property bool loginCancelled: false
    property string pendingAppId: ""
    property string pendingAppHash: ""
    property string requestedAppKeyIdentityId: ""
    property string runningAppKeyIdentityId: ""
    readonly property bool loginInProgress: loginProcess.running

    // UI shows only whether an app key pair is configured, NEVER the keys.
    // This read-only helper does not connect to Telegram or open sessions.
    property string appKeyConfigurationStatus: "NOT_CHECKED"
    property string appKeyConfigurationScope: ""
    property string appKeyConfigurationOutput: ""
    property string runningAppKeyStatusScope: ""

    function inspectApplicationKeys(identityId) {
        if (!active || appKeyStatusProcess.running)
            return false;
        const scope = identityId === undefined || identityId === null
                      ? "" : String(identityId);
        if (scope !== "" && !/^identity-[1-9][0-9]{0,8}$/.test(scope))
            return false;
        appKeyConfigurationScope = scope;
        runningAppKeyStatusScope = scope;
        appKeyConfigurationStatus = "CHECKING";
        appKeyConfigurationOutput = "";
        var commandArgs = [pythonPath, loginBridgePath, "status"];
        if (scope !== "")
            commandArgs.push("--identity", scope);
        appKeyStatusProcess.command = commandArgs;
        appKeyStatusProcess.running = true;
        return true;
    }

    function startLogin(mode) {
        if (!active || (mode !== "qr" && mode !== "phone" && mode !== "configure"))
            return;
        requestedLoginMode = mode;
        if (loginProcess.running) {
            loginCancelled = true;
            loginProcess.running = false;
            return;
        }
        launchRequestedLogin();
    }

    function launchRequestedLogin() {
        if (!active || !requestedLoginMode || loginProcess.running)
            return;
        loginMode = requestedLoginMode;
        requestedLoginMode = "";
        loginCancelled = false;
        loginState = "CONNECTING";
        loginDetail = "Connecting to Telegram...";
        qrModules = [];
        // An identity-specific configuration is a distinct complete API key
        // pair, not a Telegram login and never a different live chat account.
        var commandArgs = [pythonPath, loginBridgePath, loginMode];
        if (loginMode === "configure" && requestedAppKeyIdentityId !== "") {
            if (!/^identity-[1-9][0-9]{0,8}$/.test(requestedAppKeyIdentityId)) {
                loginState = "ERROR";
                loginDetail = "Invalid Telegram identity configuration target";
                pendingAppId = "";
                pendingAppHash = "";
                return;
            }
            commandArgs.push("--identity", requestedAppKeyIdentityId);
        }
        runningAppKeyIdentityId = loginMode === "configure"
                                  ? requestedAppKeyIdentityId : "";
        requestedAppKeyIdentityId = "";
        loginProcess.command = commandArgs;
        loginProcess.running = true;
    }

    function cancelLogin() {
        requestedLoginMode = "";
        loginCancelled = true;
        loginProcess.running = false;
        loginState = "IDLE";
        loginDetail = "";
        qrModules = [];
        pendingAppId = "";
        pendingAppHash = "";
        requestedAppKeyIdentityId = "";
        runningAppKeyIdentityId = "";
        appKeyConfigurationStatus = "NOT_CHECKED";
        appKeyConfigurationScope = "";
    }

    function submitPhone(value) {
        if (loginProcess.running && loginState === "PHONE_REQUIRED")
            loginProcess.write(JSON.stringify({action: "phone", value: String(value)}) + "\n");
    }

    function submitCode(value) {
        if (loginProcess.running && loginState === "CODE_REQUIRED")
            loginProcess.write(JSON.stringify({action: "code", value: String(value)}) + "\n");
    }

    function submitPassword(value) {
        if (loginProcess.running && loginState === "PASSWORD_REQUIRED")
            loginProcess.write(JSON.stringify({action: "password", value: String(value)}) + "\n");
    }

    function saveApplicationKeys(apiId, apiHash, identityId) {
        if (!active)
            return;
        const scope = identityId === undefined || identityId === null
                      ? "" : String(identityId);
        if (scope !== "" && !/^identity-[1-9][0-9]{0,8}$/.test(scope))
            return;
        pendingAppId = String(apiId);
        pendingAppHash = String(apiHash);
        requestedAppKeyIdentityId = scope;
        startLogin("configure");
    }

    function handleLoginEvent(line) {
        if (!active || loginCancelled)
            return;
        try {
            const event = JSON.parse(String(line));
            const state = String(event.state || "ERROR");
            loginState = state === "INVALID_CODE" ? "CODE_REQUIRED" : state;
            loginDetail = String(event.detail || "");
            qrModules = state === "QR_READY" && Array.isArray(event.modules) ? event.modules : [];
            if (state === "READY") {
                loginDetail = "Connected. Loading your conversations...";
                backendMode = "PROBING";
            }
        } catch (e) {
            loginState = "ERROR";
            loginDetail = "Invalid connection status from Telegram";
        }
    }

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
            cancelLogin();
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
        id: loginProcess
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(line) {
                adapter.handleLoginEvent(line);
            }
        }
        onStarted: {
            if (adapter.loginMode === "configure") {
                write(JSON.stringify({
                    action: "configure",
                    apiId: adapter.pendingAppId,
                    apiHash: adapter.pendingAppHash
                }) + "\n");
                adapter.pendingAppId = "";
                adapter.pendingAppHash = "";
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (adapter.loginCancelled) {
                adapter.loginCancelled = false;
                Qt.callLater(function() { adapter.launchRequestedLogin(); });
                return;
            }
            if (!adapter.active)
                return;
            if (adapter.loginState === "APP_SAVED") {
                if (adapter.runningAppKeyIdentityId === "") {
                    // Existing universal flow: continue QR pairing within
                    // this very widget, never a separate browser or terminal.
                    adapter.requestedLoginMode = "qr";
                    Qt.callLater(function() { adapter.launchRequestedLogin(); });
                } else {
                    // Only the per-identity application override was saved.
                    // NEVER start the legacy shared Telegram account here.
                    adapter.loginDetail = "Identity application keys saved privately. "
                                          + "Telegram account pairing will use them only "
                                          + "when per-identity sessions are enabled.";
                    adapter.inspectApplicationKeys(
                        adapter.runningAppKeyIdentityId);
                }
                adapter.runningAppKeyIdentityId = "";
            } else if (adapter.loginState === "READY") {
                Qt.callLater(function() { adapter.probe(); });
            } else if (adapter.loginState === "CONNECTING") {
                adapter.loginState = "ERROR";
                adapter.loginDetail = "Telegram connection stopped; retry";
            }
        }
    }

    Process {
        id: appKeyStatusProcess
        stdout: StdioCollector {
            onStreamFinished: adapter.appKeyConfigurationOutput = String(text || "")
        }
        onExited: function(exitCode) {
            if (!adapter.active
                    || adapter.runningAppKeyStatusScope
                       !== adapter.appKeyConfigurationScope)
                return;
            var result = null;
            try { result = JSON.parse(adapter.appKeyConfigurationOutput); }
            catch (e) { }
            if (exitCode !== 0 || !result || result.state !== "APP_KEY_STATUS"
                    || result.scope !== (adapter.appKeyConfigurationScope || "universal")
                    || (result.configuration !== "CONFIGURED"
                        && result.configuration !== "UNAVAILABLE")
                    || ["UNIVERSAL", "IDENTITY_OVERRIDE", "UNAVAILABLE"]
                       .indexOf(result.source) < 0) {
                adapter.appKeyConfigurationStatus = "UNAVAILABLE";
                return;
            }
            if (result.configuration === "CONFIGURED")
                adapter.appKeyConfigurationStatus =
                    result.source === "IDENTITY_OVERRIDE"
                    ? "IDENTITY OVERRIDE CONFIGURED"
                    : "UNIVERSAL APP KEYS CONFIGURED";
            else
                adapter.appKeyConfigurationStatus =
                    "APP KEYS MISSING OR INVALID";
        }
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
