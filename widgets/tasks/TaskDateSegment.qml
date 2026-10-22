import QtQuick
import "../../components"

// Three instances are used as independent MONTH / DAY / YEAR number controls.
// Text edits are committed only when complete; stepping is delegated to the
// parent date policy. This object never touches the task store.
Rectangle {
    id: segment

    property string part: "month"
    property string displayValue: ""
    property string placeholder: "MM"
    property int digitCount: 2
    property bool canEdit: false

    signal editCommitted(string part, string value)
    signal stepRequested(string part, int direction)

    function restoreText() {
        numberInput.text = displayValue;
    }
    function releaseFocus() {
        numberInput.focus = false;
    }
    onDisplayValueChanged: restoreText()

    height: 26
    color: Colors.black
    border.width: 1
    border.color: numberInput.activeFocus ? Colors.magenta : Colors.cyan
    opacity: canEdit ? 1 : 0.6
    clip: true

    TextInput {
        id: numberInput
        anchors.left: parent.left
        anchors.leftMargin: 3
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: controls.left
        anchors.rightMargin: 1
        text: segment.displayValue
        enabled: segment.canEdit
        inputMethodHints: Qt.ImhDigitsOnly
        validator: RegularExpressionValidator {
            regularExpression: /^[0-9]*$/
        }
        maximumLength: segment.digitCount
        selectByMouse: true
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: segment.digitCount === 4 ? 9 : 10
        color: Colors.white
        selectionColor: Colors.magenta
        selectedTextColor: Colors.black
        onEditingFinished: {
            segment.editCommitted(segment.part, text);
            segment.restoreText();
        }
        Keys.onUpPressed: function(event) {
            segment.stepRequested(segment.part, 1);
            event.accepted = true;
        }
        Keys.onDownPressed: function(event) {
            segment.stepRequested(segment.part, -1);
            event.accepted = true;
        }
    }

    GohuText {
        visible: segment.displayValue.length === 0 && !numberInput.activeFocus
        anchors.left: parent.left
        anchors.leftMargin: 3
        anchors.right: controls.left
        anchors.rightMargin: 1
        anchors.verticalCenter: parent.verticalCenter
        text: segment.placeholder
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: segment.digitCount === 4 ? 9 : 10
        color: Colors.cyan
        opacity: 0.6
    }

    Column {
        id: controls
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 14

        Repeater {
            model: [1, -1]
            Rectangle {
                required property int modelData
                width: controls.width
                height: segment.height / 2
                color: !segment.canEdit ? Colors.dark
                       : pressArea.pressed ? Colors.magenta
                       : pressArea.containsMouse ? Colors.yellow : Colors.black
                border.width: 1
                border.color: Colors.cyan

                GohuText {
                    anchors.centerIn: parent
                    text: modelData > 0 ? "↑" : "↓"
                    font.pixelSize: 10
                    color: pressArea.pressed ? Colors.black
                         : pressArea.containsMouse ? Colors.orange : Colors.cyan
                }
                MouseArea {
                    id: pressArea
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: segment.canEdit
                    acceptedButtons: Qt.LeftButton
                    onClicked: segment.stepRequested(segment.part, modelData)
                }
            }
        }
    }
}
