import QtQuick
import "../../components"
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy

// W10 // One fixed WEATHER instrument combining the *existing* current/air,
// six-hour and three-day data. Only presentation changes: source and forecast
// artwork classification still come from the original StationSky and policy.
Rectangle {
    id: panel
    objectName: "weather-w10-three-band-terminal"
    property var sky: null
    readonly property alias currentItem: currentBand
    readonly property alias hourlyItem: hourlyBand
    readonly property alias dailyItem: dailyBand
    readonly property alias hourRepeater: hourlyRepeater
    readonly property alias dayCardsRepeater: dayRepeater
    readonly property alias footerItem: statusFooter
    color: Colors.black
    clip: true

    // W12: all three bands fit the fixed viewport. Daily receives enough
    // room for actual glyphs while current/hourly retain readable symbols.
    readonly property real bandBudget: Math.max(1,height - 14 - 11 - 4*2)
    readonly property real dailyHeight: Math.max(62,Math.min(74,bandBudget*0.30))
    readonly property real currentHeight: Math.max(69,Math.round((bandBudget-dailyHeight)*0.47))
    readonly property real hourlyHeight: Math.max(1,bandBudget-dailyHeight-currentHeight)

    readonly property var hourlyRows: sky && sky.weatherService
        && sky.weatherService.forecastReady && sky.hourlyForecast
        ? sky.hourlyForecast : []
    readonly property var dailyRows: sky && sky.weatherService
        && sky.weatherService.forecastReady && sky.dailyForecast
        ? sky.dailyForecast : []
    readonly property bool currentReady: Boolean(sky && sky.weatherReady)
    readonly property bool airReady: Boolean(sky && sky.aqiReady)

    function reading(value, suffix) {
        if (value === null || value === undefined || String(value).trim() === "")
            return "--";
        const n = Number(value);
        return isFinite(n) && n > -900 && n < 100000
            ? Math.round(n) + (suffix || "") : "--";
    }
    function chance(value) {
        const n=Number(value);
        return value !== null && value !== undefined && String(value).trim() !== ""
            && isFinite(n) && n>=0 && n<=100 ? Math.round(n) : -1;
    }
    function rainLabel(value) {
        const n=chance(value);
        return n < 0 ? "RAIN --" : "RAIN " + n + "%";
    }
    function chanceRatio(value) {
        return Math.max(0,chance(value)) / 100;
    }
    function state(entry) {
        return sky ? sky.iconState(entry.condition,entry.weatherCode,false)
            : {icon:"?",color:"white"};
    }
    function colorFor(stateObj) {
        return sky ? sky.iconColor(stateObj.color) : Colors.white;
    }

    Column {
        id: bands
        anchors.fill: parent
        spacing: 2

        // W13 // One centered terminal heading; source state remains at right.
        Item {
            id: terminalHeading
            objectName: "weather-w13-centered-heading"
            width: parent.width
            height: 14

            GohuText {
                anchors.centerIn: parent
                width: Math.max(1,parent.width-170)
                height: parent.height
                text: "WEATHER // CONDITIONS + HOURLY + DAILY"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: Colors.cyan
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            QuietText {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 88
                height: parent.height
                text: panel.currentReady ? "WEATHER ONLINE" : "CURRENT WAITING"
                color: panel.currentReady ? Colors.cyan : Colors.orange
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: currentBand
            readonly property alias conditionIconItem: conditionArt
            readonly property alias temperatureMeterItem: temperatureBar
            readonly property alias metricCards: currentMetricRepeater
            objectName: "weather-w10-current-air-band"
            width: parent.width
            height: panel.currentHeight
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Row {
                id: currentMetrics
                anchors.fill: parent
                anchors.margins: 3
                spacing: 3

                Item {
                    id: currentCondition
                    width: Math.max(1,(currentMetrics.width-12)*0.31)
                    height: currentMetrics.height

                    // Keep the title, temperature, glyph, reading and bar
                    // together as ONE instrument centered in its own bay.
                    Column {
                        id: conditionStack
                        objectName: "weather-w13-centered-current-readout"
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        spacing: 2

                        QuietText {
                            width: parent.width
                            height: 10
                            text: "CURRENT // CONDITIONS"
                            horizontalAlignment: Text.AlignHCenter
                            font.pixelSize: 8
                            color: Colors.orange
                            elide: Text.ElideRight
                        }
                        Row {
                            id: conditionValueRow
                            width: parent.width
                            height: Math.max(30,Math.min(60,currentCondition.height-42))
                            spacing: 2
                            Item {
                                width: Math.max(1,parent.width*0.49)
                                height: parent.height
                                GohuText {
                                    anchors.centerIn: parent
                                    text: panel.currentReady
                                        ? panel.reading(panel.sky.weatherService.tempF,"°F")
                                        : "--°F"
                                    font.pixelSize: 29
                                    color: Colors.orange
                                }
                            }
                            Item {
                                id: conditionArt
                                objectName: "weather-w12-current-condition-icon"
                                width: Math.min(69,Math.max(36,conditionValueRow.height))
                                height: parent.height
                                Text {
                                    anchors.centerIn: parent
                                    text: panel.currentReady && panel.sky
                                        ? panel.sky.conditionState.icon : "?"
                                    font.pixelSize: Math.max(45,conditionArt.width)
                                    color: panel.currentReady && panel.sky
                                        ? panel.sky.iconColor(panel.sky.conditionState.color)
                                        : Colors.white
                                    visible: !panel.currentReady || !panel.sky
                                        || panel.sky.currentCelestialMode==="weather"
                                }
                                WeatherCelestialGlyph {
                                    anchors.centerIn: parent
                                    width: conditionArt.width
                                    height: Math.min(conditionArt.width,conditionArt.height)
                                    mode: panel.sky ? panel.sky.currentCelestialMode : "weather"
                                    weatherKind: panel.sky
                                        ? WeatherCyclePolicy.nightKind(panel.sky.conditionState)
                                        : "clear"
                                    solar: panel.sky ? panel.sky.skyCycle.solar : "day"
                                    moonPhase: panel.sky ? panel.sky.skyCycle.moonPhase : 0
                                    ink: panel.currentReady && panel.sky
                                        ? panel.sky.iconColor(panel.sky.conditionState.color)
                                        : Colors.white
                                    visible: panel.currentReady && panel.sky
                                        && panel.sky.currentCelestialMode!=="weather"
                                }
                            }
                        }
                        QuietText {
                            width: parent.width
                            height: 10
                            text: panel.currentReady
                                ? String(panel.sky.weatherService.condition||"--").toUpperCase()
                                : "NO OBSERVATION"
                            horizontalAlignment: Text.AlignHCenter
                            font.pixelSize: 8
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            id: temperatureBar
                            objectName: "weather-w12-temperature-meter"
                            width: parent.width
                            height: 8
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: Math.max(0,(parent.width-2)
                                       *(panel.currentReady ? panel.sky.temperatureMeter : 0))
                                color: Colors.orange
                            }
                        }
                    }
                }

                Repeater {
                    id: currentMetricRepeater
                    model: [
                        {label:"AIR QUALITY",key:"air"},
                        {label:"HUMIDITY",key:"humidity"},
                        {label:"WIND",key:"wind"},
                        {label:"PRESSURE",key:"pressure"}
                    ]
                    delegate: Item {
                        id: metric
                        required property var modelData
                        readonly property alias directionArrow: windArrow
                        readonly property alias dataMeter: metricMeter
                        readonly property alias readoutStack: metricStack
                        width: Math.max(1,(currentMetrics.width-12)*0.1725)
                        height: currentMetrics.height
                        readonly property bool hasMeter: modelData.key!=="pressure"
                        readonly property real meterRatio: !panel.sky ? 0
                            : modelData.key==="air"
                              ? (panel.airReady ? panel.sky.aqiMeter : 0)
                            : modelData.key==="humidity"
                              ? (panel.currentReady ? panel.sky.humidityMeter : 0)
                            : modelData.key==="wind"
                              ? (panel.currentReady ? panel.sky.windMeter : 0)
                            : 0

                        Column {
                            id: metricStack
                            objectName: "weather-w13-centered-reading-stack"
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            spacing: 3

                            QuietText {
                                width: parent.width
                                height: 10
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                text: modelData.label
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                            Item {
                                width: parent.width
                                height: 22
                                Row {
                                    anchors.centerIn: parent
                                    spacing: 1
                                    GohuText {
                                        id: windArrow
                                        objectName: "weather-w12-wind-arrow"
                                        visible: modelData.key==="wind"
                                        width: visible ? 19 : 0
                                        height: 20
                                        verticalAlignment: Text.AlignVCenter
                                        text: "↑"
                                        font.pixelSize: 22
                                        color: Colors.orange
                                        rotation: panel.currentReady && panel.sky
                                            ? panel.sky.windAngle(
                                                panel.sky.weatherService.windDirection)
                                            : 0
                                    }
                                    GohuText {
                                        font.pixelSize: modelData.key==="pressure" ? 12 : 15
                                        color: Colors.white
                                        text: modelData.key==="air"
                                              ? (panel.airReady
                                                 ? panel.reading(panel.sky.weatherService.aqi,"")
                                                 : "--")
                                              : modelData.key==="humidity"
                                                ? (panel.currentReady
                                                   ? panel.reading(panel.sky.humidityValue,"%")
                                                   : "--")
                                              : modelData.key==="wind"
                                                ? (panel.currentReady
                                                   ? panel.reading(panel.sky.windValue,"")
                                                   : "--")
                                              : (panel.currentReady && panel.sky.pressureValue>=0
                                                 ? panel.reading(panel.sky.pressureValue," hPa") : "--")
                                    }
                                }
                            }
                            QuietText {
                                width: parent.width
                                height: 10
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 8
                                elide: Text.ElideRight
                                text: modelData.key==="air"
                                      ? (panel.airReady
                                         ? String(panel.sky.weatherService.aqiLabel||"AQI")
                                         : "WAITING")
                                      : modelData.key==="humidity" ? "RELATIVE"
                                      : modelData.key==="wind"
                                        ? (panel.currentReady
                                           ? String(panel.sky.weatherService.windDirection||"")
                                             +" // MPH" : "WIND --")
                                      : (panel.currentReady && panel.sky.visibilityValue>=0
                                         ? "VIS "+panel.reading(panel.sky.visibilityValue," mi")
                                         : "VIS --")
                            }
                            Rectangle {
                                id: metricMeter
                                objectName: "weather-w12-current-data-meter"
                                visible: metric.hasMeter
                                width: parent.width
                                height: visible ? 8 : 0
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                                Rectangle {
                                    x: 1
                                    y: 1
                                    height: Math.max(0,parent.height-2)
                                    width: Math.max(0,(parent.width-2)*metric.meterRatio)
                                    color: Colors.orange
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: hourlyBand
            objectName: "weather-w10-hourly-band"
            width: parent.width
            height: panel.hourlyHeight
            color: Colors.black
            border.width: 1
            border.color: Colors.blue

            Row {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 3
                height: 11
                GohuText {
                    width: 135
                    font.pixelSize: 9
                    color: Colors.orange
                    text: "FORECAST // NEXT HOURS"
                }
                QuietText {
                    width: Math.max(1,parent.width-135)
                    font.pixelSize: 8
                    color: Colors.magenta
                    text: panel.sky && panel.sky.inspectedHour
                          ? String(panel.sky.inspectedHour.timeLabel||"")
                            +" // "+String(panel.sky.inspectedHour.condition||"")
                          : "SELECT HOUR TO INSPECT"
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideRight
                }
            }

            Row {
                id: hourCards
                objectName: "weather-w10-six-hour-icons"
                anchors.top: parent.top
                anchors.topMargin: 15
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 3
                spacing: 2
                Repeater {
                    id: hourlyRepeater
                    model: Math.min(6,panel.hourlyRows.length)
                    delegate: Rectangle {
                        id: hourCell
                        required property int index
                        readonly property alias mainGlyph: hourlyWeatherGlyph
                        readonly property alias rainMeter: hourlyRainMeter
                        readonly property var entry: panel.hourlyRows[index] || ({})
                        readonly property var weatherState: panel.state(entry)
                        readonly property var solarCycle:
                            WeatherCyclePolicy.forecast(entry.date,entry.time,panel.dailyRows)
                        readonly property string artwork:
                            WeatherCyclePolicy.artworkFor(weatherState,solarCycle)
                        width: Math.max(1,(hourCards.width-10)/6)
                        height: hourCards.height
                        color: panel.sky && panel.sky.inspectedHourIndex===index
                            ? Colors.dark : Colors.black
                        border.width: 1
                        border.color: panel.sky && panel.sky.inspectedHourIndex===index
                            ? Colors.magenta : Colors.blue
                        // W13 // The time, glyph, rain label and meter travel
                        // together. The meter must never drift to card bottom.
                        readonly property real artHeight:
                            Math.max(24,Math.min(56,hourCell.height-35))
                        readonly property real instrumentHeight:
                            11 + artHeight + 10 + 8 + 6
                        GohuText {
                            id: hourTime
                            objectName: "weather-w13-hour-centered-label"
                            anchors.top: parent.top
                            anchors.topMargin: Math.max(0,
                                (hourCell.height-hourCell.instrumentHeight)/2)
                            anchors.horizontalCenter: parent.horizontalCenter
                            height: 11
                            text: String(hourCell.entry.timeLabel||"--") + " "
                                  +panel.reading(hourCell.entry.tempF,"°F")
                            color: Colors.white
                            font.pixelSize: 9
                        }
                        Item {
                            id: hourArtwork
                            objectName: "weather-w13-hour-glyph"
                            width: parent.width
                            height: hourCell.artHeight
                            anchors.top: hourTime.bottom
                            anchors.topMargin: 2
                            Text {
                                anchors.centerIn: parent
                                id: hourlyWeatherGlyph
                                text: hourCell.weatherState.icon
                                font.pixelSize: Math.max(34,Math.min(56,parent.height-2))
                                color: panel.colorFor(hourCell.weatherState)
                                visible: hourCell.artwork==="weather"
                            }
                            WeatherCelestialGlyph {
                                anchors.centerIn: parent
                                width: Math.max(30,Math.min(58,parent.height-2))
                                height: width
                                mode: hourCell.artwork
                                weatherKind: WeatherCyclePolicy.nightKind(hourCell.weatherState)
                                solar: hourCell.solarCycle.solar
                                moonPhase: hourCell.solarCycle.moonPhase
                                ink: panel.colorFor(hourCell.weatherState)
                                visible: hourCell.artwork!=="weather"
                            }
                        }
                        QuietText {
                            id: hourlyRainReading
                            objectName: "weather-w13-hour-rain-caption"
                            anchors.top: hourArtwork.bottom
                            anchors.topMargin: 1
                            width: parent.width
                            height: 10
                            text: panel.rainLabel(hourCell.entry.chanceRain)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 9
                            color: Colors.cyan
                        }
                        Rectangle {
                            id: hourlyRainMeter
                            anchors.top: hourlyRainReading.bottom
                            anchors.topMargin: 2
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 3
                            anchors.rightMargin: 3
                            height: 8
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                width: Math.max(0,(parent.width-2)
                                         * panel.chanceRatio(hourCell.entry.chanceRain))
                                height: Math.max(0,parent.height-2)
                                x: 1
                                y: 1
                                color: Colors.orange
                            }
                        }
                        TapHandler {
                            onTapped: {
                                if(panel.sky)
                                    panel.sky.inspectedHourIndex=index;
                            }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
                QuietText {
                    visible: panel.hourlyRows.length===0
                    text: "HOURLY FORECAST // WAITING FOR SOURCE"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }
        }

        Rectangle {
            id: dailyBand
            objectName: "weather-w10-daily-band"
            width: parent.width
            height: panel.dailyHeight
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 2
                text: "FORECAST // DAILY"
                font.pixelSize: 9
                color: Colors.orange
            }
            Row {
                id: dayCards
                anchors.top: parent.top
                anchors.topMargin: 16
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 2
                spacing: 3
                Repeater {
                    id: dayRepeater
                    model: Math.min(3,panel.dailyRows.length)
                    delegate: Rectangle {
                        id: dayCell
                        required property int index
                        readonly property alias iconHolder: dayArtwork
                        readonly property var entry: panel.dailyRows[index] || ({})
                        readonly property var weatherState: panel.state(entry)
                        readonly property var solarCycle:
                            WeatherCyclePolicy.atLocal(entry.date,720,panel.dailyRows)
                        readonly property string artwork:
                            WeatherCyclePolicy.artworkFor(weatherState,solarCycle)
                        width: Math.max(1,(dayCards.width-6)/3)
                        height: dayCards.height
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        Row {
                            anchors.fill: parent
                            anchors.margins: 2
                            spacing: 3
                            Item {
                                id: dayArtwork
                                width: Math.min(44,parent.height)
                                height: parent.height
                                Text {
                                    anchors.centerIn: parent
                                    text: dayCell.weatherState.icon
                                    font.pixelSize: Math.min(44,parent.height)
                                    color: panel.colorFor(dayCell.weatherState)
                                    visible: dayCell.artwork==="weather"
                                }
                                WeatherCelestialGlyph {
                                    anchors.centerIn: parent
                                    width: Math.min(44,parent.height)
                                    height: width
                                    mode: dayCell.artwork
                                    solar: dayCell.solarCycle.solar
                                    moonPhase: dayCell.solarCycle.moonPhase
                                    ink: panel.colorFor(dayCell.weatherState)
                                    visible: dayCell.artwork!=="weather"
                                }
                            }
                            Column {
                                width: Math.max(1,parent.width-49)
                                height: Math.min(parent.height,34)
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 1
                                GohuText {
                                    width: parent.width
                                    height: 10
                                    font.pixelSize: 9
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    text: String(dayCell.entry.date||"--").slice(5)
                                          +"  "+panel.reading(dayCell.entry.maxTempF,"°")
                                          +" / "+panel.reading(dayCell.entry.minTempF,"°F")
                                    color: Colors.white
                                }
                                QuietText {
                                    width: parent.width
                                    height: 9
                                    font.pixelSize: 7
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    text: "SUN "+String(dayCell.entry.sunrise||"--")
                                          +" → "+String(dayCell.entry.sunset||"--")
                                }
                                Row {
                                    width: parent.width
                                    height: 8
                                    spacing: 3
                                    QuietText {
                                        width: Math.min(44,parent.width*0.42)
                                        height: parent.height
                                        font.pixelSize: 8
                                        horizontalAlignment: Text.AlignHCenter
                                        text: panel.rainLabel(dayCell.entry.chanceRain)
                                        color: Colors.cyan
                                        elide: Text.ElideRight
                                    }
                                    Rectangle {
                                        width: Math.max(1,parent.width-47)
                                        height: 7
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan
                                        Rectangle {
                                            x: 1
                                            y: 1
                                            height: Math.max(0,parent.height-2)
                                            width: Math.max(0,(parent.width-2)
                                                   *panel.chanceRatio(dayCell.entry.chanceRain))
                                            color: Colors.orange
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                QuietText {
                    visible: panel.dailyRows.length===0
                    text: "DAILY FORECAST // WAITING FOR SOURCE"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }
        }

        QuietText {
            id: statusFooter
            height: 11
            width: parent.width
            font.pixelSize: 8
            color: Colors.cyan
            elide: Text.ElideRight
            text: panel.sky && panel.sky.inspectedHourMetrics
                  && panel.sky.inspectedHourMetrics.length>0
                  ? "INSPECT // "+panel.sky.inspectedHourMetrics.slice(0,3)
                    .map(function(v){return v.title+" "+v.value;}).join(" // ")
                  : panel.currentReady
                    ? "ATMOSPHERE // CLOUD "
                      +panel.reading(panel.sky.cloudCoverValue,"%")
                      +" // UV "+panel.reading(panel.sky.uvValue,"")
                      +" // PRECIP "+panel.reading(panel.sky.precipValue," mm")
                    : "READ ONLY // CURRENT / HOURLY / DAILY SOURCE STATUS"
        }
    }
}
