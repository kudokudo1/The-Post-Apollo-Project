import QtQuick
import QtQuick.Effects
import qs.components

Rectangle {
    id: root

    required property var receptionistService

    property string floorLabel: "NO FLOOR"
    property string roomLabel: "NO ROOM"
    property int readyCount: 0
    property int specialistCount: 0
    property int attentionCount: 0

    signal routeRequested(string route)
    signal typingChanged(bool active)

    color: Colors.black
    border.width: 1
    border.color: Colors.magenta

    Connections {
        target: root.receptionistService

        function onRouteRequested(route) {
            root.routeRequested(route);
        }
    }

    Column {
        anchors {
            fill: parent
            margins: 10
        }

        spacing: 9

        Rectangle {
            id: receptionStage

            width: parent.width
            height: Math.max(210, root.height * 0.34)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.22
                color: Colors.cyan
            }

            GohuText {
                anchors {
                    top: parent.top
                    horizontalCenter: parent.horizontalCenter
                    topMargin: 12
                }

                text: "RECEPTION // FRONT DESK"
                font.pixelSize: 14
                color: Colors.magenta
            }

            Rectangle {
                id: avatarHead

                width: 72
                height: 72
                radius: 36
                anchors {
                    horizontalCenter: parent.horizontalCenter
                    top: parent.top
                    topMargin: 48
                }

                color: Colors.black
                border.width: 2
                border.color: Colors.magenta

                RectangularShadow {
                    anchors.fill: parent
                    spread: 5
                    z: -1
                    opacity: 0.38
                    color: Colors.magenta
                }

                GohuText {
                    anchors.centerIn: parent
                    text: "R"
                    font.pixelSize: 30
                    color: Colors.cyan
                }
            }

            Rectangle {
                width: 150
                height: 68
                radius: 10
                anchors {
                    horizontalCenter: parent.horizontalCenter
                    top: avatarHead.bottom
                    topMargin: 5
                }

                color: Colors.black
                border.width: 2
                border.color: Colors.cyan
            }

            Rectangle {
                id: desk

                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    leftMargin: 28
                    rightMargin: 28
                    bottomMargin: 18
                }

                height: 58
                color: Colors.black
                border.width: 2
                border.color: Colors.orange

                GohuText {
                    anchors {
                        left: parent.left
                        verticalCenter: parent.verticalCenter
                        leftMargin: 14
                    }

                    text:
                        "FLOOR // "
                        + root.floorLabel
                        + "    ROOM // "
                        + root.roomLabel
                    font.pixelSize: 10
                    color: Colors.white
                    elide: Text.ElideRight
                    width: parent.width - deskControls.width - 34
                }

                Row {
                    id: deskControls

                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        rightMargin: 10
                    }

                    spacing: 7

                    Repeater {
                        model: [
                            { label: "☎", route: "phone", color: Colors.green },
                            { label: "🎙︎", route: "intercom", color: Colors.omnitrix },
                            { label: "🗒︎", route: "reports", color: Colors.magenta },
                            { label: "!", route: "rounds", color: Colors.orange }
                        ]

                        Rectangle {
                            required property var modelData

                            width: 42
                            height: 36
                            color:
                                deskControlMouse.pressed
                                ? Colors.black
                                : Colors.dark
                            border.width:
                                deskControlMouse.containsMouse
                                ? 2 : 1
                            border.color:
                                deskControlMouse.containsMouse
                                ? Colors.orange
                                : modelData.color

                            GohuText {
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset: 2
                                width: parent.width
                                height: parent.height
                                visible:
                                    parent.modelData.route === "intercom"
                                text: parent.modelData.label
                                font.pixelSize: 20
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                color:
                                    deskControlMouse.containsMouse
                                    ? Colors.orange
                                    : parent.modelData.color
                            }

                            NotoText {
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset:
                                    parent.modelData.route === "reports"
                                    ? 2 : 0
                                width: parent.width
                                height: parent.height
                                visible:
                                    parent.modelData.route !== "intercom"
                                text: parent.modelData.label
                                font.pixelSize:
                                    parent.modelData.label === "☎"
                                    ? 23
                                    : parent.modelData.route === "reports"
                                    ? 20
                                    : 11
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                color:
                                    deskControlMouse.containsMouse
                                    ? Colors.orange
                                    : parent.modelData.color
                            }

                            MouseArea {
                                id: deskControlMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked:
                                    root.receptionistService.request(
                                        parent.modelData.route,
                                        ""
                                    )
                            }
                        }
                    }
                }
            }
        }

        Row {
            id: routeButtons

            width: parent.width
            height: 38
            spacing: 7

            Repeater {
                model: ["SURGERY", "REPORTS", "ROUNDS", "STAFF"]

                Rectangle {
                    required property string modelData

                    width: (routeButtons.width - 21) / 4
                    height: 38
                    color:
                        routeMouse.pressed
                        ? Colors.black
                        : Colors.dark
                    border.width:
                        routeMouse.containsMouse
                        ? 2 : 1
                    border.color:
                        routeMouse.containsMouse
                        ? Colors.orange
                        : Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: parent.modelData
                        font.pixelSize: 11
                        color:
                            routeMouse.containsMouse
                            ? Colors.orange
                            : Colors.cyan
                    }

                    MouseArea {
                        id: routeMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked:
                            root.receptionistService.request(
                                parent.modelData.toLowerCase(),
                                ""
                            )
                    }
                }
            }
        }

        Rectangle {
            id: statusStrip

            width: parent.width
            height: 38
            color: Colors.dark
            border.width: 1
            border.color: Colors.green

            GohuText {
                anchors {
                    fill: parent
                    margins: 8
                }

                verticalAlignment: Text.AlignVCenter
                text:
                    "STAFF READY "
                    + String(root.readyCount)
                    + "/"
                    + String(root.specialistCount)
                    + "    //    ATTENTION "
                    + String(root.attentionCount)
                    + "    //    AUTHORITY: ROUTE + EXPLAIN + INITIATE"
                font.pixelSize: 10
                color: Colors.green
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: transcriptFrame

            width: parent.width
            height:
                Math.max(
                    90,
                    root.height
                    - receptionStage.height
                    - routeButtons.height
                    - statusStrip.height
                    - composer.height
                    - 45
                )
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Flickable {
                id: transcript

                anchors.fill: parent
                anchors.margins: 8
                contentWidth: width
                contentHeight: transcriptColumn.height
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Column {
                    id: transcriptColumn

                    width: transcript.width
                    spacing: 6

                    Repeater {
                        model: root.receptionistService.transcript

                        Column {
                            required property var modelData

                            width: transcriptColumn.width
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text: String(parent.modelData.sender || "")
                                font.pixelSize: 9
                                color:
                                    String(parent.modelData.sender || "") === "RECEPTION"
                                    ? Colors.magenta
                                    : Colors.green
                            }

                            GohuText {
                                width: parent.width
                                text: String(parent.modelData.body || "")
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }

        Row {
            id: composer

            width: parent.width
            height: 42
            spacing: 7

            Rectangle {
                width: composer.width - sendButton.width - composer.spacing
                height: composer.height
                color: Colors.dark
                border.width: receptionInput.activeFocus ? 2 : 1
                border.color:
                    receptionInput.activeFocus
                    ? Colors.orange
                    : Colors.cyan

                TextInput {
                    id: receptionInput

                    anchors {
                        fill: parent
                        leftMargin: 10
                        rightMargin: 10
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
                        const message = String(text || "").trim();

                        if (root.receptionistService.submit(message))
                            text = "";

                        Qt.callLater(function() {
                            transcript.contentY = Math.max(
                                0,
                                transcript.contentHeight - transcript.height
                            );
                        });

                        event.accepted = true;
                    }
                }

                GohuText {
                    anchors {
                        left: parent.left
                        verticalCenter: parent.verticalCenter
                        leftMargin: 10
                    }

                    visible: receptionInput.text.length === 0
                    text: "ASK RECEPTION TO ROUTE YOU..."
                    font.pixelSize: 10
                    color: Colors.white
                    opacity: 0.38
                }
            }

            Rectangle {
                id: sendButton

                width: 86
                height: composer.height
                color:
                    sendMouse.pressed
                    ? Colors.black
                    : Colors.dark
                border.width:
                    sendMouse.containsMouse
                    ? 2 : 1
                border.color:
                    sendMouse.containsMouse
                    ? Colors.orange
                    : Colors.green
                opacity:
                    receptionInput.text.trim().length > 0
                    ? 1.0 : 0.48

                GohuText {
                    anchors.centerIn: parent
                    text: "ASK"
                    font.pixelSize: 11
                    color:
                        sendMouse.containsMouse
                        ? Colors.orange
                        : Colors.green
                }

                MouseArea {
                    id: sendMouse

                    anchors.fill: parent
                    enabled: receptionInput.text.trim().length > 0
                    hoverEnabled: true
                    cursorShape:
                        enabled
                        ? Qt.PointingHandCursor
                        : Qt.ArrowCursor

                    onClicked: {
                        const message =
                            String(receptionInput.text || "").trim();

                        root.receptionistService.submit(message);
                        receptionInput.text = "";

                        Qt.callLater(function() {
                            transcript.contentY = Math.max(
                                0,
                                transcript.contentHeight - transcript.height
                            );
                        });
                    }
                }
            }
        }
    }
}
