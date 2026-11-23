import QtQuick
import "../components"
import "ForestChatSessionPolicy.js" as SessionPolicy

// Forest's chat rail borrows Social's contact-list presentation recipe:
// a fixed heading, vertical ListView, row previews and the shared star scroll.
// Social ContactList is provider/contact-specific; Forest owns no contacts.
// Read-only until a trusted Forest session source supplies real sessions.
Rectangle {
    id: chatListRoot

    property var sessions: []
    property bool hostConnected: false
    // These read-only signals come from B0; they do not establish a chat host.
    property string treeKey: ""
    property string inventoryStatus: "NOT_CHECKED"
    property int discoveredModels: 0
    property string selectedModel: ""
    // The host must already authorize owner and Tree scope. This is only
    // a defensive presentation filter; it never authorizes SQLite access.
    readonly property var visibleSessions: hostConnected
        ? SessionPolicy.openSessions(sessions, treeKey) : []

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
            text: "CHATS // " + String(chatListRoot.visibleSessions.length).padStart(2, "0")
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
            text: chatListRoot.hostConnected ? "OPEN SESSIONS" : "CHAT HOST OFFLINE"
            elide: Text.ElideRight
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Colors.green
        }
    }

    // Show a REAL B0 model signal even while protected B1 session reads
    // remain unavailable. This status never means that a Tree is running.
    Rectangle {
        id: modelStatusStrip
        anchors.top: chatListHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        color: Colors.black
        GohuText {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 10
            anchors.rightMargin: 9
            anchors.topMargin: 8
            font.pixelSize: 9
            color: chatListRoot.inventoryStatus === "REACHABLE"
                   ? Colors.green : Colors.orange
            text: chatListRoot.inventoryStatus === "REACHABLE"
                ? "OLLAMA // " + chatListRoot.discoveredModels + " FOUND"
                : chatListRoot.inventoryStatus === "CHECKING"
                    ? "OLLAMA // SCANNING"
                    : chatListRoot.inventoryStatus === "NOT_CHECKED"
                        ? "OLLAMA // NOT SCANNED" : "OLLAMA // OFFLINE"
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
        GohuText {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 10
            anchors.rightMargin: 9
            anchors.bottomMargin: 8
            font.pixelSize: 9
            color: Colors.cyan
            text: chatListRoot.selectedModel
                ? "MODEL // " + chatListRoot.selectedModel
                : "MODEL // NOT SELECTED"
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }
    }

    ListView {
        id: activeChatList
        anchors.top: modelStatusStrip.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        anchors.rightMargin: 19
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        clip: true
        spacing: 7
        model: chatListRoot.hostConnected ? chatListRoot.visibleSessions : []
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
                text: "OPEN // REV " + String(modelData.revision)
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
        visible: !chatListRoot.hostConnected || chatListRoot.visibleSessions.length === 0
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Colors.green
    }
}
