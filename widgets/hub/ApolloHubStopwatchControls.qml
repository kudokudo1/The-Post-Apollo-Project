import QtQuick
import "../../components"

// P3 TimeW: same owner stopwatch, two control surfaces.
// No Timer, ElapsedTimer, Date clock or new stopwatch state lives here.
Item {
    id: stopwatchUi

    property var stopwatchSnapshot: null
    signal actionRequested(string action)

    readonly property bool ready:
        stopwatchSnapshot !== null
        && stopwatchSnapshot.source === "timew-monotonic-stopwatch"
        && typeof stopwatchSnapshot.elapsed === "string"
    readonly property bool running: ready && stopwatchSnapshot.running === true
    readonly property bool started: ready && stopwatchSnapshot.started === true
    readonly property int lapCount:
        ready ? Number(stopwatchSnapshot.lapCount) : 0
    readonly property int lapLimit:
        ready ? Number(stopwatchSnapshot.lapLimit) : 0
    readonly property var recentLaps:
        ready && Array.isArray(stopwatchSnapshot.recentLaps)
        ? stopwatchSnapshot.recentLaps : []
    readonly property string statusLine:
        ready ? "STOPWATCH // " + (running ? "RUNNING" : started ? "PAUSED" : "READY")
              + " // LAPS " + String(lapCount) : "STOPWATCH // OWNER UNAVAILABLE"

    Column {
        anchors.fill: parent
        spacing: 5

        GohuText {
            width: parent.width
            height: stopwatchUi.height >= 300 ? 45 : 36
            font.pixelSize: stopwatchUi.height >= 300 ? 27 : 22
            color: stopwatchUi.ready ? Colors.white : Colors.orange
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            text: stopwatchUi.ready
                  ? stopwatchUi.stopwatchSnapshot.elapsed : "--:--:--.--"
        }
        GohuText {
            width: parent.width
            height: 18
            color: stopwatchUi.running ? Colors.orange : Colors.cyan
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            text: stopwatchUi.statusLine
        }

        Row {
            width: parent.width
            height: 30
            spacing: 5
            ActionButton {
                width: Math.max(1,(parent.width-parent.spacing)/2)
                height: parent.height
                label: stopwatchUi.running ? "PAUSE" : "START"
                labelPixelSize: 12
                available: stopwatchUi.ready
                softGlowEnabled: false
                onLeftClicked: stopwatchUi.actionRequested(
                    stopwatchUi.running ? "pause" : "start")
            }
            ActionButton {
                width: Math.max(1,(parent.width-parent.spacing)/2)
                height: parent.height
                label: "LAP"
                labelPixelSize: 12
                available: stopwatchUi.running
                           && stopwatchUi.lapCount < stopwatchUi.lapLimit
                softGlowEnabled: false
                onLeftClicked: stopwatchUi.actionRequested("lap")
            }
        }
        ActionButton {
            width: parent.width
            height: 29
            label: "RESET STOPWATCH"
            labelPixelSize: 11
            available: stopwatchUi.ready && !stopwatchUi.running
                       && stopwatchUi.started
            softGlowEnabled: false
            onLeftClicked: stopwatchUi.actionRequested("reset")
        }

        GohuText {
            visible: stopwatchUi.height >= 300
            width: parent.width
            height: 17
            font.pixelSize: 10
            color: Colors.cyan
            horizontalAlignment: Text.AlignHCenter
            text: "RECENT LAPS // " + String(stopwatchUi.lapCount)
        }
        Repeater {
            model: stopwatchUi.height >= 300
                   ? stopwatchUi.recentLaps : []
            delegate: GohuText {
                required property var modelData
                width: stopwatchUi.width
                height: 19
                font.pixelSize: 10
                color: Colors.white
                elide: Text.ElideRight
                text: "LAP " + String(modelData.index)
                      + " // +" + String(modelData.split)
                      + " // " + String(modelData.total)
            }
        }
    }
}
