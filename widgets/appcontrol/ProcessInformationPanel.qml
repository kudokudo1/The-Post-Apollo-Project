import QtQuick
import QtQuick.Layouts
import "../../components"

// Read-only information overlay. It does not own selection or authorize actions.
Rectangle {
    id: root
    property var task: null
    property string purpose: ""
    property string scopeText: ""
    property string virtualMemory: "?"
    property bool contextActive: false
    property bool open: false
    property real maximumHeight: 0
    readonly property string targetIdentity: task
        ? String(task.pid || 0) + "|" + String(task.startTicks || 0) + "|" + String(task.comm || "")
        : ""
    onTargetIdentityChanged: open = false
    onContextActiveChanged: if (!contextActive) open = false
    onOpenChanged: if (open) body.contentY = 0

    visible: contextActive && open && !!task && height > 0
    height: Math.max(0, Math.min(maximumHeight, contents.implicitHeight + header.height + 22))
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true
    z: 400

    MouseArea { anchors.fill: parent }
    Row {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 7
        height: 26
        spacing: 5
        GohuText {
            width: Math.max(0, parent.width - close.width - parent.spacing)
            height: parent.height
            text: "PROCESS // INFORMATION"
            color: Colors.cyan
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        CloseButton {
            id: close
            objectName: "processInformationClose"
            width: 26
            height: 26
            onCloseRequested: root.open = false
        }
    }
    Flickable {
        id: body
        objectName: "processInformationScroll"
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 7
        anchors.rightMargin: 18
        contentWidth: width
        contentHeight: contents.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        Column {
            id: contents
            width: body.width
            spacing: 8
            GohuText {
                width: parent.width
                text: root.task ? String(root.task.comm || "PROCESS") + " // PID " + String(root.task.pid || "?") : ""
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 13
                wrapMode: Text.WrapAnywhere
            }
            GohuText {
                width: parent.width
                text: "PROCESS PURPOSE"
                color: Colors.orange
                font.pixelSize: 12
            }
            GohuText {
                objectName: "processInformationPurpose"
                width: parent.width
                text: root.purpose || "NO DESCRIPTION AVAILABLE"
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: Colors.white
                font.pixelSize: 12
            }
            Rectangle {
                objectName: "processInformationScope"
                width: parent.width
                height: scopeContents.implicitHeight + 14
                color: Colors.black
                border.color: Colors.cyan
                Column {
                    id: scopeContents
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 7
                    spacing: 5
                    GohuText {
                        width: parent.width
                        text: "PROCESS SCOPE // LIMIT = THIS PROCESS"
                        wrapMode: Text.Wrap
                        color: Colors.cyan
                        font.pixelSize: 11
                    }
                    GohuText {
                        width: parent.width
                        text: root.scopeText || "NO LIVE PROCESS SCOPE FOUND"
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: Colors.white
                        font.pixelSize: 11
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "TECHNICAL INFORMATION"
                color: Colors.magenta
                font.pixelSize: 12
            }
            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: 8
                rowSpacing: 4
                Repeater {
                    model: [
                        ["USER", root.task ? String(root.task.user || "?") : "?"],
                        ["PPID", root.task ? String(root.task.ppid || "?") : "?"],
                        ["VIRT", root.virtualMemory],
                        ["STATE", root.task ? String(root.task.state || "?") : "?"]
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        GohuText {
                            Layout.preferredWidth: 64
                            text: modelData[0]
                            color: Colors.cyan
                            font.pixelSize: 11
                        }
                        GohuText {
                            Layout.fillWidth: true
                            text: modelData[1]
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                            color: Colors.white
                            font.pixelSize: 11
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "COMMAND LINE"
                color: Colors.magenta
                font.pixelSize: 11
            }
            GohuText {
                objectName: "processInformationArguments"
                width: parent.width
                text: root.task ? String(root.task.args || "") : ""
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.72
            }
        }
    }
    NeonScrollBar {
        flickable: body
        geometryMode: "viewport"
        visible: scrollable
        railColor: Colors.cyan
        handleColor: Colors.magenta
        wheelEnabled: false
    }
}
