import QtQuick
import Quickshell
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: chatFeed

    property var conversation: null
    property var messages: []
    property bool loading: false
    property string error: ""

    property bool sending: false
    property string sendError: ""
    property int sendSuccessSerial: 0

    signal sendRequested(string conversationId, string text)

    signal composerEscapeRequested

    property int pendingSendSerial: -1

    // Host-level presentation knobs keep this surface transport-agnostic.
    // Sessions keeps the plain-text defaults; Hospital can opt into
    // Markdown/richer rendering without forking the conversation shell.
    property int messageTextFormat: Text.PlainText
    property string emptyConversationLabel: "SELECT A CONTACT"
    property string composerPlaceholder: "MESSAGE..."
    property string sendLabel: "SEND"
    property string sendingLabel: "SENDING"

    // Discord mode keeps this panel's shell underneath Vesktop:
    // the 0.85 background and cyan OUTER frame remain, while all inner
    // chat/header/composer contents disappear.
    property bool discordMode: false

    // Root must stay transparent or it blocks the translucent background.
    color: "transparent"
    radius: 0

    // =========================================================
    // BASE CHAT BACKGROUND
    // =========================================================

    Rectangle {
        id: chatBackground

        anchors.fill: parent

        color: Colors.black

        // Only this layer is transparent.
        opacity: 0.85

        radius: 0
        z: 0
    }

    // =========================================================
    // HEADER
    // =========================================================

    Rectangle {
        id: header

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }

        height: 60

        visible: !chatFeed.discordMode

        color: Colors.dark
        radius: 0

        z: 4

        // =====================================================
        // CONTACT INFO
        // =====================================================

        Row {
            id: headerContact

            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 18
            }

            spacing: 12

            // =================================================
            // DEFAULT CONTACT ICON
            // =================================================

            Rectangle {
                id: contactIcon

                width: 34
                height: 34

                visible: !chatFeed.discordMode && chatFeed.conversation !== null

                color: Colors.black

                radius: 0

                border.width: 1
                border.color: Colors.cyan

                layer.enabled: Window.window !== null && (visible)

                layer.effect: DropShadow {
                    color: Colors.cyan

                    opacity: 0.55

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 12
                    samples: 15

                    transparentBorder: true
                }

                Text {
                    anchors.centerIn: parent

                    text: "ጸ"

                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 21

                    color: Colors.cyan
                }
            }

            // =================================================
            // CONTACT NAME
            // =================================================

            Text {
                id: headerText

                anchors.verticalCenter: parent.verticalCenter

                text: chatFeed.conversation ? (chatFeed.conversation.displayNameInProfile || chatFeed.conversation.nickname || chatFeed.conversation.id) : "SELECT A CONTACT"

                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 18

                color: Colors.cyan

                layer.enabled: Window.window !== null

                layer.effect: DropShadow {
                    color: Colors.cyan

                    opacity: 0.65

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 14
                    samples: 15

                    transparentBorder: true
                }
            }
        }

        // =====================================================
        // HEADER SEPARATOR
        // =====================================================

        Rectangle {
            id: headerLine

            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }

            height: 2

            color: Colors.cyan
            radius: 0
        }

        SafeDropShadow {
            anchors.fill: headerLine
            safeSource: headerLine
            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            color: Colors.cyan
            opacity: 0.6

            transparentBorder: true
        }
    }

    // =========================================================
    // MESSAGE VIEWPORT
    // =========================================================

    Rectangle {
        id: messageViewport

        anchors {
            top: header.bottom
            left: parent.left
            right: parent.right
            bottom: composer.visible ? composer.top : parent.bottom
        }

        visible: !chatFeed.discordMode

        // Important: do NOT make this Colors.black,
        // otherwise it hides the transparency behind it.
        color: "transparent"

        radius: 0
        z: 1
    }

    // =========================================================
    // MESSAGE FEED
    // =========================================================

    ListView {
        id: messageList

        anchors {
            fill: messageViewport

            topMargin: 18
            leftMargin: 16
            rightMargin: 16

            bottomMargin: chatFeed.sendError !== "" ? 30 : 16
        }

        z: 2

        visible: !chatFeed.discordMode && chatFeed.conversation && chatFeed.messages.length > 0 && chatFeed.error === ""

        spacing: 10
        clip: true

        model: chatFeed.messages

        onCountChanged: {
            if (count > 0) {
                positionViewAtEnd();
            }
        }

        delegate: Item {
            id: messageDelegate

            required property var modelData

            width: messageList.width

            property bool outgoing: modelData.direction === "outgoing"

            property real maxBubbleWidth: messageList.width * 0.72

            property real desiredWidth: Math.min(maxBubbleWidth, Math.max(120, messageMeasure.implicitWidth + 24))

            height: messageBubble.height + 4

            Text {
                id: messageMeasure

                visible: false

                text: modelData.body || ""

                textFormat: chatFeed.messageTextFormat

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 14
            }

            Rectangle {
                id: messageBubble

                width: messageDelegate.desiredWidth

                height: messageText.implicitHeight + 24

                anchors.right: messageDelegate.outgoing ? parent.right : undefined

                anchors.left: messageDelegate.outgoing ? undefined : parent.left

                color: Colors.dark
                radius: 0

                border.width: 1

                border.color: messageDelegate.outgoing ? Colors.orange : Colors.cyan

                RectangularShadow {
                    anchors.fill: parent

                    spread: 2

                    color: messageDelegate.outgoing ? Colors.orange : Colors.cyan

                    opacity: 0.18

                    z: -1
                }

                RectangularShadow {
                    anchors.fill: parent

                    spread: 7

                    color: messageDelegate.outgoing ? Colors.orange : Colors.cyan

                    opacity: 0.04

                    z: -2
                }

                Text {
                    id: messageText

                    x: 12
                    y: 12

                    width: messageBubble.width - 24

                    text: modelData.body || ""

                    wrapMode: Text.Wrap
                    textFormat: chatFeed.messageTextFormat

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 14

                    color: messageDelegate.outgoing ? Colors.orange : Colors.cyan
                }
            }
        }
    }

    // =========================================================
    // EMPTY STATE
    // =========================================================

    Text {
        id: emptyText

        anchors.centerIn: messageViewport

        visible: !chatFeed.discordMode && !chatFeed.conversation && !chatFeed.loading

        z: 3

        text: chatFeed.emptyConversationLabel

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 18

        color: Colors.cyan
    }

    SafeDropShadow {
        anchors.fill: emptyText

        safeSource: emptyText
        horizontalOffset: 0
        verticalOffset: 0

        radius: 14
        samples: 15

        color: Colors.cyan

        opacity: emptyText.visible ? 0.60 : 0.0

        transparentBorder: true
    }

    // =========================================================
    // LOADING STATE
    // =========================================================

    Text {
        id: loadingText

        anchors.centerIn: messageViewport

        visible: !chatFeed.discordMode && chatFeed.conversation && chatFeed.loading && chatFeed.messages.length === 0

        z: 3

        text: "LOADING..."

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 16

        color: Colors.orange
    }

    SafeDropShadow {
        anchors.fill: loadingText

        safeSource: loadingText
        horizontalOffset: 0
        verticalOffset: 0

        radius: 14
        samples: 15

        color: Colors.orange

        opacity: loadingText.visible ? 0.70 : 0.0

        transparentBorder: true
    }

    // =========================================================
    // ERROR STATE
    // =========================================================

    Text {
        id: errorText

        anchors.centerIn: messageViewport

        visible: !chatFeed.discordMode && chatFeed.error !== ""

        z: 3

        width: messageViewport.width - 80
        height: Math.min(implicitHeight, 96)

        text: chatFeed.error

        wrapMode: Text.Wrap
        maximumLineCount: 5
        elide: Text.ElideRight
        clip: true

        horizontalAlignment: Text.AlignHCenter

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 14

        color: Colors.red
    }

    SafeDropShadow {
        anchors.fill: errorText

        safeSource: errorText
        horizontalOffset: 0
        verticalOffset: 0

        radius: 14
        samples: 15

        color: Colors.red

        opacity: errorText.visible ? 0.75 : 0.0

        transparentBorder: true
    }

    // =========================================================
    // COMPOSER
    // =========================================================

    Rectangle {
        id: composer

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom

            leftMargin: 16
            rightMargin: 16
            bottomMargin: 16
        }

        height: 54

        visible: !chatFeed.discordMode && chatFeed.conversation !== null

        color: Colors.dark
        radius: 0

        border.width: 1

        border.color: messageInput.activeFocus ? Colors.orange : Colors.cyan

        z: 4

        RectangularShadow {
            anchors.fill: parent

            spread: 3

            color: messageInput.activeFocus ? Colors.orange : Colors.cyan

            opacity: messageInput.activeFocus ? 0.50 : 0.25

            z: -1
        }

        RectangularShadow {
            anchors.fill: parent

            spread: 10

            color: messageInput.activeFocus ? Colors.orange : Colors.cyan

            opacity: messageInput.activeFocus ? 0.09 : 0.05

            z: -2
        }

        TextInput {
            id: messageInput

            anchors {
                left: parent.left
                right: sendButton.left
                verticalCenter: parent.verticalCenter

                leftMargin: 14
                rightMargin: 12
            }

            height: 30

            verticalAlignment: TextInput.AlignVCenter

            clip: true

            enabled: !chatFeed.sending

            color: enabled ? Colors.white : Colors.cyan

            selectionColor: Colors.orange

            selectedTextColor: Colors.black

            font.family: "GohuFont 11 Nerd Font Mono"

            font.pixelSize: 14

            Keys.onReturnPressed: function (event) {
                chatFeed.trySend();
                event.accepted = true;
            }

            Keys.onEnterPressed: function (event) {
                chatFeed.trySend();
                event.accepted = true;
            }

            Keys.onEscapePressed: function (event) {
                chatFeed.composerEscapeRequested();

                event.accepted = true;
            }
        }

        Text {
            anchors {
                left: messageInput.left
                verticalCenter: messageInput.verticalCenter
            }

            visible: messageInput.text.length === 0 && !messageInput.activeFocus

            text: chatFeed.composerPlaceholder

            font.family: "GohuFont 11 Nerd Font Mono"

            font.pixelSize: 14

            color: Colors.cyan

            opacity: 0.55
        }

        Rectangle {
            id: sendButton

            anchors {
                right: parent.right
                top: parent.top
                bottom: parent.bottom
            }

            width: 92

            radius: 0

            property bool canSend: !chatFeed.sending && messageInput.text.trim() !== ""

            property bool isHovered: sendMouse.containsMouse && canSend

            property bool isPressed: sendMouse.pressed && canSend

            color: isPressed ? Colors.magenta : isHovered ? Colors.yellow : Colors.dark

            Rectangle {
                anchors {
                    left: parent.left
                    top: parent.top
                    bottom: parent.bottom
                }

                width: 1

                color: sendButton.isPressed ? Colors.magenta : sendButton.isHovered ? Colors.orange : sendButton.canSend ? Colors.orange : Colors.cyan
            }

            Text {
                id: sendText

                anchors.centerIn: parent

                text: chatFeed.sending ? chatFeed.sendingLabel : chatFeed.sendLabel

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 14

                color: sendButton.isPressed ? Colors.black : sendButton.isHovered ? Colors.orange : sendButton.canSend ? Colors.orange : Colors.cyan
            }

            SafeDropShadow {
                anchors.fill: sendText

                safeSource: sendText
                horizontalOffset: 0
                verticalOffset: 0

                radius: 14
                samples: 15

                color: sendButton.isPressed ? Colors.magenta : sendButton.isHovered ? Colors.orange : sendButton.canSend ? Colors.orange : Colors.cyan

                opacity: sendButton.isPressed ? 1.0 : sendButton.isHovered ? 0.8 : sendButton.canSend ? 0.6 : 0.25

                transparentBorder: true
            }

            RectangularShadow {
                anchors.fill: parent

                spread: 3

                color: sendButton.isPressed ? Colors.magenta : sendButton.isHovered ? Colors.orange : sendButton.canSend ? Colors.orange : Colors.cyan

                opacity: sendButton.isPressed ? 0.60 : sendButton.isHovered ? 0.50 : sendButton.canSend ? 0.30 : 0.12

                z: -1
            }

            RectangularShadow {
                anchors.fill: parent

                spread: 10

                color: sendButton.isPressed ? Colors.magenta : sendButton.isHovered ? Colors.orange : sendButton.canSend ? Colors.orange : Colors.cyan

                opacity: sendButton.isPressed ? 0.12 : sendButton.isHovered ? 0.09 : sendButton.canSend ? 0.06 : 0.03

                z: -2
            }

            MouseArea {
                id: sendMouse

                anchors.fill: parent

                hoverEnabled: true

                enabled: sendButton.canSend

                onClicked: {
                    chatFeed.trySend();
                }
            }
        }
    }

    // =========================================================
    // SEND ERROR
    // =========================================================

    Text {
        id: sendErrorText

        anchors {
            left: parent.left
            right: parent.right
            bottom: composer.top

            leftMargin: 20
            rightMargin: 20
            bottomMargin: 6
        }

        visible: !chatFeed.discordMode && chatFeed.sendError !== ""

        z: 5

        text: chatFeed.sendError

        wrapMode: Text.Wrap
        maximumLineCount: 3
        elide: Text.ElideRight
        clip: true

        horizontalAlignment: Text.AlignHCenter

        font.family: "GohuFont 11 Nerd Font Mono"

        font.pixelSize: 12

        color: Colors.red
    }

    SafeDropShadow {
        anchors.fill: sendErrorText

        safeSource: sendErrorText
        horizontalOffset: 0
        verticalOffset: 0

        radius: 14
        samples: 15

        color: Colors.red

        opacity: sendErrorText.visible ? 0.75 : 0.0

        transparentBorder: true
    }

    // =========================================================
    // FULL CHAT BORDER
    // =========================================================

    Rectangle {
        id: chatFrame

        anchors.fill: parent

        color: "transparent"

        radius: 0

        border.width: 1
        border.color: Colors.cyan

        // Keep the outer cyan frame in Discord mode. Only the inner
        // contents disappear.
        visible: true

        z: 20
    }

    // =========================================================
    // SEND LOGIC
    // =========================================================

    function trySend() {
        if (!conversation)
            return;

        if (sending)
            return;

        const text = messageInput.text.trim();

        if (text === "")
            return;

        pendingSendSerial = sendSuccessSerial;

        sendRequested(conversation.id, text);
    }

    onSendSuccessSerialChanged: {
        if (pendingSendSerial >= 0 && sendSuccessSerial > pendingSendSerial) {
            messageInput.clear();

            pendingSendSerial = -1;

            messageInput.forceActiveFocus();

            Qt.callLater(function () {
                if (messageList.count > 0) {
                    messageList.positionViewAtEnd();
                }
            });
        }
    }

    function focusMessageInput() {
        if (!conversation)
            return;

        Qt.callLater(function () {
            messageInput.forceActiveFocus();
        });
    }
}
