import QtQuick
import "../components"
import "../services/finance/FinanceInputPolicy.js" as Rules

// Fixed dollar glyph outside the editable numeric area; zero cents implied.
Rectangle {
    id: money
    property string value: ""
    property bool canEdit: true
    signal valueEdited(string value)
    height: 28
    color: Colors.dark
    border.color: editor.activeFocus ? Colors.magenta : Colors.cyan
    border.width: 1

    function normalize() {
        const normalized=Rules.normalizeAmount(value);
        if(normalized!==null && normalized!==value)valueEdited(normalized);
    }
    GohuText {
        id: dollar
        anchors.left: parent.left
        anchors.leftMargin: 7
        anchors.verticalCenter: parent.verticalCenter
        text: "$"
        font.pixelSize: 12
        color: Colors.cyan
    }
    TextInput {
        id: editor
        anchors.left: dollar.right
        anchors.leftMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: Colors.white
        font.pixelSize: 12
        verticalAlignment: TextInput.AlignVCenter
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        selectByMouse: true
        readOnly: !money.canEdit
        text: money.value
        onTextEdited: money.valueEdited(text)
        onEditingFinished: money.normalize()
    }
}
