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
    readonly property var sourceSkyHost: sourceSky
    readonly property var phaseInstrument: moonVisual
    readonly property var moonSource: sourceSky.moonObservation
    readonly property var positionSource: sourceSky.celestialObservation
    readonly property bool moonReady: !!moonSource && moonSource.ready
        && !!moonSource.ephemeris && moonSource.ephemeris.available
    readonly property var moonEphemeris: moonReady ? moonSource.ephemeris : null
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
    readonly property int renderedFactCount: moonFactRepeater.count

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

    StationCosmosVisualInstruments {
        id: moonVisual
        objectName: "cosmos-c8-moon-phase"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.min(166,Math.max(0,moonPane.height-109))
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

    Rectangle {
        id: compactReadings
        objectName: "cosmos-c8-moon-readings"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: moonVisual.bottom
        anchors.topMargin: 3
        anchors.bottom: parent.bottom
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        clip: true

        GohuText {
            id: readingsTitle
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 3
            height: 12
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
            text: "MOON // USNO " + moonPane.moonStatus
                + " // CURRENT POSITION " + moonPane.positionStatus
        }

        Grid {
            id: factGrid
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: readingsTitle.bottom
            anchors.topMargin: 1
            anchors.bottom: sourceNote.top
            anchors.bottomMargin: 1
            anchors.leftMargin: 3
            anchors.rightMargin: 3
            columns: 3
            spacing: 2

            Repeater {
                id: moonFactRepeater
                model: 9
                delegate: Rectangle {
                    objectName: "cosmos-c8-moon-fact"
                    required property int index
                    readonly property var factData: moonPane.facts[index]
                    width: Math.max(1,(factGrid.width-2*factGrid.spacing)/3)
                    height: Math.max(1,(factGrid.height-2*factGrid.spacing)/3)
                    color: Colors.black
                    border.width: 1
                    border.color: index < 3 ? Colors.magenta
                        : index < 6 ? Colors.cyan : Colors.orange
                    Column {
                        anchors.fill: parent
                        anchors.margins: 2
                        spacing: 1
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: factData ? factData.label : "--"
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.white
                            text: factData ? factData.value : "--"
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        QuietText {
            id: sourceNote
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 3
            anchors.rightMargin: 3
            height: 12
            font.pixelSize: 8
            color: moonSource && moonSource.failed ? Colors.orange : Colors.yellow
            elide: Text.ElideRight
            text: moonPane.moonReady && moonPane.moonEphemeris.noRiseSet
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
