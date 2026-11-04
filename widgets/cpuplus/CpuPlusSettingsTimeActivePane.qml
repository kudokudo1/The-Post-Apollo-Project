import QtQuick
import Quickshell
import qs.services.time
import "../../components"

// CPU++ middle/target bay. The SystemClock below is a view tick only: host
// time and policy come from the OS and Clock-owned TimeSettings singleton.
// No saved profile, timezone writer, or independent time configuration.
Item {
    id: activeTime
    property bool panelVisible: visible
    readonly property bool referenceFresh:
        TimeSettings.hasFreshReference(hostClock.date.getTime())
    readonly property bool zoneOffsetMismatch:
        TimeSettings.dockZoneOffsetMismatch(hostClock.date.getTime())
    readonly property string accuracyLabel:
        referenceFresh
        ? (Math.abs(TimeSettings.referenceOffsetMs) >=
           TimeSettings.referenceWarningThresholdMs
           ? "REFERENCE MISMATCH" : "WITHIN 1S THRESHOLD")
        : "NOT RECENTLY VERIFIED"

    SystemClock {
        id: hostClock
        precision: SystemClock.Seconds
    }

    Flickable {
        id: activeScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, activeBody.y + activeBody.implicitHeight + 12)

        Column {
            id: activeBody
            x: 6
            y: 8
            width: Math.max(0, activeScroll.width - 18)
            spacing: 11

            GohuText {
                width: parent.width
                text: "ACTIVE // HOST TIME"
                font.pixelSize: 12
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: Qt.formatDateTime(hostClock.date, "hh:mm:ss AP")
                font.pixelSize: 18
                color: Colors.white
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: Qt.formatDate(hostClock.date, "ddd, MMM d yyyy")
                font.pixelSize: 10
                color: Colors.white
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.65
            }
            GohuText {
                width: parent.width
                text: "ZONE // SYSTEM ACTIVE"
                font.pixelSize: 11
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: String(TimeSettings.hostInfo.timezone || "UNKNOWN")
                font.pixelSize: 12
                color: Colors.white
                elide: Text.ElideMiddle
            }
            GohuText {
                width: parent.width
                text: String(TimeSettings.hostInfo.utcOffset || "UNKNOWN")
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                visible: TimeSettings.timezoneConfirmRequired
                width: parent.width
                text: "PENDING // " + TimeSettings.zoneChoice
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.65
            }
            GohuText {
                width: parent.width
                text: "ACCURACY // " + activeTime.accuracyLabel
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                color: activeTime.referenceFresh
                       && Math.abs(TimeSettings.referenceOffsetMs)
                          < TimeSettings.referenceWarningThresholdMs
                       ? Colors.white : Colors.yellow
            }
            GohuText {
                width: parent.width
                visible: activeTime.referenceFresh
                text: "MEASURED // "
                      + (TimeSettings.referenceOffsetMs / 1000).toFixed(3)
                      + "S"
                font.pixelSize: 10
                color: Colors.yellow
            }
            GohuText {
                width: parent.width
                text: activeTime.zoneOffsetMismatch
                      ? "DISPLAY / HOST ZONE OFFSET MISMATCH"
                      : "DISPLAY / HOST ZONE // NO KNOWN MISMATCH"
                font.pixelSize: 9
                color: activeTime.zoneOffsetMismatch ? Colors.orange : Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "DISPLAY CAL // " + TimeSettings.displayOffsetLabel
                font.pixelSize: 10
                color: TimeSettings.displayDeviationActive
                       ? Colors.yellow : Colors.white
            }
            GohuText {
                width: parent.width
                text: "PREVIEW // "
                      + Qt.formatDateTime(
                          new Date(TimeSettings.adjustedEpochMs(
                                       hostClock.date.getTime())),
                          "hh:mm:ss AP")
                font.pixelSize: 11
                color: Colors.white
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.65
            }
            GohuText {
                width: parent.width
                text: "CONFIGURATION // HOST"
                font.pixelSize: 11
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "PROFILE SAVING NOT YET ENABLED"
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "Accuracy is unknown without a fresh source measurement. No underline is not a guarantee."
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
        }
    }
    NeonScrollBar {
        flickable: activeScroll
        visible: activeTime.panelVisible && scrollable
    }
}
