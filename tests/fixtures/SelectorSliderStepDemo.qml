import QtQuick
import "../../components" as Components

// F3 STEP demo: local mock owner state only, no real system operations.
// Candidate detents move during drag; owner selection commits on release.
Item {
    id: demo
    width: 740
    height: 400
    property real zoom: 40
    property real temperature: 35

    Rectangle {
        anchors.fill: parent
        radius: 3
        color: Components.Colors.black
        border.width: 1
        border.color: Components.Colors.cyan
    }

    Components.GohuText {
        x: 18
        y: 12
        text: "F3 // SELECTOR STEP"
        color: Components.Colors.cyan
        font.pixelSize: 14
    }

    Components.GohuText {
        x: 18
        y: 34
        text: "MOCK DATA // DRAG = DETENT PREVIEW // RELEASE = COMMIT"
        color: Components.Colors.orange
        font.pixelSize: 9
    }

    Components.SelectorSlider {
        id: zoomSlider
        x: 56
        y: 72
        height: 254
        selectorProfile: "step"
        sideLabel: "ZOOM"
        accentColor: Components.Colors.cyan
        handleGlowColor: Components.Colors.magenta
        minimumValue: 0
        maximumValue: 100
        currentValue: demo.zoom
        valueStep: 10
        valueDecimals: 0
        valueSuffix: "%"
        onValueRequested: function(value) { demo.zoom = value; }
    }

    Components.GohuText {
        x: 183
        y: 112
        text: "OWNER // " + demo.zoom.toFixed(0) + "%"
        color: Components.Colors.white
        font.pixelSize: 12
    }

    Components.GohuText {
        x: 183
        y: 140
        text: zoomSlider.stepPreviewActive
            ? "PRE // " + zoomSlider.pendingStepValue.toFixed(0) + "%"
            : "PRE // —"
        color: Components.Colors.yellow
        font.pixelSize: 11
    }

    Components.GohuText {
        x: 183
        y: 166
        text: "10% DETENTS"
        color: Components.Colors.cyan
        font.pixelSize: 10
    }

    Components.SelectorSlider {
        id: temperatureSlider
        x: 418
        y: 72
        height: 254
        selectorProfile: "step"
        sideLabel: "TEMP"
        accentColor: Components.Colors.orange
        handleGlowColor: Components.Colors.magenta
        minimumValue: -40
        maximumValue: 160
        currentValue: demo.temperature
        valueStep: 25
        valueDecimals: 0
        valueSuffix: "°C"
        onValueRequested: function(value) { demo.temperature = value; }
    }

    Components.GohuText {
        x: 545
        y: 112
        text: "OWNER // " + demo.temperature.toFixed(0) + "°C"
        color: Components.Colors.white
        font.pixelSize: 12
    }

    Components.GohuText {
        x: 545
        y: 140
        text: temperatureSlider.stepPreviewActive
            ? "PRE // " + temperatureSlider.pendingStepValue.toFixed(0) + "°C"
            : "PRE // —"
        color: Components.Colors.yellow
        font.pixelSize: 11
    }

    Components.GohuText {
        x: 545
        y: 166
        text: "25°C DETENTS"
        color: Components.Colors.orange
        font.pixelSize: 10
    }

    Components.GohuText {
        x: 18
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        text: "DRAG // PREVIEW      RELEASE // COMMIT      ESC // CANCEL      WHEEL/UP/DOWN // 1 STEP"
        color: Components.Colors.white
        font.pixelSize: 10
    }
}
