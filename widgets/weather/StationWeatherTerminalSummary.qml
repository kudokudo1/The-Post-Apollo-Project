import QtQuick
import "../../components"
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy

// W8 // One read-only weather terminal instrument shared by the complete
// WEATHER workspace and its OVERVIEW. It never owns providers, timers, or
// refresh actions. Detailed existing SKY artwork remains below it in WEATHER.
Rectangle {
    id: terminal
    objectName: "weather-w8-terminal-summary"
    property var weatherService: null
    property bool compact: false
    // Read-only geometry for native visual-fit verification.
    readonly property alias currentMetricItem: metricRow
    readonly property alias hourlyItem: hourlyRow
    readonly property alias dailyItem: dailyRow
    readonly property bool conditionsReady:
        Boolean(weatherService && weatherService.ready)
    readonly property bool forecastReady:
        Boolean(weatherService && weatherService.forecastReady)
    readonly property bool airReady:
        Boolean(weatherService && weatherService.aqiReady)
    readonly property var hourlySamples:
        forecastReady && weatherService.hourlyForecast
        && typeof weatherService.hourlyForecast.length === "number"
        ? weatherService.hourlyForecast : []
    readonly property var dailySamples:
        forecastReady && weatherService.dailyForecast
        && typeof weatherService.dailyForecast.length === "number"
        ? weatherService.dailyForecast : []

    height: compact ? 158 : 164
    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan
    clip: true

    function validNumber(value, digits) {
        if(value === null || value === undefined || String(value).trim() === "")
            return "--";
        const number = Number(value);
        return isFinite(number) && number > -900 && number < 100000
            ? number.toFixed(digits) : "--";
    }
    function percent(value) {
        const number=Number(value);
        return value !== null && value !== undefined
            && String(value).trim() !== "" && isFinite(number)
            && number>=0 && number<=100
            ? Math.round(number) + "%" : "--";
    }
    function temp(value) {
        const n=Number(value);
        return value !== null && value !== undefined
            && String(value).trim() !== "" && isFinite(n)
            && n>-900 && n<200 ? Math.round(n)+"°F" : "--°F";
    }
    readonly property var metrics: [
        {label:"CONDITIONS",value:conditionsReady
             ? temp(weatherService.tempF) : "--°F",
         info:conditionsReady ? String(weatherService.condition||"UNKNOWN").toUpperCase()
              : "WAITING FOR CURRENT",accent:Colors.orange},
        {label:"AIR QUALITY",value:airReady
             ? "AQI "+validNumber(weatherService.aqi,0) : "AQI --",
         info:airReady ? "PM2.5 "+validNumber(weatherService.pm25,1) : "WAITING FOR AIR",
         accent:Colors.green},
        {label:"HUMIDITY / WIND",value:conditionsReady
             ? percent(weatherService.humidity) : "--",
         info:conditionsReady ? validNumber(weatherService.windMph,0)+" MPH"
              +" // "+String(weatherService.windDirection||"") : "WIND -- MPH",
         accent:Colors.cyan},
        {label:"PRESSURE",value:conditionsReady
             ? validNumber(weatherService.pressureHpa,0)+" hPa" : "-- hPa",
         info:conditionsReady ? "VIS "+validNumber(weatherService.visibilityMiles,1)+" MI"
             : "VISIBILITY --",accent:Colors.magenta}
    ]

    Column {
        id: content
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2

        Row {
            width: parent.width
            height: 14
            spacing: 3
            GohuText {
                width: Math.max(1,parent.width*0.63)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "WEATHER // CURRENT + AIR + FORECAST"
                color: Colors.cyan
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            QuietText {
                width: Math.max(1,parent.width*0.35)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                text: terminal.conditionsReady
                      ? (terminal.forecastReady && terminal.airReady
                         ? "CURRENT / AIR / FCST READY" : "PARTIAL SOURCE")
                      : "CURRENT WAITING"
                color: terminal.conditionsReady ? Colors.cyan : Colors.orange
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }

        Row {
            id: metricRow
            objectName: "weather-w8-current-air-metrics"
            width: parent.width
            height: 48
            spacing: 3
            Repeater {
                model: terminal.metrics
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: Math.max(1,(metricRow.width-9)/4)
                    height: metricRow.height
                    Rectangle {
                        visible: index>0
                        width: 1
                        height: parent.height-8
                        x: 0
                        y: 4
                        color: modelData.accent
                        opacity: 0.65
                    }
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 1
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.label
                            font.pixelSize: 9
                            color: modelData.accent
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 14
                            text: modelData.value
                            font.pixelSize: index===0 ? 18 : 14
                            color: modelData.accent
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.info
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            height: 10
            text: "FORECAST TIMES // RAIN CHANCE FOR EACH LISTED PERIOD"
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
        }

        Row {
            id: hourlyRow
            objectName: "weather-w8-hourly-strip"
            width: parent.width
            height: 29
            spacing: 3
            Repeater {
                model: Math.min(3,terminal.hourlySamples.length)
                delegate: Item {
                    required property int index
                    readonly property var sample: terminal.hourlySamples[index] || {}
                    readonly property var cycle:
                        WeatherCyclePolicy.forecast(sample.date,sample.time,terminal.dailySamples)
                    width: Math.max(1,(hourlyRow.width-6)/3)
                    height: hourlyRow.height
                    Rectangle {
                        visible: index>0
                        x: 0
                        height: parent.height
                        width: 1
                        color: Colors.blue
                    }
                    Row {
                        anchors.fill: parent
                        anchors.margins: 2
                        spacing: 3
                        StationWeatherLineGlyph {
                            width: 27
                            height: 27
                            mode: cycle.solar==="night" ? "night-weather" : "weather"
                            condition: sample.condition || ""
                            weatherCode: sample.weatherCode
                            moonPhase: cycle.moonPhase
                            ink: Colors.orange
                        }
                        Column {
                            width: Math.max(1,parent.width-30)
                            spacing: 2
                            GohuText {
                                width: parent.width
                                height: 10
                                text: String(sample.date||"--").slice(5)
                                      +" "+String(sample.timeLabel||"--")
                                      +"  "+terminal.temp(sample.tempF)
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                height: 10
                                text: terminal.percent(sample.chanceRain)+" CHANCE"
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            GohuText {
                visible: terminal.hourlySamples.length===0
                width: parent.width
                text: "HOURLY FORECAST // WAITING FOR PROVIDER"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        GohuText {
            width: parent.width
            height: 10
            text: "NEXT DAYS // HIGH / LOW + PEAK RAIN CHANCE"
            color: Colors.magenta
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        Row {
            id: dailyRow
            objectName: "weather-w8-daily-strip"
            width: parent.width
            height: 29
            spacing: 3
            Repeater {
                model: Math.min(3,terminal.dailySamples.length)
                delegate: Item {
                    required property int index
                    readonly property var sample: terminal.dailySamples[index] || {}
                    readonly property var cycle:
                        WeatherCyclePolicy.atLocal(sample.date,720,terminal.dailySamples)
                    width: Math.max(1,(dailyRow.width-6)/3)
                    height: dailyRow.height
                    Rectangle {
                        visible: index>0
                        x: 0
                        height: parent.height
                        width: 1
                        color: Colors.magenta
                    }
                    Row {
                        anchors.fill: parent
                        anchors.margins: 2
                        spacing: 3
                        StationWeatherLineGlyph {
                            width: 27
                            height: 27
                            mode: "weather"
                            condition: sample.condition || ""
                            weatherCode: sample.weatherCode
                            moonPhase: cycle.moonPhase
                            ink: Colors.magenta
                        }
                        Column {
                            width: Math.max(1,parent.width-30)
                            spacing: 2
                            GohuText {
                                width: parent.width
                                height: 10
                                text: String(sample.date || "--").slice(5)+"  "
                                      +terminal.temp(sample.maxTempF)
                                      +"/"+terminal.temp(sample.minTempF)
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                height: 10
                                text: terminal.percent(sample.chanceRain)+" PEAK RAIN CHANCE"
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            GohuText {
                visible: terminal.dailySamples.length===0
                width: parent.width
                text: "DAILY FORECAST // WAITING FOR PROVIDER"
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }
}
