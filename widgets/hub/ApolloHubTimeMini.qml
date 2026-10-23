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

    // Stage 7B only adapts presentation to the size already granted by the
    // Hub tile (H:1/H:2/H:3). No second timer or modified clock semantics.
    readonly property int densityLevel: height >= 300 ? 3
                                        : height >= 180 ? 2 : 1

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
        id: timeContent
        width: parent.width
        height: childrenRect.height
        spacing: timeMini.densityLevel === 3 ? 9
                 : timeMini.densityLevel === 2 ? 6 : 3
        // Compact H:1 stays top-aligned. Bigger tile chassis centers its
        // actual clock content instead of leaving a huge blank lower half.
        y: timeMini.densityLevel > 1
           ? Math.max(0, Math.floor((timeMini.height - height) / 2)) : 0

        Row {
            id: timeRow
            width: parent.width
            height: timeMini.densityLevel === 3 ? 58
                    : timeMini.densityLevel === 2 ? 44 : 30
            spacing: 6

            GohuText {
                width: Math.max(20, timeRow.width - formatButton.width
                                - timeRow.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: timeMini.densityLevel > 1
                                     ? Text.AlignHCenter : Text.AlignLeft
                color: timeMini.timeReady ? Colors.white : Colors.orange
                font.pixelSize: timeMini.densityLevel === 3
                                ? (timeMini.use24Hour ? 42 : 34)
                                : timeMini.densityLevel === 2
                                ? (timeMini.use24Hour ? 32 : 28)
                                : (timeMini.use24Hour ? 23 : 20)
                elide: Text.ElideRight
                text: timeMini.timeReady
                      ? timeMini.timeSnapshot.displayTime : "--:--:--"
            }

            ActionButton {
                id: formatButton
                width: timeMini.densityLevel > 1 ? 54 : 44
                height: timeMini.densityLevel === 3 ? 32
                        : timeMini.densityLevel === 2 ? 28 : 24
                label: timeMini.use24Hour ? "24H" : "12H"
                labelPixelSize: timeMini.densityLevel > 1 ? 12 : 11
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: timeMini.timeReady
                onLeftClicked: timeMini.toggleHourFormat()
            }
        }

        GohuText {
            width: parent.width
            height: timeMini.densityLevel === 3 ? 27
                    : timeMini.densityLevel === 2 ? 21 : 17
            font.pixelSize: timeMini.densityLevel === 3 ? 18
                            : timeMini.densityLevel === 2 ? 15 : 12
            horizontalAlignment: timeMini.densityLevel > 1
                                 ? Text.AlignHCenter : Text.AlignLeft
            color: Colors.cyan
            elide: Text.ElideRight
            text: timeMini.timeReady
                  ? timeMini.timeSnapshot.dateLabel : "LOCAL DATE UNAVAILABLE"
        }

        GohuText {
            width: parent.width
            height: timeMini.densityLevel === 3 ? 24
                    : timeMini.densityLevel === 2 ? 19 : 16
            font.pixelSize: timeMini.densityLevel === 3 ? 15
                            : timeMini.densityLevel === 2 ? 13 : 11
            horizontalAlignment: timeMini.densityLevel > 1
                                 ? Text.AlignHCenter : Text.AlignLeft
            color: Colors.orange
            elide: Text.ElideRight
            text: timeMini.timeReady
                  ? timeMini.timeSnapshot.utcOffsetLabel
                  : "UTC OFFSET UNKNOWN"
        }
    }
}
