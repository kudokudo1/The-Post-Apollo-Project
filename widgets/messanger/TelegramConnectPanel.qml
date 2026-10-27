import QtQuick
import "../../components"

// Same-pane Telegram connection wizard. The QR URL, login code, and passwords
// stay in local process memory; no browser window, terminal or logs are used.
Rectangle {
    id: panel
    property var adapter: null
    // The very same login panel also serves explicit key editing from Social
    // Settings, including after a Telegram account has already connected.
    // Identity overrides are APPLICATION keys only; the live adapter still
    // uses the one shared Telegram personal.session until a separate rollout.
    property bool editApplicationKeys: false
    property string keyIdentityId: ""
    signal closeKeyEditorRequested()
    readonly property bool identityKeyEditor: editApplicationKeys && keyIdentityId !== ""
    readonly property string step: adapter ? String(adapter.loginState || "IDLE") : "IDLE"
    readonly property bool busy: adapter ? adapter.loginInProgress : false
    readonly property var qrMatrixRows: adapter ? adapter.qrModules : []
    onQrMatrixRowsChanged: qrCanvas.requestPaint()

    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true

    component ActionButton: Rectangle {
        id: action
        property string title: ""
        signal clicked()
        height: 43
        width: parent ? Math.min(280, parent.width) : 240
        color: enabled ? Colors.dark : Colors.black
        border.color: enabled ? Colors.orange : Colors.cyan
        border.width: 1
        opacity: enabled ? 1 : 0.5
        Text {
            anchors.centerIn: parent
            text: action.title
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 13
            color: action.enabled ? Colors.cyan : Colors.white
        }
        MouseArea {
            anchors.fill: parent
            enabled: action.enabled
            onClicked: action.clicked()
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 20
        contentHeight: body.height
        contentWidth: width
        clip: true
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: body
            width: parent.width
            spacing: 16

            Text {
                text: panel.editApplicationKeys
                      ? "TELEGRAM // APP CONFIGURATION"
                      : "TELEGRAM // CONNECT ACCOUNT"
                color: Colors.orange
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 19
                font.bold: true
            }
            Text {
                text: panel.adapter && panel.adapter.loginDetail
                    ? panel.adapter.loginDetail
                    : panel.adapter ? panel.adapter.backendDetail : "Connect Telegram"
                width: parent.width
                wrapMode: Text.WordWrap
                color: Colors.cyan
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 13
            }

            Column {
                width: parent.width
                spacing: 12
                visible: panel.step === "APP_REQUIRED" || panel.editApplicationKeys
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: panel.identityKeyEditor
                          ? "OPTIONAL IDENTITY APPLICATION KEYS // " + panel.keyIdentityId
                            + ". Other identities and the shared application keys are unchanged."
                          : "UNIVERSAL APPLICATION KEYS // Shared by default across Post-Apollo identities."
                    color: Colors.orange
                    font.pixelSize: 12
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "Telegram issues the API ID and API hash on its official developer portal. App registration cannot be completed by Telethon. Enter the issued values here. Account sign-in, phone codes and QR pairing stay in this widget."

                    color: Colors.white
                    font.pixelSize: 13
                }
                Text { text: "API ID"; color: Colors.cyan }
                Rectangle {
                    width: Math.min(parent.width, 350); height: 39
                    color: Colors.dark; border.color: Colors.orange
                    TextInput {
                        id: apiIdInput
                        anchors.fill: parent; anchors.margins: 9
                        color: Colors.white
                        font.pixelSize: 15
                        inputMethodHints: Qt.ImhDigitsOnly
                    }
                }
                Text { text: "API HASH"; color: Colors.cyan }
                Rectangle {
                    width: Math.min(parent.width, 350); height: 39
                    color: Colors.dark; border.color: Colors.orange
                    TextInput {
                        id: apiHashInput
                        anchors.fill: parent; anchors.margins: 9
                        color: Colors.white
                        font.pixelSize: 15
                        echoMode: TextInput.Password
                    }
                }
                ActionButton {
                    title: "SAVE APP KEYS"
                    enabled: !panel.busy
                             && /^\d+$/.test(apiIdInput.text.trim())
                             && /^[a-fA-F0-9]{32}$/.test(apiHashInput.text.trim())
                    onClicked: {
                        const idValue = apiIdInput.text;
                        const hashValue = apiHashInput.text;
                        apiIdInput.text = "";
                        apiHashInput.text = "";
                        panel.adapter.saveApplicationKeys(
                            idValue, hashValue,
                            panel.identityKeyEditor ? panel.keyIdentityId : "");
                        if (panel.identityKeyEditor)
                            panel.closeKeyEditorRequested();
                    }
                }
                Text {
                    text: "Your API hash is masked and saved to a private local config file. The hash is never displayed again or sent in process arguments. Telegram's developer registration is a separate provider-controlled requirement."
                    color: Colors.white
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }
            }

            ActionButton {
                title: "BACK TO TELEGRAM"
                visible: panel.editApplicationKeys
                enabled: !panel.busy
                onClicked: panel.closeKeyEditorRequested()
            }

            Column {
                width: parent.width
                spacing: 12
                visible: !panel.editApplicationKeys && panel.step === "QR_READY"
                Text {
                    width: parent.width
                    text: "On your phone: Telegram > Settings > Devices > Link Desktop Device"
                    color: Colors.white
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                }
                Rectangle {
                    width: 270; height: 270
                    color: "white"
                    Canvas {
                        id: qrCanvas
                        anchors.fill: parent
                        anchors.margins: 10
                        renderStrategy: Canvas.Immediate
                        onVisibleChanged: if (visible) requestPaint()
                        onPaint: {
                            const ctx = getContext("2d");
                            if (!ctx)
                                return;
                            ctx.fillStyle = "#ffffff";
                            ctx.fillRect(0, 0, width, height);
                            const rows = panel.qrMatrixRows || [];
                            const count = rows.length;
                            if (count === 0)
                                return;
                            const pixelSize = Math.floor(Math.min(width, height) / count);
                            if (pixelSize < 1)
                                return;
                            const size = pixelSize * count;
                            const left = Math.floor((width - size) / 2);
                            const top = Math.floor((height - size) / 2);
                            ctx.fillStyle = "#000000";
                            for (let row = 0; row < count; row++) {
                                const bits = String(rows[row]);
                                if (bits.length !== count)
                                    return;
                                for (let col = 0; col < count; col++) {
                                    if (bits.charAt(col) === "1")
                                        ctx.fillRect(left + col * pixelSize, top + row * pixelSize, pixelSize, pixelSize);
                                }
                            }
                        }
                    }
                }
                Text {
                    text: "Waiting for approval on your phone. The QR refreshes automatically."
                    color: Colors.cyan
                    width: parent.width; wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }
            }

            Column {
                width: parent.width
                spacing: 12
                visible: !panel.editApplicationKeys && panel.step === "PHONE_REQUIRED"
                Text { text: "PHONE WITH COUNTRY CODE"; color: Colors.cyan }
                Rectangle {
                    width: Math.min(parent.width, 350); height: 40
                    color: Colors.dark; border.color: Colors.orange
                    TextInput {
                        id: phoneInput
                        anchors.fill: parent; anchors.margins: 9
                        color: Colors.white
                        font.pixelSize: 15
                        inputMethodHints: Qt.ImhDialableCharactersOnly
                    }
                }
                ActionButton {
                    title: "SEND VERIFICATION CODE"
                    enabled: phoneInput.text.trim() !== ""
                    onClicked: {
                        const phone = phoneInput.text;
                        phoneInput.text = "";
                        panel.adapter.submitPhone(phone);
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 12
                visible: !panel.editApplicationKeys && panel.step === "CODE_REQUIRED"
                Text { text: "VERIFICATION CODE"; color: Colors.cyan }
                Rectangle {
                    width: Math.min(parent.width, 350); height: 40
                    color: Colors.dark; border.color: Colors.orange
                    TextInput {
                        id: codeInput
                        anchors.fill: parent; anchors.margins: 9
                        color: Colors.white
                        font.pixelSize: 16
                        inputMethodHints: Qt.ImhDigitsOnly
                    }
                }
                ActionButton {
                    title: "VERIFY CODE"
                    enabled: codeInput.text.trim() !== ""
                    onClicked: {
                        const code = codeInput.text;
                        codeInput.text = "";
                        panel.adapter.submitCode(code);
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 12
                visible: !panel.editApplicationKeys && panel.step === "PASSWORD_REQUIRED"
                Text {
                    text: "TWO-STEP VERIFICATION PASSWORD"
                    color: Colors.cyan
                    width: parent.width; wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: Math.min(parent.width, 350); height: 40
                    color: Colors.dark; border.color: Colors.orange
                    TextInput {
                        id: passwordInput
                        anchors.fill: parent; anchors.margins: 9
                        color: Colors.white
                        font.pixelSize: 15
                        echoMode: TextInput.Password
                    }
                }
                ActionButton {
                    title: "VERIFY PASSWORD"
                    enabled: passwordInput.text !== ""
                    onClicked: {
                        const password = passwordInput.text;
                        passwordInput.text = "";
                        panel.adapter.submitPassword(password);
                    }
                }
            }

            ActionButton {
                title: panel.busy ? "RESTART QR PAIRING" : "CONNECT WITH QR"
                visible: !panel.editApplicationKeys
                         && panel.step !== "APP_REQUIRED" && panel.step !== "PASSWORD_REQUIRED"
                         && panel.step !== "CODE_REQUIRED"
                onClicked: panel.adapter.startLogin("qr")
            }
            ActionButton {
                title: "USE PHONE NUMBER"
                visible: !panel.editApplicationKeys && panel.step !== "APP_REQUIRED"
                         && panel.step !== "PASSWORD_REQUIRED"
                         && panel.step !== "CODE_REQUIRED"
                onClicked: panel.adapter.startLogin("phone")
            }
            ActionButton {
                title: "CANCEL CONNECTION"
                visible: panel.busy
                onClicked: panel.adapter.cancelLogin()
            }
        }
    }
}
