import QtQuick
import "../../components"

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
    function glyph(weatherCode, condition) {
        const n=Number(weatherCode);
        const label=String(condition||"").toLowerCase();
        if(weatherCode === null || weatherCode === undefined
           || String(weatherCode).trim()==="")
            return label.indexOf("rain")>=0 ? "☂"
              : label.indexOf("sun")>=0 || label.indexOf("clear")>=0 ? "☀"
              : label.indexOf("cloud")>=0 ? "☁" : "◌";
        if(n === 0) return "☀";
        if(n<=3) return "☁";
        if(n===45 || n===48) return "≋";
        if((n>=51 && n<=67) || (n>=80 && n<=82)) return "☂";
        if((n>=71 && n<=77) || (n>=85 && n<=86)) return "❄";
        if(n>=95) return "⚡";
        return "◌";
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
                font.pixelSize: 10
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
            height: 43
            spacing: 3
            Repeater {
                model: terminal.metrics
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(metricRow.width-9)/4)
                    height: metricRow.height
                    color: Colors.black
                    border.width: 1
                    border.color: modelData.accent
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 1
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.label
                            font.pixelSize: 8
                            color: modelData.accent
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 14
                            text: modelData.value
                            font.pixelSize: 12
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            height: 9
                            text: modelData.info
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            height: 10
            text: "NEXT HOURS // TEMPERATURE + PRECIPITATION"
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
        }

        Row {
            id: hourlyRow
            objectName: "weather-w8-hourly-strip"
            width: parent.width
            height: 30
            spacing: 3
            Repeater {
                model: Math.min(3,terminal.hourlySamples.length)
                delegate: Rectangle {
                    readonly property var sample: terminal.hourlySamples[index] || {}
                    width: Math.max(1,(hourlyRow.width-6)/3)
                    height: hourlyRow.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 4
                        GohuText {
                            width: 20
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: terminal.glyph(sample.weatherCode,sample.condition)
                            font.pixelSize: 18
                            color: Colors.yellow
                        }
                        Column {
                            width: Math.max(1,parent.width-24)
                            spacing: 1
                            GohuText {
                                width: parent.width
                                height: 10
                                text: String(sample.timeLabel || "--")
                                      +" // "+terminal.temp(sample.tempF)
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                height: 9
                                text: "RAIN "+terminal.percent(sample.chanceRain)
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            QuietText {
                visible: terminal.hourlySamples.length===0
                width: parent.width
                text: "HOURLY FORECAST // WAITING FOR PROVIDER"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        QuietText {
            width: parent.width
            height: 10
            text: "NEXT DAYS // HIGH + LOW + PRECIPITATION"
            color: Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
        }

        Row {
            id: dailyRow
            objectName: "weather-w8-daily-strip"
            width: parent.width
            height: 30
            spacing: 3
            Repeater {
                model: Math.min(3,terminal.dailySamples.length)
                delegate: Rectangle {
                    readonly property var sample: terminal.dailySamples[index] || {}
                    width: Math.max(1,(dailyRow.width-6)/3)
                    height: dailyRow.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta
                    Row {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 4
                        GohuText {
                            width: 20
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            text: terminal.glyph(sample.weatherCode,sample.condition)
                            font.pixelSize: 18
                            color: Colors.yellow
                        }
                        Column {
                            width: Math.max(1,parent.width-24)
                            spacing: 1
                            GohuText {
                                width: parent.width
                                height: 10
                                text: String(sample.date || "--") + " // "
                                      +terminal.temp(sample.maxTempF)
                                      +"/"+terminal.temp(sample.minTempF)
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                height: 9
                                text: "RAIN "+terminal.percent(sample.chanceRain)
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
            QuietText {
                visible: terminal.dailySamples.length===0
                width: parent.width
                text: "DAILY FORECAST // WAITING FOR PROVIDER"
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }
}
