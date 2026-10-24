import QtQuick
import "../components"

// FinanceW M0: opt-in in-process tool slot, never an external launcher.
// The Loader's lifetime follows the installed Component, not window size,
// visibility, selected display level, or temporary navigation changes.
// Future domain owners supply reviewed QML Components to this slot.
Item {
    id: host
    property string domainTitle: ""
    property Component embeddedComponent: null
    readonly property bool toolConnected: embeddedComponent !== null

    Loader {
        id: internalTool
        anchors.fill: parent
        active: host.toolConnected
        sourceComponent: host.embeddedComponent
        visible: host.toolConnected
    }

    Column {
        anchors.top: parent.top
        anchors.topMargin: 16
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.max(0, parent.width - 12)
        spacing: 12
        visible: !host.toolConnected

        GohuText {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: host.domainTitle
            font.pixelSize: 11
            color: Colors.white
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: "IN-WORKSPACE TOOL // NOT CONNECTED"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
    }
}
