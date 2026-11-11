import QtQuick
import QtQuick.Controls
import qs.services.time
import "../components"
import "../services/time/AlarmManagerPolicy.js" as Policy

// Single compact face for independent saved alarms. List and editor scroll
// independently; header and emergency STOP ALL remain available.
Column {
    id: pane
    spacing: 8
    property int selectedId: 0
    readonly property var selectedAlarm: AlarmManagerService.findAlarm(selectedId)
    property string draftMode: "weekly"
    property var draftDays: [0, 1, 2, 3, 4, 5, 6]
    property bool draftKeepSaved: true
    property bool draftEnabled: false
    property bool draftSoundEnabled: true
    property string draftSoundId: "chime"
    property int draftVolume: 60
    property int deleteConfirmId: 0
    readonly property bool editingActive:
        alarmSearch.activeFocus || alarmName.activeFocus
        || alarmHour.activeFocus || alarmMinute.activeFocus
        || alarmDate.activeFocus || alarmResumeDate.activeFocus

    readonly property var visibleAlarms: {
        const term = alarmSearch.text.toLowerCase().trim();
        const rows = AlarmManagerService.document.alarms;
        return term ? rows.filter(function(a) {
            return a.name.toLowerCase().indexOf(term) >= 0
                || String(a.id).indexOf(term) >= 0;
        }) : rows;
    }
    readonly property var days: ["SUN","MON","TUE","WED","THU","FRI","SAT"]

    function choose(id) {
        const a = AlarmManagerService.findAlarm(id);
        if (!a) return;
        selectedId = id;
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
        alarmDate.text = a.date || Policy.dateOffset(Date.now(), 1);
        alarmResumeDate.text = a.pausedUntilDate || "";
        editorScroll.contentY = 0;
    }
    function create() {
        const id = AlarmManagerService.createAlarm();
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
        const patch = {
            name: alarmName.text.trim() || "ALARM",
            hour: hour, minute: minute,
            mode: draftMode,
            weekdays: draftDays.slice(),
            date: draftMode === "once" ? alarmDate.text.trim() : "",
            keepSaved: draftKeepSaved,
            enabled: arm ? true : draftEnabled,
            soundEnabled: draftSoundEnabled,
            soundId: draftSoundId,
            volumePercent: draftVolume
        };
        if (AlarmManagerService.saveAlarm(selectedId, patch))
            choose(selectedId);
    }
    function toggleDay(index) {
        if (draftDays.indexOf(index) >= 0)
            draftDays = draftDays.filter(function(x) { return x !== index; });
        else
            draftDays = draftDays.concat([index]).sort(function(a,b) {return a-b;});
    }
    function stepSelection(delta) {
        const rows = visibleAlarms;
        if (rows.length < 1) return;
        let idx = rows.findIndex(function(a) { return a.id === selectedId; });
        idx = Math.max(0, Math.min(rows.length - 1, idx + delta));
        choose(rows[idx].id);
        alarmList.positionViewAtIndex(idx, ListView.Contain);
    }
    onSelectedAlarmChanged: {
        if (!selectedAlarm && AlarmManagerService.count > 0)
            choose(AlarmManagerService.document.alarms[0].id);
    }
    Component.onCompleted: {
        if (AlarmManagerService.count)
            choose(AlarmManagerService.document.alarms[0].id);
    }

    Row {
        id: headerRow
        height: 34
        width: pane.width
        spacing: 6
        GohuText {
            width: Math.max(0, headerRow.width - newAlarm.width
                             - emergencyStop.width - 2 * headerRow.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            text: "ALARMS // " + AlarmManagerService.count + " / " + Policy.MAX_ALARMS
            color: Colors.cyan
            font.pixelSize: 12
        }
        ActionButton {
            id: emergencyStop
            width: 88
            height: parent.height
            label: "STOP ALL"
            labelPixelSize: 10
            accentColor: Colors.red
            available: AlarmManagerService.ringingCount > 0
            onLeftClicked: AlarmManagerService.stopAll()
        }
        ActionButton {
            id: newAlarm
            width: 77
            height: parent.height
            label: "+ NEW"
            labelPixelSize: 10
            accentColor: Colors.orange
            available: AlarmManagerService.canEdit
                && AlarmManagerService.count < Policy.MAX_ALARMS
            onLeftClicked: pane.create()
        }
    }

    TextField {
        id: alarmSearch
        width: pane.width
        height: 30
        placeholderText: "SEARCH SAVED ALARMS"
        placeholderTextColor: Colors.cyan
        color: Colors.magenta
        selectionColor: Colors.magenta
        selectedTextColor: Colors.black
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: 11
        background: Rectangle {
            color: Colors.black
            border.width: 1
            border.color: alarmSearch.activeFocus ? Colors.magenta : Colors.cyan
        }
    }

    Item {
        id: listFrame
        width: pane.width
        height: 155
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
            model: pane.visibleAlarms
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds
            delegate: Row {
                id: entry
                width: alarmList.width
                height: 37
                spacing: 5
                readonly property var rowAlarm: modelData
                ActionButton {
                    width: Math.max(0, entry.width - toggleAlarm.width - entry.spacing)
                    height: parent.height
                    selected: pane.selectedId === entry.rowAlarm.id
                    labelHorizontalAlignment: Text.AlignLeft
                    labelPixelSize: 10
                    label: ("0" + entry.rowAlarm.hour).slice(-2) + ":"
                        + ("0" + entry.rowAlarm.minute).slice(-2) + " // "
                        + entry.rowAlarm.name
                        + (entry.rowAlarm.ringing ? " // RINGING" : "")
                        + (entry.rowAlarm.completed ? " // DONE" : "")
                    accentColor: entry.rowAlarm.ringing ? Colors.magenta
                        : entry.rowAlarm.enabled ? Colors.orange : Colors.white
                    trackLabelGlowLocally: true
                    onLeftClicked: pane.choose(entry.rowAlarm.id)
                }
                ActionButton {
                    id: toggleAlarm
                    width: 61
                    height: parent.height
                    label: entry.rowAlarm.enabled ? "ON" : "OFF"
                    selected: entry.rowAlarm.enabled
                    labelPixelSize: 10
                    accentColor: entry.rowAlarm.enabled ? Colors.orange : Colors.cyan
                    available: AlarmManagerService.canEdit
                    onLeftClicked: {
                        AlarmManagerService.enableAlarm(
                            entry.rowAlarm.id, !entry.rowAlarm.enabled);
                        if (pane.selectedId === entry.rowAlarm.id)
                            pane.draftEnabled = !entry.rowAlarm.enabled;
                    }
                }
            }
        }
        NeonScrollBar {
            id: listRail
            flickable: alarmList
            accountForContentOrigin: true
            geometryMode: "viewport"
            x: listFrame.width - width - 3
            y: alarmList.y
            height: alarmList.height
            handleStyle: "star"
            railColor: Colors.cyan
            handleColor: Colors.magenta
            handleBorderColor: Colors.magenta
            railGlowColor: Colors.white
            containGlow: true
            visible: scrollable
        }
    }

    Row {
        id: panRow
        width: pane.width
        height: 27
        spacing: 8
        ActionButton {
            width: (panRow.width - panRow.spacing) / 2
            height: parent.height
            label: "◀ PREVIOUS"
            labelPixelSize: 10
            accentColor: Colors.white
            available: pane.visibleAlarms.length > 1
            onLeftClicked: pane.stepSelection(-1)
        }
        ActionButton {
            width: (panRow.width - panRow.spacing) / 2
            height: parent.height
            label: "NEXT ▶"
            labelPixelSize: 10
            accentColor: Colors.white
            available: pane.visibleAlarms.length > 1
            onLeftClicked: pane.stepSelection(1)
        }
    }

    GohuText {
        width: pane.width
        text: pane.selectedAlarm
            ? "EDIT // #" + pane.selectedId + " // "
              + AlarmManagerService.nextText(pane.selectedId)
            : "SELECT AN ALARM OR PRESS + NEW"
        color: Colors.cyan
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }

    Item {
        id: editorFrame
        width: pane.width
        height: 264
        visible: pane.selectedAlarm !== null
        Flickable {
            id: editorScroll
            anchors {
                top: parent.top
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                rightMargin: editorRail.crossExtent + 6
            }
            contentWidth: width
            contentHeight: editorContent.implicitHeight
            clip: true
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: editorContent
                width: editorScroll.width
                spacing: 8
                Row {
                    id: entryFields
                    width: parent.width
                    height: 56
                    spacing: 6
                    Column {
                        width: 51
                        spacing: 4
                        GohuText {
                            text: "HOUR"
                            color: Colors.cyan
                            font.pixelSize: 10
                        }
                        TextField {
                            id: alarmHour
                            width: parent.width
                            height: 33
                            maximumLength: 2
                            inputMethodHints: Qt.ImhDigitsOnly
                            validator: IntValidator {bottom: 0; top: 23}
                            color: Colors.magenta
                            font.pixelSize: 12
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: alarmHour.activeFocus
                                    ? Colors.magenta : Colors.cyan
                            }
                        }
                    }
                    Column {
                        width: 60
                        spacing: 4
                        GohuText {
                            text: "MIN"
                            color: Colors.cyan
                            font.pixelSize: 10
                        }
                        TextField {
                            id: alarmMinute
                            width: parent.width
                            height: 33
                            maximumLength: 2
                            inputMethodHints: Qt.ImhDigitsOnly
                            validator: IntValidator {bottom: 0; top: 59}
                            color: Colors.magenta
                            font.pixelSize: 12
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: alarmMinute.activeFocus
                                    ? Colors.magenta : Colors.cyan
                            }
                        }
                    }
                    Column {
                        width: Math.max(0, entryFields.width - 111 - 2 * entryFields.spacing)
                        spacing: 4
                        GohuText {
                            text: "NAME"
                            color: Colors.cyan
                            font.pixelSize: 10
                        }
                        TextField {
                            id: alarmName
                            width: parent.width
                            height: 33
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
                    id: scheduleModes
                    width: parent.width
                    height: 33
                    spacing: 7
                    ActionButton {
                        width: (scheduleModes.width - scheduleModes.spacing) / 2
                        height: parent.height
                        label: "ONE TIME"
                        labelPixelSize: 11
                        selected: pane.draftMode === "once"
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftMode = "once"
                    }
                    ActionButton {
                        width: (scheduleModes.width - scheduleModes.spacing) / 2
                        height: parent.height
                        label: "REPEAT / WEEKLY"
                        labelPixelSize: 11
                        selected: pane.draftMode === "weekly"
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftMode = "weekly"
                    }
                }
                Row {
                    width: parent.width
                    height: 33
                    visible: pane.draftMode === "weekly"
                    spacing: 3
                    Repeater {
                        model: pane.days
                        delegate: ActionButton {
                            width: Math.floor((editorContent.width - 6 * 3) / 7)
                            height: 33
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
                    height: 33
                    visible: pane.draftMode === "once"
                    spacing: 8
                    GohuText {
                        width: 116
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        text: "DATE // YYYY-MM-DD"
                        color: Colors.cyan
                        font.pixelSize: 10
                    }
                    TextField {
                        id: alarmDate
                        width: Math.max(0, onceDateRow.width - 116 - onceDateRow.spacing)
                        height: parent.height
                        maximumLength: 10
                        color: Colors.magenta
                        font.pixelSize: 12
                        background: Rectangle {
                            color: Colors.black
                            border.width: 1
                            border.color: alarmDate.activeFocus
                                ? Colors.magenta : Colors.cyan
                        }
                    }
                }
                Row {
                    id: keepRow
                    width: parent.width
                    height: 29
                    spacing: 7
                    ActionButton {
                        width: parent.width
                        height: parent.height
                        label: pane.draftKeepSaved
                            ? "KEEP SAVED AFTER COMPLETION // YES"
                            : "DELETE AFTER COMPLETION // YES"
                        labelPixelSize: 10
                        selected: pane.draftKeepSaved
                        accentColor: Colors.magenta
                        onLeftClicked: pane.draftKeepSaved = !pane.draftKeepSaved
                    }
                }
                Row {
                    id: pauseRow
                    width: parent.width
                    height: 33
                    spacing: 7
                    GohuText {
                        width: 66
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        text: "RESUME ON"
                        font.pixelSize: 10
                        color: Colors.cyan
                    }
                    TextField {
                        id: alarmResumeDate
                        width: Math.max(0, pauseRow.width - 66 - 87
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
                        width: 87
                        height: parent.height
                        label: alarmResumeDate.text.trim() === "" ? "RESUME" : "PAUSE"
                        labelPixelSize: 10
                        accentColor: Colors.yellow
                        available: pane.selectedAlarm !== null
                        onLeftClicked: {
                            AlarmManagerService.pauseAlarm(
                                pane.selectedId, alarmResumeDate.text.trim());
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "SOUND // EACH ALARM HAS ITS OWN TONE + VOLUME"
                    color: Colors.cyan
                    font.pixelSize: 10
                }
                Row {
                    id: soundChoices
                    width: parent.width
                    height: 31
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
                    height: 31
                    spacing: 6
                    ActionButton {
                        width: 68
                        height: parent.height
                        label: "-10 VOL"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftVolume = Math.max(0,pane.draftVolume-10)
                    }
                    GohuText {
                        width: Math.max(0, volumeRow.width - 136
                                          - 2 * volumeRow.spacing)
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        text: pane.draftVolume + "%"
                        color: Colors.white
                        font.pixelSize: 11
                    }
                    ActionButton {
                        width: 68
                        height: parent.height
                        label: "+10 VOL"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftVolume = Math.min(100,pane.draftVolume+10)
                    }
                }
                Row {
                    id: soundOptions
                    width: parent.width
                    height: 31
                    spacing: 6
                    ActionButton {
                        width: (soundOptions.width - soundOptions.spacing) / 2
                        height: parent.height
                        label: pane.draftSoundEnabled ? "SOUND // ON" : "SOUND // OFF"
                        labelPixelSize: 10
                        selected: pane.draftSoundEnabled
                        accentColor: Colors.cyan
                        onLeftClicked: pane.draftSoundEnabled = !pane.draftSoundEnabled
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
        }
        NeonScrollBar {
            id: editorRail
            flickable: editorScroll
            accountForContentOrigin: true
            geometryMode: "viewport"
            x: editorFrame.width - width - 3
            y: editorScroll.y
            height: editorScroll.height
            handleStyle: "star"
            railColor: Colors.cyan
            handleColor: Colors.magenta
            handleBorderColor: Colors.magenta
            railGlowColor: Colors.white
            containGlow: true
            visible: scrollable
        }
    }

    Row {
        id: editorActions
        width: pane.width
        height: 34
        spacing: 6
        visible: pane.selectedAlarm !== null
        ActionButton {
            width: (editorActions.width - 2 * editorActions.spacing) / 3
            height: parent.height
            label: "SAVE"
            labelPixelSize: 11
            accentColor: Colors.cyan
            available: AlarmManagerService.canEdit
            onLeftClicked: pane.apply(false)
        }
        ActionButton {
            width: (editorActions.width - 2 * editorActions.spacing) / 3
            height: parent.height
            label: "SAVE + ARM"
            labelPixelSize: 11
            accentColor: Colors.orange
            available: AlarmManagerService.canEdit
            onLeftClicked: pane.apply(true)
        }
        ActionButton {
            width: (editorActions.width - 2 * editorActions.spacing) / 3
            height: parent.height
            label: pane.deleteConfirmId === pane.selectedId ? "CONFIRM DELETE" : "DELETE"
            labelPixelSize: 10
            accentColor: Colors.red
            available: AlarmManagerService.canEdit
            onLeftClicked: {
                if (pane.deleteConfirmId !== pane.selectedId) {
                    pane.deleteConfirmId = pane.selectedId;
                    return;
                }
                const id = pane.selectedId;
                pane.deleteConfirmId = 0;
                if (AlarmManagerService.removeAlarm(id))
                    pane.selectedId = 0;
            }
        }
    }
    Row {
        id: ringActions
        width: pane.width
        height: 31
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
        width: pane.width
        text: "STATUS // " + AlarmManagerService.feedback
        color: AlarmManagerService.storageError ? Colors.orange : Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: pane.width
        text: "STORE // " + AlarmManagerService.storageState.toUpperCase()
            + "    AUDIO // " + AlarmManagerService.audioState
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
