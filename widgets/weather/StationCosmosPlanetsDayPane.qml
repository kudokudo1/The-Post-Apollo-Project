import QtQuick
import "../../components"
import "StationCosmosPlanetEventPolicy.js" as Events

// C38 // Focused PLANETS civil-day timeline, reusing the exact USNO
// dated event policy. Discrete R/T/S events, not simulated orbital motion.
Rectangle {
    id: day
    objectName: "cosmos-c38-planets-day-events"
    color: Colors.black
    clip: true
    property var datedRows: []
    property string civilDate: ""
    property bool sourceReady: false
    property string sourceStatus: "SOURCE WAITING"
    property bool compactInPlanets: false
    property bool controlledSelection: false
    signal planetPicked(string name)
    property string selectedPlanet: "ALL"
    property string selectedKind: "ALL"
    property int windowHours: 24
    property real viewStartMinute: 0
    property var hoveredEvent: null
    property var lockedEvent: null
    readonly property int viewSpan: Events.viewportSpan(windowHours)
    readonly property var ticks: Events.rulerTicks(viewStartMinute,viewSpan)
    readonly property var rows: sourceReady ? datedRows : Events.clockRows([],civilDate)
    readonly property var events: Events.orderedEvents(rows,selectedPlanet,selectedKind)
    readonly property var inspectedEvent: lockedEvent || hoveredEvent
    function setWindow(hours,focus) {
        const newSpan=Events.viewportSpan(hours);
        viewStartMinute=Events.zoomStart(viewStartMinute,viewSpan,newSpan,focus);
        windowHours=hours;
    }
    function pickPlanet(name) {
        if (!controlledSelection) selectedPlanet=name;
        lockedEvent=null;hoveredEvent=null;
        planetPicked(name);
    }
    function pickKind(name) {
        selectedKind=name;lockedEvent=null;hoveredEvent=null;
    }
    function step(direction) {
        if(events.length) lockedEvent=Events.stepEvent(events,inspectedEvent,direction);
    }
    onLockedEventChanged: {
        if(lockedEvent && lockedEvent.minute!==undefined)
            viewStartMinute=Events.revealStart(lockedEvent.minute,viewStartMinute,viewSpan);
    }
    onCivilDateChanged: {
        viewStartMinute=0;windowHours=24;lockedEvent=null;hoveredEvent=null;
    }
    onDatedRowsChanged: {lockedEvent=null;hoveredEvent=null;}
    onSelectedPlanetChanged: {lockedEvent=null;hoveredEvent=null;}

    Column {
        id: content
        anchors.fill: parent
        anchors.margins: 3
        spacing: 3
        Row {
            id: heading
            width: parent.width
            height: day.compactInPlanets ? 0 : 17
            visible: !day.compactInPlanets
            spacing: 4
            GohuText {
                width: Math.max(1,heading.width*0.55)
                text: "PLANET CLOCK // CIVIL DAY"
                color: Colors.magenta;font.pixelSize: 10
                elide: Text.ElideRight
            }
            QuietText {
                width: Math.max(1,heading.width*0.45-4)
                text: day.sourceReady ? "USNO MRST // "+day.civilDate : day.sourceStatus
                color: day.sourceReady?Colors.cyan:Colors.orange
                font.pixelSize: 8;elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
            }
        }
        Row {
            id: planets
            objectName: "cosmos-c38-planet-selectors"
            width: parent.width
            height: day.compactInPlanets ? 16 : 20
            spacing: 3
            Repeater {
                model: ["ALL","MERCURY","VENUS","MARS","JUPITER","SATURN"]
                delegate: ActionButton {
                    required property string modelData
                    width: Math.max(1,(planets.width-5*planets.spacing)/6)
                    height: planets.height
                    label: modelData==="ALL"?"ALL":Events.planetLabel(modelData)
                    labelPixelSize: 8;contentPadding: 0
                    selected: day.selectedPlanet===modelData
                    accentColor: Colors.cyan
                    onClicked: day.pickPlanet(modelData)
                }
            }
        }
        Row {
            id: zoomRow
            objectName: "cosmos-c38-6-12-24-hour-windows"
            width: parent.width
            height: day.compactInPlanets ? 16 : 18
            spacing: 3
            Repeater {
                model: Events.WINDOW_HOURS
                delegate: ActionButton {
                    required property var modelData
                    width: 28;height: zoomRow.height
                    label: modelData+"H";labelPixelSize: 8
                    contentPadding: 0;accentColor: Colors.cyan
                    selected: day.windowHours===modelData
                    onClicked: day.setWindow(modelData,day.viewStartMinute+day.viewSpan/2)
                }
            }
            Item {
                id: ruler
                width: Math.max(1,zoomRow.width-93)
                height: zoomRow.height
                Repeater {
                    model: day.ticks
                    delegate: QuietText {
                        required property var modelData
                        required property int index
                        x: Math.max(0,Math.min(Math.max(0,ruler.width-36),
                            Events.rulerX(index,ruler.width,15)-18))
                        width: 36;height: 18
                        text: modelData.label
                        color: Colors.cyan;font.pixelSize: 8
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
        Column {
            id: lanes
            objectName: "cosmos-c38-five-planet-event-lanes"
            width: parent.width
            height: Math.max(day.compactInPlanets ? 55 : 65,
                content.height-heading.height-planets.height
                -zoomRow.height-kinds.height-inspector.height-note.height
                -6*content.spacing)
            spacing: 2
            Repeater {
                model: day.rows
                delegate: Row {
                    id: lane
                    required property var modelData
                    width: lanes.width
                    height: Math.max(day.compactInPlanets ? 9 : 11,
                        Math.floor((lanes.height-4*lanes.spacing)/5))
                    spacing: 3
                    ActionButton {
                        width: 77;height: lane.height
                        label: Events.planetLabel(lane.modelData.name)
                        labelPixelSize: 8;contentPadding: 0
                        selected: day.selectedPlanet===lane.modelData.name
                        accentColor: lane.modelData.available?Colors.cyan:Colors.orange
                        onClicked: day.pickPlanet(day.selectedPlanet===lane.modelData.name
                            ?"ALL":lane.modelData.name)
                    }
                    Rectangle {
                        id: track
                        objectName: "cosmos-c38-dated-event-track"
                        width: Math.max(1,lane.width-80)
                        height: lane.height;clip: true
                        color: Colors.dark
                        border.width: 1
                        border.color: day.inspectedEvent
                            && day.inspectedEvent.planet===lane.modelData.name
                            ? Colors.magenta : Colors.blue
                        Repeater {
                            model: day.ticks
                            delegate: Rectangle {
                                required property int index
                                x: Events.rulerX(index,track.width,15)
                                width: 1;height: track.height
                                color: Colors.cyan;opacity: 0.25
                            }
                        }
                        QuietText {
                            anchors.centerIn: parent
                            visible: !lane.modelData.available
                            text: lane.modelData.status
                            color: Colors.orange;font.pixelSize: 8
                        }
                        MouseArea {
                            id: pan
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            property real downX: 0
                            property real from: 0
                            onPressed: function(mouse) {
                                downX=mouse.x;from=day.viewStartMinute;
                            }
                            onPositionChanged: function(mouse) {
                                if(pressed && day.windowHours<24)
                                    day.viewStartMinute=Events.panStart(from,day.viewSpan,
                                        mouse.x-downX,Math.max(1,track.width-15));
                            }
                            onWheel: function(wheel) {
                                const opts=Events.WINDOW_HOURS;
                                const i=opts.indexOf(day.windowHours);
                                day.setWindow(opts[Math.max(0,Math.min(2,
                                    i+(wheel.angleDelta.y>0?-1:1)))],
                                    day.viewStartMinute+(wheel.x/Math.max(1,track.width))
                                    *day.viewSpan);
                                wheel.accepted=true;
                            }
                        }
                        Repeater {
                            model: Events.visibleEvents(lane.modelData,day.selectedKind,
                                day.viewStartMinute,day.viewSpan)
                            delegate: Rectangle {
                                id: marker
                                required property var modelData
                                width: 15;height: Math.max(8,track.height-2);y: 1
                                x: Events.viewX(modelData.minute,day.viewStartMinute,
                                    day.viewSpan,track.width,width)
                                radius: 2
                                readonly property bool focused: day.inspectedEvent
                                    && day.inspectedEvent.id===modelData.id
                                color: focused?Colors.yellow:Colors.black
                                border.width: focused?2:1
                                border.color: modelData.kind==="rise"?Colors.cyan:
                                    modelData.kind==="transit"?Colors.magenta:Colors.orange
                                GohuText {
                                    anchors.centerIn: parent
                                    text: marker.modelData.kind==="rise"?"R":
                                        marker.modelData.kind==="transit"?"T":"S"
                                    color: marker.focused?Colors.black:marker.border.color
                                    font.pixelSize: 8
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onEntered: day.hoveredEvent=marker.modelData
                                    onExited: {
                                        if(day.hoveredEvent &&
                                           day.hoveredEvent.id===marker.modelData.id)
                                            day.hoveredEvent=null;
                                    }
                                    onClicked: day.lockedEvent=marker.modelData
                                }
                            }
                        }
                    }
                }
            }
        }
        Row {
            id: kinds
            objectName: "cosmos-c38-rise-transit-set-controls"
            width: parent.width
            height: day.compactInPlanets ? 16 : 20
            spacing: 3
            Repeater {
                model: [{id:"ALL",label:"ALL EVENTS"},{id:"rise",label:"R / RISE"},
                    {id:"transit",label:"T / TRANSIT"},{id:"set",label:"S / SET"}]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(kinds.width-96-5*kinds.spacing)/4)
                    height: kinds.height;label: modelData.label
                    labelPixelSize: 8;contentPadding: 0
                    selected: day.selectedKind===modelData.id
                    accentColor: modelData.id==="rise"?Colors.cyan:
                        modelData.id==="transit"?Colors.magenta:
                        modelData.id==="set"?Colors.orange:Colors.yellow
                    onClicked: day.pickKind(modelData.id)
                }
            }
            ActionButton {
                width: 45;height: kinds.height;label: "PREV"
                labelPixelSize: 8;contentPadding: 0
                available: day.events.length>0
                onClicked: day.step(-1)
            }
            ActionButton {
                width: 45;height: kinds.height;label: "NEXT"
                labelPixelSize: 8;contentPadding: 0
                available: day.events.length>0
                onClicked: day.step(1)
            }
        }
        Rectangle {
            id: inspector
            objectName: "cosmos-c38-selected-source-event"
            width: parent.width
            height: day.compactInPlanets ? 25 : 39
            color: Colors.dark;border.width: 1
            border.color: day.inspectedEvent?Colors.magenta:Colors.cyan
            Column {
                anchors.fill: parent;anchors.margins: 3;spacing: 2
                GohuText {
                    width: parent.width
                    height: day.compactInPlanets ? 12 : 15
                    text: day.inspectedEvent?Events.eventDetail(day.inspectedEvent)
                        :"SELECT A REAL RISE / TRANSIT / SET MARKER"
                    color: Colors.yellow;font.pixelSize: 10;elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    height: day.compactInPlanets ? 9 : 12
                    text: day.inspectedEvent
                        ? Events.eventOrdinal(day.events,day.inspectedEvent)
                            +" // "+day.inspectedEvent.date+" // USNO MRST"
                        : day.events.length+" REAL EVENTS // LOCAL CIVIL TIME"
                    color: Colors.cyan;font.pixelSize: 8;elide: Text.ElideRight
                }
            }
        }
        QuietText {
            id: note
            width: parent.width
            height: day.compactInPlanets ? 0 : 11
            visible: !day.compactInPlanets
            text: "WHEEL ZOOM // DRAG PAN // R/T/S SOURCE EVENTS, NOT ORBITS OR CONTINUOUS SKY TRACKS"
            color: Colors.orange;font.pixelSize: 8;elide: Text.ElideRight
        }
    }
}
