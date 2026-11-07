import QtQuick
import "../../components"

// C8 // COSMOS MOON uses the established MAGICK compact phase instrument.
// The original StationSky owns all USNO collectors and UTC/civil calculations.
// This changes presentation only. The full SKY report remains in INDEX.
Rectangle {
    id: moonPane
    objectName: "cosmos-c8-moon-fixed-pane"
    color: Colors.black
    clip: true

    property var weatherService: null
    property var spaceService: null
    property real runtimeNowMs: Date.now()
    signal routeRequested(string path)
    // Match COSMOS Overview/Modes: 6 px between stage boundary and content.
    readonly property int contentInset: 6
    readonly property var sourceSkyHost: sourceSky
    readonly property var phaseInstrument: moonVisual
    readonly property var moonSource: sourceSky.moonObservation
    readonly property var positionSource: sourceSky.celestialObservation
    readonly property bool moonReady: !!moonSource && moonSource.ready
        && !!moonSource.ephemeris && moonSource.ephemeris.available
    readonly property var moonEphemeris: moonReady ? moonSource.ephemeris : null
    readonly property bool hasNoRiseSet: moonEphemeris !== null
        && moonEphemeris !== undefined
        && moonEphemeris.noRiseSet === true
    readonly property var positionSnapshot: positionSource && positionSource.ready
        ? positionSource.snapshot : null
    readonly property var moonPosition: positionSnapshot ? positionSnapshot.moon : null

    function present(value) {
        if (value === null || value === undefined || String(value).trim() === "")
            return "--";
        return String(value);
    }
    function degrees(value) {
        return value === null || value === undefined
            || !isFinite(Number(value)) ? "--"
            : Number(value).toFixed(1) + "°";
    }
    readonly property string moonStatus: !moonSource || !moonSource.configured
        ? "UNAVAILABLE" : moonSource.loading ? "RECEIVING"
        : moonSource.failed ? "OFFLINE"
        : moonSource.ready ? "RECEIVED" : "WAITING"
    readonly property string positionStatus: !positionSource || !positionSource.configured
        ? "UNAVAILABLE" : positionSource.loading ? "RECEIVING"
        : positionSource.failed ? "OFFLINE"
        : positionSource.ready ? "RECEIVED" : "WAITING"
    readonly property var facts: [
        {label:"MOONRISE",value:moonReady ? present(moonEphemeris.rise) : "--"},
        {label:"UPPER TRANSIT",value:moonReady ? present(moonEphemeris.transit) : "--"},
        {label:"MOONSET",value:moonReady ? present(moonEphemeris.set) : "--"},
        {label:"VISIBILITY",value:positionSnapshot
            ? (moonPosition ? "ABOVE DISPLAY LIMIT" : "NOT IN USNO LIST") : "--"},
        {label:"ALTITUDE // HC",value:moonPosition
            ? degrees(moonPosition.altitude) : "--"},
        {label:"AZIMUTH // ZN",value:moonPosition
            ? degrees(moonPosition.azimuth) + " // " + present(moonPosition.direction)
            : "--"},
        {label:"SOURCE DATE",value:moonReady
            ? present(moonEphemeris.sourceDate) : "--"},
        {label:"CIVIL OFFSET",value:sourceSky.moonCivilOffsetMinutes === null
            || sourceSky.moonCivilOffsetMinutes === undefined
            ? "--" : sourceSky.moonCivilOffsetMinutes + " M"},
        {label:"OFFSET ORIGIN",value:present(sourceSky.moonCivilOffsetSource)}
    ]
    // Nine original data fields, now arranged by meaning and importance.
    // Three position instruments, three event readings, three provenance fields.
    readonly property int renderedFactCount: 9

    StationSky {
        id: sourceSky
        width: 1
        height: 1
        opacity: 0
        visible: moonPane.visible
        sourceOnly: true
        subjectRoute: "cosmos/moon/ephemeris"
        weatherService: moonPane.weatherService
        spaceService: moonPane.spaceService
        runtimeNowMs: moonPane.runtimeNowMs
    }

    // C18 // MOON adopts the same top-spanning mode rail as COSMOS SUN.
    Row {
        id: titleRail
        objectName: "cosmos-c9-moon-free-header"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        anchors.topMargin: moonPane.contentInset
        height: 16
        spacing: 4
        GohuText {
            id: moonHeading
            width: Math.min(155,Math.max(1,titleRail.width*0.38))
            height: parent.height
            text: "LUNAR // OBSERVATION"
            color: Colors.magenta
            font.pixelSize: 10
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        QuietText {
            width: Math.max(1,titleRail.width-moonHeading.width-titleRail.spacing)
            height: parent.height
            text: "USNO "+moonPane.moonStatus+" // SKY "+moonPane.positionStatus
            color: moonPane.moonStatus==="OFFLINE" || moonPane.positionStatus==="OFFLINE"
                ? Colors.orange : Colors.cyan
            font.pixelSize: 8
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }
    }

    Row {
        id: moonModeRail
        objectName: "cosmos-c18-moon-fullwidth-mode-rail"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: titleRail.bottom
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        anchors.topMargin: 2
        height: 27
        spacing: 4
        ActionButton {
            objectName: "cosmos-c18-moon-observation-tab"
            width: Math.max(1,(moonModeRail.width-2*moonModeRail.spacing)/3)
            height: 27
            label: "PHASE + POSITION"
            labelPixelSize: 9
            contentPadding: 1
            selected: true
            accentColor: Colors.magenta
        }
        ActionButton {
            id: moonYearButton
            objectName: "cosmos-c11-open-moon-year"
            width: Math.max(1,(moonModeRail.width-2*moonModeRail.spacing)/3)
            height: 27
            label: "LUNAR WHEEL"
            labelPixelSize: 9
            contentPadding: 1
            accentColor: Colors.cyan
            onClicked: moonPane.routeRequested("cosmos/moon/year")
        }
        ActionButton {
            id: moonForecastButton
            objectName: "cosmos-c17-open-moon-forecast"
            width: Math.max(1,(moonModeRail.width-2*moonModeRail.spacing)/3)
            height: 27
            label: "FORECAST"
            labelPixelSize: 9
            contentPadding: 1
            accentColor: Colors.cyan
            onClicked: moonPane.routeRequested("cosmos/moon/forecast")
        }
    }

    Row {
        id: heroRow
        objectName: "cosmos-c9-moon-hero-row"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        anchors.top: moonModeRail.bottom
        // Keep the nine source-backed Moon readings within compact viewport.
        height: Math.min(166,Math.max(0,moonPane.height-138))
        spacing: 5

        // Identical interactive MAGICK phase instrument, not a duplicated canvas.
        // Keeping its compact height preserves eight phase selectors and CURRENT.
        StationCosmosVisualInstruments {
            id: moonVisual
            objectName: "cosmos-c8-moon-phase"
            width: Math.max(1,Math.round((heroRow.width-heroRow.spacing)*0.62))
            height: heroRow.height
            compactMode: true
            showMoon: true
            showSun: false
            moonReady: moonPane.moonReady
            moonEphemeris: moonPane.moonEphemeris
            astronomySummary: sourceSky.astronomySummary
            twilightSummary: sourceSky.twilightSummary
            currentSolarPosition: sourceSky.currentSolarPosition
            providerLocalMinute: sourceSky.providerLocalMinute
            latitude: moonPane.weatherService ? moonPane.weatherService.latitude : ""
            longitude: moonPane.weatherService ? moonPane.weatherService.longitude : ""
            solarDate: sourceSky.astronomySummary.date
            solarCivilOffsetMinutes: sourceSky.moonCivilOffsetMinutes
            solarOffsetSource: sourceSky.moonCivilOffsetSource
        }

        // Asymmetric vertical current-sky instrument beside the phase artwork.
        Rectangle {
            id: positionColumn
            objectName: "cosmos-c9-moon-tall-position"
            width: Math.max(1,heroRow.width-moonVisual.width-heroRow.spacing)
            height: heroRow.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 3
                QuietText {
                    width: parent.width
                    height: 12
                    text: "CURRENT SKY // POSITION"
                    color: Colors.cyan
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
                Rectangle {
                    objectName: "cosmos-c8-moon-fact"
                    width: parent.width
                    height: Math.max(20,(positionColumn.height-29)*0.37)
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 1
                        QuietText {
                            width: parent.width
                            text: moonPane.facts[4].label
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: moonPane.facts[4].value
                            font.pixelSize: 20
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
                Rectangle {
                    objectName: "cosmos-c8-moon-fact"
                    width: parent.width
                    height: Math.max(19,(positionColumn.height-29)*0.30)
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2
                        QuietText {
                            width: parent.width
                            text: moonPane.facts[5].label
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: moonPane.facts[5].value
                            font.pixelSize: 11
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
                Rectangle {
                    objectName: "cosmos-c8-moon-fact"
                    width: parent.width
                    height: Math.max(18,positionColumn.height-29
                        -Math.max(20,(positionColumn.height-29)*0.37)
                        -Math.max(19,(positionColumn.height-29)*0.30)-6)
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 1
                        QuietText {
                            width: parent.width
                            text: moonPane.facts[3].label
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: moonPane.facts[3].value
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    // One continuous event ribbon, with a brighter transit reading instead of
    // three identical cards. The dividers replace three enclosing borders.
    Rectangle {
        id: compactReadings
        objectName: "cosmos-c8-moon-readings"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        anchors.top: heroRow.bottom
        anchors.topMargin: 4
        anchors.bottom: parent.bottom
        anchors.bottomMargin: moonPane.contentInset
        color: Colors.black
        border.width: 0
        clip: true

        Rectangle {
            id: eventRibbon
            objectName: "cosmos-c9-moon-event-ribbon"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: Math.min(51,Math.max(1,compactReadings.height-39))
            color: Colors.dark
            border.width: 1
            border.color: Colors.yellow
            Row {
                id: eventRow
                anchors.fill: parent
                anchors.margins: 3
                spacing: 0
                Repeater {
                    model: 3
                    delegate: Item {
                        objectName: "cosmos-c8-moon-fact"
                        required property int index
                        readonly property var eventData: moonPane.facts[index]
                        width: index===1 ? eventRow.width*0.36
                                         : eventRow.width*0.32
                        height: eventRow.height
                        Rectangle {
                            visible: index>0
                            width: 1
                            height: parent.height-4
                            anchors.verticalCenter: parent.verticalCenter
                            color: Colors.cyan
                            opacity: 0.58
                        }
                        Column {
                            anchors.fill: parent
                            anchors.leftMargin: 7
                            anchors.topMargin: 3
                            spacing: 3
                            QuietText {
                                width: parent.width
                                text: eventData ? eventData.label : "--"
                                font.pixelSize: 8
                                color: index===1 ? Colors.yellow : Colors.cyan
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                text: eventData ? eventData.value : "--"
                                font.pixelSize: index===1 ? 15 : 12
                                color: index===1 ? Colors.yellow : Colors.white
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        // Source details are deliberately unboxed: small provenance annotations
        // beneath the event group, retaining the original three values.
        Row {
            id: provenanceRow
            objectName: "cosmos-c9-moon-free-provenance"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: eventRibbon.bottom
            anchors.topMargin: 2
            height: Math.max(1,compactReadings.height-eventRibbon.height-16)
            spacing: 4
            Repeater {
                model: 3
                delegate: Item {
                    objectName: "cosmos-c8-moon-fact"
                    required property int index
                    readonly property var sourceData: moonPane.facts[index+6]
                    width: Math.max(1,(provenanceRow.width-8)/3)
                    height: provenanceRow.height
                    Column {
                        anchors.fill: parent
                        spacing: 0
                        QuietText {
                            width: parent.width
                            text: sourceData ? sourceData.label : "--"
                            font.pixelSize: 8
                            color: Colors.orange
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: sourceData ? sourceData.value : "--"
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        QuietText {
            id: sourceNote
            objectName: "cosmos-c8-moon-source-note"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 12
            font.pixelSize: 8
            color: moonSource && moonSource.failed ? Colors.orange : Colors.yellow
            elide: Text.ElideRight
            text: moonPane.hasNoRiseSet
                ? "USNO // NO RISE OR SET FOR THIS CIVIL DATE // NO EVENT INVENTED"
                : moonSource && moonSource.failed
                  ? moonPane.present(moonSource.errorText)
                  : positionSource && positionSource.failed
                    ? moonPane.present(positionSource.errorText)
                    : !moonSource || !moonSource.configured
                      ? sourceSky.moonInputIssue()
                      : positionSnapshot
                        ? "FIX "+moonPane.present(positionSnapshot.date)
                          +" "+moonPane.present(positionSnapshot.time)
                          +" UTC // HC DISPLAY LIMIT > -3°"
                        : "USNO DATE-SCOPED RISE/SET/TRANSIT // POSITION WAITING"
        }
    }
}
