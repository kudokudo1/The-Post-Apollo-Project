import QtQuick
import "../../components"

// B2 read-only CPU++ presentation. Snapshot is injected by the Hub;
// this component never accesses SystemTelemetry or starts sampling.
Item {
    id: systemMini

    property var systemSnapshot: null

    readonly property string systemState:
        systemSnapshot && systemSnapshot.state
        ? String(systemSnapshot.state) : "disconnected"
    readonly property bool systemReady:
        systemState === "ready" && systemSnapshot !== null
        && systemSnapshot.fresh === true

    // Never draw missing, stale, or invalid readings as zero-percent use.
    // Optional SWAP/rootfs readings may legitimately be absent on a ready
    // CPU/RAM observation.
    function safePercent(value) {
        if (!systemReady || typeof value !== "number"
                || !isFinite(value) || value < 0 || value > 100)
            return -1;
        return value;
    }

    readonly property real cpuUsage:
        safePercent(systemSnapshot ? systemSnapshot.cpuPercent : -1)
    readonly property real ramUsage:
        safePercent(systemSnapshot ? systemSnapshot.memoryPercent : -1)
    readonly property real swapUsage:
        safePercent(systemSnapshot ? systemSnapshot.swapPercent : -1)
    readonly property real rootUsage:
        safePercent(systemSnapshot ? systemSnapshot.rootFilesystemPercent : -1)

    readonly property int ageMinutes:
        systemSnapshot && typeof systemSnapshot.ageMinutes === "number"
        && isFinite(systemSnapshot.ageMinutes)
        && systemSnapshot.ageMinutes >= 0
        ? systemSnapshot.ageMinutes : -1

    readonly property string statusLine:
        systemReady
        ? ("CPU++ // FRESH" + (ageMinutes >= 0
           ? " // " + ageMinutes + " MIN OLD" : ""))
        : "CPU++ // " + systemState.toUpperCase().replace(/-/g, " ")

    component UsageGauge: Column {
        id: gauge

        property string labelText: ""
        property real percentValue: -1
        property bool prominent: false

        spacing: 3

        GohuText {
            width: gauge.width
            height: gauge.prominent ? 19 : 18
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: gauge.prominent ? 14 : 12
            color: gauge.percentValue >= 0 ? Colors.white : Colors.orange
            elide: Text.ElideRight
            text: gauge.labelText + "  "
                  + (gauge.percentValue >= 0
                     ? String(gauge.percentValue) + "%" : "--")
        }

        Rectangle {
            id: track
            width: gauge.width
            height: gauge.prominent ? 5 : 4
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            opacity: gauge.percentValue >= 0 ? 1.0 : 0.55

            Rectangle {
                anchors.left: parent.left
                anchors.leftMargin: 1
                anchors.verticalCenter: parent.verticalCenter
                height: Math.max(0, parent.height - 2)
                width: gauge.percentValue >= 0
                       ? Math.max(0, (track.width - 2)
                                      * gauge.percentValue / 100) : 0
                color: Colors.orange
                visible: gauge.percentValue >= 0
            }
        }
    }

    Row {
        id: metrics
        anchors.fill: parent
        spacing: 12

        Column {
            width: Math.max(0, (metrics.width - metrics.spacing) / 2)
            spacing: 9

            UsageGauge {
                width: parent.width
                labelText: "CPU"
                prominent: true
                percentValue: systemMini.cpuUsage
            }
            UsageGauge {
                width: parent.width
                labelText: "RAM"
                prominent: true
                percentValue: systemMini.ramUsage
            }
        }

        Column {
            width: Math.max(0, (metrics.width - metrics.spacing) / 2)
            spacing: 9

            UsageGauge {
                width: parent.width
                labelText: "SWAP"
                percentValue: systemMini.swapUsage
            }
            UsageGauge {
                width: parent.width
                labelText: "ROOT FS"
                percentValue: systemMini.rootUsage
            }
        }
    }
}
