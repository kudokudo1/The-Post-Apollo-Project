import QtQuick
import "../components"
import "../services/forest"

// Read-only P2C hardware view inside Forest's existing model popup.
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
    readonly property string snapshotStatus: capacity.status
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
                        : capacity.status === "OBSERVED" ? "LAST P2C SNAPSHOT"
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
