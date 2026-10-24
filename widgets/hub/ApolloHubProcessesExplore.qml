import QtQuick
import "../../components"

// P2-B1: inspect only. The parent AppControl owns polling, process
// selection, protected-process locks, confirmation and SIGTERM/SIGSTOP.
// No OS process action is exposed until its owner publishes a typed,
// identity-validated request API. PID+name here is DISPLAY identity only.
Item {
    id: processExplore

    property var processSnapshot: null
    property bool appControlAvailable: false
    signal openAppControlRequested()
    property int selectedPid: -1
    property string selectedName: ""
    property bool detailOpen: false

    readonly property string sourceState:
        processSnapshot && typeof processSnapshot.state === "string"
        ? processSnapshot.state : "unavailable"
    readonly property var entries:
        processSnapshot && Array.isArray(processSnapshot.items)
        ? processSnapshot.items : []
    readonly property var selectedEntry: {
        for (let i = 0; i < entries.length; ++i) {
            const item = entries[i];
            if (item && item.pid === selectedPid && item.name === selectedName)
                return item;
        }
        return null;
    }
    readonly property bool validSelection: selectedEntry !== null
    readonly property string statusLine:
        sourceState === "error" || sourceState === "unavailable"
        ? "PROCESSES // " + sourceState.toUpperCase()
        : detailOpen ? (validSelection
              ? "PROCESS // OBSERVED ONLY // OPEN OWNER FOR CONTROLS"
              : "PROCESS // SELECTION NO LONGER OBSERVED")
        : "PROCESSES // " + String(processSnapshot.shown)
          + " OF " + String(processSnapshot.total)
          + (sourceState === "refreshing" ? " // REFRESHING" : " // OBSERVED")

    function inspect(item) {
        if (!item || sourceState === "error" || sourceState === "unavailable")
            return;
        for (let i = 0; i < entries.length; ++i) {
            if (entries[i] && entries[i].pid === item.pid
                    && entries[i].name === item.name) {
                selectedPid = item.pid;
                selectedName = item.name;
                detailOpen = true;
                return;
            }
        }
    }

    GohuText {
        id: processHeader
        anchors.top: parent.top
        width: parent.width
        height: 20
        font.pixelSize: 10
        color: Colors.orange
        elide: Text.ElideRight
        text: processExplore.sourceState === "unavailable"
              ? "APP CONTROL NOT CONNECTED"
              : processExplore.sourceState === "error"
                ? "PROCESS SAMPLE FAILED"
                : "OWNER SAMPLE // " + processExplore.processSnapshot.shown
                  + " OF " + processExplore.processSnapshot.total
                  + " // NOT GUARANTEED CURRENT"
    }

    Item {
        visible: !processExplore.detailOpen
        anchors.top: processHeader.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        ListView {
            id: runningList
            anchors.fill: parent
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            spacing: 3
            model: processExplore.entries
            delegate: ActionButton {
                id: runningRow
                required property var modelData
                width: runningList.width
                height: processExplore.height >= 300 ? 39 : 32
                label: String(modelData.name) + "  #" + String(modelData.pid)
                labelPixelSize: 11
                softGlowEnabled: false
                trackLabelGlowLocally: true
                onLeftClicked: processExplore.inspect(runningRow.modelData)
            }
        }
        GohuText {
            anchors.centerIn: parent
            width: parent.width
            height: 25
            visible: processExplore.entries.length === 0
            font.pixelSize: 11
            color: Colors.orange
            horizontalAlignment: Text.AlignHCenter
            text: processExplore.sourceState === "empty"
                  ? "NO PROCESSES IN SAMPLE"
                  : "PROCESS SAMPLE // " + processExplore.sourceState.toUpperCase()
        }
    }

    Item {
        visible: processExplore.detailOpen
        anchors.top: processHeader.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        Column {
            width: parent.width
            spacing: processExplore.height >= 300 ? 9 : 4

            GohuText {
                width: parent.width
                font.pixelSize: processExplore.height >= 300 ? 17 : 13
                color: processExplore.validSelection ? Colors.white : Colors.orange
                elide: Text.ElideRight
                text: processExplore.validSelection
                      ? processExplore.selectedEntry.name : "PROCESS NOT OBSERVED"
            }
            GohuText {
                width: parent.width
                font.pixelSize: 11
                color: Colors.cyan
                text: processExplore.validSelection
                      ? "PID " + processExplore.selectedEntry.pid
                        + " // " + (processExplore.selectedEntry.stopped
                                    ? "STOPPED (OBSERVED)"
                                    : "STATE " + (processExplore.selectedEntry.state || "?"))
                      : "OLD SELECTION // UNAVAILABLE"
            }
            GohuText {
                width: parent.width
                font.pixelSize: 11
                color: Colors.cyan
                text: processExplore.validSelection
                      ? "CPU " + (processExplore.selectedEntry.cpu >= 0
                                  ? processExplore.selectedEntry.cpu + "%" : "--")
                        + " // MEM " + (processExplore.selectedEntry.memoryPercent >= 0
                                       ? processExplore.selectedEntry.memoryPercent + "%" : "--")
                      : "CPU / MEMORY // UNKNOWN"
            }
            GohuText {
                width: parent.width
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
                text: "OBSERVATION ONLY // USE APP CONTROL FOR FREEZE, RESUME, END OR RESTART"
            }
            Row {
                width: parent.width
                height: 28
                spacing: 5
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "APP CONTROL"
                    labelPixelSize: 10
                    available: processExplore.appControlAvailable
                    softGlowEnabled: false
                    onLeftClicked: processExplore.openAppControlRequested()
                }
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "BACK TO RUNNING"
                    labelPixelSize: 10
                    softGlowEnabled: false
                    onLeftClicked: processExplore.detailOpen = false
                }
            }
        }
    }
}
