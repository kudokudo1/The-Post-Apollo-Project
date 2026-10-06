import QtQuick
import Quickshell
import QtQuick.Effects
import qs.components

Rectangle {
    id: root

    required property var registryService
    required property var intercomService

    property string workingDirectory: ""
    property string floorLabel: "NO FLOOR"
    property string roomLabel: "NO ROOM"
    property int channelIndex: 0
    property int selectedSpecialistIndex: 0
    property var channelModes: ["ROOM", "FLOOR", "SPECIALIST", "HOSPITAL"]

    signal typingChanged(bool active)

    readonly property string channelType:
        String(channelModes[Math.max(0, Math.min(channelModes.length - 1, channelIndex))] || "HOSPITAL")
    readonly property var selectedSpecialist:
        registryService.specialistAt(selectedSpecialistIndex)
    readonly property string selectedSpecialistId:
        selectedSpecialist ? String(selectedSpecialist.id || "") : ""
    readonly property string channelLabel: {
        if (channelType === "ROOM")
            return String(roomLabel || "NO ROOM");

        if (channelType === "FLOOR")
            return String(floorLabel || "NO FLOOR");

        if (channelType === "SPECIALIST")
            return selectedSpecialist
                ? String(selectedSpecialist.name || selectedSpecialist.id || "SPECIALIST")
                : "NO SPECIALIST";

        return "HOSPITAL WIDE";
    }
    readonly property var currentMessages:
        intercomService.messagesFor(
            channelType,
            channelLabel,
            selectedSpecialistId
        )

    function sendCurrent() {
        const specialist = selectedSpecialist;
        const body = String(messageInput.text || "").trim();

        if (!specialist || !body)
            return false;

        if (!intercomService.sendMessage(
                specialist,
                channelType,
                channelLabel,
                body,
                workingDirectory))
            return false;

        messageInput.text = "";
        Qt.callLater(function() {
            transcript.contentY = Math.max(
                0,
                transcript.contentHeight - transcript.height
            );
        });
        return true;
    }

    onVisibleChanged: {
        if (!visible) {
            messageInput.focus = false;
            typingChanged(false);
            return;
        }

        if (selectedSpecialistIndex >= registryService.specialistCount)
            selectedSpecialistIndex = 0;
    }

    width: 430
    height: 390
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta

    RectangularShadow {
        anchors.fill: parent
        spread: 5
        z: -1
        opacity: 0.42
        color: Colors.magenta
    }

    GohuText {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            leftMargin: 11
            rightMargin: 11
            topMargin: 9
        }

        height: 22
        text: "INTERCOM // " + root.channelType
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    Row {
        id: channelRow

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            leftMargin: 8
            rightMargin: 8
            topMargin: 36
        }

        height: 32
        spacing: 5

        Repeater {
            model: root.channelModes

            Rectangle {
                required property string modelData
                required property int index

                width: (channelRow.width - 15) / 4
                height: 30
                color:
                    index === root.channelIndex
                    ? Colors.yellow
                    : channelMouse.pressed
                    ? Colors.black
                    : Colors.dark
                border.width:
                    index === root.channelIndex
                    || channelMouse.containsMouse
                    ? 2 : 1
                border.color:
                    index === root.channelIndex
                    ? Colors.magenta
                    : channelMouse.containsMouse
                    ? Colors.orange
                    : Colors.cyan

                GohuText {
                    anchors.centerIn: parent
                    text: parent.modelData
                    font.pixelSize: 9
                    color:
                        parent.index === root.channelIndex
                        ? Colors.magenta
                        : channelMouse.containsMouse
                        ? Colors.orange
                        : Colors.cyan
                }

                MouseArea {
                    id: channelMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: root.channelIndex = parent.index
                }
            }
        }
    }

    Column {
        id: recipientColumn

        anchors {
            left: parent.left
            right: parent.right
            top: channelRow.bottom
            leftMargin: 8
            rightMargin: 8
            topMargin: 8
        }

        spacing: 5

        GohuText {
            width: parent.width
            text:
                "CHANNEL // "
                + root.channelLabel
                + "    TO // "
                + (
                    root.selectedSpecialist
                    ? String(
                        root.selectedSpecialist.name
                        || root.selectedSpecialist.id
                        || "SPECIALIST"
                    )
                    : "NO SPECIALIST"
                  )
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
        }

        Row {
            id: recipientRow

            width: parent.width
            height: 30
            spacing: 5

            Repeater {
                model: root.registryService.specialists

                Rectangle {
                    required property var modelData
                    required property int index

                    readonly property string presence:
                        String(modelData.presence || "UNKNOWN").toUpperCase()
                    readonly property color stateColor:
                        presence === "READY"
                        ? Colors.green
                        : presence === "OFFLINE"
                        ? Colors.red
                        : Colors.orange

                    width:
                        Math.max(
                            86,
                            (
                                recipientRow.width
                                - Math.max(
                                    0,
                                    root.registryService.specialistCount - 1
                                  ) * recipientRow.spacing
                            )
                            / Math.max(
                                1,
                                root.registryService.specialistCount
                              )
                        )
                    height: 30
                    color:
                        index === root.selectedSpecialistIndex
                        ? Colors.yellow
                        : recipientMouse.pressed
                        ? Colors.black
                        : Colors.dark
                    border.width:
                        index === root.selectedSpecialistIndex
                        || recipientMouse.containsMouse
                        ? 2 : 1
                    border.color:
                        index === root.selectedSpecialistIndex
                        ? Colors.magenta
                        : recipientMouse.containsMouse
                        ? Colors.orange
                        : stateColor
                    opacity:
                        String(modelData.presence || "") === "READY"
                        ? 1.0 : 0.58

                    GohuText {
                        anchors.centerIn: parent
                        text:
                            String(parent.modelData.name || parent.modelData.id || "STAFF")
                            + " // "
                            + parent.presence
                        font.pixelSize: 9
                        color:
                            parent.index === root.selectedSpecialistIndex
                            ? Colors.magenta
                            : parent.stateColor
                    }

                    MouseArea {
                        id: recipientMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked:
                            root.selectedSpecialistIndex = parent.index
                    }
                }
            }
        }
    }

    Rectangle {
        id: transcriptFrame

        anchors {
            left: parent.left
            right: parent.right
            top: recipientColumn.bottom
            leftMargin: 8
            rightMargin: 8
            topMargin: 8
        }

        height: 160
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        clip: true

        Flickable {
            id: transcript

            anchors.fill: parent
            anchors.margins: 7
            contentWidth: width
            contentHeight: transcriptColumn.height
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            Column {
                id: transcriptColumn

                width: transcript.width
                spacing: 7

                Repeater {
                    model: root.currentMessages

                    Column {
                        required property var modelData

                        width: transcriptColumn.width
                        spacing: 2

                        GohuText {
                            width: parent.width
                            text:
                                String(parent.modelData.sender || "OPERATOR")
                                + " // "
                                + String(parent.modelData.launchedAt || "")
                                + " // "
                                + String(parent.modelData.specialistName || "")
                            font.pixelSize: 9
                            color: Colors.green
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text: String(parent.modelData.body || "")
                            font.pixelSize: 10
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }
                    }
                }

                GohuText {
                    width: parent.width
                    visible: root.currentMessages.length === 0
                    text: "NO TRAFFIC ON THIS CHANNEL"
                    font.pixelSize: 10
                    color: Colors.cyan
                    opacity: 0.62
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Rectangle {
        id: composerFrame

        anchors {
            left: parent.left
            right: sendButton.left
            top: transcriptFrame.bottom
            leftMargin: 8
            rightMargin: 6
            topMargin: 8
        }

        height: 42
        color: Colors.dark
        border.width: messageInput.activeFocus ? 2 : 1
        border.color:
            messageInput.activeFocus
            ? Colors.orange
            : Colors.cyan

        TextInput {
            id: messageInput

            anchors {
                fill: parent
                leftMargin: 9
                rightMargin: 9
            }

            verticalAlignment: TextInput.AlignVCenter
            clip: true
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.pixelSize: 11

            onActiveFocusChanged:
                root.typingChanged(activeFocus)

            Keys.onReturnPressed: function(event) {
                root.sendCurrent();
                event.accepted = true;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 9
            }

            visible: messageInput.text.length === 0
            text: "MESSAGE SPECIALIST..."
            font.pixelSize: 10
            color: Colors.white
            opacity: 0.38
        }
    }

    Rectangle {
        id: sendButton

        anchors {
            right: parent.right
            top: transcriptFrame.bottom
            rightMargin: 8
            topMargin: 8
        }

        width: 82
        height: 42
        color:
            sendMouse.pressed
            ? Colors.black
            : Colors.dark
        border.width:
            sendMouse.containsMouse ? 2 : 1
        border.color:
            sendMouse.containsMouse
            ? Colors.orange
            : Colors.green
        opacity:
            root.selectedSpecialist
            && String(root.selectedSpecialist.presence || "") === "READY"
            && messageInput.text.trim().length > 0
            ? 1.0 : 0.48

        GohuText {
            anchors.centerIn: parent
            text: "SEND"
            font.pixelSize: 11
            color:
                sendMouse.containsMouse
                ? Colors.orange
                : Colors.green
        }

        MouseArea {
            id: sendMouse

            anchors.fill: parent
            enabled:
                root.selectedSpecialist
                && String(root.selectedSpecialist.presence || "") === "READY"
                && messageInput.text.trim().length > 0
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: root.sendCurrent()
        }
    }

    GohuText {
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            leftMargin: 10
            rightMargin: 10
            bottomMargin: 8
        }

        height: 20
        text:
            root.intercomService.lastError
            || root.intercomService.lastStatus
            || "READY // SEEDED INTERACTIVE SESSION"
        font.pixelSize: 9
        color:
            root.intercomService.lastError
            ? Colors.red
            : root.intercomService.lastStatus
            ? Colors.green
            : Colors.cyan
        elide: Text.ElideRight
    }
}
