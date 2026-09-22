import QtQuick
import Quickshell
import "../components"
import qs.services.notifications
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: notificationsWindow

    // ===== WINDOW ===============================================

    implicitWidth: 420
    implicitHeight: 150

    anchors {
        top: true
        bottom: false
        left: false
        right: true
    }

    margins {
        top: 90
        bottom: 0
        left: 0
        right: 20
    }

    exclusiveZone: 0

    color: "transparent"

    surfaceFormat.opaque: false

    visible: NotificationsService.activeNotifications.count > 0

    //Component.onCompleted: {
    //  NotificationsService.push("TEST", "META APOLLO", "The notification frontend is connected.");
    //`` }

    // ===== CONTENT ==============================================

    Timer {
        interval: 1500
        running: true
        repeat: false

        onTriggered: {
            NotificationsService.pushRich({
                "id": "apollo-structure-test",
                "source": "META APOLLO",
                "title": "STRUCTURED DATA TEST",
                "message": "Testing rich history data.",
                "category": "resource",
                "severity": "warning",
                "tags": ["cpu", "memory", "test"],
                "metrics": {
                    "cpuPercent": 47,
                    "ramMb": 3821,
                    "uptimeSeconds": 19420
                },
                "context": {
                    "app": "brave",
                    "pid": 12345
                },
                "actions": [
                    {
                        "id": "open-resource",
                        "label": "OPEN"
                    },
                    {
                        "id": "kill-resource",
                        "label": "KILL"
                    }
                ]
            });
        }
    }

    Item {
        id: notificationContainer

        anchors.fill: parent

        Repeater {
            model: NotificationsService.activeNotifications

            Rectangle {
                id: notificationCard

                required property int index
                required property string source
                required property string sourceId
                required property string title
                required property string message
                required property string appIcon
                required property string image
                required property string category
                required property string severity

                anchors.fill: parent

                visible: notificationCard.index === NotificationsService.activeNotifications.count - 1

                color: Colors.black

                border.width: 1
                border.color: Colors.cyan

                // ===== APP ICON ================================

                Image {
                    id: notificationIcon

                    width: 42
                    height: 42

                    anchors.left: parent.left
                    anchors.top: parent.top

                    anchors.leftMargin: 15
                    anchors.topMargin: 15

                    source: notificationCard.image !== "" ? notificationCard.image : notificationCard.appIcon !== "" ? Quickshell.iconPath(notificationCard.appIcon, true) : ""

                    fillMode: Image.PreserveAspectFit
                }

                // ===== TEXT ====================================

                Column {
                    anchors.left: notificationIcon.source.toString() !== "" ? notificationIcon.right : parent.left

                    anchors.right: parent.right
                    anchors.top: parent.top

                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    anchors.topMargin: 13

                    spacing: 5

                    Text {
                        width: parent.width

                        text: notificationCard.sourceId !== "" ? notificationCard.source + "  [" + notificationCard.sourceId + "]" : notificationCard.source

                        color: Colors.cyan

                        font.pixelSize: 13

                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width

                        text: notificationCard.title

                        color: Colors.orange

                        font.pixelSize: 18

                        wrapMode: Text.Wrap
                    }

                    Text {
                        width: parent.width

                        text: notificationCard.message

                        color: Colors.white

                        font.pixelSize: 14

                        wrapMode: Text.Wrap

                        maximumLineCount: 3

                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width

                        text: "CATEGORY: " + notificationCard.category + "    SEVERITY: " + notificationCard.severity

                        color: Colors.cyan

                        font.pixelSize: 10
                    }
                }

                // ===== GLOW ====================================

                RectangularShadow {
                    anchors.fill: parent

                    spread: 3

                    z: -1

                    opacity: 0.55

                    color: Colors.cyan
                }

                RectangularShadow {
                    anchors.fill: parent

                    spread: 12

                    z: -2

                    opacity: 0.08

                    color: Colors.cyan
                }
            }
        }
    }
}
