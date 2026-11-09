import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

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
    readonly property int contentInset: isMoon ? HeaderGeometry.inset : 0
    readonly property var wheelItem: annualWheel

    GohuText {
        id: annualHeader
        objectName: "cosmos-c44-moon-year-header"
        visible: annualFocus.isMoon
        anchors.top: annualHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        anchors.topMargin: visible ? HeaderGeometry.inset : 0
        height: visible ? HeaderGeometry.titleHeight : 0
        text: "LUNAR // " + (annualFocus.moonView === "forecast"
            ? "FORECAST" : "YEAR")
        color: Colors.magenta
        font.pixelSize: 10
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    Row {
        id: lunarModeRail
        objectName: "cosmos-c11-moon-year-mode-rail"
        visible: annualFocus.isMoon
        anchors.top: annualHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        anchors.topMargin: visible ? HeaderGeometry.titleToTabs : 0
        height: visible ? HeaderGeometry.tabHeight : 0
        spacing: HeaderGeometry.tabSpacing

        ActionButton {
            objectName: "cosmos-c11-back-to-moon"
            width: HeaderGeometry.buttonWidth(lunarModeRail.width,2)
            height: HeaderGeometry.tabHeight
            label: "OVERVIEW"
            labelPixelSize: 10
            contentPadding: 1
            selected: false
            accentColor: Colors.cyan
            onClicked: annualFocus.routeRequested("cosmos/moon/ephemeris")
        }
        ActionButton {
            objectName: "cosmos-c17-moon-wheel-tab"
            width: HeaderGeometry.buttonWidth(lunarModeRail.width,2)
            height: HeaderGeometry.tabHeight
            label: "LUNAR YEAR"
            labelPixelSize: 10
            contentPadding: 1
            selected: annualFocus.moonView !== "forecast"
            accentColor: selected ? Colors.magenta : Colors.cyan
            onClicked: annualFocus.routeRequested("cosmos/moon/year")
        }
    }

    // C23 // All MOON views show the same cyan rule beneath the mode tabs.
    // Match COSMOS SUN's 5px tab-to-divider gap, and keep 3px
    // between the divider and the wheel. SUN remains at y=0.
    Rectangle {
        id: moonHeaderDivider
        objectName: "cosmos-c23-moon-year-divider"
        visible: annualFocus.isMoon
        anchors.top: lunarModeRail.bottom
        anchors.topMargin: visible ? HeaderGeometry.tabsToRule : 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: annualFocus.contentInset
        anchors.rightMargin: annualFocus.contentInset
        height: visible ? HeaderGeometry.ruleHeight : 0
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
        anchors.topMargin: annualFocus.isMoon ? HeaderGeometry.ruleToContent : 0

        view: annualFocus.annualView
        lockedView: annualFocus.annualView
        compactForecast: annualFocus.isMoon && annualFocus.moonView === "forecast"
        weatherService: annualFocus.weatherService
        runtimeNowMs: annualFocus.runtimeNowMs
    }
}
