import QtQuick
import QtQuick.Controls
import "../../components"

// P3-D: presentation and edit drafts only. TimeW owns up to 8 timers,
// countdown identities, one monotonic clock and the heartbeat. No Timer here.
Item {
    id: countdownUi

    property var countdownSnapshot: null
    property int selectedTimerId: -1
    property string nameDraft: ""
    property string hoursDraft: "0"
    property string minutesDraft: "5"
    property string secondsDraft: "0"
    property bool editDirty: false
    property bool removeArmed: false
    property bool initialized: false
    property string localFeedback: ""
    signal actionRequested(int id, string action,
                           string name, string hours, string minutes, string seconds)
    signal inputFocusChanged(bool focused)

    readonly property bool ready: countdownSnapshot !== null
        && countdownSnapshot.source === "timew-monotonic-countdowns"
        && Array.isArray(countdownSnapshot.timers)
    readonly property var timers: ready ? countdownSnapshot.timers : []
    readonly property var selectedTimer: {
        for (let i = 0; i < timers.length; ++i) {
            if (timers[i] && timers[i].id === selectedTimerId)
                return timers[i];
        }
        return timers.length ? timers[0] : null;
    }
    readonly property bool timerReady:
        ready && selectedTimer !== null && selectedTimer.status === "ready"
    readonly property bool timerRunning:
        ready && selectedTimer !== null && selectedTimer.status === "running"
    readonly property string statusLine:
        ready ? "COUNTDOWN // " + String(countdownSnapshot.runningCount)
                  + " ACTIVE // " + String(timers.length) + " TIMERS"
              : "COUNTDOWN // OWNER UNAVAILABLE"

    function loadDraft(entry) {
        if (!entry) return;
        nameDraft = String(entry.name);
        hoursDraft = String(entry.hours);
        minutesDraft = String(entry.minutes);
        secondsDraft = String(entry.seconds);
        nameField.text = nameDraft;
        hoursField.text = hoursDraft;
        minutesField.text = minutesDraft;
        secondsField.text = secondsDraft;
        editDirty = false;
        removeArmed = false;
    }
    function syncSelection() {
        if (!ready) return;
        let entry = null;
        for (let i = 0; i < timers.length; ++i) {
            if (timers[i].id === selectedTimerId) {
                entry = timers[i];
                break;
            }
        }
        if (!entry && timers.length) {
            for (let j = 0; j < timers.length; ++j)
                if (timers[j].id === countdownSnapshot.selectedId)
                    entry = timers[j];
            if (!entry) entry = timers[0];
        }
        if (entry && selectedTimerId !== entry.id) {
            selectedTimerId = entry.id;
            loadDraft(entry);
        } else if (entry && !editDirty
                   && !nameField.activeFocus && !hoursField.activeFocus
                   && !minutesField.activeFocus && !secondsField.activeFocus) {
            loadDraft(entry);
        }
    }
    function selectTimer(id) {
        if (!ready) return;
        if (editDirty) {
            localFeedback = "APPLY OR RESET DRAFT BEFORE SWITCHING";
            return;
        }
        for (let i = 0; i < timers.length; ++i) {
            if (timers[i].id === id) {
                selectedTimerId = id;
                loadDraft(timers[i]);
                localFeedback = "";
                return;
            }
        }
    }
    function issue(action) {
        if (!ready || selectedTimer === null) return;
        if (editDirty) {
            localFeedback = "APPLY OR RESET DRAFT BEFORE ACTION";
            return;
        }
        removeArmed = false;
        localFeedback = "";
        actionRequested(selectedTimer.id, action, "", "", "", "");
    }
    function applyEdits() {
        if (!timerReady || !editDirty) return;
        if (nameDraft.trim().length === 0 || nameDraft.length > 32
                || !/^[0-9]{1,2}$/.test(hoursDraft)
                || !/^[0-9]{1,2}$/.test(minutesDraft)
                || !/^[0-9]{1,2}$/.test(secondsDraft)
                || Number(hoursDraft) > 99
                || Number(minutesDraft) > 59
                || Number(secondsDraft) > 59
                || (Number(hoursDraft) + Number(minutesDraft)
                    + Number(secondsDraft) === 0)) {
            localFeedback = "INVALID NAME OR DURATION // 1S MIN";
            return;
        }
        editDirty = false;
        removeArmed = false;
        localFeedback = "";
        actionRequested(selectedTimer.id, "edit", nameDraft,
                        hoursDraft, minutesDraft, secondsDraft);
    }

    Component.onCompleted: {
        initialized = true;
        syncSelection();
    }
    onCountdownSnapshotChanged: {
        if (initialized) syncSelection();
    }
    onVisibleChanged: {
        if (!visible) inputFocusChanged(false);
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: controlsColumn.height
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: controlsColumn
            width: parent.width
            height: childrenRect.height
            spacing: 6

            Row {
                width: parent.width
                height: 27
                spacing: 5
                GohuText {
                    width: Math.max(1, parent.width - newButton.width - parent.spacing)
                    height: parent.height
                    font.pixelSize: 10
                    color: Colors.cyan
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: countdownUi.statusLine
                }
                ActionButton {
                    id: newButton
                    width: 93
                    height: parent.height
                    label: "NEW TIMER"
                    labelPixelSize: 10
                    available: countdownUi.ready
                               && !countdownUi.editDirty
                               && countdownUi.timers.length
                                  < countdownUi.countdownSnapshot.maxTimers
                    softGlowEnabled: false
                    onLeftClicked: {
                        countdownUi.selectedTimerId = -1;
                        countdownUi.localFeedback = "";
                        countdownUi.actionRequested(-1,"create","","","","");
                    }
                }
            }

            ListView {
                id: timerList
                width: parent.width
                height: 34
                orientation: ListView.Horizontal
                spacing: 5
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                model: countdownUi.timers
                delegate: ActionButton {
                    required property var modelData
                    width: Math.min(143, Math.max(101, timerList.width * 0.52))
                    height: timerList.height
                    label: String(modelData.name) + " // "
                           + (modelData.status === "running" ? "ON" : modelData.status)
                    labelPixelSize: 10
                    selected: countdownUi.selectedTimer !== null
                              && countdownUi.selectedTimer.id === modelData.id
                    softGlowEnabled: false
                    onLeftClicked: countdownUi.selectTimer(modelData.id)
                }
            }

            GohuText {
                width: parent.width
                height: 37
                color: countdownUi.timerRunning ? Colors.orange : Colors.white
                font.pixelSize: 25
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: countdownUi.selectedTimer
                      ? countdownUi.selectedTimer.remaining : "--:--:--"
            }
            GohuText {
                width: parent.width
                height: 16
                color: Colors.cyan
                font.pixelSize: 10
                horizontalAlignment: Text.AlignHCenter
                text: countdownUi.selectedTimer
                      ? ("STATUS // " + countdownUi.selectedTimer.status.toUpperCase()
                         + (countdownUi.selectedTimer.error
                            ? " // " + countdownUi.selectedTimer.error : ""))
                      : "NO TIMER SELECTED"
            }

            TextField {
                id: nameField
                width: parent.width
                height: 29
                placeholderText: "TIMER NAME"
                font.pixelSize: 12
                maximumLength: 32
                color: Colors.white
                selectedTextColor: Colors.black
                selectionColor: Colors.magenta
                enabled: countdownUi.timerReady
                background: Rectangle {
                    color: Colors.black
                    border.color: nameField.activeFocus ? Colors.orange : Colors.cyan
                    radius: 0
                }
                onTextEdited: {
                    countdownUi.nameDraft = text;
                    countdownUi.editDirty = true;
                    countdownUi.removeArmed = false;
                }
                onActiveFocusChanged: countdownUi.inputFocusChanged(activeFocus)
            }
            Row {
                width: parent.width
                height: 30
                spacing: 5
                Repeater {
                    model: ["HH", "MM", "SS"]
                    delegate: Item {
                        required property string modelData
                        required property int index
                        width: Math.max(1, (parent.width - parent.spacing * 2) / 3)
                        height: parent.height
                        TextField {
                            id: digitField
                            anchors.fill: parent
                            objectName: modelData
                            placeholderText: modelData
                            maximumLength: 2
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                            color: Colors.white
                            enabled: countdownUi.timerReady
                            validator: RegularExpressionValidator {
                                regularExpression: /[0-9]{0,2}/
                            }
                            background: Rectangle {
                                color: Colors.black
                                border.color: digitField.activeFocus
                                              ? Colors.orange : Colors.cyan
                                radius: 0
                            }
                            Component.onCompleted: {
                                text = index === 0 ? countdownUi.hoursDraft
                                     : index === 1 ? countdownUi.minutesDraft
                                     : countdownUi.secondsDraft;
                            }
                            Connections {
                                target: countdownUi
                                function onSelectedTimerIdChanged() {
                                    digitField.text = index === 0 ? countdownUi.hoursDraft
                                                    : index === 1 ? countdownUi.minutesDraft
                                                    : countdownUi.secondsDraft;
                                }
                            }
                            onTextEdited: {
                                if (index === 0) countdownUi.hoursDraft = text;
                                else if (index === 1) countdownUi.minutesDraft = text;
                                else countdownUi.secondsDraft = text;
                                countdownUi.editDirty = true;
                                countdownUi.removeArmed = false;
                            }
                            onActiveFocusChanged:
                                countdownUi.inputFocusChanged(activeFocus)
                        }
                    }
                }
            }
            Row {
                width: parent.width
                height: 29
                spacing: 5
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "APPLY EDITS"
                    labelPixelSize: 10
                    available: countdownUi.timerReady && countdownUi.editDirty
                    softGlowEnabled: false
                    onLeftClicked: countdownUi.applyEdits()
                }
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "RESET DRAFT"
                    labelPixelSize: 10
                    available: countdownUi.selectedTimer !== null
                               && countdownUi.editDirty
                    softGlowEnabled: false
                    onLeftClicked: {
                        countdownUi.loadDraft(countdownUi.selectedTimer);
                        countdownUi.localFeedback = "";
                    }
                }
            }

            Row {
                width: parent.width
                height: 31
                spacing: 5
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: countdownUi.timerRunning ? "PAUSE"
                           : countdownUi.selectedTimer
                             && countdownUi.selectedTimer.status === "paused"
                           ? "RESUME" : "START"
                    labelPixelSize: 11
                    available: countdownUi.selectedTimer !== null
                               && !countdownUi.editDirty
                               && countdownUi.selectedTimer.status !== "finished"
                    softGlowEnabled: false
                    onLeftClicked: countdownUi.issue(
                        countdownUi.timerRunning ? "pause" : "start")
                }
                ActionButton {
                    width: Math.max(1, (parent.width - parent.spacing) / 2)
                    height: parent.height
                    label: "RESET"
                    labelPixelSize: 11
                    available: countdownUi.selectedTimer !== null
                               && !countdownUi.editDirty
                    softGlowEnabled: false
                    onLeftClicked: countdownUi.issue("reset")
                }
            }
            ActionButton {
                width: parent.width
                height: 29
                label: countdownUi.removeArmed ? "CONFIRM REMOVE TIMER"
                                              : "REMOVE TIMER"
                labelPixelSize: 10
                destructive: true
                available: countdownUi.ready && countdownUi.selectedTimer !== null
                           && countdownUi.timers.length > 1
                           && !countdownUi.editDirty
                softGlowEnabled: false
                onLeftClicked: {
                    if (!countdownUi.removeArmed) {
                        countdownUi.removeArmed = true;
                        countdownUi.localFeedback = "PRESS REMOVE AGAIN TO CONFIRM";
                    } else {
                        countdownUi.removeArmed = false;
                        countdownUi.issue("remove");
                    }
                }
            }
            GohuText {
                width: parent.width
                height: 35
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
                text: countdownUi.localFeedback.length
                      ? countdownUi.localFeedback
                      : countdownUi.countdownSnapshot
                        && countdownUi.countdownSnapshot.feedback
                      ? countdownUi.countdownSnapshot.feedback
                      : "TIMEW OWNER // SESSION-LOCAL TIMERS"
            }
        }
    }
}
