import QtQuick
import "../../components"

// B5 mini tile: passive rendering of the ONE bridge uptimeSnapshot.
// Linux boot uptime, not Hub, Quickshell or desktop-session duration.
// The backend owns procfs reads and its one-minute refresh.
Item {
    id: uptimeMini

    property var uptimeSnapshot: null
    // Stage 7D: fill existing height without another uptime reader.
    readonly property int densityLevel: height >= 300 ? 3
                                        : height >= 180 ? 2 : 1

    readonly property string uptimeState:
        uptimeSnapshot && uptimeSnapshot.state
        ? String(uptimeSnapshot.state) : "unobserved"
    readonly property bool uptimeReady:
        uptimeState === "ready" && uptimeSnapshot !== null
        && uptimeSnapshot.ready === true
        && validPart(uptimeSnapshot.days)
        && validPart(uptimeSnapshot.hours)
        && validPart(uptimeSnapshot.minutes)
    readonly property string statusLine:
        uptimeReady ? "UPTIME // READY // APPROX"
        : uptimeState === "ready" ? "UPTIME // UNAVAILABLE"
        : "UPTIME // " + uptimeState.toUpperCase().replace(/-/g, " ")

    function validPart(value) {
        return typeof value === "number" && isFinite(value)
               && value >= 0 && Math.floor(value) === value;
    }

    function displayPart(value) {
        return uptimeReady ? String(value) : "--";
    }

    // Shared number/unit column keeps all three values aligned.
    component UptimePart: Column {
        id: part
        property string unitText: ""
        property string valueText: "--"
        property bool known: false
        readonly property int digitHeight:
            uptimeMini.densityLevel === 3 ? 76
            : uptimeMini.densityLevel === 2 ? 54 : 31
        readonly property int unitHeight:
            uptimeMini.densityLevel === 3 ? 24
            : uptimeMini.densityLevel === 2 ? 18 : 13
        spacing: uptimeMini.densityLevel === 3 ? 6
                 : uptimeMini.densityLevel === 2 ? 4 : 2
        height: digitHeight + spacing + unitHeight

        GohuText {
            width: parent.width
            height: part.digitHeight
            font.pixelSize: uptimeMini.densityLevel === 3 ? 55
                            : uptimeMini.densityLevel === 2 ? 39 : 23
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            color: part.known ? Colors.white : Colors.orange
            elide: Text.ElideRight
            text: part.valueText
        }

        GohuText {
            width: parent.width
            height: part.unitHeight
            font.pixelSize: uptimeMini.densityLevel === 3 ? 16
                            : uptimeMini.densityLevel === 2 ? 13 : 10
            horizontalAlignment: Text.AlignHCenter
            color: Colors.cyan
            text: part.unitText
        }
    }


    Column {
        id: uptimeContent
        width: parent.width
        height: childrenRect.height
        y: uptimeMini.densityLevel > 1
           ? Math.max(0, Math.floor((uptimeMini.height - height) / 2)) : 0
        spacing: uptimeMini.densityLevel === 3 ? 18
                 : uptimeMini.densityLevel === 2 ? 12 : 8

        GohuText {
            width: parent.width
            height: uptimeMini.densityLevel === 3 ? 26
                    : uptimeMini.densityLevel === 2 ? 21 : 16
            font.pixelSize: uptimeMini.densityLevel === 3 ? 16
                            : uptimeMini.densityLevel === 2 ? 13 : 10
            color: Colors.cyan
            elide: Text.ElideRight
            text: "LINUX // SINCE BOOT"
        }

        Grid {
            id: uptimeDigits
            width: parent.width
            height: childrenRect.height
            columns: 3
            columnSpacing: 6

            UptimePart {
                width: Math.max(0, (uptimeDigits.width - uptimeDigits.columnSpacing * 2) / 3)
                known: uptimeMini.uptimeReady
                unitText: "DAYS"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.days : -1)
            }
            UptimePart {
                width: Math.max(0, (uptimeDigits.width - uptimeDigits.columnSpacing * 2) / 3)
                known: uptimeMini.uptimeReady
                unitText: "HOURS"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.hours : -1)
            }
            UptimePart {
                width: Math.max(0, (uptimeDigits.width - uptimeDigits.columnSpacing * 2) / 3)
                known: uptimeMini.uptimeReady
                unitText: "MIN"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.minutes : -1)
            }
        }
    }
}
