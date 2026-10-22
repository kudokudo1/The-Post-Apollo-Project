import QtQuick
import "../../components"

// B10 passive local Time formatter presentation.
// The parent tile owns the single pre-existing one-second clock.
// There is no timer, clock service, date calculation, or preference store.
Item {
    id: timeMini

    property var timeSnapshot: null
    property bool use24Hour: true
    signal toggleHourFormat()

    readonly property bool timeReady:
        timeSnapshot !== null && timeSnapshot.state === "ready"
        && typeof timeSnapshot.displayTime === "string"
        && typeof timeSnapshot.dateLabel === "string"
        && typeof timeSnapshot.utcOffsetLabel === "string"
    readonly property string statusLine:
        timeReady
        ? "TIME // LOCAL CLOCK // " + (use24Hour ? "24H" : "12H")
        : "TIME // UNAVAILABLE"
          + (timeSnapshot && timeSnapshot.error
             ? " // " + String(timeSnapshot.error) : "")

    Column {
        anchors.fill: parent
        spacing: 3

        Row {
            id: timeRow
            width: parent.width
            height: 30
            spacing: 6

            GohuText {
                width: Math.max(20, timeRow.width - formatButton.width
                                - timeRow.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                color: timeMini.timeReady ? Colors.white : Colors.orange
                font.pixelSize: timeMini.use24Hour ? 23 : 20
                elide: Text.ElideRight
                text: timeMini.timeReady
                      ? timeMini.timeSnapshot.displayTime : "--:--:--"
            }

            ActionButton {
                id: formatButton
                width: 44
                height: 24
                label: timeMini.use24Hour ? "24H" : "12H"
                labelPixelSize: 11
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: timeMini.timeReady
                onLeftClicked: timeMini.toggleHourFormat()
            }
        }

        GohuText {
            width: parent.width
            height: 17
            font.pixelSize: 12
            color: Colors.cyan
            elide: Text.ElideRight
            text: timeMini.timeReady
                  ? timeMini.timeSnapshot.dateLabel : "LOCAL DATE UNAVAILABLE"
        }

        GohuText {
            width: parent.width
            height: 16
            font.pixelSize: 11
            color: Colors.orange
            elide: Text.ElideRight
            text: timeMini.timeReady
                  ? timeMini.timeSnapshot.utcOffsetLabel
                  : "UTC OFFSET UNKNOWN"
        }
    }
}
