import QtQuick
import Quickshell
import "../../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: contactRoot

    // ============================================================
    // DATA
    // ============================================================

    property var conversations: []
    property var selectedConversation: null

    // ============================================================
    // CONTROL STATE
    // ============================================================

    property int selectedIndex: -1
    property bool keyboardActive: false
    property bool keyboardFocused: false

    // Discord mode keeps the panel shell visible underneath Vesktop.
    // Only the inner header/list contents disappear; the 0.85 background
    // and cyan OUTER border remain.
    property bool discordMode: false

    signal contactClicked

    // ============================================================
    // PANEL
    // ============================================================

    color: Qt.rgba(Colors.black.r, Colors.black.g, Colors.black.b, 0.85)

    radius: 0

    border.width: 1
    border.color: Colors.cyan

    clip: true

    // ============================================================
    // HELPERS
    // ============================================================

    function clearSelection() {
        selectedIndex = -1;
        selectedConversation = null;
    }

    function ensureValidIndex() {
        if (conversations.length === 0) {
            selectedIndex = -1;
            selectedConversation = null;
            return;
        }

        if (selectedIndex < 0 || selectedIndex >= conversations.length) {
            selectedIndex = 0;
            selectedConversation = conversations[0];
        }

        conversationList.currentIndex = selectedIndex;
    }

    function selectIndex(index) {
        if (conversations.length === 0)
            return false;

        if (index < 0 || index >= conversations.length)
            return false;

        selectedIndex = index;

        conversationList.currentIndex = index;

        selectedConversation = conversations[index];

        conversationList.positionViewAtIndex(index, ListView.Contain);

        return true;
    }

    function moveSelection(direction) {
        if (conversations.length === 0) {
            clearSelection();
            return;
        }

        var nextIndex = selectedIndex;

        if (nextIndex < 0)
            nextIndex = 0;
        else
            nextIndex += direction;

        if (nextIndex < 0)
            nextIndex = conversations.length - 1;

        if (nextIndex >= conversations.length)
            nextIndex = 0;

        selectIndex(nextIndex);
    }

    function activateCurrent() {
        if (conversations.length === 0)
            return false;

        ensureValidIndex();

        if (selectedIndex < 0)
            return false;

        selectedConversation = conversations[selectedIndex];

        return true;
    }

    // ============================================================
    // CONVERSATIONS CHANGED
    // ============================================================

    onConversationsChanged: {
        if (conversations.length === 0) {
            clearSelection();
            return;
        }

        if (selectedIndex >= conversations.length) {
            selectedIndex = -1;
            selectedConversation = null;
        }
    }

    // ============================================================
    // CONTACTS HEADER
    // ============================================================

    Rectangle {
        id: contactsHeader

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }

        height: 70

        visible: !contactRoot.discordMode

        color: Colors.dark

        radius: 0
        border.width: 1
        border.color: Colors.cyan

        z: 10

        // ========================================================
        // CONTACTS TITLE
        // ========================================================

        Text {
            id: contactsHeaderText

            anchors {
                left: parent.left
                top: parent.top

                leftMargin: 18
                topMargin: 10
            }

            text: "CONTACTS"

            font.family: "GohuFont 11 Nerd Font Mono"

            font.pixelSize: 18

            color: Colors.cyan

            layer.enabled: true

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

        // ========================================================
        // CONVERSATION COUNT
        // ========================================================

        Row {
            anchors {
                left: parent.left
                bottom: parent.bottom

                leftMargin: 18
                bottomMargin: 9
            }

            spacing: 8

            Text {
                text: "CONVERSATION(S):"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 12

                color: Colors.white

                opacity: 0.70
            }

            Text {
                text: contactRoot.conversations.length

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 12

                color: Colors.orange

                layer.enabled: true

                layer.effect: DropShadow {
                    color: Colors.orange

                    opacity: 0.80

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 14
                    samples: 15

                    transparentBorder: true
                }
            }
        }

        // ========================================================
        // HEADER SEPARATOR
        // ========================================================

        Rectangle {
            id: contactsHeaderLine

            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }

            height: 2

            color: Colors.cyan
            radius: 0
        }

        DropShadow {
            anchors.fill: contactsHeaderLine
            source: contactsHeaderLine

            horizontalOffset: 0
            verticalOffset: 0

            radius: 14
            samples: 15

            color: Colors.cyan

            opacity: 0.60

            transparentBorder: true
        }
    }

    // ============================================================
    // CONTACT LIST
    // ============================================================

    ListView {
        id: conversationList

        anchors {
            top: contactsHeader.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom

            topMargin: 10
            bottomMargin: 10
            leftMargin: 8
            rightMargin: 8
        }

        visible: !contactRoot.discordMode

        model: contactRoot.conversations

        spacing: 7

        clip: true

        currentIndex: contactRoot.selectedIndex

        delegate: Rectangle {
            id: contactButton

            required property var modelData
            required property int index

            width: conversationList.width
            height: 66

            radius: 0
            clip: false

            // ====================================================
            // STATE
            // ====================================================

            property bool isSelected: contactRoot.selectedIndex === index

            property bool isHovered: !contactRoot.keyboardActive && contactMouse.containsMouse

            property bool isPressed: contactMouse.pressed

            // ====================================================
            // POWER-STYLE BUTTON COLOR
            // ====================================================

            color: contactButton.isPressed ? Colors.magenta : contactButton.isHovered ? Colors.yellow : contactButton.isSelected ? Colors.yellow : Colors.black

            // ====================================================
            // SELECTED CONTACT BORDER
            // ====================================================

            border.width: contactButton.isSelected || contactButton.isHovered || contactButton.isPressed ? 1 : 0

            border.color: contactButton.isPressed ? Colors.magenta : contactButton.isHovered ? Colors.orange : contactButton.isSelected ? Colors.orange : "transparent"

            // ====================================================
            // CONTACT NAME
            // ====================================================

            Text {
                id: contactName

                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top

                    leftMargin: 12
                    rightMargin: 12
                    topMargin: 10
                }

                text: modelData.displayNameInProfile || modelData.nickname || modelData.id || "UNKNOWN"

                elide: Text.ElideRight

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 15

                color: contactButton.isPressed ? Colors.black : contactButton.isHovered ? Colors.orange : contactButton.isSelected ? Colors.orange : Colors.cyan

                z: 2

                layer.enabled: contactButton.isSelected || contactButton.isHovered

                layer.effect: DropShadow {
                    color: Colors.orange

                    opacity: 1.0

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 30
                    samples: 60

                    transparentBorder: true
                }
            }

            // ====================================================
            // LAST MESSAGE
            // ====================================================

            Text {
                id: contactPreview

                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom

                    leftMargin: 12
                    rightMargin: 12
                    bottomMargin: 9
                }

                text: modelData.lastMessage ? modelData.lastMessage : ""

                elide: Text.ElideRight

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 11

                color: contactButton.isPressed ? Colors.black : contactButton.isHovered ? Colors.orange : contactButton.isSelected ? Colors.orange : Colors.white

                opacity: contactButton.isPressed ? 1.0 : 0.70

                z: 2
            }

            // ====================================================
            // MOUSE
            // ====================================================

            MouseArea {
                id: contactMouse

                anchors.fill: parent

                hoverEnabled: true

                acceptedButtons: Qt.LeftButton | Qt.RightButton

                onEntered: {
                    contactRoot.keyboardActive = false;
                }

                onClicked: function (mouse) {
                    contactRoot.keyboardActive = false;

                    if (mouse.button === Qt.LeftButton) {
                        contactRoot.selectIndex(contactButton.index);

                        contactRoot.contactClicked();
                    }

                    if (mouse.button === Qt.RightButton) {
                        console.log("Contact right-clicked:", contactButton.index);
                    }
                }
            }

            // ====================================================
            // POWER-STYLE BUTTON GLOW
            // ====================================================

            DropShadow {
                source: contactButton

                anchors.fill: contactButton

                horizontalOffset: 0
                verticalOffset: 0

                radius: 12
                samples: 25

                z: -1

                color: contactButton.isPressed ? Colors.magenta : contactButton.isHovered ? Colors.orange : contactButton.isSelected ? Colors.orange : Colors.cyan

                opacity: contactButton.isPressed ? 0.55 : contactButton.isHovered ? 0.55 : contactButton.isSelected ? 0.55 : 0.0

                transparentBorder: true
            }
        }
    }
}
