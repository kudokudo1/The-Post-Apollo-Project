import QtQuick
import "../../components"
import "StationInteractiveSeriesPolicy.js" as Series

// V1 // A real observation-time chart with independently scaled, labeled
// series. Source owner supplies the history; this component never fetches.
// User can inspect timestamps, switch 6/24/48h and toggle comparison.
Rectangle {
    id: inspector
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    height: 258

    property string title: "LIVE OBSERVATIONS"
    property string leftTitle: "SOLAR WIND"
    property string leftUnit: "KM/S"
    property string leftField: "solarWindSpeed"
    property color leftColor: Colors.orange
    property var leftSamples: []
    property string rightTitle: "IMF BZ"
    property string rightUnit: "NT"
    property string rightField: "bz"
    property color rightColor: Colors.magenta
    property var rightSamples: []
    property real runtimeNowMs: 0
    property string rangeId: "24h"
    property bool showRight: true
    property real hoverTimeMs: -1
    property real lockedTimeMs: -1

    readonly property real durationMs: Series.durationFor(rangeId)
    readonly property var leftModel: Series.model(leftSamples,leftField,
                                      runtimeNowMs,durationMs,192)
    readonly property var rightModel: Series.model(rightSamples,rightField,
                                       runtimeNowMs,durationMs,192)
    readonly property real activeTimeMs: lockedTimeMs > 0
                                        ? lockedTimeMs : hoverTimeMs
    readonly property var leftFocus: Series.nearestValue(leftModel,
                                       activeTimeMs,20*60000)
    readonly property var rightFocus: showRight
        ? Series.nearestValue(rightModel,activeTimeMs,20*60000) : null
    readonly property bool hasPoints:
        leftModel.count > 0 || (showRight && rightModel.count > 0)

    onLeftModelChanged: graphCanvas.requestPaint()
    onRightModelChanged: graphCanvas.requestPaint()
    onShowRightChanged: graphCanvas.requestPaint()
    onHoverTimeMsChanged: graphCanvas.requestPaint()
    onLockedTimeMsChanged: graphCanvas.requestPaint()
    onWidthChanged: graphCanvas.requestPaint()

    Column {
        id: content
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        Row {
            width: parent.width
            height: 25
            spacing: 6

            GohuText {
                width: Math.max(0,parent.width-390)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: inspector.title
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            Repeater {
                model: Series.PRESETS
                delegate: ActionButton {
                    required property var modelData
                    width: 49
                    height: 24
                    label: modelData.label
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    selected: inspector.rangeId === modelData.id
                    onClicked: {
                        inspector.rangeId = modelData.id;
                        inspector.hoverTimeMs = -1;
                        inspector.lockedTimeMs = -1;
                    }
                }
            }

            ActionButton {
                width: 91
                height: 24
                label: inspector.showRight ? "BZ: ON" : "BZ: OFF"
                labelPixelSize: 10
                selected: inspector.showRight
                accentColor: Colors.magenta
                onClicked: inspector.showRight = !inspector.showRight
            }

            ActionButton {
                width: 130
                height: 24
                label: "UNLOCK POINT"
                labelPixelSize: 9
                available: inspector.lockedTimeMs > 0
                accentColor: Colors.orange
                onClicked: inspector.lockedTimeMs = -1
            }
        }

        Row {
            width: parent.width
            height: 18
            spacing: 16

            GohuText {
                text: "● " + inspector.leftTitle + " [" + inspector.leftUnit + "]"
                      + " N=" + inspector.leftModel.count
                font.pixelSize: 10
                color: inspector.leftColor
            }
            GohuText {
                text: (inspector.showRight ? "● " : "○ ") + inspector.rightTitle
                      + " [" + inspector.rightUnit + "] N="
                      + inspector.rightModel.count
                font.pixelSize: 10
                color: inspector.rightColor
            }
            QuietText {
                text: "INDEPENDENT AXES // NO INTERPOLATION"
                font.pixelSize: 9
                color: Colors.yellow
            }
        }

        Rectangle {
            id: plotFrame
            width: parent.width
            height: 135
            color: Colors.black
            border.width: 1
            border.color: Colors.blue

            Canvas {
                id: graphCanvas
                anchors.fill: parent
                anchors.margins: 8
                renderStrategy: Canvas.Immediate
                onHeightChanged: requestPaint()

                function drawSegments(context, chart, colorValue) {
                    if (!chart || chart.count === 0)
                        return;
                    const segments = chart.segments || [];
                    context.strokeStyle = String(colorValue);
                    context.fillStyle = String(colorValue);
                    context.lineWidth = 1.8;
                    for (let i=0;i<segments.length;i++) {
                        const points=segments[i];
                        if (!points.length)continue;
                        if (points.length === 1) {
                            const dot=points[0];
                            context.beginPath();
                            context.arc(Series.xPosition(dot.timeMs,chart,width),
                                      Series.yPosition(dot.value,chart.axis,height),
                                      2.8,0,Math.PI*2);
                            context.fill();
                            continue;
                        }
                        context.beginPath();
                        for (let p=0;p<points.length;p++) {
                            const x=Series.xPosition(points[p].timeMs,chart,width);
                            const y=Series.yPosition(points[p].value,chart.axis,height);
                            if (p===0)context.moveTo(x,y);
                            else context.lineTo(x,y);
                        }
                        context.stroke();
                    }
                }

                onPaint: {
                    const context=getContext("2d");
                    context.clearRect(0,0,width,height);
                    context.lineWidth=1;
                    context.strokeStyle=String(Colors.blue);
                    context.globalAlpha=0.28;
                    for(let line=1;line<=3;line++){
                        const y=line*height/4;
                        context.beginPath();
                        context.moveTo(0,y);
                        context.lineTo(width,y);
                        context.stroke();
                    }
                    context.globalAlpha=1;
                    graphCanvas.drawSegments(context,inspector.leftModel,
                                             inspector.leftColor);
                    if(inspector.showRight)
                        graphCanvas.drawSegments(context,inspector.rightModel,
                                                 inspector.rightColor);
                    if(inspector.activeTimeMs>0 && inspector.hasPoints) {
                        const x=Series.xPosition(inspector.activeTimeMs,
                                                  inspector.leftModel,width);
                        context.globalAlpha=0.85;
                        context.strokeStyle=String(Colors.cyan);
                        context.beginPath();
                        context.moveTo(x,0);
                        context.lineTo(x,height);
                        context.stroke();
                        context.globalAlpha=1;
                    }
                }
            }

            MouseArea {
                anchors.fill: graphCanvas
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.CrossCursor

                function nearestForX(x) {
                    const fraction=Math.max(0,Math.min(1,
                                         x/Math.max(1,width)));
                    const desired=inspector.leftModel.startMs
                        +fraction*inspector.durationMs;
                    return Series.nearestTimestamp(
                         inspector.leftModel,
                         inspector.showRight ? inspector.rightModel : null,
                         desired);
                }

                onPositionChanged: function(mouse) {
                    if(inspector.lockedTimeMs>0)return;
                    inspector.hoverTimeMs=nearestForX(mouse.x);
                }
                onClicked: function(mouse) {
                    const selected=nearestForX(mouse.x);
                    if(selected>0)
                        inspector.lockedTimeMs=selected;
                }
                onExited: inspector.hoverTimeMs=-1
            }

            GohuText {
                anchors.centerIn: parent
                visible: !inspector.hasPoints
                text: "NO RECORDED SAMPLES IN THIS WINDOW"
                font.pixelSize: 11
                color: Colors.orange
            }
        }

        Row {
            width: parent.width
            height: 18
            spacing: 18

            GohuText {
                text: inspector.activeTimeMs>0
                    ? (inspector.lockedTimeMs>0 ? "LOCKED " : "HOVER ")
                      +Series.displayClock(inspector.activeTimeMs)
                    : "POINT INSPECTOR // HOVER OR CLICK"
                font.pixelSize: 9
                color: Colors.cyan
            }
            GohuText {
                text: inspector.activeTimeMs>0
                    ? inspector.leftTitle+" "+Series.formatNumber(
                        inspector.leftFocus ? inspector.leftFocus.value:null,1)
                        +" "+inspector.leftUnit
                      +" // "+inspector.rightTitle+" "+
                      (inspector.showRight
                       ? Series.formatNumber(
                           inspector.rightFocus ? inspector.rightFocus.value:null,1)
                       : "HIDDEN")+" "+inspector.rightUnit
                    : "OBSERVATION TIME // LOCAL DISPLAY"
                font.pixelSize: 9
                color: Colors.white
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            color: Colors.yellow
            text: "NOAA SWPC // WIND "
                 +Series.freshnessLabel(inspector.leftModel.lastMs,
                                        inspector.runtimeNowMs,45)
                 +" // BZ "
                 +Series.freshnessLabel(inspector.rightModel.lastMs,
                                        inspector.runtimeNowMs,45)
                 +" // SEPARATE AXES // OBSERVED TIMES"
                 + " // WIND GAPS "+inspector.leftModel.gaps
                 +" // BZ GAPS "+inspector.rightModel.gaps
                 +" // POINTS NEED OBSERVATION + RECEIPT TIMESTAMPS"
        }
    }
}
