import QtQuick
import Quickshell
import qs.services.time
import "../components"

// Settings UI only. All mutations are delegated to one reusable service.
// No duplicate clock, timezone engine, config writer, or background sync.
Item {
    id: pane
    property bool panelVisible: visible
    property string calibratedPreview: "--:--:--//--"

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, body.y + body.implicitHeight + 8)

        Column {
            id: body
            x: 3
            y: 3
            width: Math.max(0, scroll.width - 8)
            spacing: 12

            GohuText {
                text: "DISPLAY // LOCAL CALIBRATION"
                font.pixelSize: 12
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "VISUAL OFFSET // " + TimeSettings.displayOffsetLabel
                font.pixelSize: 14
                color: TimeSettings.displayOffsetMs === 0
                       ? Colors.white : Colors.orange
            }
            GohuText {
                width: parent.width
                text: "PREVIEW // " + pane.calibratedPreview
                font.pixelSize: 12
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "Only the Clock dock and local readout shift. UTC, world calculations, timers and Linux time do not."
                font.pixelSize: 10
                color: Colors.white
            }

            Row {
                width: parent.width
                height: 33
                spacing: 4

                Repeater {
                    model: [
                        { label: "-1M", delta: -60000 },
                        { label: "-1S", delta: -1000 },
                        { label: "RESET", delta: 0, reset: true },
                        { label: "+1S", delta: 1000 },
                        { label: "+1M", delta: 60000 }
                    ]
                    ActionButton {
                        required property var modelData
                        width: (scroll.width - 8 - 16) / 5
                        height: 32
                        label: modelData.label
                        labelPixelSize: 9
                        contentPadding: 3
                        accentColor: modelData.reset ? Colors.orange : Colors.cyan
                        available: TimeSettings.canEdit
                        onLeftClicked: {
                            if (modelData.reset)
                                TimeSettings.resetDisplay();
                            else
                                TimeSettings.adjustDisplayMs(modelData.delta);
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                text: "STORE // " + TimeSettings.storageState.toUpperCase()
                      + (TimeSettings.errorCode
                         ? " // " + TimeSettings.errorCode : "")
                color: TimeSettings.errorCode ? Colors.orange : Colors.white
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.6
            }

            Row {
                width: parent.width
                height: 32
                spacing: 7
                GohuText {
                    width: parent.width - hostRefresh.width - parent.spacing
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: "HOST // TIMEZONE + DST"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                ActionButton {
                    id: hostRefresh
                    width: 70
                    height: 29
                    label: "REFRESH"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    available: !TimeSettings.hostRefreshing
                    onLeftClicked: TimeSettings.refreshHostStatus()
                }
            }
            GohuText {
                width: parent.width
                elide: Text.ElideRight
                text: "ZONE // " + String(TimeSettings.hostInfo.timezone || "UNKNOWN")
                color: Colors.white
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                text: "OFFSET // " + String(TimeSettings.hostInfo.utcOffset || "UNKNOWN")
                color: Colors.white
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                text: "DST // AUTO // "
                      + (TimeSettings.hostInfo.status !== "ready"
                         ? "UNKNOWN"
                         : TimeSettings.hostInfo.dstActive ? "ACTIVE" : "INACTIVE")
                color: Colors.orange
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                text: "NTP // " + String(TimeSettings.hostInfo.ntpEnabled || "unknown").toUpperCase()
                      + " // SYNC " + String(TimeSettings.hostInfo.ntpSynchronized || "unknown").toUpperCase()
                color: Colors.white
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "RTC LOCAL // " + String(TimeSettings.hostInfo.rtcLocal || "unknown").toUpperCase()
                color: TimeSettings.hostInfo.rtcLocal === "yes"
                       ? Colors.orange : Colors.white
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "DST follows Linux's IANA timezone rules. An RTC stored in local time can complicate DST transitions."
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                visible: TimeSettings.hostError !== ""
                width: parent.width
                text: TimeSettings.hostError
                font.pixelSize: 10
                color: Colors.orange
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
                opacity: 0.6
            }

            GohuText {
                text: "RESYNC // ONE-SHOT REQUEST"
                font.pixelSize: 12
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "Top-right ⟳ opens this confirmation. Active Chrony gets fresh samples; if stopped, a one-shot Chrony process may jump system time. A Polkit prompt may appear. NTP is never permanently enabled."
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "CONFIRMING CONTACTS CONFIGURED TIME SERVERS. THEY CAN SEE YOUR IP; A CORRECTION CAN CHANGE LOG / FILE TIMES."
                font.pixelSize: 9
                color: Colors.orange
            }
            Row {
                width: parent.width
                height: TimeSettings.resyncConfirmRequired ? 34 : 0
                visible: TimeSettings.resyncConfirmRequired
                spacing: 6
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "CONFIRM RESYNC"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    onLeftClicked: TimeSettings.requestResync()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onLeftClicked: TimeSettings.cancelResync()
                }
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "RESULT // " + TimeSettings.resyncMessage
                font.pixelSize: 10
                color: TimeSettings.resyncStatus === "requested"
                       ? Colors.cyan : Colors.orange
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "TIME SETTINGS // SHARED SERVICE READY FOR CPU++"
                font.pixelSize: 9
                color: Colors.white
            }
        }
    }

    onPanelVisibleChanged: {
        if (panelVisible)
            TimeSettings.refreshHostStatus();
    }
}
