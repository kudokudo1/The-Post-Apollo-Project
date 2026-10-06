import QtQuick
import Quickshell
import QtQuick.Effects
import qs.components

Rectangle {
    id: root

    required property var registryService
    required property var phoneService

    property string workingDirectory: ""

    signal callLaunched(var specialist)

    readonly property int listHeight:
        Math.min(
            208,
            Math.max(
                52,
                registryService.specialistCount * 56
            )
        )

    width: 310
    height: 78 + listHeight
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
            leftMargin: 10
            rightMargin: 10
            topMargin: 9
        }

        height: 24
        text:
            root.registryService.probing
            ? "PHONE // CHECKING STAFF"
            : "PHONE // "
              + String(root.registryService.readyCount)
              + " READY"
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            topMargin: 36
            leftMargin: 8
            rightMargin: 8
        }

        height: 1
        color: Colors.cyan
        opacity: 0.62
    }

    Flickable {
        id: phoneStaffList

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            leftMargin: 8
            rightMargin: 8
            topMargin: 44
        }

        height: root.listHeight
        clip: true
        contentWidth: width
        contentHeight: phoneStaffColumn.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: phoneStaffColumn

            width: phoneStaffList.width
            spacing: 4

            Repeater {
                model: root.registryService.specialists

                Rectangle {
                    id: phoneSpecialistRow

                    required property var modelData

                    readonly property string presence:
                        String(
                            modelData.presence
                            || "UNKNOWN"
                        ).toUpperCase()
                    readonly property bool ready:
                        !!modelData.callable
                        && presence === "READY"
                    readonly property color presenceColor:
                        presence === "READY"
                        ? Colors.green
                        : presence === "OFFLINE"
                        ? Colors.red
                        : Colors.orange

                    width: phoneStaffColumn.width
                    height: 52
                    color:
                        phoneSpecialistMouse.pressed
                        ? Colors.orange
                        : Colors.dark
                    border.width:
                        phoneSpecialistMouse.containsMouse
                        ? 2 : 1
                    border.color:
                        phoneSpecialistMouse.containsMouse
                        ? Colors.orange
                        : presenceColor
                    opacity: ready ? 1.0 : 0.58

                    Column {
                        anchors {
                            left: parent.left
                            right: phoneCallLabel.left
                            verticalCenter: parent.verticalCenter
                            leftMargin: 9
                            rightMargin: 8
                        }

                        spacing: 3

                        GohuText {
                            width: parent.width
                            text:
                                String(
                                    phoneSpecialistRow
                                        .modelData.name
                                    || "SPECIALIST"
                                )
                            font.pixelSize: 11
                            color:
                                phoneSpecialistRow.ready
                                ? Colors.cyan
                                : Colors.white
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                String(
                                    phoneSpecialistRow
                                        .modelData.role
                                    || "SPECIALIST"
                                )
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.76
                            elide: Text.ElideRight
                        }
                    }

                    GohuText {
                        id: phoneCallLabel

                        anchors {
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                            rightMargin: 9
                        }

                        width: 82
                        horizontalAlignment: Text.AlignRight
                        text:
                            phoneSpecialistRow.ready
                            ? (
                                phoneSpecialistMouse.containsMouse
                                ? "CALL"
                                : phoneSpecialistRow.presence
                              )
                            : phoneSpecialistRow.presence
                        font.pixelSize: 10
                        color:
                            phoneSpecialistMouse.containsMouse
                            && phoneSpecialistRow.ready
                            ? Colors.orange
                            : phoneSpecialistRow.presenceColor
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: phoneSpecialistMouse

                        anchors.fill: parent
                        enabled: phoneSpecialistRow.ready
                        hoverEnabled: true
                        cursorShape:
                            enabled
                            ? Qt.PointingHandCursor
                            : Qt.ArrowCursor

                        onClicked: {
                            if (
                                root.phoneService.callSpecialist(
                                    phoneSpecialistRow.modelData,
                                    root.workingDirectory
                                )
                            )
                                root.callLaunched(
                                    phoneSpecialistRow.modelData
                                );
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                visible: root.registryService.specialistCount === 0
                text: "NO SPECIALISTS REGISTERED"
                font.pixelSize: 10
                color: Colors.cyan
                opacity: 0.66
                horizontalAlignment: Text.AlignHCenter
            }
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
            root.phoneService.lastError
            ? root.phoneService.lastError
            : root.phoneService.lastStatus
            ? root.phoneService.lastStatus
            : root.registryService.probing
            ? "CHECKING SPECIALIST PRESENCE"
            : "SELECT SPECIALIST // CLICK TO CALL"
        font.pixelSize: 9
        color:
            root.phoneService.lastError
            ? Colors.red
            : root.phoneService.lastStatus
            ? Colors.green
            : root.registryService.probing
            ? Colors.orange
            : Colors.cyan
        elide: Text.ElideRight
    }
}
