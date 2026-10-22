import QtQuick
import Quickshell
import "../components"
import qs.services.notifications
import "../services/notifications/NotificationFacets.js" as NotificationFacets

PanelWindow {
    id: notificationsWindow

    // Display the latest activity time for a continuing event; ordinary
    // notifications display their receipt time. Qt formats in local time.
    function eventTimestamp(createdAt, updatedAt) {
        const first = Number(createdAt || 0);
        const last = Number(updatedAt || 0);
        const time = last > first ? last : first;
        return time > 0 ? Qt.formatDateTime(new Date(time), "MM/dd/yy  h:mm AP") : "TIME UNKNOWN";
    }

    // ===== WINDOW ===============================================

    // The visible card remains 420x150. The native window is slightly larger
    // only to host the glow without clipping it.
    implicitWidth: 444
    implicitHeight: 164

    anchors {
        top: true
        bottom: false
        left: false
        right: true
    }

    margins {
        // Visible card top = 2px window margin + 2px internal offset:
        // 4px from the screen top, 2px lower than the previous position.
        top: 2
        bottom: 0
        left: 0

        // 3px window margin + 12px internal glow gutter places the visible
        // card 15px from the screen right edge: 2px farther right.
        right: 3
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
                // Each launch is a new occurrence, not an update to one
                // permanent test ID. NotificationsService assigns a unique ID.
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

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right

            topMargin: 2
            leftMargin: 12
            rightMargin: 12
        }

        height: 150

        Repeater {
            model: NotificationsService.activeNotifications

            WindowPanelFrame {
                id: notificationCard

                required property int index
                required property string notificationId
                required property string source
                required property string sourceId
                required property string title
                required property string message
                required property string appIcon
                required property string image
                required property string website
                required property string websiteIcon
                required property string category
                required property string severity
                required property double createdAt
                required property double updatedAt
                required property var context

                // The popup chassis reflects the originating organization,
                // not a mutually exclusive domain or warning severity.
                // One Apollo SYSTEM warning is still an orange Apollo popup.
                readonly property var organizationFacets: NotificationFacets.facetsFor({
                    "source": notificationCard.source,
                    "sourceId": notificationCard.sourceId,
                    "category": notificationCard.category,
                    "severity": notificationCard.severity,
                    "context": notificationCard.context
                })
                readonly property color organizationColor:
                    organizationFacets.origin === "apollo" ? Colors.orange
                    : organizationFacets.domain === "social" ? Colors.omnitrix
                    : organizationFacets.domain === "system" ? Colors.white
                    : Colors.cyan

                // Source-backed actions are displayed only while their
                // originating native notification remains callable.
                readonly property var externalActions: NotificationsService.externalActionsRevision >= 0
                    ? NotificationsService.externalActionsFor(notificationCard.notificationId) : []

                anchors.fill: parent

                visible: notificationCard.index === NotificationsService.activeNotifications.count - 1

                fillColor: Colors.black

                borderWidth: 1
                borderColor: notificationCard.organizationColor

                glowColor: notificationCard.organizationColor
                closeGlowSpread: 4
                closeGlowOpacity: 0.55
                wideGlowSpread: 12
                wideGlowOpacity: 0.14

                // ===== APP ICON ================================

                Rectangle {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }
                    anchors.leftMargin: 15
                    anchors.topMargin: 15
                    width: 42
                    height: 42
                    radius: 4
                    color: Colors.black
                    visible: notificationCard.website !== ""
                }

                Image {
                    id: notificationIcon

                    width: 42
                    height: 42

                    anchors.left: parent.left
                    anchors.top: parent.top

                    anchors.leftMargin: 15
                    anchors.topMargin: 15

                    // Website mark overrides the browser logo only when
                    // origin metadata identifies the website. Other native
                    // notifications retain their existing image preference.
                    source: notificationCard.website === "YouTube"
                        ? Qt.resolvedUrl("../assets/notifications/youtube.svg")
                        : notificationCard.website !== "" && notificationCard.websiteIcon !== ""
                        ? notificationCard.websiteIcon
                        : notificationCard.image !== "" ? notificationCard.image
                        : notificationCard.appIcon !== "" ? Quickshell.iconPath(notificationCard.appIcon, true) : ""

                    // Preserve the exact site image pixels. Some opaque
                    // favicon/image payloads became solid magenta/black tiles
                    // when passed through a separate Colorize shader.
                    fillMode: Image.PreserveAspectFit
                }

                // ===== TEXT ====================================

                Column {
                    anchors.left: notificationIcon.source.toString() !== "" ? notificationIcon.right : parent.left

                    anchors.right: parent.right
                    anchors.top: parent.top

                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    anchors.topMargin: 8
                    anchors.bottom: externalActionRow.visible ? externalActionRow.top : undefined
                    anchors.bottomMargin: externalActionRow.visible ? 4 : 0
                    clip: externalActionRow.visible

                    spacing: 4

                    GohuText {
                        width: parent.width

                        text: notificationsWindow.eventTimestamp(notificationCard.createdAt, notificationCard.updatedAt)
                        color: Colors.cyan
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width

                        text: notificationCard.website !== ""
                            ? notificationCard.source + " // " + notificationCard.website
                            : notificationCard.sourceId !== ""
                            ? notificationCard.source + "  [" + notificationCard.sourceId + "]"
                            : notificationCard.source
                        textFormat: Text.PlainText

                        color: Colors.cyan

                        font.pixelSize: 13

                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width

                        text: notificationCard.title
                        textFormat: Text.PlainText

                        color: Colors.orange

                        font.pixelSize: 18

                        wrapMode: Text.Wrap
                    }

                    Text {
                        width: parent.width

                        text: notificationCard.message
                        textFormat: Text.PlainText

                        color: Colors.white

                        font.pixelSize: 14

                        wrapMode: Text.Wrap

                        maximumLineCount: externalActionRow.visible ? 2 : 3

                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width

                        visible: !externalActionRow.visible
                        text: "CATEGORY: " + notificationCard.category + "    SEVERITY: " + notificationCard.severity

                        color: Colors.cyan

                        font.pixelSize: 10
                    }
                }

                // Native notification actions. Unlike historical metadata,
                // these are forwarded to the original sender using the live
                // QsNotification action objects held ONLY in the service.
                Row {
                    id: externalActionRow
                    anchors {
                        bottom: parent.bottom
                        right: parent.right
                    }
                    anchors.bottomMargin: 9
                    anchors.rightMargin: 13
                    spacing: 6
                    visible: notificationCard.externalActions.length > 0
                    z: 3

                    Repeater {
                        model: notificationCard.externalActions
                        delegate: Rectangle {
                            id: nativeActionButton
                            required property var modelData

                            width: Math.min(106, Math.max(60, nativeActionLabel.implicitWidth + 16))
                            height: 25
                            radius: 2
                            color: nativeActionMouse.containsMouse ? Colors.orange : Colors.black
                            border.width: 1
                            border.color: Colors.cyan

                            GohuText {
                                id: nativeActionLabel
                                anchors.fill: parent
                                anchors.margins: 3
                                text: nativeActionButton.modelData.label
                                color: nativeActionMouse.containsMouse ? Colors.black : Colors.cyan
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }

                            MouseArea {
                                id: nativeActionMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    NotificationsService.invokeExternalAction(
                                        notificationCard.notificationId,
                                        nativeActionButton.modelData.identifier
                                    );
                                }
                            }
                        }
                    }
                }

            }
        }
    }
}
