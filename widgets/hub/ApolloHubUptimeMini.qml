import QtQuick
import "../../components"

// B5 mini tile: passive rendering of the ONE bridge uptimeSnapshot.
// Linux boot uptime, not Hub, Quickshell or desktop-session duration.
// The backend owns procfs reads and its one-minute refresh.
Item {
    id: uptimeMini

    property var uptimeSnapshot: null

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
        width: Math.max(0, (uptimeDigits.width - uptimeDigits.columnSpacing * 2) / 3)
        spacing: 2

        GohuText {
            width: parent.width
            height: 31
            font.pixelSize: 23
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            color: uptimeMini.uptimeReady ? Colors.white : Colors.orange
            elide: Text.ElideRight
            text: part.valueText
        }

        GohuText {
            width: parent.width
            height: 13
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            color: Colors.cyan
            text: part.unitText
        }
    }


    Column {
        anchors {
            fill: parent
        }
        spacing: 8

        GohuText {
            width: parent.width
            height: 16
            font.pixelSize: 10
            color: Colors.cyan
            elide: Text.ElideRight
            text: "LINUX // SINCE BOOT"
        }

        Grid {
            id: uptimeDigits
            width: parent.width
            columns: 3
            columnSpacing: 6

            UptimePart {
                unitText: "DAYS"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.days : -1)
            }
            UptimePart {
                unitText: "HOURS"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.hours : -1)
            }
            UptimePart {
                unitText: "MIN"
                valueText: uptimeMini.displayPart(
                    uptimeMini.uptimeSnapshot ? uptimeMini.uptimeSnapshot.minutes : -1)
            }
        }
    }
}
