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
    // CPU++ shares the same pane/controller, but shows a narrower TIME scope.
    // Clock keeps its existing preview and timezone information by default.
    property bool showClockPreview: true
    property bool showTimezoneDetails: true
    property bool showResyncTrigger: false
    property bool showSharedServiceCaption: true
    property bool zonePickerExpanded: false
    readonly property bool zoneSearchFocused: systemZonePicker.searchFocused

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
                visible: pane.showClockPreview
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
                    text: pane.showTimezoneDetails
                          ? "HOST // TIMEZONE + DST"
                          : "HOST // DAYLIGHT SAVING"
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
            // This uses TimeW's existing country-aware, scrollable star-rail
            // zone selector, but applies the chosen zone to Linux via timedated.
            // CPU++ TIME keeps its intentionally narrower view for now.
            GohuText {
                width: parent.width
                visible: pane.showTimezoneDetails
                text: "SYSTEM TIMEZONE // CHANGE"
                font.pixelSize: 12
                color: Colors.cyan
            }
            Row {
                id: zonePresetRow
                width: parent.width
                height: pane.showTimezoneDetails ? 32 : 0
                visible: pane.showTimezoneDetails
                spacing: 5
                Repeater {
                    model: [
                        { label: "UTC", zone: "UTC" },
                        { label: "NYC", zone: "America/New_York" },
                        { label: "LON", zone: "Europe/London" },
                        { label: "TOK", zone: "Asia/Tokyo" }
                    ]
                    ActionButton {
                        required property var modelData
                        width: (zonePresetRow.width - 3 * zonePresetRow.spacing) / 4
                        height: 31
                        label: modelData.label
                        labelPixelSize: 10
                        contentPadding: 2
                        accentColor: Colors.cyan
                        available: !TimeSettings.authSessionActive
                        onLeftClicked: {
                            pane.zonePickerExpanded = false;
                            TimeSettings.prepareTimezone(modelData.zone);
                        }
                    }
                }
            }
            Item {
                width: parent.width
                height: pane.showTimezoneDetails
                        ? (pane.zonePickerExpanded ? 255 : 38) : 0
                visible: pane.showTimezoneDetails
                TimeZonePicker {
                    id: systemZonePicker
                    width: parent.width
                    selectedZone: TimeSettings.zoneChoice !== ""
                                  ? TimeSettings.zoneChoice
                                  : String(TimeSettings.hostInfo.timezone || "UTC")
                    expanded: pane.zonePickerExpanded
                    catalog: TimeSettings.zoneCatalog
                    countryIndex: TimeSettings.zoneCountryIndex
                    catalogLoading: TimeSettings.zoneCatalogLoading
                    catalogFailed: TimeSettings.zoneCatalogFailed
                    onOpenRequested: {
                        TimeSettings.loadZoneCatalog();
                        pane.zonePickerExpanded = true;
                    }
                    onToggleRequested: {
                        if (!pane.zonePickerExpanded)
                            TimeSettings.loadZoneCatalog();
                        pane.zonePickerExpanded = !pane.zonePickerExpanded;
                    }
                    onZoneChosen: function(zoneId) {
                        pane.zonePickerExpanded = false;
                        TimeSettings.prepareTimezone(zoneId);
                    }
                }
            }
            GohuText {
                width: parent.width
                visible: pane.showTimezoneDetails
                wrapMode: Text.WordWrap
                text: "DIRECTORY // "
                      + (TimeSettings.zoneCatalogLoading ? "LOADING"
                         : TimeSettings.zoneCatalogFailed ? "UNAVAILABLE"
                         : TimeSettings.zoneCatalogLoaded
                           ? TimeSettings.zoneCatalog.length + " ZONES"
                           : "NOT LOADED")
                font.pixelSize: 9
                color: Colors.white
            }
            GohuText {
                width: parent.width
                visible: pane.showTimezoneDetails
                wrapMode: Text.WordWrap
                text: "CHANGES SYSTEM LOCAL TIME IN ALL APPS. UTC INSTANT STAYS UNCHANGED. WHEN RTC LOCAL=YES, SYSTEMD MAY ALSO UPDATE HARDWARE TIME."
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                visible: pane.showTimezoneDetails
                         && TimeSettings.timezoneConfirmRequired
                text: "APPLY // " + TimeSettings.zoneChoice
                font.pixelSize: 10
                color: Colors.magenta
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                visible: pane.showTimezoneDetails
                         && TimeSettings.timezoneConfirmRequired
                height: visible ? 34 : 0
                spacing: 5
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 32
                    label: "APPLY ZONE"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    onLeftClicked: TimeSettings.requestTimezone()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 32
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    onLeftClicked: TimeSettings.cancelTimezone()
                }
            }
            GohuText {
                visible: pane.showTimezoneDetails
                width: parent.width
                wrapMode: Text.WordWrap
                text: "ZONE RESULT // " + TimeSettings.timezoneMessage
                color: TimeSettings.timezoneStatus === "completed"
                       || TimeSettings.timezoneStatus === "unchanged"
                       ? Colors.cyan : Colors.orange
                font.pixelSize: 9
            }
            GohuText {
                visible: pane.showTimezoneDetails
                         && TimeSettings.timezoneErrorCode !== ""
                width: parent.width
                text: "ERROR // " + TimeSettings.timezoneErrorCode
                color: Colors.orange
                font.pixelSize: 9
            }
            GohuText {
                width: parent.width
                elide: Text.ElideRight
                visible: pane.showTimezoneDetails
                text: "ZONE // " + String(TimeSettings.hostInfo.timezone || "UNKNOWN")
                color: Colors.white
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                visible: pane.showTimezoneDetails
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

            Row {
                width: parent.width
                height: 32
                spacing: 6

                GohuText {
                    width: parent.width
                           - (resyncLaunch.visible
                              ? resyncLaunch.width + parent.spacing : 0)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: "RESYNC // ONE-SHOT REQUEST"
                    font.pixelSize: 12
                    color: Colors.cyan
                    elide: Text.ElideRight
                }
                ActionButton {
                    id: resyncLaunch
                    visible: pane.showResyncTrigger
                    width: 76
                    height: 30
                    label: "⟳ RESYNC"
                    labelPixelSize: 10
                    contentPadding: 3
                    accentColor: Colors.cyan
                    available: TimeSettings.resyncStatus !== "working"
                               && !TimeSettings.resyncAuthPending
                    onLeftClicked: TimeSettings.prepareResync()
                }
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: pane.showResyncTrigger
                      ? "RESYNC opens confirmation. Active Chrony gets new samples; stopped Chrony may perform a one-shot jump. Polkit authorization may be required. NTP stays as configured."
                      : "Top-right ⟳ opens this confirmation. Active Chrony gets fresh samples; if stopped, a one-shot Chrony process may jump system time. A Polkit prompt may appear. NTP is never permanently enabled."
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
                visible: TimeSettings.resyncAuthPath !== "NOT REQUESTED"
                width: parent.width
                wrapMode: Text.WordWrap
                text: "AUTH // " + TimeSettings.resyncAuthPath
                font.pixelSize: 9
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.authSessionActive
                         || TimeSettings.resyncErrorCode !== ""
                         || TimeSettings.timezoneErrorCode !== ""
                wrapMode: Text.WordWrap
                text: "POLKIT // " + TimeSettings.authFlowStage
                      + (TimeSettings.authActionId !== ""
                         ? " // " + TimeSettings.authActionId : "")
                font.pixelSize: 9
                color: Colors.cyan
            }
            Row {
                width: parent.width
                spacing: 8
                height: 32

                ActionButton {
                    id: resyncDiagnoseButton
                    width: 96
                    height: 29
                    label: "DIAGNOSE"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: !TimeSettings.diagnosticBusy
                    onLeftClicked: TimeSettings.diagnoseResync()
                }
                GohuText {
                    width: Math.max(0, parent.width - resyncDiagnoseButton.width - parent.spacing)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: TimeSettings.resyncErrorCode
                          ? "ERROR // " + TimeSettings.resyncErrorCode
                          : "CHECK // READ ONLY"
                    font.pixelSize: 10
                    color: Colors.orange
                    elide: Text.ElideRight
                }
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "DIAG // " + TimeSettings.diagnosticMessage
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: TimeSettings.diagnosticDetail !== ""
                wrapMode: Text.WordWrap
                text: TimeSettings.diagnosticDetail
                font.pixelSize: 9
                color: Colors.white
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                visible: pane.showSharedServiceCaption
                text: "TIME SETTINGS // SHARED SERVICE READY FOR CPU++"
                font.pixelSize: 9
                color: Colors.white
            }
        }
    }

    onPanelVisibleChanged: {
        if (panelVisible) {
            TimeSettings.refreshHostStatus();
            if (showTimezoneDetails)
                TimeSettings.loadZoneCatalog();
        } else {
            zonePickerExpanded = false;
        }
    }
}
