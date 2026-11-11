import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import qs.services.time
import "../components"
import "../services/time/AlarmManagerPolicy.js" as Policy

// CLOCK / TOOLS / ALARM:
// All editing controls are pinned. SCHEDULE, PAUSE, and SOUND share the same
// compact control slot. Only the lower saved-alarm list scrolls; PREV/NEXT
// are owned by TimeW's persistent lower footer, not this list.
Item {
    id: pane
    clip: true

    property int selectedId: 0
    readonly property var selectedAlarm:
        Policy.byId(AlarmManagerService.document, selectedId)
    property string settingsTab: "schedule"
    property string draftMode: "weekly"
    property var draftDays: [new Date().getDay()]
    property bool draftKeepSaved: true
    property bool draftEnabled: false
    property bool draftSoundEnabled: true
    property string draftSoundId: "chime"
    property int draftVolume: 60
    property int deleteConfirmId: 0
    property bool loadingNote: false
    // An absent one-time date is an AUTO suggestion, not tomorrow by fiat.
    // Never replace a date the operator entered or explicitly moved.
    property bool loadingSelection: false
    property bool onceDateExplicit: false
    property bool noteDirty: false
    property int noteSavePendingId: 0
    property string noteSavePendingText: ""
    property string noteFeedback: ""

    readonly property bool editingActive:
        alarmSearch.activeFocus || alarmName.activeFocus
        || alarmHour.activeFocus || alarmMinute.activeFocus
        || alarmDate.activeFocus || alarmResumeDate.activeFocus
        || alarmNote.activeFocus

    readonly property var visibleAlarms: {
        const term = alarmSearch.text.toLowerCase().trim();
        const rows = AlarmManagerService.document.alarms;
        return term ? rows.filter(function(a) {
            return a.name.toLowerCase().indexOf(term) >= 0
                || String(a.id).indexOf(term) >= 0;
        }) : rows;
    }
    readonly property int selectedListIndex: visibleAlarms.findIndex(
        function(a) { return a.id === selectedId; })
    readonly property bool canStepSelection: visibleAlarms.length > 1
    readonly property string selectionLabel:
        selectedListIndex >= 0
            ? (selectedListIndex + 1) + " / " + visibleAlarms.length
            : "0 / " + visibleAlarms.length
    readonly property var dayNames: ["SUN","MON","TUE","WED","THU","FRI","SAT"]

    function canLeaveNote(id) {
        if (id === selectedId || (!noteDirty && noteSavePendingId === 0))
            return true;
        AlarmManagerService.feedback = "SAVE OR DISCARD NOTE BEFORE CHANGING ALARM";
        settingsTab = "note";
        return false;
    }
    function choose(id) {
        const a = AlarmManagerService.findAlarm(id);
        if (!a || !canLeaveNote(id)) return false;
        loadingSelection = true;
        selectedId = id;
        settingsTab = "schedule";
        deleteConfirmId = 0;
        draftMode = a.mode;
        draftDays = a.weekdays.slice();
        draftKeepSaved = a.keepSaved;
        draftEnabled = a.enabled;
        draftSoundEnabled = a.soundEnabled;
        draftSoundId = a.soundId;
        draftVolume = a.volumePercent;
        alarmName.text = a.name;
        alarmHour.text = ("0" + a.hour).slice(-2);
        alarmMinute.text = ("0" + a.minute).slice(-2);
        onceDateExplicit = a.date !== "";
        alarmDate.text = a.date || Policy.suggestedOnceDate(
            a.hour, a.minute, Date.now());
        alarmResumeDate.text = a.pausedUntilDate || "";
        loadingNote = true;
        alarmNote.text = a.note || "";
        loadingNote = false;
        noteDirty = false;
        noteFeedback = "";
        loadingSelection = false;
        return true;
    }
    function updateSuggestedOnceDate() {
        if (loadingSelection || onceDateExplicit || !selectedAlarm)
            return;
        const date = Policy.suggestedOnceDate(
            Number(alarmHour.text), Number(alarmMinute.text), Date.now());
        if (date) alarmDate.text = date;
    }
    function createScheduledTest() {
        if (!canLeaveNote(-1)) return;
        const id = AlarmManagerService.createShortTestAlarm(selectedId);
        if (id > 0) {
            alarmSearch.text = "";
            choose(id);
        }
    }
    function openNote(id) {
        // Opening the selected row's NOTE must not discard unsaved edits
        // to its name, time, weekday selection or other pinned fields.
        if (id !== selectedId && !choose(id)) return;
        settingsTab = "note";
        alarmNote.forceActiveFocus();
    }
    function saveNote() {
        if (!selectedAlarm || !AlarmManagerService.canEdit
                || noteSavePendingId !== 0) return false;
        const desired = alarmNote.text.trim();
        if (desired === (selectedAlarm.note || "")) {
            noteDirty = false;
            noteFeedback = "NOTE UNCHANGED";
            return true;
        }
        const id = selectedId;
        if (!AlarmManagerService.saveAlarmNote(id, alarmNote.text)) {
            noteFeedback = "NOTE SAVE NOT ACCEPTED";
            return false;
        }
        noteSavePendingId = id;
        noteSavePendingText = desired;
        noteDirty = true;
        noteFeedback = "SAVING // KEEP NOTE OPEN";
        return true;
    }
    function discardNote() {
        if (noteSavePendingId !== 0 || !selectedAlarm) return;
        loadingNote = true;
        alarmNote.text = selectedAlarm.note || "";
        loadingNote = false;
        noteDirty = false;
        noteFeedback = "UNSAVED NOTE DISCARDED";
    }
    function settleNoteWrite() {
        if (noteSavePendingId === 0) return;
        if (AlarmManagerService.storageState === "ready") {
            const saved = AlarmManagerService.findAlarm(noteSavePendingId);
            if (saved && (saved.note || "") === noteSavePendingText) {
                noteSavePendingId = 0;
                noteDirty = alarmNote.text.trim() !== noteSavePendingText;
                noteFeedback = "NOTE SAVED TO ALARM STORE";
            }
        } else if (AlarmManagerService.storageState === "error") {
            noteSavePendingId = 0;
            noteDirty = true;
            noteFeedback = "NOTE NOT SAVED // KEEP DRAFT VISIBLE";
            settingsTab = "note";
        }
    }
    function create() {
        if (!canLeaveNote(-1)) return;
        const id = AlarmManagerService.createAlarm();
        if (id > 0) {
            alarmSearch.text = "";
            choose(id);
        }
    }
    function copySelected() {
        if (!selectedAlarm || !canLeaveNote(-1)) return;
        const id = AlarmManagerService.duplicateAlarm(selectedId);
        if (id > 0) {
            alarmSearch.text = "";
            choose(id);
        }
    }
    function apply(arm) {
        if (!selectedAlarm) return;
        const hour = Number(alarmHour.text), minute = Number(alarmMinute.text);
        if (!/^\d{1,2}$/.test(alarmHour.text)
                || !/^\d{1,2}$/.test(alarmMinute.text)
                || hour > 23 || minute > 59) {
            AlarmManagerService.feedback = "TIME MUST BE 00:00 TO 23:59";
            return;
        }
        // Recalculate only auto-suggested one-time dates, never manually
        // chosen ones. Arming for an already-passed minute means tomorrow.
        const oneTimeDate = draftMode === "once"
            ? (onceDateExplicit ? alarmDate.text.trim()
                : Policy.suggestedOnceDate(hour, minute, Date.now())) : "";
        if (draftMode === "once" && !onceDateExplicit)
            alarmDate.text = oneTimeDate;
        const patch = {
            name: alarmName.text.trim() || "ALARM",
            hour: hour, minute: minute,
            mode: draftMode,
            weekdays: draftDays.slice(),
            date: oneTimeDate,
            keepSaved: draftKeepSaved,
            enabled: arm ? true : draftEnabled,
            soundEnabled: draftSoundEnabled,
            soundId: draftSoundId,
            volumePercent: draftVolume,
            note: alarmNote.text.trim()
        };
        const hadDraft = noteDirty;
        if (AlarmManagerService.saveAlarm(selectedId, patch)) {
            if (hadDraft) {
                noteSavePendingId = selectedId;
                noteSavePendingText = alarmNote.text.trim();
                noteFeedback = "SAVING // KEEP NOTE OPEN";
            } else {
                choose(selectedId);
            }
        }
    }
    function toggleDay(index) {
        if (draftDays.indexOf(index) >= 0)
            draftDays = draftDays.filter(function(x) { return x !== index; });
        else
            draftDays = draftDays.concat([index]).sort(function(a,b) {return a-b;});
    }
    function scheduleLabel(a) {
        if (a.mode === "once") return "ONCE " + a.date.slice(5);
        if (a.weekdays.length === 7) return "DAILY";
        const abbrev = ["SU","MO","TU","WE","TH","FR","SA"];
        return a.weekdays.map(function(d) {return abbrev[d];}).join(" ");
    }
    function shiftAlarmDate(days) {
        onceDateExplicit = true;
        const typed = alarmDate.text.trim();
        const start = Policy.validDate(typed, false)
            ? Policy.dayAt(typed, 12, 0) : Date.now();
        alarmDate.text = Policy.dateOffset(start, days);
    }
    function stepSelection(delta) {
        const rows = visibleAlarms;
        if (rows.length < 1) return;
        let idx = rows.findIndex(function(a) { return a.id === selectedId; });
        if (idx < 0)
            idx = delta > 0 ? -1 : rows.length;
        idx = Math.max(0, Math.min(rows.length - 1, idx + delta));
        if (choose(rows[idx].id))
            alarmList.positionViewAtIndex(idx, ListView.Contain);
    }
    function removeById(id) {
        if (!AlarmManagerService.canEdit) return;
        if (deleteConfirmId !== id) {
            deleteConfirmId = id;
            AlarmManagerService.feedback = "CONFIRM DELETE // PRESS RED X AGAIN";
            return;
        }
        if (!canLeaveNote(id === selectedId ? -1 : id)) return;
        deleteConfirmId = 0;
        if (AlarmManagerService.removeAlarm(id) && selectedId === id) {
            selectedId = 0;
            if (AlarmManagerService.count)
                choose(AlarmManagerService.document.alarms[0].id);
        }
    }
    onSelectedAlarmChanged: {
        if (!selectedAlarm && AlarmManagerService.count > 0)
            choose(AlarmManagerService.document.alarms[0].id);
    }
    Component.onCompleted: {
        if (AlarmManagerService.count)
            choose(AlarmManagerService.document.alarms[0].id);
    }
    Connections {
        target: AlarmManagerService
        function onCountChanged() {
            if (!pane.selectedAlarm && AlarmManagerService.count > 0)
                pane.choose(AlarmManagerService.document.alarms[0].id);
        }
        function onStorageStateChanged() {
            pane.settleNoteWrite();
        }
    }

    Column {
        id: pinnedControls
        width: pane.width
        spacing: 5

        // SEARCH, NEW, COPY and emergency STOP are one control rail.
        Row {
            id: managerCommands
            width: parent.width
            height: 32
            spacing: 5

            TextField {
                id: alarmSearch
                width: Math.max(60, managerCommands.width - newAlarm.width
                                - duplicateAlarm.width - emergencyStop.width
                                - managerCommands.spacing * 3)
                height: parent.height
                placeholderText: "SEARCH ALARMS"
                placeholderTextColor: Colors.cyan
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                leftPadding: 5
                rightPadding: 4
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: alarmSearch.activeFocus
                        ? Colors.magenta : Colors.cyan
                }
            }
            ActionButton {
                id: newAlarm
                width: 61
                height: parent.height
                label: "+ NEW"
                labelPixelSize: 10
                accentColor: Colors.orange
                available: AlarmManagerService.canEdit
                    && AlarmManagerService.count < Policy.MAX_ALARMS
                onLeftClicked: pane.create()
            }
            ActionButton {
                id: duplicateAlarm
                width: 54
                height: parent.height
                label: "COPY"
                labelPixelSize: 10
                accentColor: Colors.white
                available: pane.selectedAlarm !== null
                    && AlarmManagerService.canEdit
                    && AlarmManagerService.count < Policy.MAX_ALARMS
                onLeftClicked: pane.copySelected()
            }
            ActionButton {
                id: emergencyStop
                // This emergency action appears only when something is
                // ringing, giving the pinned SEARCH input room otherwise.
                visible: AlarmManagerService.ringingCount > 0
                width: visible ? 77 : 0
                height: parent.height
                label: "STOP ALL"
                labelPixelSize: 10
                accentColor: Colors.red
                available: AlarmManagerService.ringingCount > 0
                onLeftClicked: AlarmManagerService.stopAll()
            }
        }

        // HH, MM and NAME remain visible while the list is browsed.
        Row {
            id: entryFields
            width: parent.width
            height: 48
            spacing: 6
            visible: pane.selectedAlarm !== null

            Column {
                width: 51
                spacing: 3
                GohuText {
                    text: "HOUR"
                    color: Colors.white
                    font.pixelSize: 9
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: Colors.white
                        shadowBlur: 0.8
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                    }
                }
                TextField {
                    id: alarmHour
                    onTextChanged: pane.updateSuggestedOnceDate()
                    width: parent.width
                    height: 32
                    maximumLength: 2
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 23 }
                    color: Colors.white
                    placeholderTextColor: Colors.white
                    font.pixelSize: 12
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: Colors.white
                        shadowBlur: 0.65
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                    }
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.white
                    }
                }
            }
            Column {
                width: 51
                spacing: 3
                GohuText {
                    text: "MIN"
                    color: Colors.white
                    font.pixelSize: 9
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: Colors.white
                        shadowBlur: 0.8
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                    }
                }
                TextField {
                    id: alarmMinute
                    onTextChanged: pane.updateSuggestedOnceDate()
                    width: parent.width
                    height: 32
                    maximumLength: 2
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 59 }
                    color: Colors.white
                    placeholderTextColor: Colors.white
                    font.pixelSize: 12
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: Colors.white
                        shadowBlur: 0.65
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                    }
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.white
                    }
                }
            }
            Column {
                width: Math.max(0, entryFields.width - 102 - 2 * entryFields.spacing)
                spacing: 3
                GohuText {
                    text: "NAME"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                TextField {
                    id: alarmName
                    width: parent.width
                    height: 32
                    maximumLength: Policy.MAX_NAME_LENGTH
                    placeholderText: "ALARM NAME"
                    placeholderTextColor: Colors.cyan
                    color: Colors.magenta
                    font.pixelSize: 12
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: alarmName.activeFocus
                            ? Colors.magenta : Colors.cyan
                    }
                }
            }
        }

        Row {
            id: editTabs
            width: parent.width
            height: 29
            spacing: 4
            visible: pane.selectedAlarm !== null
            ActionButton {
                width: (editTabs.width - 3 * editTabs.spacing) / 4
                height: parent.height
                label: "SCHED"
                labelPixelSize: 9
                selected: pane.settingsTab === "schedule"
                accentColor: Colors.cyan
                onLeftClicked: pane.settingsTab = "schedule"
            }
            ActionButton {
                width: (editTabs.width - 3 * editTabs.spacing) / 4
                height: parent.height
                label: "PAUSE"
                labelPixelSize: 9
                selected: pane.settingsTab === "pause"
                accentColor: Colors.yellow
                onLeftClicked: pane.settingsTab = "pause"
            }
            ActionButton {
                width: (editTabs.width - 3 * editTabs.spacing) / 4
                height: parent.height
                label: "TONE"
                labelPixelSize: 9
                selected: pane.settingsTab === "sound"
                accentColor: Colors.cyan
                idleForegroundColor: Colors.cyan
                idleBorderColor: Colors.magenta
                idleContentGlowColor: Colors.magenta
                idleSoftGlowColor: Colors.magenta
                hoverBorderColor: Colors.magenta
                hoverContentGlowColor: Colors.magenta
                hoverSoftGlowColor: Colors.magenta
                selectedBorderColor: Colors.magenta
                selectedForegroundColor: Colors.cyan
                hoverForegroundColor: Colors.cyan
                selectedSoftGlowColor: Colors.magenta
                onLeftClicked: pane.settingsTab = "sound"
            }
            ActionButton {
                width: (editTabs.width - 3 * editTabs.spacing) / 4
                height: parent.height
                label: "NOTE"
                labelPixelSize: 9
                selected: pane.settingsTab === "note"
                accentColor: Colors.orange
                onLeftClicked: pane.settingsTab = "note"
            }
        }

        Item {
            id: editOptions
            width: parent.width
            height: 99
            clip: true
            visible: pane.selectedAlarm !== null

            // Four editors share one bounded slot. TONE and NOTE remain
            // hidden until chosen without changing the pinned layout height.
            Column {
                width: parent.width
                spacing: 5
                visible: pane.settingsTab === "schedule"
                Row {
                    id: scheduleModes
                    width: parent.width
                    height: 29
                    spacing: 6
                    ActionButton {
                        width: (scheduleModes.width - scheduleModes.spacing) / 2
                        height: parent.height
                        label: "ONE TIME"
                        labelPixelSize: 10
                        selected: pane.draftMode === "once"
                        accentColor: Colors.cyan
                        onLeftClicked: {
                            pane.draftMode = "once";
                            pane.updateSuggestedOnceDate();
                        }
                    }
                    ActionButton {
                        width: (scheduleModes.width - scheduleModes.spacing) / 2
                        height: parent.height
                        label: "REPEAT / WEEKLY"
                        labelPixelSize: 10
                        selected: pane.draftMode === "weekly"
                        accentColor: Colors.cyan
                        onLeftClicked: {
                            pane.draftMode = "weekly";
                            // A saved one-time alarm can have no weekday set.
                            // Opening weekly mode should still start with
                            // today selected, never seven defaults at once.
                            if (pane.draftDays.length === 0)
                                pane.draftDays = [new Date().getDay()];
                        }
                    }
                }
                Row {
                    id: weekChoices
                    width: parent.width
                    height: 30
                    spacing: 3
                    visible: pane.draftMode === "weekly"
                    Repeater {
                        model: pane.dayNames
                        delegate: ActionButton {
                            width: Math.max(0, (weekChoices.width
                                   - 6 * weekChoices.spacing) / 7)
                            height: parent.height
                            label: modelData
                            labelPixelSize: 9
                            selected: pane.draftDays.indexOf(index) >= 0
                            accentColor: Colors.orange
                            onLeftClicked: pane.toggleDay(index)
                        }
                    }
                }
                Row {
                    id: onceDateRow
                    width: parent.width
                    height: 30
                    spacing: 5
                    visible: pane.draftMode === "once"
                    ActionButton {
                        width: 63
                        height: parent.height
                        label: "◀ DAY"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        onLeftClicked: pane.shiftAlarmDate(-1)
                    }
                    TextField {
                        id: alarmDate
                        onTextEdited: pane.onceDateExplicit = true
                        width: Math.max(0, onceDateRow.width - 126
                                        - 2 * onceDateRow.spacing)
                        height: parent.height
                        maximumLength: 10
                        placeholderText: "YYYY-MM-DD"
                        placeholderTextColor: Colors.cyan
                        color: Colors.magenta
                        font.pixelSize: 11
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: alarmDate.activeFocus
                                ? Colors.magenta : Colors.cyan
                        }
                    }
                    ActionButton {
                        width: 63
                        height: parent.height
                        label: "DAY ▶"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        onLeftClicked: pane.shiftAlarmDate(1)
                    }
                }
                Row {
                    id: schedulingTestRow
                    width: parent.width
                    height: 29
                    spacing: 6
                    ActionButton {
                        width: pane.draftMode === "once"
                            ? (schedulingTestRow.width - schedulingTestRow.spacing) / 2 : 0
                        height: parent.height
                        visible: pane.draftMode === "once"
                        label: pane.draftKeepSaved
                            ? "KEEP AFTER RING" : "REMOVE AFTER RING"
                        labelPixelSize: 9
                        selected: pane.draftKeepSaved
                        accentColor: Colors.magenta
                        onLeftClicked: pane.draftKeepSaved = !pane.draftKeepSaved
                    }
                    ActionButton {
                        id: timedAlarmTest
                        width: pane.draftMode === "once"
                            ? (schedulingTestRow.width - schedulingTestRow.spacing) / 2
                            : schedulingTestRow.width
                        height: parent.height
                        label: "TEST // 1-2 MIN"
                        labelPixelSize: 10
                        accentColor: Colors.orange
                        available: AlarmManagerService.canEdit
                            && AlarmManagerService.count < Policy.MAX_ALARMS
                        onLeftClicked: pane.createScheduledTest()
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 6
                visible: pane.settingsTab === "pause"
                Row {
                    id: pauseRow
                    width: parent.width
                    height: 31
                    spacing: 6
                    GohuText {
                        width: 85
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        text: "RESUME ON"
                        color: Colors.cyan
                        font.pixelSize: 10
                    }
                    TextField {
                        id: alarmResumeDate
                        width: Math.max(0, pauseRow.width - 85 - 84
                                        - 2 * pauseRow.spacing)
                        height: parent.height
                        placeholderText: "YYYY-MM-DD"
                        placeholderTextColor: Colors.cyan
                        maximumLength: 10
                        color: Colors.magenta
                        font.pixelSize: 11
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: alarmResumeDate.activeFocus
                                ? Colors.magenta : Colors.cyan
                        }
                    }
                    ActionButton {
                        width: 84
                        height: parent.height
                        label: alarmResumeDate.text.trim() === "" ? "RESUME" : "PAUSE"
                        labelPixelSize: 10
                        accentColor: Colors.yellow
                        available: pane.selectedAlarm !== null
                        onLeftClicked: AlarmManagerService.pauseAlarm(
                            pane.selectedId, alarmResumeDate.text.trim())
                    }
                }
                GohuText {
                    width: parent.width
                    text: "PAUSE // ENTER FUTURE YYYY-MM-DD. CLEAR DATE + RESUME."
                    color: Colors.white
                    opacity: 0.8
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }

            Column {
                width: parent.width
                spacing: 4
                visible: pane.settingsTab === "sound"
                Row {
                    id: soundChoices
                    width: parent.width
                    height: 29
                    spacing: 5
                    Repeater {
                        model: ["chime", "soft", "urgent"]
                        delegate: ActionButton {
                            width: (soundChoices.width - 2 * soundChoices.spacing) / 3
                            height: parent.height
                            label: modelData.toUpperCase()
                            labelPixelSize: 10
                            selected: pane.draftSoundId === modelData
                            accentColor: Colors.magenta
                            onLeftClicked: pane.draftSoundId = modelData
                        }
                    }
                }
                Row {
                    id: volumeRow
                    width: parent.width
                    height: 29
                    spacing: 5
                    ActionButton {
                        width: 69
                        height: parent.height
                        label: "-10 VOL"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftVolume =
                            Math.max(0, pane.draftVolume - 10)
                    }
                    GohuText {
                        width: Math.max(0, volumeRow.width - 138
                                          - 2 * volumeRow.spacing)
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        text: "VOLUME // " + pane.draftVolume + "%"
                        color: Colors.white
                        font.pixelSize: 11
                    }
                    ActionButton {
                        width: 69
                        height: parent.height
                        label: "+10 VOL"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftVolume =
                            Math.min(100, pane.draftVolume + 10)
                    }
                }
                Row {
                    id: soundOptions
                    width: parent.width
                    height: 29
                    spacing: 5
                    ActionButton {
                        width: (soundOptions.width - soundOptions.spacing) / 2
                        height: parent.height
                        label: pane.draftSoundEnabled ? "SOUND // ON" : "SOUND // OFF"
                        labelPixelSize: 10
                        selected: pane.draftSoundEnabled
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftSoundEnabled =
                            !pane.draftSoundEnabled
                    }
                    ActionButton {
                        width: (soundOptions.width - soundOptions.spacing) / 2
                        height: parent.height
                        label: "TEST SOUND"
                        labelPixelSize: 10
                        accentColor: Colors.orange
                        onLeftClicked: AlarmManagerService.previewSound(
                            pane.draftSoundId, pane.draftVolume)
                    }
                }
            }

            Column {
                id: alarmNoteEditor
                width: parent.width
                spacing: 5
                visible: pane.settingsTab === "note"
                TextField {
                    id: alarmNote
                    width: parent.width
                    height: 31
                    maximumLength: Policy.MAX_NOTE_LENGTH
                    placeholderText: "NOTE FOR SELECTED ALARM"
                    placeholderTextColor: Colors.cyan
                    color: Colors.magenta
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    selectByMouse: true
                    readOnly: pane.noteSavePendingId !== 0
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: alarmNote.activeFocus
                            ? Colors.magenta : Colors.cyan
                    }
                    onTextChanged: {
                        if (!pane.loadingNote && pane.selectedAlarm)
                            pane.noteDirty = text.trim()
                                !== (pane.selectedAlarm.note || "");
                    }
                    onAccepted: pane.saveNote()
                }
                Row {
                    id: noteActions
                    width: parent.width
                    height: 28
                    spacing: 5
                    ActionButton {
                        width: (noteActions.width - noteActions.spacing) / 2
                        height: parent.height
                        label: "SAVE NOTE"
                        labelPixelSize: 10
                        accentColor: Colors.green
                        available: AlarmManagerService.canEdit
                            && pane.noteSavePendingId === 0
                        onLeftClicked: pane.saveNote()
                    }
                    ActionButton {
                        width: (noteActions.width - noteActions.spacing) / 2
                        height: parent.height
                        label: "DISCARD DRAFT"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        available: pane.noteSavePendingId === 0
                        onLeftClicked: pane.discardNote()
                    }
                }
                GohuText {
                    width: parent.width
                    height: 17
                    text: pane.noteFeedback || "NOTES // MAX "
                        + Policy.MAX_NOTE_LENGTH + " CHARACTERS"
                    color: Colors.white
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            id: editorActions
            width: parent.width
            height: 33
            spacing: 6
            visible: pane.selectedAlarm !== null
            ActionButton {
                width: (editorActions.width - editorActions.spacing) / 2
                height: parent.height
                label: "SAVE"
                labelPixelSize: 11
                accentColor: Colors.green
                available: AlarmManagerService.canEdit
                onLeftClicked: pane.apply(false)
            }
            ActionButton {
                width: (editorActions.width - editorActions.spacing) / 2
                height: parent.height
                label: "SAVE + ARM"
                labelPixelSize: 11
                accentColor: Colors.green
                available: AlarmManagerService.canEdit
                onLeftClicked: pane.apply(true)
            }
         }

        Row {
            id: ringActions
            width: parent.width
            height: 29
            spacing: 6
            visible: pane.selectedAlarm !== null && pane.selectedAlarm.ringing
            ActionButton {
                width: (ringActions.width - ringActions.spacing) / 2
                height: parent.height
                label: "STOP ALARM"
                labelPixelSize: 11
                accentColor: Colors.red
                onLeftClicked: AlarmManagerService.stopAlarm(pane.selectedId)
            }
            ActionButton {
                width: (ringActions.width - ringActions.spacing) / 2
                height: parent.height
                label: "SNOOZE // 5M"
                labelPixelSize: 11
                accentColor: Colors.yellow
                onLeftClicked: AlarmManagerService.snoozeAlarm(pane.selectedId)
            }
        }

        GohuText {
            width: parent.width
            height: 17
            text: "SAVED NEXT // " + AlarmManagerService.nextText(pane.selectedId)
            color: pane.selectedAlarm && pane.selectedAlarm.enabled
                   ? Colors.cyan : Colors.orange
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 17
            text: "TICK // " + (AlarmManagerService.lastSchedulerTickMs > 0
                ? new Date(AlarmManagerService.lastSchedulerTickMs).toLocaleTimeString()
                : "WAITING") + "  AUDIO // " + AlarmManagerService.audioState
            color: Colors.white
            font.pixelSize: 9
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            height: 17
            text: "STATUS // " + AlarmManagerService.feedback
            color: AlarmManagerService.storageError
                   ? Colors.orange : Colors.cyan
            font.pixelSize: 10
            elide: Text.ElideRight
        }
    }

    // Only saved alarms scroll. The navigation controls live in TimeW's
    // bottom footer, outside this clipped list and outside scroll content.
    Item {
        id: listFrame
        y: pinnedControls.y + pinnedControls.implicitHeight + 5
        width: pane.width
        height: Math.max(0, pane.height - y)
        clip: true

        ListView {
            id: alarmList
            anchors {
                top: parent.top
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                rightMargin: listRail.crossExtent + 6
            }
            clip: true
            spacing: 4
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentHeight > height
            model: pane.visibleAlarms

            delegate: Row {
                id: entry
                width: alarmList.width
                height: 40
                spacing: 2
                readonly property var rowAlarm: modelData

                // FAVORITE is always the far-left action, like Angel.
                ActionButton {
                    id: favoriteAlarm
                    width: 24
                    height: parent.height
                    label: "★"
                    labelPixelSize: 13
                    contentPadding: 2
                    selected: entry.rowAlarm.favorite === true
                    accentColor: entry.rowAlarm.favorite
                        ? Colors.magenta : Colors.white
                    idleBorderColor: entry.rowAlarm.favorite
                        ? Colors.magenta : Colors.cyan
                    selectedContentGlowColor: Colors.magenta
                    selectedSoftGlowColor: Colors.magenta
                    available: AlarmManagerService.canEdit
                    onLeftClicked: AlarmManagerService.toggleFavorite(
                        entry.rowAlarm.id)
                }
                // ON/OFF precedes the alarm selection, not after it.
                ActionButton {
                    id: toggleAlarm
                    width: 31
                    height: parent.height
                    label: entry.rowAlarm.enabled ? "ON" : "OFF"
                    selected: entry.rowAlarm.enabled
                    labelPixelSize: 9
                    contentPadding: 2
                    accentColor: entry.rowAlarm.enabled
                        ? Colors.orange : Colors.cyan
                    available: AlarmManagerService.canEdit
                    onLeftClicked: {
                        const nextState = !entry.rowAlarm.enabled;
                        if (AlarmManagerService.enableAlarm(
                                entry.rowAlarm.id, nextState)
                                && pane.selectedId === entry.rowAlarm.id)
                            pane.draftEnabled = nextState;
                    }
                }
                ActionButton {
                    id: selectAlarm
                    width: Math.max(0, entry.width - favoriteAlarm.width
                                   - toggleAlarm.width - noteAlarm.width
                                   - deleteAlarm.width - 4 * entry.spacing)
                    height: parent.height
                    selected: pane.selectedId === entry.rowAlarm.id
                    labelHorizontalAlignment: Text.AlignLeft
                    contentPadding: 4
                    labelPixelSize: 10
                    // Two lines keep the alarm's name readable in TimeW's
                    // narrow, five-action compact rows.
                    label: ("0" + entry.rowAlarm.hour).slice(-2) + ":"
                        + ("0" + entry.rowAlarm.minute).slice(-2)
                        + "\n" + entry.rowAlarm.name
                        + (entry.rowAlarm.ringing ? " RING" : "")
                        + (entry.rowAlarm.completed ? " DONE" : "")
                    accentColor: entry.rowAlarm.ringing ? Colors.magenta
                        : entry.rowAlarm.enabled ? Colors.orange : Colors.white
                    trackLabelGlowLocally: true
                    onLeftClicked: pane.choose(entry.rowAlarm.id)
                }
                // NOTE is always immediately left of the delete action.
                ActionButton {
                    id: noteAlarm
                    width: 24
                    height: parent.height
                    label: entry.rowAlarm.note ? "✎" : "+"
                    labelPixelSize: 13
                    contentPadding: 2
                    selected: pane.selectedId === entry.rowAlarm.id
                        && pane.settingsTab === "note"
                    accentColor: entry.rowAlarm.note
                        ? Colors.orange : Colors.cyan
                    available: AlarmManagerService.canEdit
                    onLeftClicked: pane.openNote(entry.rowAlarm.id)
                }
                // DELETE is always furthest right. Two clicks are required.
                ActionButton {
                    id: deleteAlarm
                    width: 24
                    height: parent.height
                    label: pane.deleteConfirmId === entry.rowAlarm.id
                        ? "!" : "×"
                    labelPixelSize: 15
                    contentPadding: 2
                    selected: pane.deleteConfirmId === entry.rowAlarm.id
                    accentColor: Colors.red
                    idleBorderColor: Colors.red
                    selectedForegroundColor: Colors.red
                    selectedBorderColor: Colors.red
                    available: AlarmManagerService.canEdit
                    onLeftClicked: pane.removeById(entry.rowAlarm.id)
                }
            }
        }

        NeonScrollBar {
            id: listRail
            flickable: alarmList
            accountForContentOrigin: true
            geometryMode: "viewport"
            x: listFrame.width - width - 3
            y: 0
            height: listFrame.height
            handleStyle: "star"
            railColor: Colors.cyan
            handleColor: Colors.magenta
            handleBorderColor: Colors.magenta
            railGlowColor: Colors.white
            containGlow: true
            visible: scrollable
        }
        GohuText {
            anchors.centerIn: parent
            visible: pane.visibleAlarms.length === 0
            text: AlarmManagerService.count > 0
                ? "NO MATCHING ALARMS" : "NO SAVED ALARMS // + NEW"
            font.pixelSize: 11
            color: Colors.cyan
        }
    }
}
