import QtQuick
import "../../components"

// The face is a tank, not a guessed completion percentage. State and elapsed
// progress are supplied by the owner; only verified completion fills green.
ActionButton {
    id: root
    property string phase: "PREPARE"
    property string caption: phase
    property real progress: 0
    property color stateColor: phase === "PREPARE" ? Colors.white
        : phase === "CALIBRATING" ? Colors.yellow
        : phase === "READY" ? Colors.orange
        : phase === "RECORDING" ? Colors.green
        : phase === "COMPLETE" ? Colors.omnitrix : Colors.red
    height: 34
    // Dedicated execution hardware, not an ordinary filter/action face.
    readonly property bool preparationFace: phase === "PREPARE" || phase === "RETRY"
    idleBorderWidth: preparationFace ? 2 : 1
    softGlowIdleOpacity: preparationFace ? 0.46 : 0.22
    accentColor: stateColor
    showLabel: false
    acceptedButtons: Qt.LeftButton
    Accessible.name: caption
    Accessible.role: Accessible.Button
    Accessible.onPressAction: if (interactive) leftClicked(null)
    contentGlowSource: captionText
    contentGlowEnabled: !pressed
    idleFillColor: Colors.dark
    GohuText {
        id: captionText
        anchors.fill: parent
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: root.preparationFace ? 13 : 11
        color: root.pressed ? Colors.black : root.hovered ? Colors.orange : root.stateColor
        text: root.caption
        elide: Text.ElideRight
    }
    Repeater {
        model: root.preparationFace ? 2 : 0
        Rectangle {
            required property int index
            width: 4
            height: Math.max(0,root.height-12)
            x: index===0 ? 6 : root.width-width-6
            y: 6
            color: root.pressed ? Colors.black : root.hovered ? Colors.orange : root.stateColor
        }
    }
    Rectangle {
        x: 1; y: 1
        height: Math.max(0, parent.height-2)
        width: Math.max(0,parent.width-2)*Math.max(0,Math.min(1,root.progress))
        color: root.stateColor
        visible: !root.pressed && width > 0
        clip: true
        GohuText {
            x: -1; y: -1
            width: root.width
            height: root.height
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 11
            color: Colors.black
            text: root.caption
            elide: Text.ElideRight
        }
    }
}
