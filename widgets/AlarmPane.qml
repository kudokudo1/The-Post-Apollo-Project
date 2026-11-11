import QtQuick
import QtQuick.Controls
import qs.services.time
import "../components"

// Compact Clock TOOLS/ALARM face. Scheduling and audio belong to one
// durable owner, not to this window's visibility or visual calibration.
Column {
    id: pane
    spacing: 10
    readonly property bool editingActive:
        alarmHourField.activeFocus || alarmMinuteField.activeFocus
        || alarmNameField.activeFocus

    GohuText {
        width: pane.width
        text: "ALARM // DAILY LOCAL TIME"
        color: Colors.cyan
        font.pixelSize: 14
    }

    GohuText {
        width: pane.width
        text: AlarmService.ringing ? "● RINGING // ACTION REQUIRED"
              : AlarmService.enabled ? "ARMED // " + AlarmService.alarm.label
              : "DISARMED // NO ALARM WILL FIRE"
        color: AlarmService.ringing ? Colors.magenta
               : AlarmService.enabled ? Colors.orange : Colors.white
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: pane.width
        text: AlarmService.nextLabel
        color: Colors.white
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }

    Row {
        id: alarmTimeInput
        width: pane.width
        height: 57
        spacing: 9

        Column {
            width: 86
            spacing: 4
            GohuText {
                text: "HOUR // 24H"
                color: Colors.cyan
                font.pixelSize: 10
            }
            TextField {
                id: alarmHourField
                width: 86
                height: 33
                text: ("0" + AlarmService.alarm.hour).slice(-2)
                maximumLength: 2
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 0; top: 23 }
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 13
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: alarmHourField.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
            }
        }

        Column {
            width: 86
            spacing: 4
            GohuText {
                text: "MINUTE"
                color: Colors.cyan
                font.pixelSize: 10
            }
            TextField {
                id: alarmMinuteField
                width: 86
                height: 33
                text: ("0" + AlarmService.alarm.minute).slice(-2)
                maximumLength: 2
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 0; top: 59 }
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 13
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: alarmMinuteField.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
            }
        }
        Column {
            width: Math.max(0, alarmTimeInput.width - 172
                               - 2 * alarmTimeInput.spacing)
            spacing: 4
            GohuText {
                text: "LABEL"
                color: Colors.cyan
                font.pixelSize: 10
            }
            TextField {
                id: alarmNameField
                width: parent.width
                height: 33
                text: AlarmService.alarm.label
                maximumLength: 40
                placeholderText: "ALARM NAME"
                placeholderTextColor: Colors.cyan
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 12
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: alarmNameField.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
            }
        }
    }

    Row {
        id: alarmArmRow
        width: pane.width
        height: 35
        spacing: 8
        ActionButton {
            width: (alarmArmRow.width - alarmArmRow.spacing) / 2
            height: parent.height
            label: AlarmService.enabled ? "UPDATE ALARM" : "ARM ALARM"
            labelPixelSize: 11
            trackLabelGlowLocally: true
            accentColor: Colors.orange
            available: AlarmService.canEdit
            onLeftClicked: AlarmService.arm(
                alarmHourField.text, alarmMinuteField.text, alarmNameField.text)
        }
        ActionButton {
            width: (alarmArmRow.width - alarmArmRow.spacing) / 2
            height: parent.height
            label: "DISARM"
            labelPixelSize: 11
            trackLabelGlowLocally: true
            accentColor: Colors.red
            available: AlarmService.canEdit && AlarmService.enabled
            onLeftClicked: AlarmService.disarm()
        }
    }

    Row {
        id: alarmRingActions
        width: pane.width
        height: 35
        spacing: 8
        ActionButton {
            width: (alarmRingActions.width - alarmRingActions.spacing) / 2
            height: parent.height
            label: "STOP"
            labelPixelSize: 12
            trackLabelGlowLocally: true
            accentColor: Colors.red
            available: AlarmService.ringing
            onLeftClicked: AlarmService.stopRinging()
        }
        ActionButton {
            width: (alarmRingActions.width - alarmRingActions.spacing) / 2
            height: parent.height
            label: "SNOOZE // 5M"
            labelPixelSize: 11
            trackLabelGlowLocally: true
            accentColor: Colors.yellow
            available: AlarmService.ringing
            onLeftClicked: AlarmService.snoozeRinging()
        }
    }

    Rectangle {
        width: pane.width
        height: 2
        color: Colors.cyan
        opacity: 0.6
    }

    Row {
        id: alarmSoundRow
        width: pane.width
        height: 34
        spacing: 8
        ActionButton {
            width: (alarmSoundRow.width - alarmSoundRow.spacing) / 2
            height: parent.height
            label: AlarmService.alarm.soundEnabled
                   ? "SOUND ON" : "SOUND OFF"
            labelPixelSize: 11
            selected: AlarmService.alarm.soundEnabled
            accentColor: Colors.cyan
            available: AlarmService.canEdit
            onLeftClicked: AlarmService.setSoundEnabled(
                !AlarmService.alarm.soundEnabled)
        }
        ActionButton {
            width: (alarmSoundRow.width - alarmSoundRow.spacing) / 2
            height: parent.height
            label: "TEST SOUND"
            labelPixelSize: 11
            accentColor: Colors.orange
            available: AlarmService.canEdit && !AlarmService.ringing
            onLeftClicked: AlarmService.previewSound()
        }
    }

    GohuText {
        width: pane.width
        text: "STATUS // " + AlarmService.feedback
        color: AlarmService.ringing ? Colors.magenta : Colors.cyan
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: pane.width
        text: "AUDIO // " + AlarmService.soundState
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: pane.width
        text: "STORE // " + AlarmService.storageState.toUpperCase()
              + (AlarmService.storageError
                 ? " // " + AlarmService.storageError : "")
        color: AlarmService.storageError ? Colors.orange : Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: pane.width
        text: "USES SYSTEM LOCAL TIME // NOT THE VISUAL OFFSET. "
              + "RUNS WITH QUICKSHELL; DOES NOT WAKE A SUSPENDED OR OFF COMPUTER."
        color: Colors.white
        font.pixelSize: 10
        opacity: 0.75
        wrapMode: Text.WordWrap
    }
}
