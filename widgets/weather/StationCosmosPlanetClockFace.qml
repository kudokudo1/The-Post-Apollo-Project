import QtQuick
import "../../components"
import "StationCosmosPlanetEventPolicy.js" as PlanetPolicy
import "StationCosmosPlanetDayWheelPolicy.js" as Day
import "StationCosmosPlanetChronographPolicy.js" as Chronograph

// C28 // Compact COSMOS CLOCK. Reuses the V3d validated USNO 24-hour
// event/ring math, not the obsolete five linear timelines.
// R/T/S are discrete provider events, NOT predicted orbital motion.
Item {
    id: face
    objectName: "cosmos-c28-planet-clock-board"
    clip: true

    property var datedRows: []
    property string civilDate: ""
    property string sourceStatus: "SOURCE WAITING"
    property bool sourceReady: false
    property bool compactInPlanets: false
    property bool controlledSelection: false
    signal planetPicked(string name)
    property int localCivilMinute: -1
    property string selectedPlanet: "ALL"
    property string selectedKind: "ALL"
    property var hoveredEvent: null
    property var lockedEvent: null

    // C35 // LIVE is the existing validated source-local clock.
    // REPLAY is an explicitly selected *civil-day demonstration*.
    // It never rewrites source events, or simulates orbital motion.
    property bool replayMode: false
    property bool replayPlaying: false
    property int previewMinute: 0
    readonly property int displayMinute: replayMode
        ? (Chronograph.validMinute(previewMinute) ? previewMinute : -1)
        : (validLocalClock ? localCivilMinute : -1)
    readonly property var upcomingEvent: Chronograph.futureEvent(events,displayMinute)
    readonly property bool replayRunning: replayDriver.running

    function startReplay() {
        if (!sourceReady || !Day.dateValid(civilDate)) return;
        replayPlaying = false;
        previewMinute = validLocalClock ? localCivilMinute : 0;
        replayMode = true;
    }
    function returnLive() {
        replayPlaying = false;
        replayMode = false;
    }
    function seekPreview(minute) {
        if (!replayMode || !sourceReady || !Chronograph.validMinute(minute))
            return;
        previewMinute = minute;
    }
    function stepPreview(delta) {
        if (!replayMode || !sourceReady) return;
        const next = Chronograph.advance(previewMinute,delta);
        if (next !== null) seekPreview(next);
    }

    Timer {
        id: replayDriver
        objectName: "cosmos-c35-day-replay-driver"
        interval: 80
        repeat: true
        running: face.visible && face.sourceReady
            && face.replayMode && face.replayPlaying
            && Day.dateValid(face.civilDate)
        // Eight civil minutes per tick ~ 14.4 seconds per preview day.
        // User-requested replay only; no fake live-time advancement.
        onTriggered: face.stepPreview(8)
    }

    // Compatibility: five planet sources remain mounted even when empty.
    readonly property int renderedRowCount: Day.PLANETS.length
    readonly property var events: sourceReady
        ? Day.datedEvents(
            PlanetPolicy.orderedEvents(datedRows,selectedPlanet,selectedKind),
            civilDate)
        : []
    readonly property var selectedEvent: lockedEvent || hoveredEvent
    readonly property bool validLocalClock: localCivilMinute >= 0
        && localCivilMinute < 1440 && /^\d{4}-\d{2}-\d{2}$/.test(civilDate)

    function eventInk(kind) {
        return kind === "rise" ? Colors.cyan
             : kind === "transit" ? Colors.magenta : Colors.orange;
    }
    function pickPlanet(name) {
        if (!controlledSelection) selectedPlanet = name;
        lockedEvent = null;
        hoveredEvent = null;
        planetPicked(name);
    }
    function pickKind(kind) {
        selectedKind = kind;
        lockedEvent = null;
        hoveredEvent = null;
    }
    function step(direction) {
        if (!events || events.length === 0) return;
        lockedEvent = PlanetPolicy.stepEvent(events,selectedEvent,direction);
    }
    onLockedEventChanged: {
        if (compactInPlanets && controlledSelection && lockedEvent
            && lockedEvent.planet !== selectedPlanet)
            planetPicked(lockedEvent.planet);
    }
    onDatedRowsChanged: { lockedEvent = null; hoveredEvent = null; }
    onCivilDateChanged: {
        lockedEvent = null;
        hoveredEvent = null;
        returnLive();
    }
    onSourceReadyChanged: {
        if (!sourceReady) {
            lockedEvent = null;
            hoveredEvent = null;
            returnLive();
        }
    }
    onEventsChanged: wheelCanvas.requestPaint()
    onSelectedPlanetChanged: wheelCanvas.requestPaint()
    onSelectedEventChanged: wheelCanvas.requestPaint()
    onValidLocalClockChanged: wheelCanvas.requestPaint()
    onLocalCivilMinuteChanged: wheelCanvas.requestPaint()
    onDisplayMinuteChanged: wheelCanvas.requestPaint()

    Row {
        id: clockHeader
        objectName: "cosmos-c28-clock-fixed-header"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 17
        spacing: 6
        GohuText {
            width: Math.max(1,(parent.width-6)*0.48)
            height: parent.height
            text: "PLANET CLOCK // CIVIL DAY"
            color: Colors.magenta
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        QuietText {
            width: Math.max(1,(parent.width-6)*0.52)
            height: parent.height
            text: face.sourceReady
                ? "USNO MRST // " + face.civilDate + " // "
                  + face.events.length + " EVENTS"
                : face.sourceStatus
            color: face.sourceReady ? Colors.cyan : Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
        }
    }

    Row {
        id: mainInstruments
        objectName: "cosmos-c28-clock-instruments"
        anchors.top: clockHeader.bottom
        anchors.topMargin: 4
        anchors.bottom: clockFooter.top
        anchors.bottomMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6

        Rectangle {
            id: wheelPanel
            objectName: "cosmos-c28-clock-dial-frame"
            width: Math.max(1,mainInstruments.width*0.55-3)
            height: mainInstruments.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Item {
                id: dialBay
                anchors.fill: parent
                anchors.margins: 2
                Canvas {
                    id: wheelCanvas
                    objectName: "cosmos-c28-clock-dial-canvas"
                    width: Math.max(1,Math.min(dialBay.width,dialBay.height)-2)
                    height: width
                    anchors.centerIn: parent
                    antialiasing: true
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const g=Day.geometry(width,height);
                        if(!g.ready) return;
                        ctx.save();
                        ctx.textAlign="center";
                        ctx.textBaseline="middle";

                        // One five-lane clock. Radius labels planet identity,
                        // angle encodes local civil time. No straight timelines.
                        for(let i=0;i<Day.PLANETS.length;i++) {
                            const name=Day.PLANETS[i];
                            const r=Day.ringRadius(name,width,height);
                            ctx.beginPath();
                            ctx.arc(g.x,g.y,r,0,Math.PI*2);
                            ctx.globalAlpha=face.selectedPlanet===name?0.95:0.45;
                            ctx.strokeStyle=face.selectedPlanet===name
                                ? String(Colors.yellow) : String(Colors.cyan);
                            ctx.lineWidth=face.selectedPlanet===name?2:1;
                            ctx.stroke();
                        }
                        ctx.globalAlpha=1;
                        // 00 top, 06 right, 12 bottom, 18 left; these are
                        // TIME headings, not geographical directions.
                        for(let hour=0;hour<24;hour+=3) {
                            const angle=hour*Math.PI/12;
                            const major=hour%6===0;
                            const sx=g.x+Math.sin(angle)*g.radius;
                            const sy=g.y-Math.cos(angle)*g.radius;
                            ctx.beginPath();
                            ctx.moveTo(sx,sy);
                            ctx.lineTo(g.x+Math.sin(angle)*(g.radius+5),
                                       g.y-Math.cos(angle)*(g.radius+5));
                            ctx.strokeStyle=String(major?Colors.yellow:Colors.blue);
                            ctx.globalAlpha=major?0.95:0.6;
                            ctx.lineWidth=major?2:1;
                            ctx.stroke();
                            if(major) {
                                ctx.fillStyle=String(Colors.yellow);
                                ctx.globalAlpha=1;
                                ctx.font="9px monospace";
                                ctx.fillText(Day.timeLabel(hour*60).slice(0,2),
                                    g.x+Math.sin(angle)*(g.radius+13),
                                    g.y-Math.cos(angle)*(g.radius+13));
                            }
                        }

                        // C35 // Progress and sweep use the same validated
                        // civil-minute timeAngle() as the existing USNO dots.
                        // The painted beam is a clock hand, not an orbit.
                        if (face.displayMinute >= 0) {
                            const a = Day.timeAngle(face.displayMinute);
                            if (a !== null) {
                                ctx.globalAlpha=0.19;
                                ctx.strokeStyle=String(face.replayMode
                                    ? Colors.magenta : Colors.yellow);
                                ctx.lineWidth=4;
                                ctx.beginPath();
                                ctx.arc(g.x,g.y,g.radius+3,-Math.PI/2,
                                    -Math.PI/2+a,false);
                                ctx.stroke();
                                ctx.globalAlpha=0.30;
                                ctx.lineWidth=5;
                                ctx.beginPath();
                                ctx.moveTo(g.x,g.y);
                                ctx.lineTo(g.x+Math.sin(a)*(g.radius-2),
                                           g.y-Math.cos(a)*(g.radius-2));
                                ctx.stroke();
                                ctx.globalAlpha=1;
                                ctx.lineWidth=1.5;
                                ctx.beginPath();
                                ctx.moveTo(g.x,g.y);
                                ctx.lineTo(g.x+Math.sin(a)*(g.radius-1),
                                           g.y-Math.cos(a)*(g.radius-1));
                                ctx.stroke();
                                ctx.fillStyle=String(face.replayMode
                                    ? Colors.magenta : Colors.yellow);
                                ctx.beginPath();
                                ctx.arc(g.x+Math.sin(a)*(g.radius+1),
                                        g.y-Math.cos(a)*(g.radius+1),
                                        2.6,0,Math.PI*2);
                                ctx.fill();
                            }
                        }
                        ctx.globalAlpha=1;
                        ctx.fillStyle=String(face.replayMode
                            ? Colors.magenta : Colors.yellow);
                        ctx.font="bold 9px monospace";
                        ctx.fillText(face.displayMinute >= 0
                            ? Day.timeLabel(face.displayMinute) : "24H",g.x,g.y);
                        ctx.font="7px monospace";
                        ctx.fillText(face.replayMode ? "REPLAY" : "LIVE",
                            g.x,g.y+12);
                        if(face.events.length===0) {
                            ctx.fillStyle=String(Colors.orange);
                            ctx.font="8px monospace";
                            ctx.fillText("NO DATED EVENTS",g.x,g.y+13);
                        }
                        ctx.restore();
                    }
                }

                // Genuine QML click targets on every validated R/T/S event;
                // positions use the same Day.point() as the full wheel.
                Repeater {
                    id: eventDots
                    model: face.events.length
                    delegate: Rectangle {
                        id: clockEvent
                        objectName: "cosmos-c5-planet-event-marker"
                        required property int index
                        readonly property var eventData: face.events[index]
                        readonly property var pos: Day.point(
                            eventData,wheelCanvas.width,wheelCanvas.height)
                        readonly property bool focused: face.selectedEvent
                            && eventData && face.selectedEvent.id===eventData.id
                        readonly property bool nearHand:
                            Chronograph.atSweep(face.displayMinute,eventData,12)
                        width: focused || nearHand ? 16 : 13
                        height: width
                        radius: width/2
                        x: wheelCanvas.x+(pos ? pos.x : 0)-width/2
                        y: wheelCanvas.y+(pos ? pos.y : 0)-height/2
                        visible: pos!==null
                        color: nearHand ? Colors.yellow : face.eventInk(eventData.kind)
                        border.width: focused || nearHand ? 2 : 1
                        border.color: focused ? Colors.white : Colors.black
                        Behavior on color { ColorAnimation { duration: 160 } }
                        GohuText {
                            anchors.centerIn: parent
                            text: clockEvent.eventData.kind==="rise"?"R"
                                : clockEvent.eventData.kind==="transit"?"T":"S"
                            font.pixelSize: 8
                            color: Colors.black
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: face.hoveredEvent=clockEvent.eventData
                            onExited: face.hoveredEvent=null
                            onClicked: face.lockedEvent=clockEvent.eventData
                        }
                    }
                }
                MouseArea {
                    anchors.fill: wheelCanvas
                    z: -1
                    cursorShape: Qt.CrossCursor
                    onClicked: function(mouse) {
                        const event=Day.pick(face.events,
                            mouse.x,mouse.y,wheelCanvas.width,wheelCanvas.height,10);
                        if(event) {
                            face.lockedEvent=event;
                            return;
                        }
                        const planet=Day.pickRing(
                            mouse.x,mouse.y,wheelCanvas.width,wheelCanvas.height,6);
                        if(planet!=="")
                            face.pickPlanet(face.selectedPlanet===planet
                                ? "ALL" : planet);
                    }
                }
            }
        }

        Rectangle {
            id: eventInspector
            objectName: "cosmos-c28-event-inspector"
            width: Math.max(1,mainInstruments.width-wheelPanel.width-mainInstruments.spacing)
            height: parent.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta
            clip: true
            Column {
                anchors.fill: parent
                anchors.margins: face.compactInPlanets ? 2 : 5
                spacing: face.compactInPlanets ? 1 : 2
                GohuText {
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 12
                    visible: !face.compactInPlanets
                    text: "EVENT // R · T · S"
                    font.pixelSize: 9
                    color: Colors.magenta
                    elide: Text.ElideRight
                }
                GohuText {
                    objectName: "cosmos-c28-selected-event"
                    width: parent.width
                    height: 17
                    text: face.selectedEvent
                        ? String(face.selectedEvent.planet)
                          + " // " + String(face.selectedEvent.kind).toUpperCase()
                        : "SELECT AN EVENT"
                    font.pixelSize: 12
                    color: Colors.yellow
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    height: 12
                    text: face.selectedEvent
                        ? String(face.selectedEvent.date)
                          + " // " + String(face.selectedEvent.clock)
                        : "24H // LOCAL CIVIL TIME"
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 16
                    visible: !face.compactInPlanets
                    text: face.selectedEvent
                        ? PlanetPolicy.eventDetail(face.selectedEvent)
                        : "CLICK R / T / S ON THE DIAL"
                    font.pixelSize: 8
                    color: Colors.orange
                    elide: Text.ElideRight
                }

                Row {
                    id: stepper
                    width: parent.width
                    height: 19
                    spacing: 4
                    ActionButton {
                        width: Math.max(1,(stepper.width-4)/2)
                        height: 19
                        label: "◀ PREV"
                        labelPixelSize: 8
                        contentPadding: 0
                        available: face.events.length>0
                        onClicked: face.step(-1)
                    }
                    ActionButton {
                        width: Math.max(1,(stepper.width-4)/2)
                        height: 19
                        label: "NEXT ▶"
                        labelPixelSize: 8
                        contentPadding: 0
                        available: face.events.length>0
                        onClicked: face.step(1)
                    }
                }

                QuietText {
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 10
                    visible: !face.compactInPlanets
                    text: "PLANET // INNER MER → OUTER SAT"
                    font.pixelSize: 8
                    color: Colors.cyan
                    elide: Text.ElideRight
                }
                Row {
                    id: planetFilters
                    objectName: "cosmos-c28-planet-filters"
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 20
                    visible: !face.compactInPlanets
                    spacing: 2
                    Repeater {
                        model: ["ALL","MERCURY","VENUS","MARS","JUPITER","SATURN"]
                        delegate: ActionButton {
                            required property string modelData
                            width: Math.max(1,(planetFilters.width-5*planetFilters.spacing)/6)
                            height: 20
                            label: modelData==="ALL"?"ALL":modelData.slice(0,3)
                            labelPixelSize: 7
                            contentPadding: 0
                            selected: face.selectedPlanet===modelData
                            accentColor: Colors.cyan
                            onClicked: face.pickPlanet(modelData)
                        }
                    }
                }

                Row {
                    id: kindFilters
                    objectName: "cosmos-c28-event-type-filters"
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 21
                    visible: !face.compactInPlanets
                    spacing: 3
                    Repeater {
                        model: [
                            {id:"ALL",label:"ALL"},
                            {id:"rise",label:"R"},
                            {id:"transit",label:"T"},
                            {id:"set",label:"S"}
                        ]
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.max(1,(kindFilters.width-3*kindFilters.spacing)/4)
                            height: 20
                            contentPadding: 0
                            labelPixelSize: 9
                            label: modelData.label
                            selected: face.selectedKind===modelData.id
                            accentColor: modelData.id==="rise" ? Colors.cyan
                                : modelData.id==="transit" ? Colors.magenta
                                : modelData.id==="set" ? Colors.orange
                                : Colors.yellow
                            onClicked: face.pickKind(modelData.id)
                        }
                    }
                }
                // C35 // Two-state clock: source LIVE versus an
                // explicitly accelerated 24h playback of the same date.
                Row {
                    id: replayControls
                    objectName: "cosmos-c35-time-controls"
                    width: parent.width
                    height: 19
                    spacing: 4
                    ActionButton {
                        objectName: "cosmos-c35-live-replay"
                        width: Math.max(1,(replayControls.width-4)/2)
                        height: 19
                        label: face.replayMode ? "LIVE" : "REPLAY"
                        labelPixelSize: 8
                        contentPadding: 0
                        accentColor: Colors.magenta
                        available: face.sourceReady
                        onClicked: {
                            if (face.replayMode) face.returnLive();
                            else face.startReplay();
                        }
                    }
                    ActionButton {
                        objectName: "cosmos-c35-replay-play-pause"
                        width: Math.max(1,(replayControls.width-4)/2)
                        height: 19
                        label: face.replayPlaying ? "PAUSE" : "PLAY"
                        labelPixelSize: 8
                        contentPadding: 0
                        accentColor: Colors.cyan
                        available: face.replayMode && face.sourceReady
                        onClicked: face.replayPlaying = !face.replayPlaying
                    }
                }
                Rectangle {
                    id: previewTrack
                    objectName: "cosmos-c35-time-scrub-track"
                    width: parent.width
                    height: face.replayMode ? 11 : 0
                    visible: face.replayMode
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Rectangle {
                        id: trackProgress
                        objectName: "cosmos-c35-sweep-progress"
                        width: parent.width*Math.max(0,face.displayMinute)/1439
                        height: parent.height
                        color: Colors.magenta
                        opacity: 0.63
                    }
                    MouseArea {
                        objectName: "cosmos-c35-scrub-input"
                        anchors.fill: parent
                        enabled: face.replayMode && face.sourceReady
                        cursorShape: Qt.PointingHandCursor
                        onClicked: function(mouse) {
                            const next = Chronograph.fractionToMinute(
                                mouse.x/Math.max(1,width));
                            if (next !== null) face.seekPreview(next);
                        }
                    }
                }
                QuietText {
                    objectName: "cosmos-c35-upcoming-event"
                    width: parent.width
                    height: 11
                    text: face.displayMinute < 0 ? "LOCAL TIME UNAVAILABLE"
                        : face.upcomingEvent
                            ? (face.replayMode ? "REPLAY" : "NEXT") + " // "
                              + String(face.upcomingEvent.planet) + " "
                              + String(face.upcomingEvent.kind).toUpperCase()
                              + " " + String(face.upcomingEvent.clock)
                            : "NO LATER DATED USNO EVENT"
                    font.pixelSize: 8
                    color: Colors.yellow
                    elide: Text.ElideRight
                }

                QuietText {
                    width: parent.width
                    height: face.compactInPlanets ? 0 : 11
                    visible: !face.compactInPlanets
                    text: face.events.length>0
                        ? Day.ordinal(face.events,face.selectedEvent)
                          + " // DATED USNO EVENTS"
                        : face.sourceStatus
                    font.pixelSize: 8
                    color: Colors.orange
                    elide: Text.ElideRight
                }
            }
        }
    }

    QuietText {
        id: clockFooter
        objectName: "cosmos-c28-clock-disclaimer"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: face.compactInPlanets ? 0 : 12
        visible: !face.compactInPlanets
        text: "ANGLE = LOCAL TIME // RING = PLANET // NO ORBITS OR RETROGRADE INFERENCE"
        font.pixelSize: 8
        color: Colors.orange
        elide: Text.ElideRight
    }
}
