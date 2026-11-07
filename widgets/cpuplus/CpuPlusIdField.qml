import QtQuick
import "../../components"

// Shared compact input for CPU++ ID editing. The editor writes only when
// an adjacent explicit SAVE or ADD action reaches the owning Social store.
Item {
    id: field
    property alias text: input.text
    property string placeholder: ""
    property int maxLength: 254
    property int hints: Qt.ImhNone
    readonly property bool editingText: input.activeFocus

    implicitHeight: 36

    Rectangle {
        anchors.fill: parent
        color: Colors.dark
        border.width: 1
        border.color: input.activeFocus ? Colors.magenta : Colors.orange
    }
    GohuText {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 7
        anchors.rightMargin: 5
        visible: input.text.length === 0 && !input.activeFocus
        text: field.placeholder
        color: Colors.white
        opacity: 0.47
        font.pixelSize: 10
        elide: Text.ElideRight
    }
    TextInput {
        id: input
        anchors.fill: parent
        anchors.margins: 6
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: 11
        color: Colors.magenta
        selectionColor: Colors.yellow
        selectedTextColor: Colors.black
        maximumLength: field.maxLength
        inputMethodHints: field.hints
        selectByMouse: true
        clip: true
        cursorDelegate: Component {
            Rectangle {
                width: 2
                color: Colors.orange
            }
        }
        Keys.onEscapePressed: function(event) {
            input.focus = false;
            event.accepted = true;
        }
    }
}
