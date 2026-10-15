import QtQuick
import "../../components" as Components

// F2 VALUE isolated demo; numbers are local mock state.
// No Git, Hospital, audio-device or brightness-service operations.
Item {
    id: demo
    width: 560
    height: 360

    property real volume: 35
    property real temperature: 18.5

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
        text: "F2 // SELECTOR VALUE"
        color: Components.Colors.cyan
        font.pixelSize: 14
    }

    Components.GohuText {
        x: 18
        y: 32
        text: "ISOLATED LIVE VALUES // NO SYSTEM ACTIONS"
        color: Components.Colors.orange
        font.pixelSize: 9
    }

    Components.SelectorSlider {
        id: volumeSlider
        x: 58
        y: 62
        height: 230
        selectorProfile: "value"
        sideLabel: "VOLUME"
        accentColor: Components.Colors.cyan
        handleGlowColor: Components.Colors.magenta
        minimumValue: 0
        maximumValue: 100
        currentValue: demo.volume
        valueStep: 5
        valueDecimals: 0
        valueSuffix: "%"
        onValueRequested: function(value) { demo.volume = value; }
    }

    Components.GohuText {
        x: 116
        y: 112
        font.pixelSize: 12
        color: Components.Colors.white
        text: "OWNER // " + demo.volume.toFixed(0) + " %"
    }

    Components.GohuText {
        x: 116
        y: 134
        font.pixelSize: 9
        color: Components.Colors.cyan
        text: "0–100 // WHEEL +5 // UP/DOWN +5"
    }

    Components.SelectorSlider {
        id: temperatureSlider
        x: 305
        y: 62
        height: 230
        selectorProfile: "value"
        sideLabel: "TEMP"
        accentColor: Components.Colors.orange
        handleGlowColor: Components.Colors.magenta
        minimumValue: -40
        maximumValue: 160
        currentValue: demo.temperature
        valueStep: 2.5
        valueDecimals: 1
        valueSuffix: "°C"
        onValueRequested: function(value) { demo.temperature = value; }
    }

    Components.GohuText {
        x: 363
        y: 112
        font.pixelSize: 12
        color: Components.Colors.white
        text: "OWNER // " + demo.temperature.toFixed(1) + " °C"
    }

    Components.GohuText {
        x: 363
        y: 134
        font.pixelSize: 9
        color: Components.Colors.orange
        text: "-40 TO 160 // STEP 2.5"
    }

    Components.GohuText {
        anchors {
            left: parent.left
            bottom: parent.bottom
            leftMargin: 18
            bottomMargin: 20
        }
        font.pixelSize: 10
        color: Components.Colors.white
        text: "DRAG = LIVE VALUE // WHEEL/KEY = STEP // READOUT = OWNER STATE"
    }
}
