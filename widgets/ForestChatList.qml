import QtQuick
import "../components"

// Forest's chat rail borrows Social's contact-list presentation recipe:
// a fixed heading, vertical ListView, row previews and the shared star scroll.
// Social ContactList is provider/contact-specific; Forest owns no contacts.
// Read-only until a trusted Forest session source supplies real sessions.
Rectangle {
    id: chatListRoot

    property var sessions: []
    property bool hostConnected: false

    color: Colors.black
    border.width: 0
    clip: true

    Rectangle {
        id: chatListHeader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 55
        color: Colors.dark

        GohuText {
            anchors.left: parent.left
            anchors.leftMargin: 11
            anchors.right: parent.right
            anchors.rightMargin: 9
            anchors.top: parent.top
            anchors.topMargin: 9
            font.pixelSize: 12
            color: Colors.cyan
            text: "CHATS // " + String(chatListRoot.sessions.length).padStart(2, "0")
            elide: Text.ElideRight
        }
        GohuText {
            anchors.left: parent.left
            anchors.leftMargin: 11
            anchors.right: parent.right
            anchors.rightMargin: 9
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            font.pixelSize: 9
            color: chatListRoot.hostConnected ? Colors.green : Colors.orange
            text: chatListRoot.hostConnected ? "ACTIVE SESSIONS" : "CHAT HOST OFFLINE"
            elide: Text.ElideRight
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Colors.cyan
        }
    }

    ListView {
        id: activeChatList
        anchors.top: chatListHeader.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        anchors.rightMargin: 19
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        clip: true
        spacing: 7
        model: chatListRoot.hostConnected ? chatListRoot.sessions : []
        // No fake selection or cross-host session activation. A future
        // authorized Forest session adapter owns selection and switching.
        delegate: Rectangle {
            required property var modelData
            width: activeChatList.width
            height: 65
            radius: 0
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            GohuText {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 9
                text: String(modelData.title || "")
                textFormat: Text.PlainText
                font.pixelSize: 12
                color: Colors.orange
                elide: Text.ElideRight
            }
            GohuText {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 9
                text: String(modelData.lastMessage || "")
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    NeonScrollBar {
        flickable: activeChatList
        handleStyle: "star"
        accountForContentOrigin: true
        visible: chatListRoot.hostConnected
                 && activeChatList.contentHeight > activeChatList.height
    }

    GohuText {
        anchors.centerIn: activeChatList
        width: Math.max(1, activeChatList.width - 8)
        text: chatListRoot.hostConnected
            ? "NO ACTIVE CHATS"
            : "NO ACTIVE CHATS\nTRUSTED CHAT HOST NOT CONNECTED"
        color: Colors.orange
        font.pixelSize: 10
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
        visible: !chatListRoot.hostConnected || chatListRoot.sessions.length === 0
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Colors.cyan
    }
}
