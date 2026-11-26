import QtQuick
import "../../components"
import "../appcontrol"
import "../../services/system"

// CPU++ owns navigation and presentation. AppControl owns the one live
// ProcessTelemetry and the birth-time-verified action gate. No second poller,
// kill/prlimit backend, detached command, or historical-census actuation.
Item {
    id: workspace
    objectName: "cpuPlusSharedKillWorkspace"
    required property var appControlWindow
    property bool active: true

    readonly property var gate: appControlWindow
        ? appControlWindow.hubProcessActionGate : null
    readonly property var taskRows: appControlWindow
        && Array.isArray(appControlWindow.taskRows)
        ? appControlWindow.taskRows : []

    property int selectedPid: 0
    property double selectedStartTicks: 0
    property string selectedComm: ""
    property bool locallyPending: false
    property int stagedLimitPercent: -1

    function matchingRow() {
        for (let i = 0; i < taskRows.length; i++) {
            const row = taskRows[i];
            if (row && row._taskRecord === true
                    && Number(row.pid) === selectedPid
                    && Number(row.startTicks) === selectedStartTicks
                    && String(row.comm || "") === selectedComm)
                return row;
        }
        return null;
    }
    readonly property var currentTask: matchingRow()
    readonly property bool exactTargetAvailable: !!gate && !!currentTask
        && !!gate.exactRow(selectedPid, selectedStartTicks, selectedComm)
    readonly property bool hasOwnedPending: !!gate && locallyPending
        && !!gate.pending && !gate.busy

    function cancelOwned() {
        if (gate && locallyPending && gate.pending && !gate.busy)
            gate.cancel();
        locallyPending = false;
    }

    function selectTarget(row) {
        if (locallyPending) cancelOwned();
        stagedLimitPercent = -1;
        history.resetDetailHistories();
        history.taskCpuHistory = [];
        history.taskMemHistory = [];
        selectedPid = Number(row && row.pid || 0);
        selectedStartTicks = Number(row && row.startTicks || 0);
        selectedComm = String(row && row.comm || "");
        history.taskHistoryPid = selectedPid;
        appendCurrentHistory();
    }

    function appendCurrentHistory() {
        const row = currentTask;
        if (!row || !active) return;
        const cpu = Number(row.cpu || 0);
        const mem = Number(row.mem || 0);
        history.taskCpuHistory =
            history.taskCpuHistory.concat([isFinite(cpu) ? cpu : 0]).slice(-132);
        history.taskMemHistory =
            history.taskMemHistory.concat([isFinite(mem) ? mem : 0]).slice(-132);
        history.taskMiniHistoryRevision += 1;
    }

    function requestRefresh() {
        if (active && appControlWindow && appControlWindow.refreshTaskManager)
            appControlWindow.refreshTaskManager();
    }

    function prepareAction(action, percent) {
        const row = currentTask;
        if (!active || !exactTargetAvailable || !gate || locallyPending)
            return false;
        const ok = gate.prepare(
            Number(row.pid), Number(row.startTicks), String(row.comm),
            action, action === "limit" ? Number(percent) : 0
        );
        if (ok) locallyPending = true;
        return !!ok;
    }

    function toggleUnlock(row) {
        if (!active || !gate || !row || !exactTargetAvailable
                || Number(row.pid) !== selectedPid
                || Number(row.startTicks) !== selectedStartTicks)
            return false;
        return gate.toggleOneShotUnlock(
            selectedPid, selectedStartTicks, selectedComm
        );
    }

    onCurrentTaskChanged: {
        if (!currentTask && locallyPending) cancelOwned();
        if (currentTask) appendCurrentHistory();
    }
    onActiveChanged: {
        if (!active) cancelOwned();
        else requestRefresh();
    }
    Component.onCompleted: requestRefresh()
    Component.onDestruction: cancelOwned()

    // Only the existing AppControl telemetry owner performs acquisition.
    // Do not keep this timer alive when CPU++ leaves PROCESS.
    Timer {
        interval: 4500
        repeat: true
        running: workspace.active && !!workspace.appControlWindow
                 && (!workspace.appControlWindow.menuOpen
                     || workspace.appControlWindow.selectedModeIndex
                        !== workspace.appControlWindow.killModeIndex)
        onTriggered: workspace.requestRefresh()
    }
    Connections {
        target: workspace.gate
        function onPendingChanged() {
            if (workspace.gate && !workspace.gate.pending)
                workspace.locallyPending = false;
        }
    }

    GraphHistory { id: graphGeometry }
    ProcessPresentationState { id: history }
    HunterPresentation {
        id: hunterGraph
        presentationState: history
        metricMode: metricCpu
    }

    QtObject {
        id: processView
        readonly property var currentTask: workspace.currentTask
        readonly property var presentation: workspace.gate
            ? workspace.gate.presentationOwner : null

        function metricIsCritical(entry, metricId) {
            return presentation ? presentation.metricIsCritical(entry, metricId) : false;
        }
        function formatMemory(kib) {
            return presentation ? presentation.formatMemory(kib) : "N/A";
        }
        function requiresDangerUnlock(entry) {
            return workspace.gate && entry
                ? workspace.gate.isProtected(Number(entry.pid),
                    Number(entry.startTicks), String(entry.comm || "")) : true;
        }
        function dangerActionUnlocked(entry, actionKind) {
            return workspace.gate && entry
                ? workspace.gate.isUnlocked(Number(entry.pid),
                    Number(entry.startTicks), String(entry.comm || ""),
                    String(actionKind || "")) : false;
        }
        function relockDangerAction(entry, actionKind) {
            // The action gate consumes one-shot unlocks on confirm/cancel.
            // A slider preview must not silently mutate shared safety state.
        }
        function hasSoftLimit() {
            return presentation && currentTask
                ? presentation.hasSoftLimit(currentTask) : false;
        }
        function limitMinimumMiB(entry) {
            return presentation && (entry || currentTask)
                ? presentation.limitMinimumMiB(entry || currentTask) : 128;
        }
        function limitMaximumMiB(entry) {
            return presentation && (entry || currentTask)
                ? presentation.limitMaximumMiB(entry || currentTask) : 8192;
        }
        function limitMiB() {
            return presentation && currentTask
                ? presentation.limitMiB(currentTask) : 0;
        }
        function limitPercent() {
            if (workspace.stagedLimitPercent >= 0)
                return workspace.stagedLimitPercent;
            return presentation && currentTask
                ? presentation.limitPercent(currentTask) : 100;
        }
        function setLimitPercent(percent) {
            if (!workspace.exactTargetAvailable) return;
            workspace.stagedLimitPercent =
                Math.max(0, Math.min(100, Math.round(Number(percent || 0))));
            // Preview only. Right bay requires APPLY then CONFIRM.
        }
        function setLimitMiB(mib) {
            if (!currentTask || !presentation) return;
            const minimum = presentation.limitMinimumMiB(currentTask);
            const maximum = presentation.limitMaximumMiB(currentTask);
            const pct = Number(mib) >= maximum ? 100
                : ((Number(mib) - minimum) / Math.max(1, maximum - minimum)) * 98.5;
            setLimitPercent(pct);
        }
        function isFrozen() {
            return presentation && currentTask
                ? presentation.isFrozen(currentTask) : false;
        }
        function requestRestart() { workspace.prepareAction("restart"); }
        function requestTerminate() { workspace.prepareAction("end"); }
        function toggleFreeze() {
            workspace.prepareAction(isFrozen() ? "resume" : "freeze");
        }
        function scopeProcessText() {
            return presentation && currentTask
                ? presentation.scopeProcessText(currentTask)
                : "NO VERIFIED LIVE PROCESS SELECTED";
        }
    }

    QtObject {
        id: taskHost
        property bool detailFocused: false
        property bool keyboardActive: false
        property bool modeRailFocused: false
        property int selectedDetailActionIndex: -1
        readonly property bool menuOpen: workspace.active
        readonly property bool hunterMetricView: false
        function setKeyboardActive(value) { keyboardActive = !!value; }
        function clearModeRailFocus() { modeRailFocused = false; }
        function setDetailFocused(value) { detailFocused = !!value; }
        function setDetailActionIndex(index) {
            selectedDetailActionIndex = Number(index);
        }
        function moveDetailSelection(direction) {
            selectedDetailActionIndex = Math.max(-2, Math.min(2,
                selectedDetailActionIndex + Number(direction || 0)));
        }
        function ensureDetailActionVisible() { }
        function isTaskMetricFavorite(entry, metricId) {
            return workspace.appControlWindow && entry
                ? workspace.appControlWindow.isTaskMetricFavorite(entry, metricId)
                : false;
        }
        function toggleTaskMetricFavorite(entry, metricId) {
            if (workspace.appControlWindow && entry)
                workspace.appControlWindow.toggleTaskMetricFavorite(entry, metricId);
        }
    }

    Component {
        id: safetyLock
        Item {
            id: safetyItem
            property var taskItem: null
            property string actionKind: "kill"
            property color accentColor: Colors.red
            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                color: Colors.black
                border.width: 1
                border.color: safetyItem.accentColor
            }
            GohuText {
                anchors.centerIn: parent
                text: workspace.gate && safetyItem.taskItem
                    && workspace.gate.isUnlocked(
                        Number(safetyItem.taskItem.pid),
                        Number(safetyItem.taskItem.startTicks),
                        String(safetyItem.taskItem.comm || ""),
                        safetyItem.actionKind) ? "◈" : "🔒"
                color: safetyItem.accentColor
                font.pixelSize: 14
            }
            MouseArea {
                anchors.fill: parent
                onClicked: workspace.toggleUnlock(safetyItem.taskItem)
            }
        }
    }

    Row {
        id: bays
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: instrumentBay
            width: Math.max(320, bays.width - targetBay.width - actuatorBay.width)
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange

            GohuText {
                id: instrumentTitle
                anchors.top: parent.top
                anchors.topMargin: 14
                anchors.horizontalCenter: parent.horizontalCenter
                text: "PROCESS // SHARED KILL DETAIL"
                color: Colors.magenta
                font.pixelSize: 12
            }
            GohuText {
                id: emptyTarget
                visible: !workspace.currentTask
                anchors.centerIn: parent
                width: parent.width - 25
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: "SELECT A LIVE PROCESS IN THE MIDDLE BAY"
                color: Colors.cyan
                font.pixelSize: 12
            }
            Flickable {
                id: detailsScroll
                anchors.top: instrumentTitle.bottom
                anchors.topMargin: 12
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 6
                clip: true
                visible: !!workspace.currentTask
                contentWidth: width
                contentHeight: details.implicitHeight + 20
                TaskManagerView {
                    id: details
                    x: 8
                    width: detailsScroll.width - 16
                    host: taskHost
                    presentationState: history
                    processController: processView
                    graphGeometry: graphGeometry
                    hunterGraph: hunterGraph
                    searchInputTarget: workspace
                    safetyLockComponent: safetyLock
                }
            }
        }

        Rectangle {
            id: targetBay
            width: 260
            height: bays.height
            color: Colors.black
            border.width: 1
            border.color: Colors.orange
            GohuText {
                id: targetTitle
                anchors.top: parent.top
                anchors.topMargin: 14
                anchors.horizontalCenter: parent.horizontalCenter
                text: "PROCESS // LIVE TARGETS"
                color: Colors.magenta
                font.pixelSize: 12
            }
            GohuText {
                id: countText
                anchors.top: targetTitle.bottom
                anchors.topMargin: 12
                anchors.horizontalCenter: parent.horizontalCenter
                text: String(workspace.taskRows.length) + " PROCESS ROWS"
                color: Colors.cyan
                font.pixelSize: 10
            }
            ListView {
                id: targets
                anchors.top: countText.bottom
                anchors.topMargin: 10
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 7
                clip: true
                spacing: 4
                model: workspace.taskRows
                delegate: Rectangle {
                    required property var modelData
                    width: targets.width
                    height: 48
                    readonly property bool selected:
                        workspace.selectedPid === Number(modelData.pid || 0)
                        && workspace.selectedStartTicks
                           === Number(modelData.startTicks || 0)
                        && workspace.selectedComm === String(modelData.comm || "")
                    color: selected ? Colors.dark : Colors.black
                    border.width: 1
                    border.color: selected ? Colors.yellow : Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 3
                        GohuText {
                            width: parent.width
                            text: String(modelData.comm || modelData.name || "PROCESS")
                            color: parent.parent.selected ? Colors.yellow : Colors.white
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }
                        GohuText {
                            text: "PID " + String(modelData.pid || "?")
                                + "  /  CPU " + Number(modelData.cpu || 0).toFixed(1) + "%"
                            color: Colors.cyan
                            font.pixelSize: 10
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: workspace.selectTarget(modelData)
                    }
                }
            }
        }

        Rectangle {
            id: actuatorBay
            width: Math.max(310, Math.floor(bays.width * 0.32))
            height: bays.height
            color: Colors.dark
            border.width: 1
            border.color: Colors.orange
            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 12
                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "CPU++ // PROCESS ACTUATORS"
                    color: Colors.magenta
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.currentTask
                        ? (String(workspace.currentTask.comm)
                           + " // PID " + workspace.selectedPid)
                        : "NO LIVE PROCESS SELECTED"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.exactTargetAvailable
                        ? "EXACT LIVE PID + START TICKS + NAME"
                        : "TARGET IDENTITY NOT VERIFIED // CONTROLS LOCKED"
                    color: workspace.exactTargetAvailable ? Colors.white : Colors.orange
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Restart, memory limit, freeze/thaw and end-process controls are the shared KILLING ACTIONS in the left bay. This bay reviews and confirms each request."
                    color: Colors.white
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    visible: workspace.stagedLimitPercent >= 0
                    text: "LIMIT PREVIEW // " + workspace.stagedLimitPercent + "%"
                    color: Colors.yellow
                    font.pixelSize: 12
                }
                Rectangle {
                    width: parent.width
                    height: 34
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.yellow
                    visible: workspace.stagedLimitPercent >= 0
                    opacity: workspace.exactTargetAvailable && !workspace.locallyPending ? 1 : 0.45
                    GohuText {
                        anchors.centerIn: parent
                        text: "APPLY LIMIT // REVIEW"
                        color: Colors.yellow
                        font.pixelSize: 11
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: workspace.exactTargetAvailable
                                 && !workspace.locallyPending
                        onClicked: workspace.prepareAction(
                            "limit", workspace.stagedLimitPercent)
                    }
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: workspace.gate ? workspace.gate.feedback : "NO SHARED ACTION OWNER"
                    color: Colors.orange
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    visible: workspace.hasOwnedPending
                    wrapMode: Text.Wrap
                    text: workspace.hasOwnedPending
                        ? ("CONFIRM " + String(workspace.gate.pending.action).toUpperCase()
                           + " FOR PID " + String(workspace.gate.pending.pid)
                           + "\nNO COMMAND HAS BEEN SENT")
                        : ""
                    color: Colors.red
                    font.pixelSize: 12
                }
                Rectangle {
                    width: parent.width
                    height: 38
                    visible: workspace.hasOwnedPending
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.red
                    GohuText {
                        anchors.centerIn: parent
                        text: "CONFIRM REQUEST"
                        color: Colors.red
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: workspace.hasOwnedPending
                        onClicked: {
                            if (workspace.gate && workspace.hasOwnedPending)
                                workspace.gate.confirm()
                        }
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 34
                    visible: workspace.hasOwnedPending
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        anchors.centerIn: parent
                        text: "CANCEL"
                        color: Colors.cyan
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: workspace.cancelOwned()
                    }
                }
                GohuText {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "Protected-process unlocks remain one-shot. Commands run only through AppControl's birth-time-verified action gate. Dispatch is not proof of success."
                    color: Colors.orange
                    font.pixelSize: 10
                }
            }
        }
    }
}
