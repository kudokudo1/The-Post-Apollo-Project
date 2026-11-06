import QtQuick
import "../../components"

// C11 // Two COSMOS destinations for the existing MAGICK JPL annual wheel.
// No copied Canvas, provider, backend script, or astronomy calculations.
Rectangle {
    id: annualFocus
    objectName: "cosmos-c11-annual-focus"
    color: Colors.black
    clip: true

    property string subject: "moon"  // "moon" or "sun"
    property var weatherService: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property bool isMoon: subject === "moon"
    readonly property string annualView: isMoon ? "moon" : "solar"
    readonly property int contentInset: isMoon ? 6 : 0
    readonly property var wheelItem: annualWheel

    Row {
        id: lunarModeRail
        objectName: "cosmos-c11-moon-year-mode-rail"
        visible: annualFocus.isMoon
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        anchors.topMargin: visible ? annualFocus.contentInset : 0
        height: visible ? 22 : 0
        spacing: 4

        ActionButton {
            objectName: "cosmos-c11-back-to-moon"
            width: Math.max(1,(lunarModeRail.width-lunarModeRail.spacing)/2)
            height: 21
            label: "PHASE + POSITION"
            labelPixelSize: 9
            contentPadding: 1
            accentColor: Colors.cyan
            onClicked: annualFocus.routeRequested("cosmos/moon/ephemeris")
        }
        ActionButton {
            width: Math.max(1,(lunarModeRail.width-lunarModeRail.spacing)/2)
            height: 21
            label: "YEAR"
            labelPixelSize: 9
            contentPadding: 1
            selected: true
            accentColor: Colors.magenta
        }
    }

    // MAGICK remains the owning renderer for the wheel and its JPL service.
    // Locking the view only hides MAGICK's three-way subject switcher, which
    // would otherwise let a COSMOS Sun screen show Moon or a forecast.
    StationMagickAnnualCalendarPane {
        id: annualWheel
        objectName: annualFocus.isMoon
            ? "cosmos-c11-moon-year-wheel" : "cosmos-c11-sun-year-wheel"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: lunarModeRail.bottom
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        anchors.bottomMargin: annualFocus.contentInset
        anchors.topMargin: annualFocus.isMoon ? 4 : 0

        view: annualFocus.annualView
        lockedView: annualFocus.annualView
        weatherService: annualFocus.weatherService
        runtimeNowMs: annualFocus.runtimeNowMs
    }
}
