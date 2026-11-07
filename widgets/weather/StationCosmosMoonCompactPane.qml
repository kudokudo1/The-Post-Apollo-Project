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

    // C19 // The detailed forecast remains in INDEX, not in the main rail.
    // The current daily forecast now shares OVERVIEW with lunar observations.
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
            width: Math.max(1,(moonModeRail.width-moonModeRail.spacing)/2)
            height: 27
            label: "OVERVIEW"
            labelPixelSize: 10
            contentPadding: 1
            selected: true
            accentColor: Colors.magenta
        }
        ActionButton {
            id: moonYearButton
            objectName: "cosmos-c11-open-moon-year"
            width: Math.max(1,(moonModeRail.width-moonModeRail.spacing)/2)
            height: 27
            label: "LUNAR YEAR"
            labelPixelSize: 10
            contentPadding: 1
            accentColor: Colors.cyan
            onClicked: moonPane.routeRequested("cosmos/moon/year")
        }
    }

    // C23 // Restore the two-pixel cyan header divider used by COSMOS SUN.
    // The 2px gap protects compact Moon disk and telemetry dimensions.
    Rectangle {
        id: moonHeaderDivider
        objectName: "cosmos-c23-moon-overview-divider"
        anchors.top: moonModeRail.bottom
        // Match SUN's five-pixel tab-to-rule breathing room.
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        height: 2
        color: Colors.cyan
    }

    // C20 // Instrument-first asymmetric board:
    // large MAGICK-derived Moon visual left; seven actual daily observations
    // and the USNO event ledger right. There is no dead provenance spacer.
    Row {
        id: heroRow
        objectName: "cosmos-c9-moon-hero-row"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: moonHeaderDivider.bottom
        // Keep the first instrument off the cyan rule.
        anchors.topMargin: 3
        anchors.bottom: parent.bottom
        anchors.leftMargin: moonPane.contentInset
        anchors.rightMargin: moonPane.contentInset
        anchors.bottomMargin: moonPane.contentInset
        spacing: 6

        Column {
            id: moonMain
            objectName: "cosmos-c20-moon-primary-instruments"
            // Moon-first: give the primary instrument 65% of the stage.
            // Right-side forecast logic and rendering remain unchanged.
            width: Math.max(1,Math.round((heroRow.width-heroRow.spacing)*0.65))
            height: heroRow.height
            spacing: 4

            // One large interactive MAGICK phase instrument; no copied canvas.
            StationCosmosVisualInstruments {
                id: moonVisual
                objectName: "cosmos-c8-moon-phase"
                width: moonMain.width
                // Restore C20's balanced lower boxes, keeping C21's
                // prominent Moon drawing and wider left column.
                height: Math.max(90,Math.round(
                    (moonMain.height-2*moonMain.spacing)*0.62))
                compactMode: true
                prominentMoon: true
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

            // Current position facts are a short telemetry rack, not three
            // equally important tall rectangles competing with the Moon image.
            Rectangle {
                id: positionColumn
                objectName: "cosmos-c9-moon-tall-position"
                width: moonMain.width
                height: Math.max(41,Math.round(
                    (moonMain.height-2*moonMain.spacing)*0.23))
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                clip: true

                QuietText {
                    id: currentSkyTitle
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 2
                    height: 11
                    text: "CURRENT SKY // POSITION"
                    color: Colors.cyan
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
                Row {
                    id: currentSkyFacts
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: currentSkyTitle.bottom
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 3
                    anchors.rightMargin: 3
                    anchors.bottomMargin: 2
                    spacing: 3
                    Repeater {
                        model: [4,5,3]
                        delegate: Column {
                            objectName: "cosmos-c8-moon-fact"
                            required property var modelData
                            readonly property var info: moonPane.facts[modelData]
                            width: Math.max(1,(currentSkyFacts.width-6)/3)
                            height: currentSkyFacts.height
                            spacing: 1
                            QuietText {
                                width: parent.width
                                height: 10
                                text: info ? info.label : "--"
                                color: Colors.cyan
                                font.pixelSize: 8
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                height: Math.max(1,currentSkyFacts.height-11)
                                text: info ? info.value : "--"
                                font.pixelSize: 10
                                color: modelData===4 ? Colors.yellow : Colors.white
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            // Provenance gets a deliberately shallow footnote shelf instead
            // of a tall empty area. The original three fields remain present.
            Row {
                id: provenanceRow
                objectName: "cosmos-c9-moon-free-provenance"
                width: moonMain.width
                // Match C20's original provenance height beneath the restored
                // current-position box, retaining all three source values.
                height: Math.max(1,moonMain.height-moonVisual.height
                    -positionColumn.height-2*moonMain.spacing)
                spacing: 3
                Repeater {
                    model: 3
                    delegate: Column {
                        objectName: "cosmos-c8-moon-fact"
                        required property int index
                        readonly property var sourceData: moonPane.facts[index+6]
                        width: Math.max(1,(provenanceRow.width-6)/3)
                        height: provenanceRow.height
                        spacing: 1
                        QuietText {
                            width: parent.width
                            height: 10
                            text: sourceData ? sourceData.label : "--"
                            color: Colors.orange
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: Math.max(1,provenanceRow.height-11)
                            text: sourceData ? sourceData.value : "--"
                            color: Colors.white
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Column {
            id: compactReadings
            objectName: "cosmos-c8-moon-readings"
            width: Math.max(1,heroRow.width-moonMain.width-heroRow.spacing)
            height: heroRow.height
            spacing: 4

            // Seven horizontal rows give dates, illumination and daylight
            // their own measured graphic instead of equal-sized empty cards.
            StationCosmosMoonForecastStrip {
                id: moonForecastStrip
                objectName: "cosmos-c19-moon-forecast-strip"
                width: compactReadings.width
                height: Math.max(94,Math.round(
                    (compactReadings.height-2*compactReadings.spacing)*0.65))
                verticalMode: true
                weatherService: moonPane.weatherService
            }

            Rectangle {
                id: eventRibbon
                objectName: "cosmos-c9-moon-event-ribbon"
                width: compactReadings.width
                height: Math.max(51,Math.round(
                    (compactReadings.height-2*compactReadings.spacing)*0.29))
                color: Colors.dark
                border.width: 1
                border.color: Colors.yellow
                clip: true
                Column {
                    id: eventRow
                    objectName: "cosmos-c20-moon-event-ledger"
                    anchors.fill: parent
                    anchors.margins: 2
                    spacing: 1
                    Repeater {
                        model: 3
                        delegate: Row {
                            objectName: "cosmos-c8-moon-fact"
                            required property int index
                            readonly property var eventData: moonPane.facts[index]
                            width: eventRow.width
                            height: Math.max(1,(eventRow.height-2*eventRow.spacing)/3)
                            spacing: 3
                            QuietText {
                                width: Math.max(1,parent.width*0.53)
                                height: parent.height
                                text: eventData ? eventData.label : "--"
                                font.pixelSize: 8
                                color: index===1 ? Colors.yellow : Colors.cyan
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: Math.max(1,parent.width*0.47-3)
                                height: parent.height
                                text: eventData ? eventData.value : "--"
                                font.pixelSize: 10
                                color: index===1 ? Colors.yellow : Colors.white
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            QuietText {
                id: sourceNote
                objectName: "cosmos-c8-moon-source-note"
                width: compactReadings.width
                height: Math.max(1,compactReadings.height
                    -moonForecastStrip.height-eventRibbon.height
                    -2*compactReadings.spacing)
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

}
