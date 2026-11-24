import QtQuick
import QtQuick.Controls as Controls
import "../../components"

// CPU++-local horizontal instrument. The shared SelectorSlider is vertical;
// retain native Qt pointer/keyboard semantics without rotating its labels.
Column {
    id: root
    property int currentValue: 0
    property bool enabledSlider: false
    signal valueRequested(real value)
    spacing: 3
    Controls.Slider {
        id: slider
        width: parent.width
        height: 40
        orientation: Qt.Horizontal
        from: 0
        to: 64
        stepSize: 4
        snapMode: Controls.Slider.SnapAlways
        value: root.currentValue
        enabled: root.enabledSlider
        focusPolicy: Qt.StrongFocus
        onMoved: if (root.enabledSlider) root.valueRequested(Math.round(value))
        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + (slider.availableHeight - height) / 2
            width: Math.max(0, slider.availableWidth)
            height: 16
            color: Colors.black
            border.width: 1
            border.color: slider.activeFocus ? Colors.magenta : Colors.cyan
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: 3
                width: Math.max(0, (parent.width - 6) * slider.visualPosition)
                color: Colors.cyan
                opacity: slider.enabled ? 0.65 : 0.2
            }
        }
        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * Math.max(0, slider.availableWidth - width)
            y: slider.topPadding + (slider.availableHeight - height) / 2
            width: 22
            height: 34
            color: slider.pressed ? Colors.yellow : Colors.white
            opacity: slider.enabled ? 1 : 0.4
            border.width: 2
            border.color: Colors.magenta
            Row {
                anchors.centerIn: parent
                spacing: 2
                Repeater {
                    model: 3
                    Rectangle { width: 2; height: 16; color: Colors.cyan }
                }
            }
        }
    }
    Row {
        width: parent.width
        Repeater {
            model: ["0", "16", "32", "48", "64 GiB"]
            delegate: GohuText {
                required property string modelData
                required property int index
                width: root.width / 5
                text: modelData
                horizontalAlignment: index === 0 ? Text.AlignLeft : index === 4 ? Text.AlignRight : Text.AlignHCenter
                font.pixelSize: 11
                color: Colors.cyan
            }
        }
    }
}
