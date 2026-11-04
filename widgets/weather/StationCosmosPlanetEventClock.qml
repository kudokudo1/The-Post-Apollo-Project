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

    // 24h starts at midnight; narrower views are confined to this civil day.
    // No source times or rows are changed by a viewport gesture.
    property int windowHours: 24
    property real viewStartMinute: 0
    readonly property int viewSpanMinutes: PlanetPolicy.viewportSpan(windowHours)
    readonly property var viewTicks: PlanetPolicy.rulerTicks(
        viewStartMinute, viewSpanMinutes)

    function setWindow(hours, focusMinute) {
        const nextSpan = PlanetPolicy.viewportSpan(hours);
        viewStartMinute = PlanetPolicy.zoomStart(
            viewStartMinute, viewSpanMinutes, nextSpan, focusMinute);
        windowHours = hours;
    }
    function wheelZoom(delta, focusMinute) {
        if (!delta) return;
        const nextHours = delta > 0
            ? (windowHours === 24 ? 12 : 6)
            : (windowHours === 6 ? 12 : 24);
        if (nextHours !== windowHours)
            setWindow(nextHours, focusMinute);
    }

    readonly property var rows: PlanetPolicy.clockRows(
        sourceReady ? providerRows : [], civilDate)
    readonly property var inspectedEvent: PlanetPolicy.selectedEvent(
        lockedEvent, hoveredEvent)
    readonly property int populatedPlanets: PlanetPolicy.rowCountWithEvents(rows)
    readonly property var inspectableEvents: PlanetPolicy.orderedEvents(
        rows, selectedPlanet, selectedKind)

    onProviderRowsChanged: { hoveredEvent = null; lockedEvent = null; }
    onCivilDateChanged: {
        hoveredEvent = null;
        lockedEvent = null;
        windowHours = 24;
        viewStartMinute = 0;
    }
    onLockedEventChanged: {
        if (lockedEvent && lockedEvent.minute !== undefined)
            viewStartMinute = PlanetPolicy.revealStart(
                lockedEvent.minute, viewStartMinute, viewSpanMinutes);
    }
    onSelectedPlanetChanged: { hoveredEvent = null; lockedEvent = null; }
    onSourceReadyChanged: {
        if (!sourceReady) { hoveredEvent = null; lockedEvent = null; }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 11
        spacing: 5

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
                  + " // " + clock.windowHours + "H WINDOW"
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
                    label: PlanetPolicy.planetLabel(modelData)
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
            Row {
                id: zoomPresetRow
                width: 80
                height: 21
                spacing: 2
                Repeater {
                    model: PlanetPolicy.WINDOW_HOURS
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(1, (zoomPresetRow.width
                                               - 2 * zoomPresetRow.spacing) / 3)
                        height: 21
                        contentPadding: 0
                        labelPixelSize: 9
                        label: modelData + "H"
                        selected: clock.windowHours === modelData
                        accentColor: Colors.cyan
                        onClicked: clock.setWindow(
                            modelData, clock.viewStartMinute
                                       + clock.viewSpanMinutes / 2)
                    }
                }
            }
            Item {
                id: clockRuler
                width: Math.max(0, parent.width - 85)
                height: 21
                Repeater {
                    model: clock.viewTicks
                    delegate: GohuText {
                        required property var modelData
                        required property int index
                        x: Math.max(0, Math.min(clockRuler.width - width,
                             PlanetPolicy.rulerX(index, clockRuler.width, 20)
                             - width / 2))
                        y: 0
                        width: 42
                        height: 19
                        text: modelData.label
                        font.pixelSize: 9
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
                        label: PlanetPolicy.planetLabel(
                            planetRow.modelData.name)
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
                        color: clock.inspectedEvent
                               && clock.inspectedEvent.planet
                                  === planetRow.modelData.name
                               ? Colors.black : Colors.dark
                        border.width: 1
                        border.color: clock.inspectedEvent
                                      && clock.inspectedEvent.planet
                                         === planetRow.modelData.name
                                      ? Colors.magenta
                                      : planetRow.modelData.available
                                        ? Colors.blue : Colors.orange
                        clip: true

                        Repeater {
                            model: clock.viewTicks
                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                x: PlanetPolicy.rulerX(index, lane.width, 20)
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

                        // Blank-lane gestures pan only the read-only viewport.
                        // Source-event markers remain independent click targets.
                        MouseArea {
                            id: lanePanArea
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton
                            preventStealing: true
                            property real pressX: 0
                            property real pressStart: 0
                            onPressed: function(mouse) {
                                pressX = mouse.x;
                                pressStart = clock.viewStartMinute;
                            }
                            onPositionChanged: function(mouse) {
                                if (pressed && clock.windowHours < 24) {
                                    clock.viewStartMinute = PlanetPolicy.panStart(
                                        pressStart, clock.viewSpanMinutes,
                                        mouse.x - pressX, lane.width - 22);
                                }
                            }
                            onWheel: function(wheel) {
                                clock.wheelZoom(wheel.angleDelta.y,
                                    clock.viewStartMinute
                                    + (wheel.x / Math.max(1, lane.width))
                                      * clock.viewSpanMinutes);
                                wheel.accepted = true;
                            }
                        }

                        Repeater {
                            model: PlanetPolicy.visibleEvents(
                                planetRow.modelData, clock.selectedKind,
                                clock.viewStartMinute, clock.viewSpanMinutes)
                            delegate: Rectangle {
                                id: eventMarker
                                required property var modelData
                                width: 20
                                height: 21
                                y: 2
                                x: PlanetPolicy.viewX(
                                    modelData.minute, clock.viewStartMinute,
                                    clock.viewSpanMinutes, lane.width, width)
                                radius: 2
                                scale: clock.inspectedEvent
                                       && clock.inspectedEvent.id === modelData.id
                                       ? 1.08 : 1.0
                                Behavior on scale {
                                    NumberAnimation { duration: 120 }
                                }
                                color: clock.lockedEvent
                                       && clock.lockedEvent.id === modelData.id
                                       ? Colors.yellow : Colors.black
                                border.width: clock.lockedEvent
                                              && clock.lockedEvent.id === modelData.id
                                              ? 2 : 1
                                border.color: modelData.kind === "rise" ? Colors.cyan
                                              : modelData.kind === "transit"
                                              ? Colors.magenta : Colors.orange
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: -2
                                    color: "transparent"
                                    radius: 4
                                    border.width: 1
                                    border.color: Colors.yellow
                                    visible: clock.inspectedEvent
                                             && clock.inspectedEvent.id
                                                === eventMarker.modelData.id
                                    opacity: 0.65
                                }
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
                                    onWheel: function(wheel) {
                                        clock.wheelZoom(wheel.angleDelta.y,
                                            eventMarker.modelData.minute);
                                        wheel.accepted = true;
                                    }
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
            height: 73
            color: Colors.dark
            border.width: 1
            border.color: clock.inspectedEvent ? Colors.magenta : Colors.blue
            Column {
                anchors.fill: parent
                anchors.margins: 5
                spacing: 4
                Row {
                    width: parent.width
                    height: 35
                    spacing: 5
                    Column {
                        width: Math.max(0, parent.width - 120)
                        height: 35
                        spacing: 3
                        GohuText {
                            width: parent.width
                            font.pixelSize: 11
                            color: Colors.yellow
                            elide: Text.ElideRight
                            text: clock.inspectedEvent
                                  ? PlanetPolicy.eventDetail(clock.inspectedEvent)
                                  : "SELECT A REAL RISE / TRANSIT / SET MARKER"
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 9
                            color: Colors.cyan
                            elide: Text.ElideRight
                            text: clock.inspectedEvent
                                  ? PlanetPolicy.eventOrdinal(
                                        clock.inspectableEvents,
                                        clock.inspectedEvent)
                                    + " // " + clock.inspectedEvent.date
                                    + " // USNO MRST"
                                  : clock.inspectableEvents.length
                                    + " REAL EVENTS // LOCAL CIVIL TIME"
                        }
                    }
                    ActionButton {
                        width: 55
                        height: 29
                        label: "PREV"
                        labelPixelSize: 10
                        contentPadding: 1
                        accentColor: Colors.cyan
                        available: clock.inspectableEvents.length > 0
                        onClicked: clock.lockedEvent = PlanetPolicy.stepEvent(
                                       clock.inspectableEvents,
                                       clock.inspectedEvent, -1)
                    }
                    ActionButton {
                        width: 55
                        height: 29
                        label: "NEXT"
                        labelPixelSize: 10
                        contentPadding: 1
                        accentColor: Colors.magenta
                        available: clock.inspectableEvents.length > 0
                        onClicked: clock.lockedEvent = PlanetPolicy.stepEvent(
                                       clock.inspectableEvents,
                                       clock.inspectedEvent, 1)
                    }
                }
                QuietText {
                    width: parent.width
                    font.pixelSize: 9
                    color: clock.sourceError ? Colors.orange : Colors.cyan
                    elide: Text.ElideRight
                    text: clock.sourceError
                          ? clock.sourceError
                          : (clock.lockedEvent
                             ? "LOCKED // PREV / NEXT CYCLE REAL EVENTS // UNLOCK TO HOVER"
                             : "HOVER TO PREVIEW // CLICK MARKER OR PREV / NEXT TO LOCK")
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: "WHEEL ZOOM // DRAG LANE PAN // 6H/12H/24H."
                  + " NO MOTION BETWEEN EVENTS; NO ZODIAC OR RETROGRADE INFERENCE."
                  + " USNO LOCAL DATE // AZ TRUE NORTH."
        }
    }
}
