import QtQuick
import Quickshell
import qs.components

// User-facing DAY / MONTH / YEAR inputs. Only the editor owns conversion
// to GitHub's ISO YYYY-MM-DD date. No date is saved until explicit SAVE.
Item {
    id: root

    property var keyboardHost: null
    signal submitted(string isoDate)

    readonly property string preview: isoValue()

    function reset(isoDate) {
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(
            String(isoDate || "").trim()
        );
        yearPart.text = match ? match[1] : "";
        monthPart.text = match ? match[2] : "";
        dayPart.text = match ? match[3] : "";
    }

    function isoValue() {
        const year = yearPart.text.trim();
        const month = monthPart.text.trim();
        const day = dayPart.text.trim();
        if (!year || !month || !day)
            return "";
        return year.padStart(4, "0") + "-"
            + month.padStart(2, "0") + "-"
            + day.padStart(2, "0");
    }

    function focusChanged(editor, active) {
        if (!keyboardHost)
            return;
        if (active)
            keyboardHost.activeTextEditor = editor;
        else if (keyboardHost.activeTextEditor === editor)
            keyboardHost.activeTextEditor = null;
    }

    function releaseFocus() {
        if (!keyboardHost)
            return;
        if (keyboardHost.activeTextEditor === dayPart.editor
                || keyboardHost.activeTextEditor === monthPart.editor
                || keyboardHost.activeTextEditor === yearPart.editor)
            keyboardHost.activeTextEditor = null;
    }

    component DatePart: Item {
        id: part
        required property string caption
        required property int digits
        property var focusOwner: null
        property alias text: entry.text
        property alias editor: entry

        height: 57

        Column {
            anchors.fill: parent
            spacing: 4

            GohuText {
                text: part.caption
                font.pixelSize: 10
                color: Colors.orange
            }

            Rectangle {
                width: parent.width
                height: 32
                color: Colors.black
                border.width: entry.activeFocus ? 2 : 1
                border.color: Colors.magenta

                TextInput {
                    id: entry
                    anchors.fill: parent
                    anchors.margins: 5
                    verticalAlignment: TextInput.AlignVCenter
                    horizontalAlignment: TextInput.AlignHCenter
                    color: Colors.magenta
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 12
                    selectByMouse: true
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: RegularExpressionValidator {
                        regularExpression: part.digits === 4
                            ? /^\d{0,4}$/ : /^\d{0,2}$/
                    }
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    cursorDelegate: Rectangle {
                        width: 2
                        color: Colors.orange
                    }
                    onActiveFocusChanged: {
                        if (part.focusOwner)
                            part.focusOwner.focusChanged(entry, activeFocus);
                    }
                    onAccepted: {
                        if (part.focusOwner)
                            part.focusOwner.submitted(part.focusOwner.isoValue());
                    }
                }
            }
        }
    }

    Row {
        width: parent.width
        height: 57
        spacing: 6

        DatePart {
            id: dayPart
            caption: "DAY"
            digits: 2
            focusOwner: root
            width: (parent.width - 12) / 3
        }

        DatePart {
            id: monthPart
            caption: "MONTH"
            digits: 2
            focusOwner: root
            width: (parent.width - 12) / 3
        }

        DatePart {
            id: yearPart
            caption: "YEAR"
            digits: 4
            focusOwner: root
            width: (parent.width - 12) / 3
        }
    }
}
