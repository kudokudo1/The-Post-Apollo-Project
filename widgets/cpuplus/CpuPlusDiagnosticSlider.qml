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
    signal valueRequested(real value)
    spacing: compact ? 0 : 2
    CpuPlusMemoryReadout {
        width: parent.width
        text: root.title + " // " + root.readout
        color: root.subjectColor
        font.pixelSize: 12
        semanticGlowColor: root.subjectColor
        elide: Text.ElideRight
    }
    Item {
        width: parent.width
        height: root.compact ? 24 : 32
        SelectorSlider {
            objectName: root.objectName + "-hardware"
            anchors.centerIn: parent
            width: parent.height
            height: parent.width
            rotation: 90
            horizontalStepPresentation: true
            selectorProfile: "step"
            minimumValue: root.minimumValue
            maximumValue: root.maximumValue
            currentValue: root.currentValue
            valueStep: root.valueStep
            valueDecimals: 0
            enabledSlider: root.adjustable && validStepDomain
            accentColor: root.subjectColor
            valueFillColor: root.fillColor
            handleColor: root.subjectColor
            handleGradientBaseColor: root.subjectColor
            handleGradientAccentColor: root.subjectColor
            handleGlowColor: root.subjectColor
            activityGlowColor: root.subjectColor
            onValueRequested: value => root.valueRequested(value)
        }
    }
}
