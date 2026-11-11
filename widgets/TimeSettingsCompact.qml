import QtQuick
import Quickshell
import qs.services.time
import "../components"

// Clock-only condensed view. The existing full TimeSettingsPane remains the
// CPU++ fallback; both views call the same TimeSettings singleton.
// The two primary pages have fixed geometry and no page Flickable.
Item {
    id: compact
    property string settingsSection: "visual"
    property string calibratedPreview: "--:--:--//--"
    property bool dock24Hour: false
    property bool dockFormatAvailable: false
    property bool zoneOpen: false
    readonly property bool zoneSearchFocused: compactZonePicker.searchFocused
    signal dockFormatRequested(bool use24)

    onSettingsSectionChanged: zoneOpen = false
    onVisibleChanged: {
        if (!visible)
            zoneOpen = false;
    }

    Column {
        id: visual
        visible: compact.settingsSection === "visual"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 3
        spacing: 5

        Row {
            width: parent.width
            height: 24
            spacing: 6
            GohuText {
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "OFFSET // " + TimeSettings.displayOffsetLabel
                font.pixelSize: 11
                color: TimeSettings.displayOffsetMs === 0 ? Colors.white : Colors.orange
                elide: Text.ElideRight
            }
            GohuText {
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "PREVIEW // " + compact.calibratedPreview
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
            }
        }
        Row {
            width: parent.width
            height: 32
            spacing: 6
            GohuText {
                width: Math.max(0, parent.width - 140 - 2 * parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "DOCK // FORMAT"
                color: Colors.cyan
                font.pixelSize: 11
            }
            TimeActionButton {
                width: 70
                height: 31
                actionRole: "time"
                label: "12H"
                labelPixelSize: 11
                selected: !compact.dock24Hour
                available: compact.dockFormatAvailable
                idleForegroundColor: Colors.cyan
                hoverForegroundColor: Colors.cyan
                selectedForegroundColor: Colors.cyan
                idleBorderColor: Colors.cyan
                hoverBorderColor: Colors.cyan
                selectedBorderColor: Colors.cyan
                idleContentGlowColor: Colors.cyan
                selectedContentGlowColor: Colors.cyan
                idleSoftGlowColor: Colors.cyan
                selectedSoftGlowColor: Colors.cyan
                onLeftClicked: compact.dockFormatRequested(false)
            }
            TimeActionButton {
                width: 70
                height: 31
                actionRole: "time"
                label: "24H"
                labelPixelSize: 11
                selected: compact.dock24Hour
                available: compact.dockFormatAvailable
                idleForegroundColor: Colors.orange
                hoverForegroundColor: Colors.orange
                selectedForegroundColor: Colors.orange
                idleBorderColor: Colors.orange
                hoverBorderColor: Colors.orange
                selectedBorderColor: Colors.orange
                idleContentGlowColor: Colors.orange
                selectedContentGlowColor: Colors.orange
                idleSoftGlowColor: Colors.orange
                selectedSoftGlowColor: Colors.orange
                onLeftClicked: compact.dockFormatRequested(true)
            }
        }
        Row {
            id: offsetControls
            width: parent.width
            height: 31
            spacing: 4
            Repeater {
                model: [
                    { label: "-1M", delta: -60000 },
                    { label: "-1S", delta: -1000 },
                    { label: "RESET", reset: true },
                    { label: "+1S", delta: 1000 },
                    { label: "+1M", delta: 60000 }
                ]
                TimeActionButton {
                    required property var modelData
                    actionRole: modelData.reset ? "cancel" : "time"
                    width: (offsetControls.width - 4 * offsetControls.spacing) / 5
                    height: 30
                    label: modelData.label
                    labelPixelSize: 10
                    contentPadding: 2
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
            height: 15
            text: "DISPLAY STORE // " + TimeSettings.storageState.toUpperCase()
                  + (TimeSettings.errorCode ? " // " + TimeSettings.errorCode : "")
            color: TimeSettings.errorCode ? Colors.orange : Colors.white
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
        Row {
            width: parent.width
            height: 28
            spacing: 6
            GohuText {
                width: Math.max(0, parent.width - 79 - parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "HOST // TIMEZONE + DST"
                color: Colors.cyan
                font.pixelSize: 11
            }
            TimeActionButton {
                width: 79
                height: 27
                label: "REFRESH"
                actionRole: "sync"
                labelPixelSize: 10
                available: !TimeSettings.hostRefreshing
                onLeftClicked: TimeSettings.refreshHostStatus()
            }
        }
        Row {
            id: compactPresets
            width: parent.width
            height: 29
            spacing: 5
            Repeater {
                model: [
                    { label: "UTC", zone: "UTC" },
                    { label: "NYC", zone: "America/New_York" },
                    { label: "LON", zone: "Europe/London" },
                    { label: "TOK", zone: "Asia/Tokyo" }
                ]
                TimeActionButton {
                    required property var modelData
                    width: (compactPresets.width - 3 * compactPresets.spacing) / 4
                    height: 28
                    label: modelData.label
                    labelPixelSize: 10
                    selected: TimeSettings.timezoneConfirmRequired
                              ? TimeSettings.zoneChoice === modelData.zone
                              : TimeSettings.hostInfo.timezone === modelData.zone
                    available: !TimeSettings.authSessionActive
                    onLeftClicked: {
                        compact.zoneOpen = false;
                        TimeSettings.prepareTimezone(modelData.zone);
                    }
                }
            }
        }
        // Search results float above the lower status rows rather than growing
        // the page. The popup keeps its own internal ListView for long catalogs.
        Item {
            id: compactZoneHost
            width: parent.width
            height: 34
            z: 30
            TimeZonePicker {
                id: compactZonePicker
                width: parent.width
                height: 34
                expanded: compact.zoneOpen
                selectedZone: TimeSettings.zoneChoice !== ""
                              ? TimeSettings.zoneChoice
                              : String(TimeSettings.hostInfo.timezone || "UTC")
                openSelectedZone: true
                zoneAccentColor: Colors.white
                catalog: TimeSettings.zoneCatalog
                countryIndex: TimeSettings.zoneCountryIndex
                catalogLoading: TimeSettings.zoneCatalogLoading
                catalogFailed: TimeSettings.zoneCatalogFailed
                onOpenRequested: {
                    TimeSettings.loadZoneCatalog();
                    compact.zoneOpen = true;
                }
                onToggleRequested: {
                    if (!compact.zoneOpen)
                        TimeSettings.loadZoneCatalog();
                    compact.zoneOpen = !compact.zoneOpen;
                }
                onZoneChosen: function(zoneId) {
                    compact.zoneOpen = false;
                    TimeSettings.prepareTimezone(zoneId);
                }
            }
        }
        Row {
            width: parent.width
            height: TimeSettings.timezoneConfirmRequired ? 31 : 0
            visible: TimeSettings.timezoneConfirmRequired
            spacing: 5
            TimeActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 30
                label: "APPLY ZONE"
                labelPixelSize: 10
                onLeftClicked: TimeSettings.requestTimezone()
            }
            TimeActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 30
                actionRole: "cancel"
                label: "CANCEL"
                labelPixelSize: 10
                onLeftClicked: TimeSettings.cancelTimezone()
            }
        }
        GohuText {
            width: parent.width
            height: 18
            font.pixelSize: 10
            text: "ZONE // " + String(TimeSettings.hostInfo.timezone || "UNKNOWN")
                  + " // " + String(TimeSettings.hostInfo.utcOffset || "UNKNOWN")
            color: Colors.white
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 18
            font.pixelSize: 10
            text: "DST // " + (TimeSettings.hostInfo.status !== "ready" ? "UNKNOWN"
                   : TimeSettings.hostInfo.dstActive ? "ACTIVE" : "INACTIVE")
                  + " // ZONE // " + TimeSettings.timezoneStatus.toUpperCase()
            color: Colors.orange
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 20
            font.pixelSize: 10
            text: "RESULT // " + (TimeSettings.timezoneErrorCode
                  ? TimeSettings.timezoneErrorCode : TimeSettings.timezoneMessage)
            color: TimeSettings.timezoneErrorCode ? Colors.orange : Colors.cyan
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 29
            wrapMode: Text.WordWrap
            text: "OFFSET IS DISPLAY-ONLY. APPLY ZONE CHANGES SYSTEM LOCAL TIME WITH CONFIRMATION; UTC INSTANT STAYS THE SAME."
            font.pixelSize: 9
            color: Colors.white
        }
    }

    Column {
        id: sync
        visible: compact.settingsSection === "sync"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 3
        spacing: 5
        GohuText {
            width: parent.width
            height: 16
            text: "NTP // " + String(TimeSettings.hostInfo.ntpEnabled || "UNKNOWN").toUpperCase()
                  + " // SYNC // "
                  + String(TimeSettings.hostInfo.ntpSynchronized || "UNKNOWN").toUpperCase()
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 17
            text: "AUTO // REFERENCE CHECK INTERVAL"
            font.pixelSize: 11
            color: Colors.cyan
        }
        Row {
            width: parent.width
            height: 169
            spacing: 6
            SelectorDial {
                id: syncIntervalDial
                width: 136
                height: 160
                labelText: "INTERVAL"
                selectorMode: "continuous"
                minimumValue: 1
                maximumValue: 168
                valueStep: 1
                valueDecimals: 0
                snapContinuousToStep: true
                numericDetentInterval: 6
                numericDetentOrigin: 0
                showNumericDetentTicks: true
                options: ["1H", "1D", "2D", "3D", "4D", "5D", "6D", "7D"]
                numericReferenceValues: [1, 24, 48, 72, 96, 120, 144, 168]
                currentValue: TimeSettings.autoCheckIntervalHours
                readoutText: Math.round(previewNumericValue) + "H"
                accentColor: Colors.cyan
                markerColor: Colors.orange
                interactive: TimeSettings.autoCheckCanEdit
                onValueRequested: function(hours) {
                    TimeSettings.setAutoCheckIntervalHours(Math.round(hours));
                }
            }
            Column {
                width: Math.max(0, parent.width - syncIntervalDial.width - parent.spacing)
                spacing: 7
                GohuText {
                    width: parent.width
                    height: 18
                    text: "EVERY // " + TimeSettings.autoCheckIntervalHours + " HOURS"
                    font.pixelSize: 11
                    color: Colors.yellow
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    height: 15
                    text: "MAX // 168H // 7 DAYS"
                    font.pixelSize: 9
                    color: Colors.white
                }
                Row {
                    width: parent.width
                    height: 34
                    spacing: 5
                    TimeActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 32
                        actionRole: "sync"
                        label: TimeSettings.autoCheckEnabled ? "AUTO ON" : "AUTO OFF"
                        selected: TimeSettings.autoCheckEnabled
                        labelPixelSize: 10
                        available: TimeSettings.autoCheckCanEdit
                        onLeftClicked: TimeSettings.setAutoCheckEnabled(!TimeSettings.autoCheckEnabled)
                    }
                    TimeActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 32
                        actionRole: "sync"
                        label: "⟳ RESYNC"
                        labelPixelSize: 10
                        available: TimeSettings.resyncStatus !== "working"
                                   && !TimeSettings.resyncAuthPending
                        onLeftClicked: TimeSettings.prepareResync()
                    }
                }
                Row {
                    width: parent.width
                    height: 34
                    spacing: 5
                    TimeActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 32
                        actionRole: "sync"
                        label: "DIAGNOSE"
                        labelPixelSize: 9
                        available: !TimeSettings.diagnosticBusy
                        onLeftClicked: TimeSettings.diagnoseResync()
                    }
                    TimeActionButton {
                        width: (parent.width - parent.spacing) / 2
                        height: 32
                        actionRole: "sync"
                        label: "CHECK TIME"
                        labelPixelSize: 9
                        available: !TimeSettings.referenceChecking
                                   && !TimeSettings.authSessionActive
                        onLeftClicked: TimeSettings.checkTimeAccuracy()
                    }
                }
                GohuText {
                    width: parent.width
                    height: 15
                    text: "6H STOPS // NO WRAP"
                    font.pixelSize: 9
                    color: Colors.cyan
                }
            }
        }
        Row {
            width: parent.width
            height: 18
            spacing: 6
            GohuText {
                width: (parent.width - parent.spacing) / 2
                height: 18
                text: "LAST // " + (TimeSettings.autoCheckLastAttemptAtMs > 0
                      ? Qt.formatDateTime(new Date(TimeSettings.autoCheckLastAttemptAtMs),
                                          "MM-dd HH:mm") : "NEVER")
                color: Colors.white
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            GohuText {
                width: (parent.width - parent.spacing) / 2
                height: 18
                text: "NEXT // " + (!TimeSettings.autoCheckEnabled ? "OFF"
                     : TimeSettings.autoCheckNextDueAtMs > 0
                     ? Qt.formatDateTime(new Date(TimeSettings.autoCheckNextDueAtMs),
                                         "MM-dd HH:mm") : "DUE")
                color: Colors.white
                font.pixelSize: 10
                elide: Text.ElideRight
            }
        }
        GohuText {
            width: parent.width
            height: 20
            text: "AUTO // " + TimeSettings.autoCheckResult
                  + (TimeSettings.autoCheckErrorCode
                     ? " // " + TimeSettings.autoCheckErrorCode : "")
            font.pixelSize: 10
            color: Colors.yellow
            elide: Text.ElideRight
        }
        Row {
            width: parent.width
            height: TimeSettings.resyncConfirmRequired ? 32 : 0
            visible: TimeSettings.resyncConfirmRequired
            spacing: 6
            TimeActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 31
                label: "CONFIRM RESYNC"
                actionRole: "sync"
                labelPixelSize: 10
                onLeftClicked: TimeSettings.requestResync()
            }
            TimeActionButton {
                width: (parent.width - parent.spacing) / 2
                height: 31
                label: "CANCEL"
                actionRole: "cancel"
                labelPixelSize: 10
                onLeftClicked: TimeSettings.cancelResync()
            }
        }
        GohuText {
            width: parent.width
            height: 20
            text: "RESYNC // " + TimeSettings.resyncMessage
            font.pixelSize: 10
            color: Colors.yellow
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 20
            text: "CHECK // " + TimeSettings.referenceStatus.toUpperCase()
                  + " // " + TimeSettings.referenceMessage
            font.pixelSize: 10
            color: Colors.cyan
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 20
            text: "DIAG // " + (TimeSettings.resyncErrorCode
                  ? TimeSettings.resyncErrorCode : TimeSettings.diagnosticMessage)
            font.pixelSize: 10
            color: TimeSettings.resyncErrorCode ? Colors.orange : Colors.white
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 29
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            color: Colors.orange
            text: TimeSettings.resyncConfirmRequired
                  ? "CONFIRMATION MAY CONTACT NTP SERVERS (IP VISIBLE) AND CHANGE LOG / FILE TIMES. POLKIT MAY PROMPT."
                  : "AUTOMATIC CHECK NEVER SETS HOST TIME. ONE-SHOT RESYNC REQUIRES CONFIRMATION / POLKIT."
        }
    }
}
