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
    property string moonView: "year"  // "year" or "forecast" on MOON
    property var weatherService: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property bool isMoon: subject === "moon"
    readonly property string annualView:
        isMoon ? (moonView === "forecast" ? "forecast" : "moon") : "solar"
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
        height: visible ? 27 : 0
        spacing: 4

        ActionButton {
            objectName: "cosmos-c11-back-to-moon"
            width: Math.max(1,(lunarModeRail.width-lunarModeRail.spacing)/2)
            height: 27
            label: "OVERVIEW"
            labelPixelSize: 10
            contentPadding: 1
            selected: false
            accentColor: Colors.cyan
            onClicked: annualFocus.routeRequested("cosmos/moon/ephemeris")
        }
        ActionButton {
            objectName: "cosmos-c17-moon-wheel-tab"
            width: Math.max(1,(lunarModeRail.width-lunarModeRail.spacing)/2)
            height: 27
            label: "LUNAR YEAR"
            labelPixelSize: 10
            contentPadding: 1
            selected: annualFocus.moonView !== "forecast"
            accentColor: selected ? Colors.magenta : Colors.cyan
            onClicked: annualFocus.routeRequested("cosmos/moon/year")
        }
    }

    // C23 // All MOON views show the same cyan rule beneath the mode tabs.
    // Reuse the original four-pixel YEAR gap: 2px spacing + 2px rule.
    // SUN's original annual renderer still starts at y=0.
    Rectangle {
        id: moonHeaderDivider
        objectName: "cosmos-c23-moon-year-divider"
        visible: annualFocus.isMoon
        anchors.top: lunarModeRail.bottom
        anchors.topMargin: visible ? 2 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        height: visible ? 2 : 0
        color: Colors.cyan
    }

    // MAGICK remains the owning renderer for the wheel and its JPL service.
    // Locking the view only hides MAGICK's three-way subject switcher, which
    // would otherwise let a COSMOS Sun screen show Moon or a forecast.
    StationMagickAnnualCalendarPane {
        id: annualWheel
        objectName: annualFocus.isMoon
            ? (annualFocus.moonView === "forecast"
                ? "cosmos-c17-moon-forecast-panel"
                : "cosmos-c11-moon-year-wheel")
            : "cosmos-c11-sun-year-wheel"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: moonHeaderDivider.bottom
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        anchors.bottomMargin: annualFocus.contentInset
        anchors.topMargin: 0

        view: annualFocus.annualView
        lockedView: annualFocus.annualView
        compactForecast: annualFocus.isMoon && annualFocus.moonView === "forecast"
        weatherService: annualFocus.weatherService
        runtimeNowMs: annualFocus.runtimeNowMs
    }
}
