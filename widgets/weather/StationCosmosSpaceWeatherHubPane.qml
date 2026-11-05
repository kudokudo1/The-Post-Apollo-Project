import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

// COSMOS C4 // SPACE is a real directory of source-backed instruments.
// The original scrollable SPACE // ALL remains in INDEX unchanged.
Rectangle {
    id: spaceHub
    color: Colors.black
    clip: true

    property var spaceService: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    function displayValue(ready, value, precision, suffix) {
        if (!ready || value === null || value === undefined
                || !isFinite(Number(value)))
            return "--";
        return Number(value).toFixed(precision) + suffix;
    }

    function availability(id, ready, loading, error, received, observed, cache) {
        const row = RuntimePolicy.displayRow(id, {
            active:true, ready:!!ready, loading:!!loading,
            errorText:error||"", receivedAt:received,
            observedAt:observed, usingCache:!!cache
        }, runtimeNowMs);
        return String(row.availability || "UNAVAILABLE").replace(/_/g," ");
    }

    readonly property var categories: [
        {title:"SOLAR WIND + IMF",
         value:displayValue(spaceService && spaceService.solarWindReady,
              spaceService ? spaceService.solarWindSpeed : null,0," KM/S"),
         detail:availability("space-wind",
             spaceService && spaceService.solarWindReady,
             spaceService && spaceService.solarWindLoading,
             spaceService ? spaceService.solarWindErrorText : "",
             spaceService ? spaceService.solarWindLastUpdated : null,
             spaceService ? spaceService.solarWindTime : null,
             spaceService && spaceService.usingPersistentSolarWindCache),
         route:"cosmos/space-weather/solar-wind",color:Colors.yellow},
        {title:"GEOMAGNETIC",
         value:"KP " + displayValue(spaceService && spaceService.kpReady,
              spaceService ? spaceService.kp : null,1,""),
         detail:availability("space-kp",
             spaceService && spaceService.kpReady,
             spaceService && spaceService.kpLoading,
             spaceService ? spaceService.kpErrorText : "",
             spaceService ? spaceService.kpLastUpdated : null,
             spaceService ? spaceService.kpTime : null,
             spaceService && spaceService.usingPersistentKpCache),
         route:"cosmos/space-weather/geomagnetic",color:Colors.cyan},
        {title:"AURORA // OVATION",
         value:"MODEL + LOCAL CELL",
         detail:"NOAA // OPEN TO LOAD FORECAST",
         route:"cosmos/space-weather/aurora",color:Colors.magenta},
        {title:"FORECASTS",
         value:"KP + STORM OUTLOOK",
         detail:"PREDICTIONS // OPEN NOAA MODEL",
         route:"cosmos/space-weather/forecasts",color:Colors.yellow},
        {title:"BULLETINS",
         value:"WATCHES + WARNINGS",
         detail:"PUBLISHED ALERTS // OPEN FEED",
         route:"cosmos/space-weather/bulletins",color:Colors.orange},
        {title:"HISTORY",
         value:"WIND / BZ / KP",
         detail:"OBSERVATION HISTORY // OPEN",
         route:"cosmos/space-weather/history",color:Colors.cyan},
        {title:"SUN // SOLAR ACTIVITY",
         value:displayValue(spaceService && spaceService.solarFluxReady,
              spaceService ? spaceService.solarFlux : null,0," SFU"),
         detail:"SUVI / X-RAY / FLARES / SOLAR CYCLE",
         route:"cosmos/sun/activity",color:Colors.orange},
        {title:"SPACE // ALL",
         value:"COMPLETE REFERENCE",
         detail:"ALL ORIGINAL NOAA INSTRUMENTS",
         route:"cosmos/space-weather/full",color:Colors.magenta}
    ]

    Column {
        id: hubBody
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        GohuText {
            width: parent.width
            height: 24
            text: "COSMOS // SPACE WEATHER"
            color: Colors.magenta
            font.pixelSize: 16
        }

        Rectangle {
            width: parent.width
            height: 2
            color: Colors.cyan
        }

        Grid {
            id: cardsGrid
            width: parent.width
            columns: 2
            rowSpacing: 8
            columnSpacing: 8

            Repeater {
                model: spaceHub.categories
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(cardsGrid.width-cardsGrid.columnSpacing)/2)
                    height: 91
                    color: Colors.dark
                    border.width: 1
                    border.color: modelData.color

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6
                        GohuText {
                            width: parent.width
                            text: modelData.title
                            font.pixelSize: 11
                            color: modelData.color
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.value
                            font.pixelSize: 16
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            text: modelData.detail
                            font.pixelSize: 9
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                    TapHandler {
                        onTapped: spaceHub.routeRequested(modelData.route)
                    }
                    HoverHandler {
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            text: "OBSERVED KP/WIND/FLUX ARE DISTINCT FROM FORECASTS // SELECT A TILE FOR DETAILS"
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
        }
    }
}
