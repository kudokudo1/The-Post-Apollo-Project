import QtQuick
import "../../components"

// B2 read-only CPU++ presentation. Snapshot is injected by the Hub;
// this component never accesses SystemTelemetry or starts sampling.
Item {
    id: systemMini

    property var systemSnapshot: null
    // Stage 7D: only presentation follows the existing tile geometry.
    readonly property int densityLevel: height >= 300 ? 3
                                        : height >= 180 ? 2 : 1
    // During a shared telemetry refresh, B2 intentionally masks numeric
    // output. Hold only the most recent valid observation for presentation
    // while LOADING, never for errors, disconnection, or stale states.
    // This keeps gauges from collapsing to zero on every refresh.
    property var lastReadySample: null

    onSystemSnapshotChanged: {
        const sample = systemSnapshot;
        if (sample && sample.state === "ready" && sample.fresh === true) {
            const stamp = Number(sample.observedAtMs);
            if (!isFinite(stamp) || stamp <= 0) {
                lastReadySample = null;
                return;
            }
            if (lastReadySample && lastReadySample.observedAtMs === stamp)
                return;
            lastReadySample = {
                observedAtMs: stamp,
                cpuPercent: sample.cpuPercent,
                memoryPercent: sample.memoryPercent,
                swapPercent: sample.swapPercent,
                rootFilesystemPercent: sample.rootFilesystemPercent
            };
        } else if (!sample || sample.state !== "loading") {
            lastReadySample = null;
        }
    }

    readonly property bool holdingPrevious:
        systemState === "loading" && lastReadySample !== null
        && isFinite(lastReadySample.observedAtMs)
        && Date.now() >= lastReadySample.observedAtMs
        && Date.now() - lastReadySample.observedAtMs <= 300000
    readonly property var displaySample:
        systemReady ? systemSnapshot
        : holdingPrevious ? lastReadySample : null

    readonly property string systemState:
        systemSnapshot && systemSnapshot.state
        ? String(systemSnapshot.state) : "disconnected"
    readonly property bool systemReady:
        systemState === "ready" && systemSnapshot !== null
        && systemSnapshot.fresh === true

    // Never draw missing, stale, or invalid readings as zero-percent use.
    // Optional SWAP/rootfs readings may legitimately be absent on a ready
    // CPU/RAM observation; displaySample is either ready or a clearly labeled
    // last observation held only during LOADING.
    function safePercent(value) {
        if (!displaySample || typeof value !== "number"
                || !isFinite(value) || value < 0 || value > 100)
            return -1;
        return value;
    }

    readonly property real cpuUsage:
        safePercent(displaySample ? displaySample.cpuPercent : -1)
    readonly property real ramUsage:
        safePercent(displaySample ? displaySample.memoryPercent : -1)
    readonly property real swapUsage:
        safePercent(displaySample ? displaySample.swapPercent : -1)
    readonly property real rootUsage:
        safePercent(displaySample ? displaySample.rootFilesystemPercent : -1)

    readonly property int ageMinutes:
        systemSnapshot && typeof systemSnapshot.ageMinutes === "number"
        && isFinite(systemSnapshot.ageMinutes)
        && systemSnapshot.ageMinutes >= 0
        ? systemSnapshot.ageMinutes : -1

    readonly property string statusLine:
        systemReady
        ? ("CPU++ // FRESH" + (ageMinutes >= 0
           ? " // " + ageMinutes + " MIN OLD" : ""))
        : holdingPrevious ? "CPU++ // REFRESHING // LAST OBSERVATION"
        : "CPU++ // " + systemState.toUpperCase().replace(/-/g, " ")

    component UsageGauge: Column {
        id: gauge

        property string labelText: ""
        property real percentValue: -1
        property bool prominent: false
        readonly property int labelHeight:
            systemMini.densityLevel === 3 ? 40
            : systemMini.densityLevel === 2 ? 29 : 19
        readonly property int trackHeight:
            systemMini.densityLevel === 3 ? 13
            : systemMini.densityLevel === 2 ? 9 : 5
        height: labelHeight + spacing + trackHeight
        spacing: systemMini.densityLevel === 3 ? 10
                 : systemMini.densityLevel === 2 ? 6 : 3

        GohuText {
            width: gauge.width
            // Preserve the shared baseline and compact H:1 typography.
            height: gauge.labelHeight
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: systemMini.densityLevel === 3
                            ? (gauge.prominent ? 26 : 22)
                            : systemMini.densityLevel === 2
                            ? (gauge.prominent ? 19 : 17)
                            : (gauge.prominent ? 14 : 12)
            color: gauge.percentValue >= 0 ? Colors.white : Colors.orange
            elide: Text.ElideRight
            text: gauge.labelText + "  "
                  + (gauge.percentValue >= 0
                     ? String(gauge.percentValue) + "%" : "--")
        }

        Rectangle {
            id: track
            width: gauge.width
            height: gauge.trackHeight
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

    // H:1 keeps the original two-column gauge order and baselines.
    // A tall narrow tile stacks four gauges; wide tiles retain two columns.
    Grid {
        id: metrics
        width: parent.width
        height: childrenRect.height
        y: systemMini.densityLevel > 1
           ? Math.max(0, Math.floor((systemMini.height - height) / 2)) : 0
        columns: systemMini.densityLevel === 3 && width < 500 ? 1 : 2
        columnSpacing: 12
        rowSpacing: 9

        UsageGauge {
            width: Math.max(0, (metrics.width
                                - metrics.columnSpacing * (metrics.columns - 1))
                                / metrics.columns)
            labelText: "CPU"
            prominent: true
            percentValue: systemMini.cpuUsage
        }
        UsageGauge {
            width: Math.max(0, (metrics.width
                                - metrics.columnSpacing * (metrics.columns - 1))
                                / metrics.columns)
            labelText: "SWAP"
            percentValue: systemMini.swapUsage
        }
        UsageGauge {
            width: Math.max(0, (metrics.width
                                - metrics.columnSpacing * (metrics.columns - 1))
                                / metrics.columns)
            labelText: "RAM"
            prominent: true
            percentValue: systemMini.ramUsage
        }
        UsageGauge {
            width: Math.max(0, (metrics.width
                                - metrics.columnSpacing * (metrics.columns - 1))
                                / metrics.columns)
            labelText: "ROOT FS"
            percentValue: systemMini.rootUsage
        }
    }
}
