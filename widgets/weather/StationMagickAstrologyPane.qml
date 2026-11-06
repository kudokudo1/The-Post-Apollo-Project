import QtQuick
import "../../components"

// M30-F // A standalone, no-outer-scroll source-verified astrology instrument.
// All chart modes use the existing single on-demand JPL/CelestialVisualService
// owned by WeatherStationW. No new Process, Timer, cache or interpretation.
Rectangle {
    id: astrology
    color: Colors.black
    clip: true

    property string subjectRoute: "magick/astrology/charts"
    property var celestialSource: null

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
            width: Math.max(0,parent.width-206)
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
            text: astrology.celestialSource
                ? astrology.celestialSource.statusText
                : "JPL UNAVAILABLE"
            color: astrology.calculated ? Colors.cyan : Colors.orange
            elide: Text.ElideRight
        }
        ActionButton {
            width: 96
            height: 25
            label: astrology.celestialSource && astrology.celestialSource.loading
                   ? "CALCULATING" : "CALCULATE"
            labelPixelSize: 9
            accentColor: Colors.magenta
            available: astrology.chartAvailable
            // The only JPL launch point, controlled by explicit user click.
            onClicked: astrology.celestialSource.refresh()
        }
    }

    Row {
        id: dateControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: calculationControls.bottom
        anchors.topMargin: 2
        height: 24
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
        height: 23
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
    }

    Row {
        id: eventAndTimeControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 23
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
                available: instrument.graphModel.ready
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
}
