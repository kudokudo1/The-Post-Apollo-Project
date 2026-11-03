import QtQuick
import "../../components"
import "StationToolsSubjectPanelPolicy.js" as ToolsPolicy
import "StationSourceHealthPolicy.js" as SourceHealth
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

// TOOLS T1 projects source/store state from existing owners. No polling,
// storage writers, file access, or new Kitty/Sway actor is created here.
Rectangle {
    id: toolsPane
    color: Colors.black

    property string subjectRoute: ""
    property var weatherService: null
    property var spaceService: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null
    property real runtimeNowMs: 0

    // Only a request. The root StationTerminal remains the sole Kitty/Sway
    // owner, including window identity, geometry, launch and exact close.
    signal terminalLaunchRequested(string mode)
    property string selectedConsoleMode: "home"

    readonly property string kind:
        ToolsPolicy.kindForRoute(subjectRoute)
    readonly property var healthRows:
        SourceHealth.buildCoreSources(
            ToolsPolicy.sourceInput(weatherService,spaceService,runtimeNowMs))
    readonly property var sourceCatalog: RuntimePolicy.sourceCatalog()
    readonly property var frameRows: ToolsPolicy.frameSources(sourceCatalog)
    readonly property var allStorageRows:
        ToolsPolicy.storageRows(persistentCacheStore,liveHistoryStore,
                                eventArchiveStore,dossierArchiveStore,runtimeNowMs)
    readonly property var visibleStorageRows:
        ToolsPolicy.storageRowsFor(subjectRoute,allStorageRows)
    readonly property string terminalTarget:
        ToolsPolicy.terminalModeForRoute(subjectRoute,selectedConsoleMode)

    function accentColor(token) {
        switch (String(token||"")) {
        case "magenta": return Colors.magenta;
        case "cyan": return Colors.cyan;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "red": return Colors.red;
        case "green": return Colors.green;
        default: return Colors.white;
        }
    }

    Flickable {
        id: toolsScroll
        anchors.fill: parent
        anchors.rightMargin: 17
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: toolsContent.implicitHeight + 20

        Column {
            id: toolsContent
            x: 15
            y: 9
            width: Math.max(0,toolsScroll.width - 29)
            spacing: 10

            GohuText {
                width: parent.width
                text: ToolsPolicy.titleFor(toolsPane.subjectRoute)
                font.pixelSize: 20
                color: Colors.magenta
                elide: Text.ElideRight
            }

            QuietText {
                width: parent.width
                text: "READ-ONLY CONTROL PLANE // ORIGINAL SOURCE, STORAGE AND KITTY OWNERS"
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }

            Column {
                width: parent.width
                spacing: 9
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"terminal")

                StationSectionDivider {
                    width: parent.width
                    title: "TERMINAL // STATION KITTY SESSION"
                }

                QuietText {
                    width: parent.width
                    text: toolsPane.terminalTarget === ""
                          ? "SELECT STAR MAP OR CONSOLES FROM THE TERMINAL SUBMODES."
                          : ToolsPolicy.terminalInstructions(toolsPane.subjectRoute)
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.yellow
                }

                Flow {
                    width: parent.width
                    spacing: 6
                    visible: toolsPane.subjectRoute === "tools/terminal/consoles"
                    Repeater {
                        model: ToolsPolicy.CONSOLE_MODES
                        delegate: ModeButton {
                            required property string modelData
                            width: Math.max(75,Math.min(101,(toolsContent.width - 42)/7))
                            height: 31
                            textOnly: true
                            bordered: false
                            selected: toolsPane.selectedConsoleMode === modelData
                            labelText: modelData.toUpperCase()
                            labelFontSize: 10
                            onTriggered: toolsPane.selectedConsoleMode = modelData
                        }
                    }
                }

                ActionButton {
                    width: Math.min(350,parent.width)
                    height: 36
                    label: toolsPane.terminalTarget === ""
                           ? "NO TERMINAL TARGET"
                           : ToolsPolicy.titleForTerminalAction(toolsPane.subjectRoute)
                             + (toolsPane.subjectRoute === "tools/terminal/consoles"
                                ? " // " + toolsPane.selectedConsoleMode.toUpperCase()
                                : "")
                    labelPixelSize: 11
                    available: toolsPane.terminalTarget !== ""
                    accentColor: Colors.cyan
                    onClicked: {
                        if (toolsPane.terminalTarget !== "")
                            toolsPane.terminalLaunchRequested(toolsPane.terminalTarget);
                    }
                }

                QuietText {
                    width: parent.width
                    text: "THE EXISTING STATION TERMINAL CONTROLS THE WAYLAND APP-ID, BAY CUTOUT, VERIFIED WINDOW GEOMETRY AND EXACT CLOSE. LAUNCH USES THAT ONE CONTROLLER; THE HEADER CLOSE BUTTON RETURNS HERE."
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"health")

                StationSectionDivider {
                    width: parent.width
                    title: "SOURCES // SIX SHARED LIVE PRODUCTS"
                }

                QuietText {
                    width: parent.width
                    text: "RECEIPT AGE IS NOT NECESSARILY PROVIDER SAMPLE AGE. STALE NOAA SAMPLES REMAIN IDENTIFIED EVEN IF RECEIVED RECENTLY."
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                }

                Repeater {
                    model: toolsPane.healthRows
                    delegate: Column {
                        required property var modelData
                        width: toolsContent.width
                        spacing: 3

                        Row {
                            width: parent.width
                            spacing: 8

                            GohuText {
                                width: Math.min(215,Math.max(120,parent.width * 0.40))
                                text: modelData.title
                                color: Colors.white
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: Math.max(0,parent.width - 225)
                                text: modelData.state
                                color: toolsPane.accentColor(modelData.accent)
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.provider + " // " + modelData.detail
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.footer
                            font.pixelSize: 9
                            color: Colors.cyan
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.30
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"provenance")

                StationSectionDivider {
                    width: parent.width
                    title: "PROVENANCE // DECLARED SOURCE CONTRACTS"
                }

                QuietText {
                    width: parent.width
                    text: "CATALOG ENTRIES " + toolsPane.sourceCatalog.length
                          + " // THESE ARE SOURCE/VIEW SPECS, NOT A COUNT OF DISTINCT POLLERS OR LIVE ONLINE FEEDS."
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                    font.pixelSize: 10
                }

                Repeater {
                    model: toolsPane.sourceCatalog
                    delegate: Column {
                        required property var modelData
                        width: toolsContent.width
                        spacing: 3

                        GohuText {
                            width: parent.width
                            text: modelData.label
                            font.pixelSize: 11
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        QuietText {
                            width: parent.width
                            font.pixelSize: 10
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                            text: "OWNER " + modelData.owner
                                  + " // " + modelData.mode
                                  + " // " + RuntimePolicy.cadenceLabel(modelData)
                                  + " // " + RuntimePolicy.retentionLabel(modelData)
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.note || "NO ADDITIONAL CONTRACT NOTE"
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.25
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"storage")

                StationSectionDivider {
                    width: parent.width
                    title: "STORAGE // ORIGINAL OWNER READBACK"
                }

                QuietText {
                    width: parent.width
                    text: "STATUS AND COUNTS ARE READ FROM THE EXISTING STORES. THIS PAGE DOES NOT SAVE, DELETE, MIGRATE, REFRESH OR ALTER THEIR FILES."
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                    font.pixelSize: 10
                }

                Repeater {
                    model: toolsPane.visibleStorageRows
                    delegate: Column {
                        required property var modelData
                        width: toolsContent.width
                        spacing: 4

                        GohuText {
                            width: parent.width
                            text: modelData.title
                            font.pixelSize: 12
                            color: Colors.white
                        }

                        GohuText {
                            width: parent.width
                            font.pixelSize: 11
                            color: modelData.state === "READY"
                                   ? Colors.green : modelData.state === "ERROR"
                                     || modelData.state === "UNSUPPORTED"
                                     ? Colors.red : Colors.yellow
                            text: "STATE " + modelData.state
                                  + " // REV " + modelData.revision
                                  + (modelData.count >= 0
                                     ? " // RECORDS OR SERIES " + modelData.count
                                     : "")
                            elide: Text.ElideRight
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.detail
                                  + (modelData.error !== ""
                                     ? " // ERROR " + modelData.error : "")
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.3
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"frames")

                StationSectionDivider {
                    width: parent.width
                    title: "FRAME CACHE // CONTRACT, NOT ARCHIVE"
                }

                QuietText {
                    width: parent.width
                    text: "FRAME PRODUCTS " + toolsPane.frameRows.length
                          + " // THE RUNTIME CATALOG DESCRIBES TEMPORARY FRAMES. NO SEPARATE PERSISTENT FRAME ARCHIVE STORE IS CONNECTED TO THIS VIEW."
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                }

                Repeater {
                    model: toolsPane.frameRows
                    delegate: Column {
                        required property var modelData
                        width: toolsContent.width
                        spacing: 3

                        GohuText {
                            width: parent.width
                            text: modelData.label
                            font.pixelSize: 11
                            color: Colors.white
                        }

                        QuietText {
                            width: parent.width
                            font.pixelSize: 10
                            color: Colors.cyan
                            wrapMode: Text.WordWrap
                            text: "OWNER " + modelData.owner
                                  + " // " + RuntimePolicy.retentionLabel(modelData)
                                  + " // " + RuntimePolicy.cadenceLabel(modelData)
                        }

                        QuietText {
                            width: parent.width
                            font.pixelSize: 9
                            text: modelData.note
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"location")

                StationSectionDivider {
                    width: parent.width
                    title: "LOCATION // PROVIDER CONTEXT"
                }

                GohuText {
                    width: parent.width
                    text: ToolsPolicy.locationLabel(toolsPane.weatherService)
                    font.pixelSize: 13
                    color: Colors.cyan
                }

                QuietText {
                    width: parent.width
                    text: "TIMEZONE // " + ToolsPolicy.timezoneLabel(toolsPane.weatherService)
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                QuietText {
                    width: parent.width
                    text: "THE COORDINATES ABOVE ARE FROM THE CURRENT WEATHER RESPONSE, ROUNDED FOR DISPLAY. THEY ARE NOT YOUR DEVICE GPS FIX OR A USER-EDITED SAVED LOCATION. OFFICIAL NWS ALERT-POINT IDENTITY REMAINS SEPARATE."
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                }
            }

            Column {
                width: parent.width
                spacing: 8
                visible: ToolsPolicy.shows(toolsPane.subjectRoute,"display")

                StationSectionDivider {
                    width: parent.width
                    title: "DISPLAY // CURRENT WEATHER CONVENTIONS"
                }

                QuietText {
                    width: parent.width
                    text: "TEMPERATURE // FAHRENHEIT     WIND // MPH     AIR QUALITY // US AQI"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    color: Colors.cyan
                }

                QuietText {
                    width: parent.width
                    text: "PRESSURE // HPA     NOAA SOLAR WIND // KM/S     MAGNETIC FIELD // NT"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                QuietText {
                    width: parent.width
                    text: "READ-ONLY INVENTORY. THERE IS NO UNIFIED UNITS, TIMEZONE OR DISPLAY-PREFERENCE WRITER CONNECTED HERE. DO NOT TREAT THESE VALUES AS EDITABLE SETTINGS."
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    color: Colors.yellow
                }
            }

            QuietText {
                width: parent.width
                font.pixelSize: 9
                color: Colors.magenta
                text: "TOOLS T1 // READ-ONLY // NO DUPLICATE POLLERS, ARCHIVE WRITERS OR KITTY ACTORS"
                wrapMode: Text.WordWrap
            }
        }
    }

    NeonScrollBar {
        flickable: toolsScroll
        geometryMode: "viewport"
        handleStyle: "star"
        visible: toolsPane.visible
                 && toolsScroll.contentHeight > toolsScroll.height + 1
    }
}
