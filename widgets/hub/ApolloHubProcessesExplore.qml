import QtQuick
import QtQuick.Controls
import "../../components"

// P2-C: AppControl's owner-owned action gateway allows real inline controls.
// The gateway checks live PID+birth+name, safety locks and confirmation
// before using AppControl's existing process/limit services.
Item {
    id: processExplore

    property var processSnapshot: null
    property var processActionGate: null
    signal inputFocusChanged(bool focused)
    property int selectedPid: -1
    property int selectedStartTicks: 0
    property string selectedName: ""
    property bool detailOpen: false
    property bool confirming: false
    property int limitDraft: 100
    readonly property bool actionReady:
        validSelection && selectedStartTicks > 0
        && processActionGate !== null && !processActionGate.busy
    readonly property bool protectedProcess:
        actionReady && processActionGate.isProtected(
            selectedPid, selectedStartTicks, selectedName)
    readonly property bool ownerUnlocked:
        actionReady && processActionGate.isUnlocked(
            selectedPid, selectedStartTicks, selectedName, "freeze")

    readonly property string sourceState:
        processSnapshot && typeof processSnapshot.state === "string"
        ? processSnapshot.state : "unavailable"
    readonly property var entries:
        processSnapshot && Array.isArray(processSnapshot.items)
        ? processSnapshot.items : []
    readonly property var selectedEntry: {
        for (let i = 0; i < entries.length; ++i) {
            const item = entries[i];
            if (item && item.pid === selectedPid
                    && item.name === selectedName
                    && item.startTicks === selectedStartTicks)
                return item;
        }
        return null;
    }
    readonly property bool validSelection: selectedEntry !== null
    readonly property string statusLine:
        sourceState === "error" || sourceState === "unavailable"
        ? "PROCESSES // " + sourceState.toUpperCase()
        : detailOpen ? (validSelection
              ? "PROCESS // INLINE CONTROLS // OWNER-GATED"
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
                selectedStartTicks = item.startTicks || 0;
                selectedName = item.name;
                detailOpen = true;
                confirming = false;
                if (processActionGate)
                    limitDraft = processActionGate.currentLimitPercent(
                        selectedPid, selectedStartTicks, selectedName);
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

    function requestAction(kind) {
        if (!actionReady || confirming)
            return;
        if (processActionGate.prepare(selectedPid, selectedStartTicks,
                                      selectedName, kind, limitDraft))
            confirming = true;
    }

    function cancelAction() {
        if (processActionGate && confirming)
            processActionGate.cancel();
        confirming = false;
    }

    function confirmAction() {
        if (!processActionGate || !confirming)
            return;
        if (processActionGate.confirm())
            confirming = false;
        else
            confirming = false;
    }

    onVisibleChanged: {
        if (!visible) {
            cancelAction();
            inputFocusChanged(false);
        }
    }
    onValidSelectionChanged: {
        if (!validSelection)
            cancelAction();
    }

    Flickable {
        id: detailsScroll
        visible: processExplore.detailOpen
        anchors.top: processHeader.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: detailColumn.height

        Column {
            id: detailColumn
            width: detailsScroll.width
            height: childrenRect.height
            spacing: processExplore.height >= 300 ? 8 : 5

            GohuText {
                width: parent.width
                height: 23
                font.pixelSize: processExplore.height >= 300 ? 17 : 13
                color: processExplore.validSelection ? Colors.white : Colors.orange
                elide: Text.ElideRight
                text: processExplore.validSelection
                      ? processExplore.selectedEntry.name : "PROCESS NO LONGER OBSERVED"
            }
            GohuText {
                width: parent.width
                height: 18
                font.pixelSize: 11
                color: Colors.cyan
                text: processExplore.validSelection
                      ? "PID " + processExplore.selectedEntry.pid
                        + " // " + (processExplore.selectedEntry.stopped
                                    ? "STOPPED" : "STATE "
                                      + (processExplore.selectedEntry.state || "?"))
                      : "STALE IDENTITY // CONTROLS DISABLED"
            }
            GohuText {
                width: parent.width
                height: 18
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
                height: 33
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                color: processExplore.protectedProcess ? Colors.orange : Colors.cyan
                text: processExplore.selectedStartTicks <= 0
                      ? "NO PROCESS START TOKEN // ACTIONS LOCKED"
                      : processExplore.protectedProcess
                        ? "PROTECTED PROCESS // UNLOCK ONCE TO REQUEST"
                        : "APP CONTROL OWNER // GUARDED ACTIONS"
            }

            ActionButton {
                visible: processExplore.protectedProcess && !processExplore.confirming
                width: parent.width
                height: 27
                label: processExplore.ownerUnlocked ? "LOCK PROTECTED PROCESS"
                       : "UNLOCK ONCE // PROTECTED"
                labelPixelSize: 10
                available: processExplore.actionReady
                softGlowEnabled: false
                onLeftClicked: {
                    if (processExplore.processActionGate)
                        processExplore.processActionGate.toggleOneShotUnlock(
                            processExplore.selectedPid,
                            processExplore.selectedStartTicks,
                            processExplore.selectedName);
                }
            }

            Row {
                visible: !processExplore.confirming
                width: parent.width
                height: 30
                spacing: 5
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "FREEZE"
                    labelPixelSize: 11
                    available: processExplore.actionReady
                               && !processExplore.selectedEntry.stopped
                               && processExplore.processActionGate.isUnlocked(
                                   processExplore.selectedPid,
                                   processExplore.selectedStartTicks,
                                   processExplore.selectedName,"freeze")
                    softGlowEnabled: false
                    onLeftClicked: processExplore.requestAction("freeze")
                }
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "RESUME"
                    labelPixelSize: 11
                    available: processExplore.actionReady
                               && processExplore.selectedEntry.stopped
                               && processExplore.processActionGate.isUnlocked(
                                   processExplore.selectedPid,
                                   processExplore.selectedStartTicks,
                                   processExplore.selectedName,"resume")
                    softGlowEnabled: false
                    onLeftClicked: processExplore.requestAction("resume")
                }
            }
            Row {
                visible: !processExplore.confirming
                width: parent.width
                height: 30
                spacing: 5
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "END"
                    labelPixelSize: 11
                    available: processExplore.actionReady
                               && processExplore.processActionGate.isUnlocked(
                                   processExplore.selectedPid,
                                   processExplore.selectedStartTicks,
                                   processExplore.selectedName,"end")
                    softGlowEnabled: false
                    onLeftClicked: processExplore.requestAction("end")
                }
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "RESTART"
                    labelPixelSize: 11
                    available: processExplore.actionReady
                               && processExplore.processActionGate.isUnlocked(
                                   processExplore.selectedPid,
                                   processExplore.selectedStartTicks,
                                   processExplore.selectedName,"restart")
                    softGlowEnabled: false
                    onLeftClicked: processExplore.requestAction("restart")
                }
            }

            GohuText {
                visible: !processExplore.confirming
                width: parent.width
                height: 18
                text: "MEMORY LIMIT // " + processExplore.limitDraft + "%"
                color: Colors.cyan
                font.pixelSize: 11
            }
            Slider {
                id: limitSlider
                visible: !processExplore.confirming
                width: parent.width
                height: 29
                from: 0
                to: 100
                stepSize: 1
                value: processExplore.limitDraft
                enabled: processExplore.actionReady
                         && processExplore.processActionGate.isUnlocked(
                             processExplore.selectedPid,
                             processExplore.selectedStartTicks,
                             processExplore.selectedName,"limit")
                onMoved: processExplore.limitDraft = Math.round(value)
                onActiveFocusChanged: processExplore.inputFocusChanged(activeFocus)
            }
            ActionButton {
                visible: !processExplore.confirming
                width: parent.width
                height: 28
                label: "APPLY MEMORY LIMIT"
                labelPixelSize: 10
                available: processExplore.actionReady
                           && processExplore.processActionGate.isUnlocked(
                               processExplore.selectedPid,
                               processExplore.selectedStartTicks,
                               processExplore.selectedName,"limit")
                softGlowEnabled: false
                onLeftClicked: processExplore.requestAction("limit")
            }

            GohuText {
                width: parent.width
                height: processExplore.confirming ? 60 : 36
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                text: !processExplore.processActionGate
                      ? "APP CONTROL ACTION OWNER UNAVAILABLE"
                      : processExplore.confirming && processExplore.processActionGate.pending
                        ? "CONFIRM " + processExplore.processActionGate.pending.action.toUpperCase()
                          + " // " + processExplore.selectedName + " [" + processExplore.selectedPid + "]"
                          + (processExplore.processActionGate.pending.action === "limit"
                             ? " // " + processExplore.processActionGate.pending.percent + "%" : "")
                          + "\nCAN INTERRUPT WORK OR DESTABILIZE THIS SESSION."
                        : processExplore.processActionGate.feedback
            }
            Row {
                visible: processExplore.confirming
                width: parent.width
                height: 30
                spacing: 5
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "CANCEL"
                    softGlowEnabled: false
                    onLeftClicked: processExplore.cancelAction()
                }
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "CONFIRM ACTION"
                    labelPixelSize: 10
                    available: processExplore.actionReady
                    softGlowEnabled: false
                    onLeftClicked: processExplore.confirmAction()
                }
            }
            ActionButton {
                visible: !processExplore.confirming
                width: parent.width
                height: 28
                label: "BACK TO RUNNING"
                labelPixelSize: 10
                softGlowEnabled: false
                onLeftClicked: processExplore.detailOpen = false
            }
        }
    }
}
