import QtQuick
import "../../components"

// Same-pane Telegram connection wizard. The QR URL, login code, and passwords
// stay in local process memory; no browser window, terminal or logs are used.
Rectangle {
    id: panel
    property var adapter: null
    readonly property string step: adapter ? String(adapter.loginState || "IDLE") : "IDLE"
    readonly property bool busy: adapter ? adapter.loginInProgress : false

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
                text: "TELEGRAM // CONNECT ACCOUNT"
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
                visible: panel.step === "APP_REQUIRED"
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "One-time Telegram application setup. Register the app keys with Telegram, then enter them here. Do not paste account codes into these fields."
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
                    enabled: apiIdInput.text.trim() !== "" && apiHashInput.text.trim() !== ""
                    onClicked: {
                        const idValue = apiIdInput.text;
                        const hashValue = apiHashInput.text;
                        apiIdInput.text = "";
                        apiHashInput.text = "";
                        panel.adapter.saveApplicationKeys(idValue, hashValue);
                    }
                }
                Text {
                    text: "Creating Telegram app credentials may require visiting my.telegram.org once. Login and daily messaging remain inside Social."
                    color: Colors.white
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }
            }

            Column {
                width: parent.width
                spacing: 12
                visible: panel.step === "QR_READY"
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
                    Image {
                        anchors.fill: parent
                        anchors.margins: 10
                        source: panel.adapter ? panel.adapter.qrSource : ""
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        asynchronous: false
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
                visible: panel.step === "PHONE_REQUIRED"
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
                visible: panel.step === "CODE_REQUIRED"
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
                visible: panel.step === "PASSWORD_REQUIRED"
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
                visible: panel.step !== "APP_REQUIRED" && panel.step !== "PASSWORD_REQUIRED"
                         && panel.step !== "CODE_REQUIRED"
                onClicked: panel.adapter.startLogin("qr")
            }
            ActionButton {
                title: "USE PHONE NUMBER"
                visible: panel.step !== "APP_REQUIRED"
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
