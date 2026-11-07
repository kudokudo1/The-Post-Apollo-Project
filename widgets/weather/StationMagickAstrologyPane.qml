import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationMagickTransitComparisonPolicy.js" as Transit
import "StationMagickTransitTimelinePolicy.js" as Timeline
import "StationMagickTransitMultiPolicy.js" as Multi
import "StationMagickTransitMatrixPolicy.js" as Matrix

// M30-F // A standalone, no-outer-scroll source-verified astrology instrument.
// All chart modes use the existing single on-demand JPL/CelestialVisualService
// owned by WeatherStationW. No new Process, Timer, cache or interpretation.
Rectangle {
    id: astrology
    color: Colors.black
    clip: true

    property string subjectRoute: "magick/astrology/charts"
    property var celestialSource: null
    // M7a // Input readiness only, not a computed full natal chart.
    property bool eventSetupOpen: false
    property bool natalMode: false
    // M8c // TRANSITS is a second verified M8b chart at an explicitly entered
    // UTC time, never a reinterpretation of the old selected-pair graph.
    property bool transitMode: false
    property bool timelineMode: false
    property bool multiMode: false
    property bool matrixMode: false
    property string selectedNatalReference: ""
    property string selectedContactUtc: ""
    property string selectedEventKind: "aspect"
    property string selectedMultiBody: ""
    property string transitExpectedUtc: ""
    onNatalModeChanged: if(!natalMode)transitMode=false
    onTransitModeChanged: if(!transitMode){
        timelineMode=false;
        multiMode=false;
        matrixMode=false;
        selectedNatalReference="";
        selectedContactUtc="";
        selectedEventKind="aspect";
        selectedMultiBody="";
    }
    // A complete independent chart service will supply this in a later
    // verified milestone. The existing M4 two-body source is NOT substituted.
    property var fullChartData: null
    WeatherServices.CelestialNatalChartService {
        id: natalSource
        active: astrology.visible
        onReadyChanged: astrology.fullChartData=
            ready?natalSource.chartData:null
        onChartDataChanged: {
            astrology.fullChartData=ready?natalSource.chartData:null;
            // Every new natal input invalidates the comparison.
            astrology.transitExpectedUtc="";
            astrology.selectedContactUtc="";
            astrology.selectedEventKind="aspect";
            astrology.selectedMultiBody="";
            astrology.selectedNatalReference="";
            transitSource.clearState();
            timelineSource.clearState();
            multiSource.clearState();
            matrixSource.clearState();
        }
    }
    WeatherServices.CelestialNatalChartService {
        id: transitSource
        active: astrology.visible && astrology.natalMode
            && astrology.transitMode && natalSource.ready
    }
    WeatherServices.CelestialTransitTimelineService {
        id: timelineSource
        active: astrology.visible && astrology.natalMode
            && astrology.transitMode && natalSource.ready
        natalChart: astrology.fullChartData
    }
    WeatherServices.CelestialTransitMultiService {
        id: multiSource
        active: astrology.visible && astrology.natalMode
            && astrology.transitMode && astrology.multiMode
            && natalSource.ready
        natalChart: astrology.fullChartData
    }
    WeatherServices.CelestialTransitMatrixService {
        id: matrixSource
        active: astrology.visible && astrology.natalMode
            && astrology.transitMode && astrology.matrixMode
            && natalSource.ready
        natalChart: astrology.fullChartData
    }
    function requestTransit(instant){
        if(!natalSource.ready||!natalSource.chartData)return false;
        const draft=Transit.makeDraft(natalSource.chartData,instant);
        if(!draft)return false;
        astrology.transitExpectedUtc=instant;
        return transitSource.calculate(draft);
    }

    readonly property bool sourceIdle: !!celestialSource
        && !celestialSource.loading
    readonly property bool calculated: !!celestialSource
        && celestialSource.ready
    readonly property bool chartAvailable: !!celestialSource
        && celestialSource.configured && celestialSource.active
        && !celestialSource.loading

    function stepSample(direction) {
        if (!instrument.graphModel.ready || !sourceIdle)
            return;
        instrument.eventOrdinal=-1;
        instrument.lockedIndex=Math.max(0,Math.min(
            instrument.graphModel.sampleCount-1,
            instrument.focusIndex+direction));
    }
    function resetChart() {
        instrument.lockedIndex=-1;
        instrument.hoveredIndex=-1;
        instrument.eventOrdinal=-1;
        instrument.selectedBody="";
        instrument.zoom=1;
        instrument.panPosition=0.5;
    }

    Row {
        id: calculationControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 26
        spacing: 5

        GohuText {
            width: Math.max(0,parent.width-365)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 11
            text: "ASTROLOGY // CELESTIAL"
            color: Colors.magenta
            elide: Text.ElideRight
        }
        QuietText {
            width: 100
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 8
            text: astrology.transitMode
                ? transitSource.statusText
                : astrology.natalMode
                ? natalSource.statusText
                : astrology.celestialSource
                  ? astrology.celestialSource.statusText
                  : "JPL UNAVAILABLE"
            color: astrology.transitMode
                ? transitSource.ready?Colors.cyan:Colors.orange
                : astrology.natalMode
                ? natalSource.ready?Colors.cyan:Colors.orange
                : astrology.calculated?Colors.cyan:Colors.orange
            elide: Text.ElideRight
        }
        ActionButton {
            width: 96
            height: 25
            label: astrology.natalMode
                ? natalSource.loading?"CALCULATING":"SET EVENT"
                : astrology.celestialSource && astrology.celestialSource.loading
                  ? "CALCULATING" : "CALCULATE"
            labelPixelSize: 9
            accentColor: Colors.magenta
            available: astrology.natalMode
                ? !natalSource.loading : astrology.chartAvailable
            // Separate owners: M4 selected pair vs private M8b event chart.
            onClicked: {
                if(astrology.natalMode)astrology.eventSetupOpen=true;
                else astrology.celestialSource.refresh();
            }
        }
        ActionButton {
            width: 61
            height: 25
            label: astrology.natalMode ? "PAIR" : "NATAL"
            labelPixelSize: 9
            accentColor: astrology.natalMode ? Colors.magenta : Colors.cyan
            selected: astrology.natalMode
            onClicked: astrology.natalMode=!astrology.natalMode
        }
        ActionButton {
            width: 88
            height: 25
            label: astrology.natalMode
                ? astrology.transitMode?"NATAL":"TRANSITS"
                : "EVENT SETUP"
            labelPixelSize: 9
            accentColor: astrology.transitMode?Colors.magenta:Colors.yellow
            available: !astrology.natalMode || natalSource.ready
            onClicked: {
                if(astrology.natalMode)
                    astrology.transitMode=!astrology.transitMode;
                else astrology.eventSetupOpen=true;
            }
        }
    }

    Row {
        id: dateControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: calculationControls.bottom
        anchors.topMargin: 2
        visible: !astrology.natalMode
        height: visible ? 24 : 0
        spacing: 4

        ActionButton {
            width: 50
            height: 23
            label: astrology.celestialSource
                   ? "◀ " + astrology.celestialSource.dateStepDays + "D"
                   : "◀ --"
            labelPixelSize: 8
            accentColor: Colors.cyan
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.jumpDate(-1)
        }
        QuietText {
            width: Math.max(35,dateControls.width-50-43-50-26-34-26
                              -6*dateControls.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            color: Colors.white
            text: astrology.celestialSource
                  ? "UTC " + astrology.celestialSource.targetDayUtc
                  : "UTC --"
            elide: Text.ElideRight
        }
        ActionButton {
            width: 43
            height: 23
            label: "TODAY"
            labelPixelSize: 8
            accentColor: Colors.orange
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.returnToToday()
        }
        ActionButton {
            width: 50
            height: 23
            label: astrology.celestialSource
                   ? astrology.celestialSource.dateStepDays + "D ▶"
                   : "-- ▶"
            labelPixelSize: 8
            accentColor: Colors.cyan
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.jumpDate(1)
        }
        ActionButton {
            width: 26
            height: 23
            label: "−"
            labelPixelSize: 10
            contentPadding: 1
            accentColor: Colors.cyan
            available: astrology.sourceIdle
                       && astrology.celestialSource.dateStepDays>1
            onClicked: astrology.celestialSource.adjustDateStepDays(-1)
        }
        QuietText {
            width: 34
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            text: astrology.celestialSource
                ? "STEP " + astrology.celestialSource.dateStepDays
                : "--"
            color: Colors.yellow
            elide: Text.ElideRight
        }
        ActionButton {
            width: 26
            height: 23
            label: "+"
            labelPixelSize: 10
            contentPadding: 1
            accentColor: Colors.cyan
            available: astrology.sourceIdle
                       && astrology.celestialSource.dateStepDays<3650
            onClicked: astrology.celestialSource.adjustDateStepDays(1)
        }
    }

    Row {
        id: pairControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: dateControls.bottom
        anchors.topMargin: 2
        visible: !astrology.natalMode
        height: visible ? 23 : 0
        spacing: 4

        ActionButton {
            width: 62
            height: 22
            label: "◀ PAIR"
            labelPixelSize: 9
            accentColor: Colors.cyan
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.cyclePair(-1)
        }
        QuietText {
            width: Math.max(18,parent.width-62-62-75-3*pairControls.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            text: astrology.celestialSource
                ? astrology.celestialSource.pairLabel : "NO PAIR"
            color: Colors.magenta
            elide: Text.ElideRight
        }
        ActionButton {
            width: 62
            height: 22
            label: "PAIR ▶"
            labelPixelSize: 9
            accentColor: Colors.cyan
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.cyclePair(1)
        }
        ActionButton {
            width: 75
            height: 22
            label: astrology.celestialSource
                ? "SPAN " + astrology.celestialSource.spanDays + "D" : "SPAN --"
            labelPixelSize: 9
            accentColor: Colors.yellow
            available: astrology.sourceIdle
            onClicked: astrology.celestialSource.cycleSpan()
        }
    }

    StationMagickCelestialInstrument {
        id: instrument
        visible: !astrology.natalMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: pairControls.bottom
        anchors.bottom: eventAndTimeControls.top
        anchors.topMargin: 3
        anchors.bottomMargin: 2
        compactMode: true
        showCompactHelioControls: true
        neonEnabled: true
        visualData: astrology.calculated
                    ? astrology.celestialSource.visualData : null
        mode: astrology.subjectRoute === "magick/astrology/aspects"
              ? "aspects"
              : astrology.subjectRoute === "magick/astrology/retrogrades"
              ? "retro" : "wheel"
        // M6c // Transits route currently means two source UTC snapshots.
        zodiacPresentation: astrology.subjectRoute === "magick/astrology/transits"
                            ? "compare" : "wheel"
    }

    StationMagickNatalChartWheelPane {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: pairControls.bottom
        anchors.topMargin: 3
        anchors.bottom: eventAndTimeControls.top
        anchors.bottomMargin: 2
        visible: astrology.natalMode && !astrology.transitMode
        chartData: astrology.fullChartData
    }

    Item {
        id:transitDeck
        anchors.left:parent.left
        anchors.right:parent.right
        anchors.top:pairControls.bottom
        anchors.topMargin:3
        anchors.bottom:eventAndTimeControls.top
        anchors.bottomMargin:2
        visible: astrology.natalMode && astrology.transitMode
        clip:true

        Row {
            id:transitViewRow
            anchors.top:parent.top
            anchors.left:parent.left
            anchors.right:parent.right
            height:24
            spacing:4
            ActionButton {
                width:Math.max(33,(transitViewRow.width-3*transitViewRow.spacing)/4)
                height:23;label:"WHEEL";labelPixelSize:9
                selected:!astrology.timelineMode&&!astrology.multiMode
                    &&!astrology.matrixMode
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:{
                    astrology.timelineMode=false;
                    astrology.multiMode=false;
                    astrology.matrixMode=false;
                }
            }
            ActionButton {
                width:Math.max(33,(transitViewRow.width-3*transitViewRow.spacing)/4)
                height:23;label:"TIMELINE";labelPixelSize:9
                selected:astrology.timelineMode
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:{
                    astrology.multiMode=false;
                    astrology.matrixMode=false;
                    astrology.timelineMode=true;
                }
            }
            ActionButton {
                width:Math.max(33,(transitViewRow.width-3*transitViewRow.spacing)/4)
                height:23;label:"MULTI";labelPixelSize:9
                selected:astrology.multiMode
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:{
                    astrology.timelineMode=false;
                    astrology.matrixMode=false;
                    astrology.multiMode=true;
                }
            }
            ActionButton {
                width:Math.max(33,(transitViewRow.width-3*transitViewRow.spacing)/4)
                height:23;label:"MATRIX";labelPixelSize:9
                selected:astrology.matrixMode
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:{
                    astrology.timelineMode=false;
                    astrology.multiMode=false;
                    astrology.matrixMode=true;
                }
            }
        }

        StationMagickTransitChartPane {
            anchors.left:parent.left
            anchors.right:parent.right
            anchors.top:transitViewRow.bottom
            anchors.topMargin:3
            anchors.bottom:parent.bottom
            visible: astrology.natalMode && astrology.transitMode
                && !astrology.timelineMode && !astrology.multiMode
                && !astrology.matrixMode
            natalData: astrology.fullChartData
            transitData: transitSource.ready?transitSource.chartData:null
            expectedUtc: astrology.transitExpectedUtc
            selectedContactUtc: astrology.selectedContactUtc
            selectedEventKind: astrology.selectedEventKind
            inspectionTarget: astrology.selectedMultiBody
            inspectionNatal: astrology.selectedNatalReference
            loading: transitSource.loading
            statusText: transitSource.statusText
            onCalculateRequested: function(instant){
                astrology.selectedContactUtc="";
                astrology.selectedEventKind="aspect";
                astrology.selectedMultiBody="";
                astrology.selectedNatalReference="";
                astrology.requestTransit(instant);
            }
        }

        StationMagickTransitTimelinePane {
            anchors.left:parent.left
            anchors.right:parent.right
            anchors.top:transitViewRow.bottom
            anchors.topMargin:3
            anchors.bottom:parent.bottom
            visible: astrology.natalMode && astrology.transitMode
                && astrology.timelineMode && !astrology.multiMode
                && !astrology.matrixMode
            natalData: astrology.fullChartData
            finder: timelineSource
            onContactRequested: function(exactUtc) {
                const minute=Timeline.nearestMinute(exactUtc);
                if(!minute)return;
                astrology.selectedContactUtc=exactUtc;
                astrology.selectedEventKind="aspect";
                astrology.selectedNatalReference="";
                astrology.selectedMultiBody=
                    timelineSource.ready?timelineSource.result.transit_body:"";
                astrology.timelineMode=false;
                astrology.requestTransit(minute);
            }
        }

        StationMagickTransitMultiPane {
            anchors.left:parent.left
            anchors.right:parent.right
            anchors.top:transitViewRow.bottom
            anchors.topMargin:3
            anchors.bottom:parent.bottom
            visible: astrology.natalMode && astrology.transitMode
                && astrology.multiMode && !astrology.matrixMode
            natalData: astrology.fullChartData
            finder:multiSource
            onEventRequested: function(exactUtc,body,kind) {
                const minute=Multi.nearestMinute(exactUtc);
                if(!minute)return;
                astrology.selectedContactUtc=exactUtc;
                astrology.selectedEventKind=kind;
                astrology.selectedMultiBody=body;
                astrology.selectedNatalReference="";
                astrology.multiMode=false;
                astrology.requestTransit(minute);
            }
        }
        StationMagickTransitMatrixPane {
            anchors.left:parent.left
            anchors.right:parent.right
            anchors.top:transitViewRow.bottom
            anchors.topMargin:3
            anchors.bottom:parent.bottom
            visible:astrology.natalMode && astrology.transitMode
                && astrology.matrixMode
            natalData:astrology.fullChartData
            finder:matrixSource
            onEventRequested:function(exactUtc,natalBody,transitBody,kind){
                const minute=Matrix.nearestMinute(exactUtc);
                if(!minute)return;
                astrology.selectedContactUtc=exactUtc;
                astrology.selectedEventKind=kind;
                astrology.selectedMultiBody=transitBody;
                astrology.selectedNatalReference=natalBody;
                astrology.matrixMode=false;
                astrology.requestTransit(minute);
            }
        }

    }

    Row {
        id: eventAndTimeControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: !astrology.natalMode
        height: visible ? 23 : 0
        spacing: 3

        Repeater {
            model: [
                {id:"prev-event",label:"◀ EVENT"},
                {id:"next-event",label:"EVENT ▶"},
                {id:"prev-time",label:"◀ TIME"},
                {id:"next-time",label:"TIME ▶"},
                {id:"unlock",label:"UNLOCK"},
                {id:"reset",label:"RESET"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(1,(eventAndTimeControls.width-
                         5*eventAndTimeControls.spacing)/6)
                height: 22
                label: modelData.label
                labelPixelSize: 8
                contentPadding: 1
                accentColor: modelData.id==="reset"
                             ? Colors.orange : Colors.cyan
                available: !astrology.natalMode && instrument.graphModel.ready
                    && (modelData.id.indexOf("event")<0
                        || instrument.eventsInView.length>0)
                onClicked: {
                    if(modelData.id==="prev-event")instrument.stepToEvent(-1);
                    else if(modelData.id==="next-event")instrument.stepToEvent(1);
                    else if(modelData.id==="prev-time")astrology.stepSample(-1);
                    else if(modelData.id==="next-time")astrology.stepSample(1);
                    else if(modelData.id==="unlock"){
                        instrument.eventOrdinal=-1;
                        instrument.lockedIndex=-1;
                    } else if(modelData.id==="reset")astrology.resetChart();
                }
            }
        }
    }
    // M7a // Explicit ephemeral chart parameters, full-screen overlay.
    StationMagickEventChartSetupPane {
        anchors.fill: parent
        z: 25
        visible: astrology.eventSetupOpen
        onCloseRequested: astrology.eventSetupOpen=false
        onCalculateRequested: function(draft) {
            astrology.natalMode=true;
            astrology.eventSetupOpen=false;
            natalSource.calculate(draft);
        }
    }
}
