import QtQuick
import "../../components"

// Horizontal mounting of the existing Post-Apollo STEP instrument. The
// shared thumb, ruler, glow, detents, gesture preview and release are intact.
Column {
    id: root
    property int currentValue: 0
    property bool enabledSlider: false
    signal valueRequested(real value)
    spacing: 3

    Item {
        id: mounting
        width: root.width
        height: 46
        SelectorSlider {
            id: selector
            objectName: "cpuplusSharedHorizontalSelector"
            anchors.centerIn: parent
            width: 44
            height: mounting.width
            rotation: 90
            horizontalStepPresentation: true
            selectorProfile: "step"
            minimumValue: 0
            maximumValue: 64
            valueStep: 4
            valueDecimals: 0
            valueSuffix: "GiB"
            currentValue: root.currentValue
            enabledSlider: root.enabledSlider
            enabled: enabledSlider
            onValueRequested: function(value) {
                if (root.enabledSlider) root.valueRequested(value);
            }
        }
    }
    Item {
        width: root.width
        height: 15
        Repeater {
            model: [0, 16, 32, 48, 64]
            delegate: GohuText {
                required property int modelData
                required property int index
                // The rotated slider's endpoints include equal thumb/track
                // insets. Align each label with the actual detent center.
                readonly property real detentCenter: root.width / 2
                    + selector.handleTravel() * (modelData / 64 - 0.5)
                text: String(modelData)
                width: Math.min(implicitWidth, root.width / 5)
                x: Math.max(0, Math.min(root.width - width, detentCenter - width / 2))
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 11
                color: Colors.cyan
            }
        }
    }
}
