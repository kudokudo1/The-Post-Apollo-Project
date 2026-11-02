import QtQuick
import "../../components"
import "../../services/system" as SystemServices
import "WeatherRelationshipPolicy.js" as RelationshipPolicy

// Compact dual-series Weather relationship inspector.
//
// Both lines are independently normalized to show shape, not magnitude.
// The parent supplies already-aligned value arrays and any statistical text.
Rectangle {
    id: inspector

    property string title: "RELATIONSHIP"
    property string leftLabel: "LEFT"
    property string rightLabel: "RIGHT"
    property var leftValues: []
    property var rightValues: []
    property string summaryText: ""
    property string footerText: ""
    property color leftColor: Colors.cyan
    property color rightColor: Colors.orange
    property int maximumPoints: 48

    readonly property var leftDisplayValues:
        graphHistory.downsampleHistory(
            RelationshipPolicy.normalized(leftValues),
            maximumPoints
        )
    readonly property var rightDisplayValues:
        graphHistory.downsampleHistory(
            RelationshipPolicy.normalized(rightValues),
            maximumPoints
        )
    readonly property int pointCount:
        Math.min(leftDisplayValues.length, rightDisplayValues.length)
    readonly property bool chartReady: pointCount >= 2

    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan
    height: 188

    SystemServices.GraphHistory {
        id: graphHistory
    }

    onLeftDisplayValuesChanged: chart.requestPaint()
    onRightDisplayValuesChanged: chart.requestPaint()
    onWidthChanged: chart.requestPaint()
    onHeightChanged: chart.requestPaint()

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 7

        Row {
            width: parent.width
            height: 18
            spacing: 10

            GohuText {
                width: Math.max(0, parent.width - 250)
                text: inspector.title
                font.pixelSize: 11
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: 240
                text: inspector.summaryText
                font.pixelSize: 9
                color: Colors.white
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }

        Row {
            width: parent.width
            height: 16
            spacing: 16

            GohuText {
                text: "● " + inspector.leftLabel
                font.pixelSize: 9
                color: inspector.leftColor
            }

            GohuText {
                text: "● " + inspector.rightLabel
                font.pixelSize: 9
                color: inspector.rightColor
            }

            QuietText {
                width: Math.max(0, parent.width - 290)
                text: "NORMALIZED SHAPE // N=" + inspector.pointCount
                font.pixelSize: 8
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }

        Rectangle {
            width: parent.width
            height: 94
            color: Colors.black
            border.width: 1
            border.color: Colors.blue

            Canvas {
                id: chart
                anchors.fill: parent
                anchors.margins: 7

                function drawSeries(context, values, colorValue, count) {
                    if (!values || values.length < 2)
                        return;
                    const points = graphHistory.linePoints(
                        values,
                        chart.width,
                        chart.height,
                        1,
                        Math.max(2, count),
                        3,
                        3
                    );
                    if (points.length < 2)
                        return;
                    context.beginPath();
                    context.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++)
                        context.lineTo(points[i].x, points[i].y);
                    context.strokeStyle =
                        graphHistory.cssColor(colorValue, 0.96);
                    context.lineWidth = 1.7;
                    context.stroke();
                }

                onPaint: {
                    const context = getContext("2d");
                    context.clearRect(0, 0, width, height);

                    context.strokeStyle =
                        graphHistory.cssColor(Colors.blue, 0.28);
                    context.lineWidth = 1;
                    for (let row = 1; row <= 3; row++) {
                        const y = row * height / 4;
                        context.beginPath();
                        context.moveTo(0, y);
                        context.lineTo(width, y);
                        context.stroke();
                    }

                    if (!inspector.chartReady)
                        return;

                    inspector.chartReady;
                    drawSeries(
                        context,
                        inspector.leftDisplayValues,
                        inspector.leftColor,
                        inspector.pointCount
                    );
                    drawSeries(
                        context,
                        inspector.rightDisplayValues,
                        inspector.rightColor,
                        inspector.pointCount
                    );
                }
            }

            GohuText {
                anchors.centerIn: parent
                visible: !inspector.chartReady
                text: "COLLECTING HISTORY // NEED ≥2 ALIGNED POINTS"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        QuietText {
            width: parent.width
            text: inspector.footerText
            font.pixelSize: 8
            wrapMode: Text.WordWrap
            color: Colors.orange
        }
    }
}
