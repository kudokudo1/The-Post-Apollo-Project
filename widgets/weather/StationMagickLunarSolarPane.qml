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
        height: Math.max(0,lunarSolarPane.height-focusTabs.height-4)
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

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: focusTabs.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 4
        visible: lunarSolarPane.isCalendar
        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        Column {
            anchors.centerIn: parent
            width: Math.max(0,parent.width-28)
            spacing: 8
            GohuText {
                width: parent.width
                font.pixelSize: 13
                color: Colors.orange
                text: "PRACTICE CALENDAR // NOT CONNECTED"
                horizontalAlignment: Text.AlignHCenter
            }
            QuietText {
                width: parent.width
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
                text: "CURRENT LUNAR AND SOLAR OBSERVATIONS ARE AVAILABLE UNDER THE OTHER TABS. NO SAVED RITUAL EVENTS, REMINDERS OR HISTORICAL CALENDAR DATA ARE GENERATED HERE."
                horizontalAlignment: Text.AlignHCenter
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                ActionButton {
                    width: 100
                    height: 26
                    label: "VIEW MOON"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    onClicked: lunarSolarPane.routeRequested("magick/lunar-solar/moon")
                }
                ActionButton {
                    width: 100
                    height: 26
                    label: "VIEW SOLAR"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    onClicked: lunarSolarPane.routeRequested("magick/lunar-solar/seasons")
                }
            }
        }
    }
}
