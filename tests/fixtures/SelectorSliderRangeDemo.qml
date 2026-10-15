import QtQuick
import "../../components" as Components

// F5 RANGE isolated mock owner. No Git, Hospital, sound or system service.
Item {
    id: demo
    width: 880
    height: 425

    property real percentLow: 20
    property real percentHigh: 75
    property real tempLow: -15
    property real tempHigh: 45

    Rectangle {
        anchors.fill: parent
        color: Components.Colors.black
        radius: 3
        border.width: 1
        border.color: Components.Colors.cyan
    }

    Components.GohuText {
        x: 18
        y: 14
        font.pixelSize: 14
        text: "F5 // SELECTOR RANGE"
        color: Components.Colors.cyan
    }

    Components.GohuText {
        x: 18
        y: 38
        font.pixelSize: 9
        text: "TWO HANDLES // ONE INTERVAL // MOCK OWNER ONLY"
        color: Components.Colors.orange
    }

    Components.SelectorSlider {
        id: percentSlider
        x: 155
        y: 66
        height: 255
        selectorProfile: "range"
        sideLabel: "FILTER"
        accentColor: Components.Colors.cyan
        rangeLowerColor: Components.Colors.magenta
        rangeUpperColor: Components.Colors.orange
        minimumValue: 0
        maximumValue: 100
        lowerValue: demo.percentLow
        upperValue: demo.percentHigh
        valueDecimals: 0
        valueSuffix: "%"
        rangeStep: 5
        onRangeRequested: function(low, high) {
            demo.percentLow = low;
            demo.percentHigh = high;
        }
    }

    Components.GohuText {
        x: 300
        y: 112
        text: "OWNER // " + demo.percentLow.toFixed(0)
            + "–" + demo.percentHigh.toFixed(0) + "%"
        font.pixelSize: 12
        color: Components.Colors.white
    }

    Components.GohuText {
        x: 300
        y: 139
        text: percentSlider.rangePreviewActive
            ? "PRE // " + percentSlider.rangePreviewLower.toFixed(0)
                + "–" + percentSlider.rangePreviewUpper.toFixed(0) + "%"
            : "PRE // —"
        font.pixelSize: 11
        color: Components.Colors.yellow
    }

    Components.SelectorSlider {
        id: tempSlider
        x: 538
        y: 66
        height: 255
        selectorProfile: "range"
        sideLabel: "THERMAL"
        accentColor: Components.Colors.orange
        rangeLowerColor: Components.Colors.magenta
        rangeUpperColor: Components.Colors.cyan
        minimumValue: -40
        maximumValue: 80
        lowerValue: demo.tempLow
        upperValue: demo.tempHigh
        valueDecimals: 0
        valueSuffix: "°C"
        rangeStep: 5
        onRangeRequested: function(low, high) {
            demo.tempLow = low;
            demo.tempHigh = high;
        }
    }

    Components.GohuText {
        x: 700
        y: 112
        text: "OWNER // " + demo.tempLow.toFixed(0)
            + " to " + demo.tempHigh.toFixed(0)
        font.pixelSize: 12
        color: Components.Colors.white
    }

    Components.GohuText {
        x: 700
        y: 139
        text: tempSlider.rangePreviewActive
            ? "PRE // " + tempSlider.rangePreviewLower.toFixed(0)
                + " to " + tempSlider.rangePreviewUpper.toFixed(0)
            : "PRE // —"
        font.pixelSize: 11
        color: Components.Colors.yellow
    }

    Components.GohuText {
        x: 20
        y: 340
        text: "DRAG LO OR HI // MOVE ONE ENDPOINT"
        font.pixelSize: 10
        color: Components.Colors.white
    }

    Components.GohuText {
        x: 20
        y: 361
        text: "DRAG CENTER BAND OR SHIFT+DRAG // MOVE ENTIRE INTERVAL"
        font.pixelSize: 10
        color: Components.Colors.white
    }

    Components.GohuText {
        x: 20
        y: 382
        text: "RELEASE // COMMIT   ESC // CANCEL   LEFT/RIGHT // CHOOSE ENDPOINT   UP/DOWN // STEP"
        font.pixelSize: 9
        color: Components.Colors.cyan
    }
}
