import QtQuick
import "../../components"

// M30-D // A focused, non-scrolling MAGICK lunar/solar control station.
// Observation is owned by the existing source-only SKY. The visual
// instrument is the original COSMOS V2 component in compact mode.
// Symbolic practices and personal calendar storage remain unconnected.
Rectangle {
    id: lunarSolarPane
    color: Colors.black
    clip: true

    property string subjectRoute: "magick/lunar-solar/moon"
    property var weatherService: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property bool isCalendar:
        subjectRoute === "magick/lunar-solar/calendar"
    readonly property bool isSolar:
        subjectRoute === "magick/lunar-solar/seasons"

    StationSky {
        id: sourceSky
        width: 1
        height: 1
        opacity: 0
        visible: lunarSolarPane.visible && !lunarSolarPane.isCalendar
        sourceOnly: true
        subjectRoute: lunarSolarPane.isSolar
            ? "cosmos/sun/position" : "cosmos/moon/ephemeris"
        weatherService: lunarSolarPane.weatherService
        runtimeNowMs: lunarSolarPane.runtimeNowMs
    }

    Row {
        id: focusTabs
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 23
        spacing: 4
        Repeater {
            model: [
                {id:"magick/lunar-solar/moon",label:"MOON"},
                {id:"magick/lunar-solar/seasons",label:"SOLAR + SEASONS"},
                {id:"magick/lunar-solar/calendar",label:"CALENDAR"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(1,(focusTabs.width-2*focusTabs.spacing)/3)
                height: 23
                contentPadding: 1
                label: modelData.label
                labelPixelSize: 9
                selected: lunarSolarPane.subjectRoute === modelData.id
                accentColor: selected ? Colors.magenta : Colors.cyan
                onClicked: lunarSolarPane.routeRequested(modelData.id)
            }
        }
    }

    StationCosmosVisualInstruments {
        id: focusedInstrument
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: focusTabs.bottom
        anchors.topMargin: 4
        // Keep the existing compact interactive controls at natural height,
        // freeing the unused lower viewport for original ephemeris/light data.
        height: Math.min(186,Math.max(0,
            lunarSolarPane.height-focusTabs.height-4))
        visible: !lunarSolarPane.isCalendar
        compactMode: true
        showMoon: !lunarSolarPane.isSolar
        showSun: lunarSolarPane.isSolar

        moonReady: !!sourceSky.moonObservation
                   && sourceSky.moonObservation.ready
        moonEphemeris: sourceSky.moonObservation
                       ? sourceSky.moonObservation.ephemeris : null
        astronomySummary: sourceSky.astronomySummary
        twilightSummary: sourceSky.twilightSummary
        currentSolarPosition: sourceSky.currentSolarPosition
        providerLocalMinute: sourceSky.providerLocalMinute
        latitude: lunarSolarPane.weatherService
                  ? lunarSolarPane.weatherService.latitude : ""
        longitude: lunarSolarPane.weatherService
                   ? lunarSolarPane.weatherService.longitude : ""
        solarDate: sourceSky.astronomySummary.date
        solarCivilOffsetMinutes: sourceSky.moonCivilOffsetMinutes
        solarOffsetSource: sourceSky.moonCivilOffsetSource
    }

    // M30-E // The former blank area is now a source-backed event rack.
    // The two panels are siblings, never a whole-screen scrolling page.
    StationMagickLunarSolarDetails {
        id: detailRack
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: focusedInstrument.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 4
        visible: !lunarSolarPane.isCalendar
        isSolar: lunarSolarPane.isSolar
        skySource: sourceSky
    }

    // M7a // Existing forecast service, not a synthetic lunar ephemeris.
    StationMagickForecastCalendarPane {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: focusTabs.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 4
        visible: lunarSolarPane.isCalendar
        weatherService: lunarSolarPane.weatherService
    }
}
