import QtQuick
import "../components"
import "../services/forest"
import "../services/forest/ForestCapacityPolicy.js" as CapacityPolicy

// Read-only P2C hardware view inside Forest's independent diagnostics popup.
// CHECK is an explicit local diagnostic, NOT a model readiness/admission gate.
// This view does not change the shared P0 source for header/model LIVE badges.
Item {
    id: hardware
    // Selected Tree is a UI presentation choice, not a C5 access grant.
    property string selectedModelName: ""
    readonly property bool currentModelObservation:
        selectedModelName !== ""
        && capacity.status === "OBSERVED"
        && capacity.requestedModel === selectedModelName
        && capacity.data.model.name === selectedModelName
        && capacity.data.model.matched === true
    readonly property var memoryPlacement: currentModelObservation
        ? capacity.data.model.placement : {state:"UNKNOWN",share:null,label:"?"}
    // Explicitly retained samples are historical, not current resource hints.
    property var observationA: null
    property var observationB: null
    readonly property var captureCandidate: currentModelObservation && !capacity.scanning
        ? CapacityPolicy.holdMemoryObservation(capacity.status, selectedModelName,
            capacity.data, capacity.observationSequence, capacity.lastObservedLocalTime) : null
    function clearObservations() {
        observationA = null;
        observationB = null;
    }
    onSelectedModelNameChanged: clearObservations()
    function captureObservation(slot) {
        if (!captureCandidate || !visible) return false;
        if (slot === "A") observationA = captureCandidate;
        else if (slot === "B") observationB = captureCandidate;
        else return false;
        return true;
    }
    readonly property string snapshotStatus: capacity.status
    readonly property string lastObservedLocalTime: capacity.lastObservedLocalTime
    readonly property bool checking: capacity.scanning
    readonly property var snapshot: capacity.data
    function checkNow() {
        // The only P2C request for the selected model is this operator click.
        // Switching Tree cannot reinterpret prior report as a new model.
        return capacity.inspectCapacity(selectedModelName);
    }

    ForestCapacityAdapter {
        id: capacity
    }

    Flickable {
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentHeight: reportColumn.height
        contentWidth: width

        Column {
            id: reportColumn
            width: hardware.width
            spacing: 5

            Rectangle {
                width: parent.width
                height: 28
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: checkButton.left
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: capacity.scanning ? "READING LOCAL DIAGNOSTICS"
                        : capacity.status === "OBSERVED"
                            ? "P2C OBSERVED " + capacity.lastObservedLocalTime
                        : capacity.status === "STALE" ? "P2C SNAPSHOT EXPIRED"
                        : capacity.status === "NOT_CHECKED" ? "PRESS CHECK"
                        : "OBSERVATION UNAVAILABLE"
                    font.pixelSize: 10
                    color: capacity.status === "OBSERVED" ? Colors.green : Colors.orange
                    elide: Text.ElideRight
                }
                Rectangle {
                    id: checkButton
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    anchors.verticalCenter: parent.verticalCenter
                    width: 61
                    height: 21
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Accessible.name: "Check local Forest P2C hardware diagnostics, read-only"
                    GohuText {
                        anchors.centerIn: parent
                        text: capacity.scanning ? "..." : "CHECK"
                        font.pixelSize: 9
                        color: Colors.cyan
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !capacity.scanning
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: hardware.checkNow()
                    }
                }
            }

            GohuText {
                width: parent.width
                text: "MODEL PREFLIGHT // " + (hardware.selectedModelName || "NONE SELECTED")
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.magenta
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: 48
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 8
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    text: hardware.currentModelObservation
                        ? ("INSTALLED " + (capacity.data.model.installed ? "YES" : "NO")
                            + " // RESIDENT " + (capacity.data.model.resident ? "YES" : "NO"))
                        : hardware.selectedModelName
                            ? "SELECTED MODEL NOT CHECKED // PRESS CHECK"
                            : "SELECT A MODEL TO CHECK EXACT MATCH"
                    textFormat: Text.PlainText
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    color: hardware.currentModelObservation ? Colors.green : Colors.orange
                }
                GohuText {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    text: hardware.currentModelObservation
                        ? ("ARTIFACT " + capacity.data.model.artifactMiB
                            + " / RES MEM " + capacity.data.model.residentMiB
                            + " / VRAM REP " + capacity.data.model.vramMiB + " MiB")
                        : "MODEL METRICS // UNKNOWN"
                    textFormat: Text.PlainText
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    color: Colors.cyan
                }
            }
            GohuText {
                width: parent.width
                text: hardware.currentModelObservation
                    ? "P2C TAGS/PS CROSS-CHECK // MATCH (ONE RESPONSE)"
                    : "P2C MODEL EVIDENCE // UNCHECKED OR REFUSED"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: hardware.currentModelObservation ? Colors.cyan : Colors.orange
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: placementColumn.implicitHeight + 12
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: placementColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 6
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: "MODEL MEMORY // REPORTED VRAM SHARE"
                        font.pixelSize: 10
                        color: Colors.magenta
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: hardware.memoryPlacement.state === "NOT_RESIDENT"
                            ? "NOT RESIDENT // NO SHARE"
                            : hardware.memoryPlacement.share === null
                                ? "SHARE UNKNOWN // INSUFFICIENT COUNTERS"
                                : "VRAM / REPORTED RESIDENT BYTES // " + hardware.memoryPlacement.label
                        font.pixelSize: 9
                        color: Colors.cyan
                        wrapMode: Text.WordWrap
                    }
                    Rectangle {
                        id: placementTrack
                        width: parent.width
                        height: 8
                        visible: hardware.memoryPlacement.share !== null
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.cyan
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: 1
                            width: Math.max(0, placementTrack.width - 2)
                                * (hardware.memoryPlacement.share === null ? 0 : hardware.memoryPlacement.share)
                            color: Colors.cyan
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: "CPU/GPU EXECUTION SHARE // UNKNOWN"
                        font.pixelSize: 9
                        color: Colors.orange
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "MEMORY COUNTERS ONLY // NOT GPU UTILIZATION OR HOST RAM SHARE"
                        font.pixelSize: 9
                        color: Colors.orange
                        wrapMode: Text.WordWrap
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: sampleColumn.implicitHeight + 12
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: sampleColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 6
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: "CONTEXT // MEMORY OBSERVATIONS"
                        color: Colors.magenta
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: hardware.currentModelObservation
                            && capacity.data.model.contextTokens !== null
                            ? "REPORTED CONTEXT // " + capacity.data.model.contextTokens + " TOKENS"
                            : "REPORTED CONTEXT // UNKNOWN"
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Row {
                        width: parent.width
                        spacing: 3
                        Repeater {
                            model: ["HOLD A", "HOLD B", "CLEAR"]
                            delegate: Rectangle {
                                required property string modelData
                                width: (sampleColumn.width - 6) / 3
                                height: 23
                                readonly property bool available: modelData === "CLEAR"
                                    ? !!hardware.observationA || !!hardware.observationB
                                    : !!hardware.captureCandidate
                                color: Colors.black
                                border.width: 1
                                border.color: available ? Colors.cyan : Colors.orange
                                Accessible.name: modelData + " historical resident memory observation"
                                GohuText {
                                    anchors.centerIn: parent
                                    text: parent.modelData
                                    font.pixelSize: 9
                                    color: parent.available ? Colors.cyan : Colors.orange
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: parent.available
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: {
                                        if (parent.modelData === "CLEAR") hardware.clearObservations();
                                        else hardware.captureObservation(parent.modelData === "HOLD A" ? "A" : "B");
                                    }
                                }
                            }
                        }
                    }
                    Repeater {
                        model: [hardware.observationA, hardware.observationB]
                        delegate: GohuText {
                            required property var modelData
                            required property int index
                            width: sampleColumn.width
                            text: (index === 0 ? "A" : "B") + " // " + (modelData
                                ? modelData.model + " / CHECK " + modelData.sequence
                                    + " / " + modelData.time + " / OLLAMA " + modelData.version
                                    + "\nCTX " + (modelData.contextTokens === null ? "?" : modelData.contextTokens)
                                    + " / RES " + CapacityPolicy.memoryObservationLabel(modelData.residentBytes)
                                    + " / VRAM " + CapacityPolicy.memoryObservationLabel(modelData.vramBytes)
                                : "NO HELD OBSERVATION")
                            textFormat: Text.PlainText
                            font.pixelSize: 9
                            color: Colors.cyan
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: CapacityPolicy.observationComparison(hardware.observationA, hardware.observationB)
                        font.pixelSize: 9
                        color: Colors.orange
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "HISTORICAL COUNTERS ONLY // NO PEAK OR MINIMUM REQUIREMENT"
                        font.pixelSize: 9
                        color: Colors.orange
                        wrapMode: Text.WordWrap
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "MODEL MEMORY REQUIREMENTS UNCALIBRATED // BENCHMARK HOLD"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: "HOST // SYSTEM HINTS, NOT MODEL REQUIREMENTS"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.magenta
                elide: Text.ElideRight
            }

            Rectangle {
                width: parent.width
                height: 28
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.centerIn: parent
                    text: "MEM AVAILABLE // " + capacity.data.hostRam + " MiB"
                    textFormat: Text.PlainText
                    font.pixelSize: 10
                    color: Colors.white
                }
            }
            Rectangle {
                width: parent.width
                height: 28
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.centerIn: parent
                    text: "CPU VISIBLE " + capacity.data.cpuVisible
                        + " // AFFINITY " + capacity.data.cpuAffinity
                    textFormat: Text.PlainText
                    font.pixelSize: 10
                    color: Colors.white
                }
            }
            GohuText {
                width: parent.width
                text: "DRM GPU // " + capacity.data.gpuHint
                    + " (" + capacity.data.gpuCount + " COUNTER SETS)"
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.orange
                elide: Text.ElideRight
            }
            Repeater {
                model: capacity.data.gpuCards
                delegate: Rectangle {
                    width: reportColumn.width
                    height: 44
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta
                    GohuText {
                        anchors.top: parent.top
                        anchors.topMargin: 6
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        text: modelData.card.toUpperCase()
                            + " // TOTAL " + modelData.totalMiB
                            + " MiB / USED " + modelData.usedMiB + " MiB"
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 6
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        text: "HEADROOM EST // " + modelData.headroomMiB
                            + " MiB (NOT ALLOCATABLE PROOF)"
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                }
            }
            ForestGroupObservationView {
                width: parent.width
            }
            ForestResourceFitExample {
                width: parent.width
            }
            GohuText {
                width: parent.width
                text: "NO VERIFIED OLLAMA GPU MAPPING OR C5 PERMIT"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "NO BENCHMARK / NO INFERENCE / CHECK AGAIN TO REFRESH"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
        }
    }
}
