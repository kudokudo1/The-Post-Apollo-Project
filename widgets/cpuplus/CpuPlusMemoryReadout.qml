import QtQuick
import "../../components"
import "CpuPlusMemoryReadout.js" as Readout

// Local memory-panel readout. One existing sampled glow per visible line.
Item {
    id: root
    property string text: ""
    property color color: Colors.cyan
    property alias font: face.font
    property alias wrapMode: face.wrapMode
    property alias horizontalAlignment: face.horizontalAlignment
    property alias verticalAlignment: face.verticalAlignment
    property alias fontSizeMode: face.fontSizeMode
    property alias minimumPixelSize: face.minimumPixelSize
    property alias elide: face.elide
    implicitHeight: face.implicitHeight
    implicitWidth: face.implicitWidth
    height: implicitHeight
    GohuText {
        id: face
        anchors.fill: parent
        text: Readout.format(root.text,root.color,Colors.white)
        textFormat: Text.RichText
        color: root.color
    }
    TextHashGlow {
        safeSource: root.visible ? face : null
        requestedVisible: root.visible
        foregroundColor: Colors.white
        preferredGlowColor: root.color===Colors.white?Colors.cyan:root.color
        opacity: 0.95
    }
}
