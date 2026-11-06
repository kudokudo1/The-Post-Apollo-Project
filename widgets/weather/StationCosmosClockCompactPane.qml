import QtQuick
import "../../components"
import "StationCosmosPlanetEventPolicy.js" as Events

// C6 // One source-backed, fixed-height USNO event clock. Zoom/pan and
// event inspection use date-scoped rise/transit/set points, never a fake
// continuous orbital path. The existing SKY service still owns the data.
Rectangle {
    id: compactClock
    objectName: "cosmos-c6-planet-clock"
    color: Colors.black
    clip: true
    property var clockRows: []
    property string civilDate: ""
    property string sourceStatus: ""
    property string sourcePrecision: ""
    property string azimuthReference: ""
    property int windowHours: 24
    property real viewStartMinute: 0
    property string selectedPlanet: "ALL"
    property string selectedKind: "ALL"
    property var selectedEvent: null
    property bool inspecting: false
    property int inspectPage: 0

    readonly property int renderedRowCount: laneRepeater.count
    readonly property int spanMinutes: Events.viewportSpan(windowHours)
    readonly property var ordered: Events.orderedEvents(
        clockRows,selectedPlanet,selectedKind)
    readonly property var ticks: Events.rulerTicks(viewStartMinute,spanMinutes)
    readonly property var eventFacts: {
        var e=selectedEvent||{};
        return [
          {name:"PLANET",value:e.planet||"--"},
          {name:"EVENT",value:e.kind?e.kind.toUpperCase():"--"},
          {name:"LOCAL TIME",value:e.clock||"--"},
          {name:"LOCAL DATE",value:e.date||civilDate||"--"},
          {name:"TRANSIT ALT",value:e.altitude===null||e.altitude===undefined
              ? "NOT APPLICABLE" : Number(e.altitude).toFixed(1)+"° "+(e.hemisphere||"")},
          {name:"RISE / SET AZ",value:e.azimuth===null||e.azimuth===undefined
              ? "NOT APPLICABLE" : Number(e.azimuth).toFixed(1)+"° TRUE N"},
          {name:"PRECISION",value:sourcePrecision||"USNO MRST"},
          {name:"REFERENCE",value:azimuthReference||"TRUE NORTH"}
        ];
    }
    function setWindow(hours) {
        var oldSpan=Events.viewportSpan(windowHours);
        var nextSpan=Events.viewportSpan(hours);
        var minute=selectedEvent ? selectedEvent.minute
            : viewStartMinute+oldSpan/2;
        viewStartMinute=Events.zoomStart(
            viewStartMinute,oldSpan,nextSpan,minute);
        windowHours=hours;
    }
    function cyclePlanet() {
        const options=["ALL","MERCURY","VENUS","MARS","JUPITER","SATURN"];
        selectedPlanet=options[(options.indexOf(selectedPlanet)+1)%options.length];
        selectedEvent=null;
        inspecting=false;
    }
    function cycleKind() {
        const options=["ALL","rise","transit","set"];
        selectedKind=options[(options.indexOf(selectedKind)+1)%options.length];
        selectedEvent=null;
        inspecting=false;
    }
    function stepEvent(direction) {
        selectedEvent=Events.stepEvent(ordered,selectedEvent,direction);
        if(selectedEvent) {
            viewStartMinute=Events.revealStart(
                selectedEvent.minute,viewStartMinute,spanMinutes);
            inspecting=true;
        }
    }
    onCivilDateChanged: {
        selectedEvent=null;
        inspecting=false;
        viewStartMinute=0;
        windowHours=24;
    }
    onClockRowsChanged: {
        selectedEvent=null;
        inspecting=false;
    }
    Row {
        id: zoomBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 23
        spacing: 4
        Repeater {
            model: [24,12,6]
            delegate: ActionButton {
                required property var modelData
                width: 48
                height: 22
                contentPadding: 1
                label: modelData+"H"
                labelPixelSize: 9
                selected: compactClock.windowHours===modelData
                accentColor: Colors.cyan
                onClicked: compactClock.setWindow(modelData)
            }
        }
        ActionButton {
            width: Math.max(1,(zoomBar.width-156)/2)
            height: 22
            contentPadding: 1
            label: "PLANET "+compactClock.selectedPlanet
            labelPixelSize: 8
            selected: compactClock.selectedPlanet!=="ALL"
            onClicked: compactClock.cyclePlanet()
        }
        ActionButton {
            width: Math.max(1,(zoomBar.width-156)/2)
            height: 22
            contentPadding: 1
            label: "EVENT "+compactClock.selectedKind.toUpperCase()
            labelPixelSize: 8
            selected: compactClock.selectedKind!=="ALL"
            onClicked: compactClock.cycleKind()
        }
    }
    Row {
        id: detailBar
        anchors.top: zoomBar.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        height: 23
        spacing: 4
        ActionButton {
            width: 55
            height: 22
            label: compactClock.inspecting ? "CLOCK" : "DETAIL"
            labelPixelSize: 9
            contentPadding: 1
            selected: compactClock.inspecting
            available: compactClock.ordered.length > 0
            onClicked: {
                if(!compactClock.selectedEvent)
                    compactClock.stepEvent(1);
                else compactClock.inspecting=!compactClock.inspecting;
            }
        }
        ActionButton {
            width: 48
            height: 22
            label: "PREV"
            labelPixelSize: 8
            contentPadding: 1
            available: compactClock.ordered.length > 0
            onClicked: compactClock.stepEvent(-1)
        }
        ActionButton {
            width: 48
            height: 22
            label: "NEXT"
            labelPixelSize: 8
            contentPadding: 1
            available: compactClock.ordered.length > 0
            onClicked: compactClock.stepEvent(1)
        }
        QuietText {
            width: Math.max(1,detailBar.width-163)
            height: 22
            verticalAlignment: Text.AlignVCenter
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
            text: compactClock.selectedEvent
                ? Events.eventDetail(compactClock.selectedEvent)
                : compactClock.ordered.length+" EVENTS // "+compactClock.civilDate
        }
    }
    Item {
        id: clockDisplay
        visible: !compactClock.inspecting
        anchors.top: detailBar.bottom
        anchors.topMargin: 4
        anchors.bottom: bottomLabel.top
        anchors.bottomMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        Row {
            id: ruler
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 15
            Repeater {
                model: 5
                delegate: QuietText {
                    required property int index
                    width: ruler.width/5
                    font.pixelSize: 8
                    color: Colors.cyan
                    horizontalAlignment: index===4 ? Text.AlignRight : Text.AlignLeft
                    text: compactClock.ticks[index]
                        ? compactClock.ticks[index].label : "--"
                }
            }
        }
        Column {
            id: lanes
            anchors.top: ruler.bottom
            anchors.topMargin: 2
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            spacing: 3
            Repeater {
                id: laneRepeater
                model: 5
                delegate: Rectangle {
                    required property int index
                    readonly property var planetRow:
                        compactClock.clockRows && compactClock.clockRows.length > index
                        ? compactClock.clockRows[index] : null
                    readonly property string planetName:
                        planetRow ? planetRow.name
                        : ["MERCURY","VENUS","MARS","JUPITER","SATURN"][index]
                    width: lanes.width
                    height: Math.max(1,(lanes.height-4*lanes.spacing)/5)
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    opacity: compactClock.selectedPlanet==="ALL"
                        || compactClock.selectedPlanet===planetName ? 1 : 0.35
                    Row {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 5
                        GohuText {
                            width: 65
                            text: planetName
                            color: Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            id: lane
                            width: Math.max(1,parent.width-70)
                            height: Math.max(10,parent.height)
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.magenta
                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                property real startX: 0
                                property real start: 0
                                onPressed: function(mouse) {
                                    startX=mouse.x;
                                    start=compactClock.viewStartMinute;
                                }
                                onPositionChanged: function(mouse) {
                                    if(pressed) compactClock.viewStartMinute =
                                        Events.panStart(start,compactClock.spanMinutes,
                                                        mouse.x-startX,width);
                                }
                                onWheel: function(wheel) {
                                    compactClock.setWindow(wheel.angleDelta.y>0
                                        ? (compactClock.windowHours===24?12:6)
                                        : (compactClock.windowHours===6?12:24));
                                    wheel.accepted=true;
                                }
                            }
                            Repeater {
                                model: planetRow && planetRow.events
                                    ? planetRow.events.length : 0
                                delegate: Rectangle {
                                    objectName: "cosmos-c5-planet-event-marker"
                                    required property int index
                                    readonly property var eventData: planetRow.events[index]
                                    readonly property var markerX:
                                        Events.viewX(eventData.minute,
                                            compactClock.viewStartMinute,
                                            compactClock.spanMinutes,lane.width,9)
                                    visible: markerX !== null
                                        && (compactClock.selectedKind==="ALL"
                                            || compactClock.selectedKind===eventData.kind)
                                        && (compactClock.selectedPlanet==="ALL"
                                            || compactClock.selectedPlanet===planetName)
                                    x: markerX === null ? 0 : markerX
                                    y: 1
                                    width: 9
                                    height: Math.max(1,lane.height-3)
                                    color: eventData.kind==="rise" ? Colors.cyan
                                         : eventData.kind==="transit" ? Colors.yellow
                                         : Colors.magenta
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            compactClock.selectedEvent=eventData;
                                            compactClock.inspectPage=0;
                                            compactClock.inspecting=true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    Item {
        id: clockInspector
        visible: compactClock.inspecting
        anchors.top: detailBar.bottom
        anchors.topMargin: 4
        anchors.bottom: bottomLabel.top
        anchors.bottomMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        Row {
            id: inspectBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 24
            spacing: 5
            GohuText {
                width: Math.max(1,inspectBar.width-105)
                height: 23
                text: "USNO "+(compactClock.selectedEvent
                    ? compactClock.selectedEvent.planet : "EVENT")
                    +" // RISE + TRANSIT + SET"
                font.pixelSize: 10
                color: Colors.magenta
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            ActionButton {
                width: 95
                height: 23
                contentPadding: 1
                label: compactClock.inspectPage===0 ? "DETAIL 1/2" : "DETAIL 2/2"
                labelPixelSize: 9
                selected: true
                onClicked: compactClock.inspectPage=1-compactClock.inspectPage
            }
        }
        Grid {
            id: eventGrid
            anchors.top: inspectBar.bottom
            anchors.topMargin: 4
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            columns: 2
            spacing: 5
            Repeater {
                model: compactClock.selectedEvent ? 4 : 0
                delegate: Rectangle {
                    objectName: "cosmos-c6-clock-fact"
                    required property int index
                    readonly property var factData:
                        compactClock.eventFacts[compactClock.inspectPage*4+index]
                    width: Math.max(1,(eventGrid.width-5)/2)
                    height: Math.max(1,(eventGrid.height-5)/2)
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 3
                        SecondaryText {
                            width: parent.width
                            text: factData ? factData.name : "--"
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: factData ? factData.value : "--"
                            color: Colors.white
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
    QuietText {
        id: bottomLabel
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 12
        font.pixelSize: 8
        color: Colors.orange
        elide: Text.ElideRight
        text: compactClock.sourceStatus+" // "+compactClock.windowHours
            +"H LOCAL CIVIL DAY // EVENT POINTS ONLY, NOT TRAJECTORIES"
    }
}
