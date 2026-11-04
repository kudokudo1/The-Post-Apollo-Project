import QtQuick
import qs.services.time
import "../../components"

// CPU++ right/actuator bay. Milestone 1 is intentionally read-only:
// it exposes the existing Clock-owned host diagnostics and safe queries.
// Future NTP policy/source/RTC mutations require their own authorization flow.
Item {
    id: advancedTime
    property bool panelVisible: visible

    Flickable {
        id: advancedScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, advancedBody.y
                                + advancedBody.implicitHeight + 12)

        Column {
            id: advancedBody
            x: 5
            y: 7
            width: Math.max(0, advancedScroll.width - 16)
            spacing: 11

            GohuText {
                width: parent.width
                text: "ADVANCED // HOST DIAGNOSTICS"
                color: Colors.magenta
                font.pixelSize: 12
            }
            Row {
                width: parent.width
                height: 32
                spacing: 7
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 30
                    label: "REFRESH"
                    labelPixelSize: 10
                    accentColor: Colors.white
                    available: !TimeSettings.hostRefreshing
                    onLeftClicked: TimeSettings.refreshHostStatus()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 30
                    label: "DIAGNOSE"
                    labelPixelSize: 10
                    accentColor: Colors.yellow
                    available: !TimeSettings.diagnosticBusy
                    onLeftClicked: TimeSettings.diagnoseResync()
                }
            }
            GohuText {
                width: parent.width
                text: "HOST // "
                      + String(TimeSettings.hostInfo.status || "UNKNOWN").toUpperCase()
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.hostError !== ""
                text: "HOST ERROR // " + TimeSettings.hostError
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "DST // AUTO // "
                      + (TimeSettings.hostInfo.status !== "ready"
                         ? "UNKNOWN"
                         : TimeSettings.hostInfo.dstActive ? "ACTIVE" : "INACTIVE")
                font.pixelSize: 11
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "SYSTEM ZONE // " + String(TimeSettings.hostInfo.timezone)
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "UTC OFFSET // " + String(TimeSettings.hostInfo.utcOffset)
                font.pixelSize: 10
                color: Colors.white
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.6
            }
            GohuText {
                width: parent.width
                text: "SYNC // HOST POLICY"
                font.pixelSize: 12
                color: Colors.yellow
            }
            GohuText {
                width: parent.width
                text: "NTP SERVICE // "
                      + String(TimeSettings.hostInfo.ntpEnabled || "unknown").toUpperCase()
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "OS SYNCHRONIZED // "
                      + String(TimeSettings.hostInfo.ntpSynchronized || "unknown").toUpperCase()
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "ONE-SHOT RESULT // " + TimeSettings.resyncMessage
                font.pixelSize: 10
                color: Colors.yellow
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.resyncErrorCode !== ""
                text: "SYNC ERROR // " + TimeSettings.resyncErrorCode
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "LOCAL DIAG // " + TimeSettings.diagnosticMessage
                font.pixelSize: 10
                color: Colors.yellow
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.diagnosticDetail !== ""
                text: TimeSettings.diagnosticDetail
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "DIAGNOSE checks local prerequisites only; it does not verify NTP server reachability."
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.6
            }
            GohuText {
                width: parent.width
                text: "HARDWARE CLOCK // RTC"
                font.pixelSize: 12
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "RTC IN LOCAL TIME // "
                      + String(TimeSettings.hostInfo.rtcLocal || "unknown").toUpperCase()
                font.pixelSize: 10
                color: TimeSettings.hostInfo.rtcLocal === "yes"
                       ? Colors.orange : Colors.white
            }
            GohuText {
                width: parent.width
                text: "Linux applies DST from the selected IANA zone. Local-time RTC can complicate DST transitions."
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.6
            }
            GohuText {
                width: parent.width
                text: "AUTHORIZATION // LAST REQUEST"
                font.pixelSize: 11
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: TimeSettings.authFlowStage
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.authActionId !== ""
                text: TimeSettings.authActionId
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "SOURCE SELECTION / AUTO POLICY / RTC WRITES / HISTORY // NOT YET ENABLED"
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }
        }
    }

    NeonScrollBar {
        flickable: advancedScroll
        visible: advancedTime.panelVisible && scrollable
    }
}
