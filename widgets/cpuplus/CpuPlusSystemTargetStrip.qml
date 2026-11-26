import QtQuick
import "../../components"

// SYSTEM-only filter strip. Use the canonical action chassis directly:
// no label-dependent Row geometry, bespoke hover palette or new icons.
Flow {
    id: root
    property var choices: []
    property string selectedKey: "ALL"
    signal targetRequested(string key)
    spacing: 4

    Repeater {
        model: root.visible ? root.choices : []
        ActionButton {
            id: filter
            required property var modelData
            objectName: "cpuplusSystemTarget-" + String(modelData.key)
            width: 36
            height: 36
            accentColor: Colors.resourceColor(modelData.key)
            selected: root.selectedKey === String(modelData.key)
            selectedForegroundColor: accentColor
            selectedBorderColor: accentColor
            selectedContentGlowColor: accentColor
            selectedSoftGlowColor: accentColor
            contentGlowSelectedOpacity: 0.95
            normalFace: true
            label: String(modelData.symbol || "")
            labelPixelSize: 24
            contentPadding: 0
            labelElide: Text.ElideNone
            acceptedButtons: Qt.LeftButton
            Accessible.name: String(modelData.name || "")
            Accessible.role: Accessible.Button
            Accessible.onPressAction: root.targetRequested(String(modelData.key))
            onLeftClicked: root.targetRequested(String(modelData.key))
        }
    }
}
