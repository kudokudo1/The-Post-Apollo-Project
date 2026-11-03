import QtQuick
import "../../components"
import "StationCosmosPlanetEventPolicy.js" as PlanetPolicy

// V2b // Five real local-day USNO rise / transit / set event lanes.
// This is an interactive dated event display, NOT a continuous sky path.
// Data are supplied by StationSky's existing sole USNO service instance.
Rectangle {
    id: clock
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    height: 414

    property var providerRows: []
    property string civilDate: ""
    property bool sourceReady: false
    property bool sourceLoading: false
    property bool sourceConfigured: false
    property bool sourcePartial: false
    property string sourceError: ""
    property string sourcePrecision: ""
    property string azimuthReference: ""

    property string selectedPlanet: "ALL"
    property string selectedKind: "ALL"
    property var hoveredEvent: null
    property var lockedEvent: null

    readonly property var rows: PlanetPolicy.clockRows(
        sourceReady ? providerRows : [], civilDate)
    readonly property var inspectedEvent: PlanetPolicy.selectedEvent(
        lockedEvent, hoveredEvent)
    readonly property int populatedPlanets: PlanetPolicy.rowCountWithEvents(rows)

    onProviderRowsChanged: { hoveredEvent = null; lockedEvent = null; }
    onCivilDateChanged: { hoveredEvent = null; lockedEvent = null; }
    onSourceReadyChanged: {
        if (!sourceReady) { hoveredEvent = null; lockedEvent = null; }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 11
        spacing: 7

        Row {
            width: parent.width
            height: 22
            spacing: 9

            GohuText {
                width: Math.max(0, parent.width - 157)
                text: "✦ PLANET CLOCK // CIVIL DAY"
                color: Colors.magenta
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            GohuText {
                width: 148
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 10
                color: clock.sourceReady
                       ? (clock.sourcePartial ? Colors.yellow : Colors.cyan)
                       : Colors.orange
                text: !clock.sourceConfigured ? "INPUTS MISSING"
                      : clock.sourceLoading ? "RECEIVING"
                      : clock.sourceReady && clock.sourcePartial ? "PARTIAL USNO"
                      : clock.sourceReady ? "USNO RECEIVED" : "UNAVAILABLE"
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
            text: "USNO MRST // " + (clock.civilDate || "DATE --")
                  + " // " + clock.populatedPlanets + "/5 DATED PLANETS"
                  + " // " + (clock.sourcePrecision || "PROVIDER TIME")
        }

        Row {
            id: planetFilterRow
            width: parent.width
            height: 29
            spacing: 5

            ActionButton {
                width: Math.max(1, (planetFilterRow.width - 5 * planetFilterRow.spacing) / 6)
                height: 28
                label: "ALL"
                labelPixelSize: 10
                contentPadding: 1
                selected: clock.selectedPlanet === "ALL"
                accentColor: Colors.magenta
                onClicked: clock.selectedPlanet = "ALL"
            }
            Repeater {
                model: PlanetPolicy.PLANETS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1, (planetFilterRow.width - 5 * planetFilterRow.spacing) / 6)
                    height: 28
                    contentPadding: 1
                    label: modelData
                    labelPixelSize: 10
                    selected: clock.selectedPlanet === modelData
                    accentColor: Colors.cyan
                    onClicked: clock.selectedPlanet = modelData
                }
            }
        }

        Row {
            width: parent.width
            height: 22
            spacing: 5
            QuietText {
                width: 80
                text: "BODY / STATUS"
                font.pixelSize: 9
                color: Colors.orange
            }
            Item {
                id: clockRuler
                width: Math.max(0, parent.width - 85)
                height: 21
                Repeater {
                    model: ["00", "06", "12", "18", "24"]
                    delegate: GohuText {
                        required property var modelData
                        required property int index
                        x: index / 4 * (clockRuler.width - width)
                        y: 0
                        width: 25
                        height: 19
                        text: modelData
                        font.pixelSize: 10
                        color: Colors.cyan
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        Column {
            id: planetLanes
            width: parent.width
            height: 147
            spacing: 3

            Repeater {
                model: clock.rows
                delegate: Row {
                    id: planetRow
                    required property var modelData
                    width: planetLanes.width
                    height: 26
                    spacing: 5
                    visible: clock.selectedPlanet === "ALL"
                             || clock.selectedPlanet === modelData.name

                    ActionButton {
                        width: 80
                        height: 25
                        label: planetRow.modelData.name
                        labelPixelSize: 9
                        contentPadding: 1
                        accentColor: planetRow.modelData.available
                                     ? Colors.cyan : Colors.orange
                        selected: clock.selectedPlanet === planetRow.modelData.name
                        onClicked: clock.selectedPlanet =
                            clock.selectedPlanet === planetRow.modelData.name
                            ? "ALL" : planetRow.modelData.name
                    }

                    Rectangle {
                        id: lane
                        width: Math.max(0, planetRow.width - 85)
                        height: 25
                        color: Colors.dark
                        border.width: 1
                        border.color: planetRow.modelData.available
                                      ? Colors.blue : Colors.orange
                        clip: true

                        Repeater {
                            model: [0, 360, 720, 1080, 1440]
                            delegate: Rectangle {
                                required property var modelData
                                x: Math.min(lane.width - 1,
                                            modelData / 1440 * (lane.width - 1))
                                y: 0
                                width: 1
                                height: lane.height
                                color: Colors.cyan
                                opacity: 0.24
                            }
                        }

                        QuietText {
                            anchors.centerIn: parent
                            visible: !planetRow.modelData.available
                            text: planetRow.modelData.status
                            color: Colors.orange
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }

                        Repeater {
                            model: PlanetPolicy.eventsFor(
                                planetRow.modelData, clock.selectedKind)
                            delegate: Rectangle {
                                id: eventMarker
                                required property var modelData
                                width: 20
                                height: 21
                                y: 2
                                x: Math.max(1, Math.min(lane.width - width - 1,
                                    PlanetPolicy.timeX(modelData.minute,
                                                      lane.width - width - 2)))
                                radius: 2
                                color: clock.lockedEvent
                                       && clock.lockedEvent.id === modelData.id
                                       ? Colors.yellow : Colors.black
                                border.width: clock.lockedEvent
                                              && clock.lockedEvent.id === modelData.id
                                              ? 2 : 1
                                border.color: modelData.kind === "rise" ? Colors.cyan
                                              : modelData.kind === "transit"
                                              ? Colors.magenta : Colors.orange
                                GohuText {
                                    anchors.centerIn: parent
                                    text: eventMarker.modelData.kind === "rise" ? "R"
                                          : eventMarker.modelData.kind === "transit"
                                          ? "T" : "S"
                                    font.pixelSize: 10
                                    color: clock.lockedEvent
                                           && clock.lockedEvent.id
                                              === eventMarker.modelData.id
                                           ? Colors.black : eventMarker.border.color
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    acceptedButtons: Qt.LeftButton
                                    hoverEnabled: true
                                    preventStealing: true
                                    cursorShape: Qt.PointingHandCursor
                                    onEntered: clock.hoveredEvent = eventMarker.modelData
                                    onExited: {
                                        if (clock.hoveredEvent
                                            && clock.hoveredEvent.id
                                               === eventMarker.modelData.id)
                                            clock.hoveredEvent = null;
                                    }
                                    onClicked: clock.lockedEvent = eventMarker.modelData
                                }
                            }
                        }
                    }
                }
            }
        }

        Row {
            id: eventFilterRow
            width: parent.width
            height: 27
            spacing: 5

            Repeater {
                model: [
                    {id:"ALL", label:"ALL EVENTS"},
                    {id:"rise", label:"R // RISE"},
                    {id:"transit", label:"T // TRANSIT"},
                    {id:"set", label:"S // SET"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(0, (eventFilterRow.width - 90 - 4 *
                                           eventFilterRow.spacing) / 4)
                    height: 26
                    contentPadding: 1
                    labelPixelSize: 9
                    label: modelData.label
                    selected: clock.selectedKind === modelData.id
                    accentColor: modelData.id === "rise" ? Colors.cyan
                                 : modelData.id === "transit" ? Colors.magenta
                                 : modelData.id === "set" ? Colors.orange
                                 : Colors.yellow
                    onClicked: {
                        clock.selectedKind = modelData.id;
                        clock.hoveredEvent = null;
                        clock.lockedEvent = null;
                    }
                }
            }
            ActionButton {
                width: 90
                height: 26
                contentPadding: 1
                label: "UNLOCK"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: clock.lockedEvent !== null
                onClicked: clock.lockedEvent = null
            }
        }

        Rectangle {
            width: parent.width
            height: 45
            color: Colors.dark
            border.width: 1
            border.color: clock.inspectedEvent ? Colors.magenta : Colors.blue
            Column {
                anchors.fill: parent
                anchors.margins: 5
                spacing: 2
                GohuText {
                    width: parent.width
                    font.pixelSize: 11
                    color: Colors.yellow
                    elide: Text.ElideRight
                    text: clock.inspectedEvent
                          ? PlanetPolicy.eventDetail(clock.inspectedEvent)
                          : "CHOOSE A PLANET / CLICK R, T OR S TO LOCK"
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                    text: clock.sourceError
                          ? clock.sourceError
                          : (clock.lockedEvent ? "LOCKED // UNLOCK TO INSPECT MORE"
                             : "HOVER FOR DETAILS // CLICK TO HOLD EVENT")
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: "DATED USNO CALCULATIONS, NOT LIVE PLANET TRACKS."
                  + " NO MOTION BETWEEN EVENTS; NO ZODIAC OR RETROGRADE INFERENCE."
                  + " AZIMUTH FROM TRUE NORTH."
        }
    }
}
