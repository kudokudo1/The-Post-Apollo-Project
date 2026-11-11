"""Regression contract for Clock's inline one-time/pause calendar picker."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
PICKER = (ROOT / "widgets/AlarmCalendarPicker.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/AlarmManagerPolicy.js").read_text(encoding="utf-8")


class ClockAlarmCalendarPickerContracts(unittest.TestCase):
    def test_two_existing_editors_have_calendar_controls(self):
        self.assertIn("id: onceCalendarButton", PANE)
        self.assertIn("id: pauseCalendarButton", PANE)
        self.assertIn('alarmCalendarPicker.openFor(\n                            "once"', PANE)
        self.assertIn('alarmCalendarPicker.openFor(\n                            "pause"', PANE)
        self.assertIn("AlarmCalendarPicker {", PANE)
        self.assertIn("onDateChosen: function(target, dateKey)", PANE)
        self.assertIn("pane.onceDateExplicit = true;", PANE)
        self.assertIn("alarmResumeDate.text = dateKey;", PANE)
        self.assertIn("|| alarmCalendarPicker.visible", PANE)
        self.assertIn("alarmCalendarPicker.dismiss();", PANE)

    def test_no_silent_save_schedule_or_new_window(self):
        self.assertIn("signal dateChosen(string target, string dateKey)", PICKER)
        self.assertIn("if (!maySelect(key)) return false;", PICKER)
        self.assertIn("dateChosen(target, key);", PICKER)
        self.assertIn("Policy.validDate(key, false)", PICKER)
        self.assertIn("key > Policy.dayKey(now)", PICKER)
        self.assertIn("Policy.dayAt(key, alarmHour, alarmMinute) > now", PICKER)
        self.assertIn("Keys.onEscapePressed: dismiss()", PICKER)
        self.assertIn("onClicked: picker.dismiss()", PICKER)
        for forbidden in ("Window {", "Process {", "FileView {",
                          "saveAlarm(", "pushRich(", "setDnd("):
            self.assertNotIn(forbidden, PICKER)
        self.assertIn('label: "SAVE + ARM"', PANE)
        self.assertIn('label: "SAVE NOTE"', PANE)
        self.assertIn("id: listFrame", PANE)
        self.assertIn("id: listRail", PANE)
        self.assertIn("id: alarmList", PANE)
        self.assertIn("readonly property var calendarCells:", PICKER)
        self.assertIn("for (let i = 0; i < 42; i++)", PICKER)
        self.assertIn("new Date(viewYear, viewMonth, 1 + i - firstWeekday, 12)", PICKER)
        self.assertIn("columns: 7", PICKER)
        self.assertIn("modelData.inMonth && picker.maySelect(modelData.dateKey)", PICKER)
        self.assertIn("function validDate(value, allowEmpty)", POLICY)


if __name__ == "__main__":
    unittest.main()
