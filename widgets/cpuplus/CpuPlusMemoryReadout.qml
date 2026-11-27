import QtQuick
import "../../components"
import "CpuPlusMemoryReadout.js" as Readout

// Local memory-panel readout. One existing sampled glow per visible line.
Item {
    id: root
    property string text: ""
    // Opt-in help vocabulary; ordinary instrument readouts remain unchanged.
    property string helpSubject: ""
    property color color: Colors.cyan
    property color semanticGlowColor: color===Colors.white ? Colors.cyan : color
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
        text: root.helpSubject!=="" ? Readout.formatHelp(root.text,root.helpSubject,{
            white:Colors.white, orange:Colors.orange, magenta:Colors.magenta,
            omnitrix:Colors.omnitrix, cyan:Colors.cyan, blue:Colors.blue,
            yellow:Colors.yellow, red:Colors.red
        }) : Readout.format(root.text,root.color,Colors.white)
        textFormat: Text.RichText
        color: root.color
    }
    TextHashGlow {
        safeSource: root.visible ? face : null
        requestedVisible: root.visible
        foregroundColor: Colors.white
        preferredGlowColor: root.semanticGlowColor
        radius: root.helpSubject!=="" ? 5 : VisualLanguage.textHashRadius
        samples: root.helpSubject!=="" ? 7 : VisualLanguage.textHashSamples
        opacity: root.helpSubject!=="" ? 0.65 : 0.95
    }
}
