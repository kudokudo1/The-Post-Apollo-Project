import QtQuick
import "../../components"

// Upright owner readout around the existing rotated STEP hardware.
Column {
    id: root
    property string title: ""
    property string readout: ""
    property real minimumValue: 1
    property real maximumValue: 120
    property real currentValue: 30
    property real valueStep: 1
    property color subjectColor: Colors.white
    property color fillColor: Colors.omnitrix
    property bool adjustable: true
    property bool compact: false
    property bool vertical: false
    property string shortTitle: title
    property real verticalTravel: 96
    // Cool white hardware with a restrained semantic tint, not saturated ink.
    readonly property color hardwareFace: Qt.rgba(0.72+subjectColor.r*0.28,0.72+subjectColor.g*0.28,0.72+subjectColor.b*0.28,1)
    signal valueRequested(real value)
    spacing: compact ? 0 : 2
    CpuPlusMemoryReadout {
        width: parent.width
        text: root.vertical ? root.shortTitle : root.title + " // " + root.readout
        horizontalAlignment: root.vertical ? Text.AlignHCenter : Text.AlignLeft
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 7
        height: root.vertical ? 15 : implicitHeight
        color: root.subjectColor
        font.pixelSize: 12
        semanticGlowColor: root.fillColor
        elide: Text.ElideRight
    }
    Item {
        width: parent.width
        height: root.vertical ? root.verticalTravel : (root.compact ? 22 : 32)
        SelectorSlider {
            objectName: root.objectName + "-hardware"
            anchors.centerIn: parent
            width: root.vertical ? Math.min(parent.width,32) : parent.height
            height: root.vertical ? parent.height : parent.width
            rotation: root.vertical ? 0 : 90
            horizontalStepPresentation: !root.vertical
            compactVerticalStep: root.vertical
            focusBorderColor: Colors.magenta
            selectorProfile: "step"
            minimumValue: root.minimumValue
            maximumValue: root.maximumValue
            currentValue: root.currentValue
            valueStep: root.valueStep
            valueDecimals: 0
            enabledSlider: root.adjustable && validStepDomain
            accentColor: root.subjectColor
            frameColor: "#FFFFFF"
            responsiveHardware: true
            energizedValueFill: true
            frameGlowColor: root.fillColor
            valueFillColor: root.fillColor
            handleColor: root.hardwareFace
            handleGradientBaseColor: root.hardwareFace
            handleGradientAccentColor: root.subjectColor
            handleGlowColor: root.fillColor
            activityGlowColor: root.fillColor
            onValueRequested: value => root.valueRequested(value)
        }
    }
    CpuPlusMemoryReadout {
        visible: root.vertical
        width: parent.width
        height: 15
        text: root.readout.replace(" SEC","s").replace(" MS","ms")
        color: root.subjectColor
        semanticGlowColor: root.fillColor
        font.pixelSize: 10
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 7
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
    }
}
