import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var roundsService

    property string filterMode: "ATTENTION"
    property int selectedIndex: -1

    readonly property var displayedRooms: {
        const source =
            root.roundsService
            && Array.isArray(root.roundsService.rooms)
            ? root.roundsService.rooms
            : [];

        if (root.filterMode === "ALL")
            return source;

        return source.filter(function(room) {
            return Number((room || {}).attentionRank || 0) > 0;
        });
    }

    readonly property var selectedRoom: {
        if (selectedIndex < 0
                || selectedIndex >= displayedRooms.length)
            return null;

        return displayedRooms[selectedIndex] || null;
    }

    signal roomActivated(var room)

    function shortSha(value) {
        const sha = String(value || "");
        return sha.length > 10 ? sha.slice(0, 10) : sha;
    }

    function stateColor(stateValue) {
        const state = String(stateValue || "").toUpperCase();

        if (state === "DIVERGED" || state === "MISSING")
            return Colors.red;
        if (state === "AHEAD")
            return Colors.orange;
        if (state === "IN_MAIN" || state === "AT_MAIN")
            return Colors.green;

        return Colors.cyan;
    }

    function selectRoom(index) {
        const requested = Number(index);

        if (requested < 0 || requested >= displayedRooms.length)
            return false;

        selectedIndex = requested;
        return true;
    }

    function activateSelectedRoom() {
        if (!selectedRoom)
            return;

        roomActivated(selectedRoom);
    }

    onDisplayedRoomsChanged: {
        if (displayedRooms.length === 0)
            selectedIndex = -1;
        else if (selectedIndex < 0
                || selectedIndex >= displayedRooms.length)
            selectedIndex = 0;
    }

    component RoundsButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 28
        color:
            !enabledAction
            ? Colors.black
            : selectedAction
            ? Colors.yellow
            : mouse.pressed
            ? Colors.orange
            : Colors.black
        border.width:
            selectedAction || mouse.containsMouse
            ? 2 : 1
        border.color:
            !enabledAction
            ? Colors.cyan
            : selectedAction
            ? Colors.orange
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 8
            color:
                button.selectedAction
                ? Colors.magenta
                : mouse.pressed
                ? Colors.black
                : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: button.triggered()
        }
    }

    component MetricBox: Rectangle {
        property string label: ""
        property string value: "0"
        property color accent: Colors.cyan

        height: 48
        color: Colors.black
        border.width: 1
        border.color: accent

        Column {
            anchors.centerIn: parent
            spacing: 2

            GohuText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: parent.parent.value
                font.pixelSize: 13
                color: parent.parent.accent
            }

            GohuText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: parent.parent.label
                font.pixelSize: 6
                color: Colors.white
                opacity: 0.72
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            hoverEnabled: true

            onWheel: function(wheel) {
                wheel.accepted = true;
            }
        }

        Column {
            anchors {
                fill: parent
                margins: 10
            }
            spacing: 8

            Row {
                width: parent.width
                height: 30
                spacing: 8

                GohuText {
                    width: parent.width - 214
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        root.roundsService.running
                        ? "ROUNDS // WALKING FLOORS"
                        : "ROUNDS // HOSPITAL BOARD"
                    font.pixelSize: 11
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                RoundsButton {
                    width: 72
                    label: "ATTENTION"
                    selectedAction: root.filterMode === "ATTENTION"
                    onTriggered: {
                        root.filterMode = "ATTENTION";
                        root.selectedIndex =
                            root.displayedRooms.length > 0 ? 0 : -1;
                    }
                }

                RoundsButton {
                    width: 48
                    label: "ALL"
                    selectedAction: root.filterMode === "ALL"
                    onTriggered: {
                        root.filterMode = "ALL";
                        root.selectedIndex =
                            root.displayedRooms.length > 0 ? 0 : -1;
                    }
                }

                RoundsButton {
                    width: 78
                    label:
                        root.roundsService.running
                        ? "ROUNDING"
                        : "REFRESH"
                    enabledAction: !root.roundsService.running
                    onTriggered: root.roundsService.refresh()
                }
            }

            Row {
                width: parent.width
                height: 48
                spacing: 6

                MetricBox {
                    width: (parent.width - 24) / 5
                    label: "FLOORS"
                    value: String(root.roundsService.floorCount)
                    accent: Colors.cyan
                }

                MetricBox {
                    width: (parent.width - 24) / 5
                    label: "ROOMS"
                    value: String(root.roundsService.roomCount)
                    accent: Colors.blue
                }

                MetricBox {
                    width: (parent.width - 24) / 5
                    label: "ATTENTION"
                    value: String(root.roundsService.attentionCount)
                    accent:
                        root.roundsService.attentionCount > 0
                        ? Colors.orange
                        : Colors.green
                }

                MetricBox {
                    width: (parent.width - 24) / 5
                    label: "DIVERGED"
                    value: String(root.roundsService.divergedCount)
                    accent:
                        root.roundsService.divergedCount > 0
                        ? Colors.red
                        : Colors.green
                }

                MetricBox {
                    width: (parent.width - 24) / 5
                    label: "MISSING"
                    value: String(root.roundsService.missingCount)
                    accent:
                        root.roundsService.missingCount > 0
                        ? Colors.red
                        : Colors.green
                }
            }

            Rectangle {
                width: parent.width
                height: 28
                color: Colors.black
                border.width: 1
                border.color:
                    root.roundsService.lastError
                    ? Colors.red
                    : Colors.cyan

                GohuText {
                    anchors {
                        fill: parent
                        margins: 6
                    }

                    text:
                        root.roundsService.lastError
                        ? root.roundsService.lastError
                        : root.roundsService.lastRefreshedAt
                        ? "LAST ROUND // "
                          + root.roundsService.lastRefreshedAt
                        : "ROUNDS NOT RUN"
                    font.pixelSize: 7
                    color:
                        root.roundsService.lastError
                        ? Colors.red
                        : Colors.cyan
                    elide: Text.ElideRight
                }
            }

            Row {
                width: parent.width
                height: parent.height - 130
                spacing: 10

                Rectangle {
                    width: (parent.width - 10) * 0.64
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: roomBoard

                        anchors {
                            fill: parent
                            margins: 6
                        }

                        clip: true
                        contentWidth: width
                        contentHeight: roomColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: roomColumn
                            width: roomBoard.width
                            spacing: 5

                            Repeater {
                                model: root.displayedRooms

                                Rectangle {
                                    required property int index
                                    required property var modelData

                                    width: roomColumn.width
                                    height: 76
                                    color:
                                        root.selectedIndex === index
                                        ? Colors.yellow
                                        : Colors.dark
                                    border.width:
                                        root.selectedIndex === index
                                        || roomMouse.containsMouse
                                        ? 2 : 1
                                    border.color:
                                        root.selectedIndex === index
                                        ? Colors.orange
                                        : root.stateColor(modelData.state)

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 6
                                        }
                                        spacing: 3

                                        Row {
                                            width: parent.width

                                            GohuText {
                                                width: parent.width * 0.58
                                                text:
                                                    String(
                                                        modelData.floorLabel
                                                        || "FLOOR"
                                                    )
                                                    + " // "
                                                    + String(
                                                        modelData.team
                                                        || "ROOM"
                                                    )
                                                font.pixelSize: 8
                                                color:
                                                    root.selectedIndex === index
                                                    ? Colors.magenta
                                                    : Colors.cyan
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width * 0.42
                                                text:
                                                    String(
                                                        modelData.attentionLabel
                                                        || "CHECK"
                                                    )
                                                    + " // "
                                                    + String(
                                                        modelData.state
                                                        || "UNKNOWN"
                                                    )
                                                font.pixelSize: 8
                                                color:
                                                    root.stateColor(
                                                        modelData.state
                                                    )
                                                horizontalAlignment:
                                                    Text.AlignRight
                                                elide: Text.ElideRight
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    modelData.responsibility
                                                    || "NO RESPONSIBILITY"
                                                )
                                            font.pixelSize: 7
                                            color: Colors.white
                                            opacity: 0.86
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    modelData.branch
                                                    || "NO BRANCH"
                                                )
                                                + " // +"
                                                + String(
                                                    modelData.ahead || 0
                                                )
                                                + " / -"
                                                + String(
                                                    modelData.behind || 0
                                                )
                                                + (
                                                    modelData.head
                                                    ? " // "
                                                      + root.shortSha(
                                                          modelData.head
                                                      )
                                                    : ""
                                                )
                                            font.pixelSize: 7
                                            color: Colors.orange
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    modelData.updatedAt
                                                    || "NO TOUCH DATA"
                                                )
                                            font.pixelSize: 6
                                            color: Colors.white
                                            opacity: 0.52
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: roomMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor

                                        onClicked:
                                            root.selectRoom(index)

                                        onDoubleClicked: {
                                            root.selectRoom(index);
                                            root.activateSelectedRoom();
                                        }
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible:
                                    !root.roundsService.running
                                    && root.displayedRooms.length === 0
                                text:
                                    root.filterMode === "ATTENTION"
                                    ? "NO ROOMS REQUIRE ATTENTION"
                                    : "NO ROOMS AVAILABLE"
                                font.pixelSize: 8
                                color: Colors.cyan
                                opacity: 0.62
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                Rectangle {
                    width: (parent.width - 10) * 0.36
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        readonly property var room:
                            root.selectedRoom || ({})

                        GohuText {
                            width: parent.width
                            text:
                                root.selectedRoom
                                ? "ROUND NOTE // "
                                  + String(parent.room.team || "ROOM")
                                : "ROUND NOTE // SELECT ROOM"
                            font.pixelSize: 10
                            color: Colors.magenta
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.magenta
                            opacity: 0.68
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "FLOOR // "
                                + String(parent.room.floorLabel || "—")
                            font.pixelSize: 7
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "REPO // "
                                + String(parent.room.repository || "—")
                            font.pixelSize: 7
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "STATE // "
                                + String(parent.room.state || "—")
                            font.pixelSize: 8
                            color:
                                root.stateColor(parent.room.state)
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "RELATION // +"
                                + String(parent.room.ahead || 0)
                                + " / -"
                                + String(parent.room.behind || 0)
                            font.pixelSize: 7
                            color: Colors.orange
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "HEAD // "
                                + (
                                    root.shortSha(parent.room.head)
                                    || "—"
                                )
                            font.pixelSize: 7
                            color: Colors.blue
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                String(
                                    parent.room.responsibility
                                    || "NO RESPONSIBILITY RECORDED"
                                )
                            font.pixelSize: 8
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }

                        Item {
                            width: 1
                            height: 6
                        }

                        RoundsButton {
                            width: parent.width
                            label: "OPEN ROOM"
                            enabledAction: !!root.selectedRoom
                            onTriggered: root.activateSelectedRoom()
                        }
                    }
                }
            }
        }
    }
}
