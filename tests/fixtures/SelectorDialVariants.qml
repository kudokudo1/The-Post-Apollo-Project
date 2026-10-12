import QtQuick
import qs.components

// Manual fixture: embed this Item in a Quickshell test surface.
// Deliberately not mounted by shell.qml or the live Git menu.
Item {
    id: root
    width: 288
    height: 166

    property real temperature: 187.25
    property int heatZoneIndex: 1

    Row {
        anchors.fill: parent
        spacing: 12

        SelectorDial {
            id: temperatureDial
            width: 136
            height: 160
            labelText: "TEMPERATURE"
            selectorMode: "continuous"
            minimumValue: 0
            maximumValue: 300
            currentValue: root.temperature
            valueStep: 1
            valueDecimals: 2
            options: ["0", "150", "300"] // optional reference marks, not detents
            displayOptions: ["0", "150", "300"]
            onValueRequested: function(value) {
                root.temperature = value;
            }
        }

        SelectorDial {
            id: zoneDial
            width: 136
            height: 160
            labelText: "HEAT // ZONES"
            selectorMode: "zones"
            options: ["low", "medium", "high"]
            displayOptions: ["LOW", "MED", "HIGH"]
            currentIndex: root.heatZoneIndex
            onSelectionRequested: function(index, value) {
                root.heatZoneIndex = index;
            }
        }
    }
}
