import QtQuick
import "../../components"

// M30-E // Read-only focused Moon/solar reference rack.
// The hidden source-only SKY owns the original USNO observation and
// calibrated civil/twilight models. This component starts no collector.
// Unavailable readings show --; reference/photographic windows are models.
Rectangle {
    id: rack
    color: Colors.dark
    border.width: 1
    border.color: rack.isSolar ? Colors.orange : Colors.cyan
    clip: true

    property bool isSolar: false
    property var skySource: null

    readonly property var moonActor: skySource ? skySource.moonObservation : null
    readonly property bool moonReady: !!moonActor && moonActor.ready
        && !!moonActor.ephemeris && moonActor.ephemeris.available
    readonly property var moon: moonReady ? moonActor.ephemeris : null
    readonly property var astronomy: skySource ? skySource.astronomySummary : null
    readonly property var twilight: skySource ? skySource.twilightSummary : null
    readonly property bool twilightReady: !!twilight && twilight.available
    readonly property var sunNow: skySource ? skySource.currentSolarPosition : null

    function field(value) {
        if (value === undefined || value === null)
            return "--";
        const shown = String(value).trim();
        return shown !== "" ? shown : "--";
    }
    function solarField(value) {
        return twilightReady ? field(value) : "--";
    }
    function lightWindow(start, end) {
        if (!twilightReady) return "--";
        const a = field(start), b = field(end);
        return a !== "--" && b !== "--" ? a + " → " + b : "--";
    }

    readonly property var moonTimes: [
        {label:"MOONRISE", value:moonReady ? field(moon.rise) : "--"},
        {label:"UPPER TRANSIT",value:moonReady ? field(moon.transit) : "--"},
        {label:"MOONSET",value:moonReady ? field(moon.set) : "--"}
    ]
    readonly property var moonContext: [
        {label:"SOURCE DATE",value:moonReady ? field(moon.sourceDate) : "--"},
        {label:"CIVIL OFFSET",value:skySource ? field(skySource.moonCivilOffsetMinutes) + " M" : "--"},
        {label:"OFFSET ORIGIN",value:skySource ? field(skySource.moonCivilOffsetSource) : "--"}
    ]
    readonly property var dawn: [
        {label:"ASTRO DAWN",value:solarField(twilight ? twilight.astronomicalDawn : null)},
        {label:"NAUTICAL",value:solarField(twilight ? twilight.nauticalDawn : null)},
        {label:"CIVIL DAWN",value:solarField(twilight ? twilight.civilDawn : null)},
        {label:"SOLAR NOON",value:solarField(twilight ? twilight.solarNoon : null)}
    ]
    readonly property var dusk: [
        {label:"SUNSET",value:astronomy && astronomy.available ? field(astronomy.sunset) : "--"},
        {label:"CIVIL DUSK",value:solarField(twilight ? twilight.civilDusk : null)},
        {label:"NAUTICAL",value:solarField(twilight ? twilight.nauticalDusk : null)},
        {label:"ASTRO DUSK",value:solarField(twilight ? twilight.astronomicalDusk : null)}
    ]
    readonly property var morningLight: [
        {label:"BLUE // AM",value:lightWindow(
            twilight ? twilight.blueMorningStart : null,
            twilight ? twilight.blueMorningEnd : null)},
        {label:"GOLDEN // AM",value:lightWindow(
            twilight ? twilight.goldenMorningStart : null,
            twilight ? twilight.goldenMorningEnd : null)}
    ]
    readonly property var eveningLight: [
        {label:"GOLDEN // PM",value:lightWindow(
            twilight ? twilight.goldenEveningStart : null,
            twilight ? twilight.goldenEveningEnd : null)},
        {label:"BLUE // PM",value:lightWindow(
            twilight ? twilight.blueEveningStart : null,
            twilight ? twilight.blueEveningEnd : null)}
    ]

    Column {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 4

        Row {
            width: parent.width
            height: 15
            spacing: 6
            GohuText {
                width: Math.max(0,parent.width-104)
                font.pixelSize: 10
                color: rack.isSolar ? Colors.orange : Colors.cyan
                text: rack.isSolar
                    ? "TWILIGHT + PHOTO LIGHT // LOCAL"
                    : "MOON // ONE-DAY EPHEMERIS"
                elide: Text.ElideRight
            }
            QuietText {
                width: 98
                font.pixelSize: 8
                color: rack.isSolar
                       ? (rack.twilightReady ? Colors.cyan : Colors.yellow)
                       : (rack.moonReady ? Colors.cyan : Colors.yellow)
                text: rack.isSolar
                    ? (rack.twilightReady ? "SOLAR MODEL" : "MODEL WAITING")
                    : (rack.moonReady ? "USNO RECEIVED" : "USNO UNAVAILABLE")
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }

        Loader {
            width: parent.width
            height: Math.max(0,parent.height-21)
            sourceComponent: rack.isSolar ? solarDetails : lunarDetails
        }
    }

    Component {
        id: lunarDetails
        Column {
            width: parent ? parent.width : 0
            spacing: 7

            Row {
                id: eventRow
                width: parent.width
                height: 35
                spacing: 6
                Repeater {
                    model: rack.moonTimes
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(eventRow.width-2*eventRow.spacing)/3)
                        spacing: 2
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 12
                            color: Colors.white
                            text: modelData.value
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Row {
                id: provenanceRow
                width: parent.width
                height: 34
                spacing: 6
                Repeater {
                    model: rack.moonContext
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(provenanceRow.width-2*provenanceRow.spacing)/3)
                        spacing: 2
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.cyan
                            text: modelData.value
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                font.pixelSize: 8
                color: rack.moonReady ? Colors.orange : Colors.yellow
                text: rack.moonReady
                    ? (rack.moon.noRiseSet
                       ? "USNO REPORTS NO RISE / SET FOR THIS CIVIL DATE"
                       : "USNO LOCAL RISE / TRANSIT / SET // SCHEMATIC PHASE ABOVE")
                    : "USNO EVENT TIMES NOT READY // NO TIMES INVENTED"
                elide: Text.ElideRight
            }
        }
    }

    Component {
        id: solarDetails
        Column {
            width: parent ? parent.width : 0
            spacing: 3

            Row {
                id: dawnRow
                width: parent.width
                height: 28
                spacing: 4
                Repeater {
                    model: rack.dawn
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(dawnRow.width-3*dawnRow.spacing)/4)
                        spacing: 1
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.cyan
                            text: modelData.value
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Row {
                id: duskRow
                width: parent.width
                height: 28
                spacing: 4
                Repeater {
                    model: rack.dusk
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(duskRow.width-3*duskRow.spacing)/4)
                        spacing: 1
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.magenta
                            text: modelData.value
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                height: 13
                font.pixelSize: 9
                color: Colors.orange
                text: "PHOTO LIGHT // BLUE + GOLDEN WINDOWS"
                elide: Text.ElideRight
            }

            Row {
                id: photoMorningRow
                width: parent.width
                height: 28
                spacing: 7
                Repeater {
                    model: rack.morningLight
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(photoMorningRow.width-photoMorningRow.spacing)/2)
                        spacing: 1
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            color: Colors.cyan
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            text: modelData.value
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Row {
                id: photoEveningRow
                width: parent.width
                height: 28
                spacing: 7
                Repeater {
                    model: rack.eveningLight
                    delegate: Column {
                        required property var modelData
                        width: Math.max(1,(photoEveningRow.width-photoEveningRow.spacing)/2)
                        spacing: 1
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.label
                            color: Colors.magenta
                        }
                        GohuText {
                            width: parent.width
                            font.pixelSize: 9
                            text: modelData.value
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                font.pixelSize: 8
                color: Colors.yellow
                text: rack.sunNow && rack.sunNow.available
                    ? "SUN NOW // ALT "
                      + rack.sunNow.altitudeDegrees.toFixed(1) + "°  AZ "
                      + rack.sunNow.azimuthDegrees.toFixed(1)
                      + "° // CALCULATED"
                    : "SUN NOW // CALIBRATED POSITION NOT AVAILABLE"
                elide: Text.ElideRight
            }
        }
    }
}
