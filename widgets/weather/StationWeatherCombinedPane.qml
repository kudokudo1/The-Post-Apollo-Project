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
    color: Colors.black
    clip: true

    readonly property var hourlyRows: sky && sky.hourlyForecast ? sky.hourlyForecast : []
    readonly property var dailyRows: sky && sky.dailyForecast ? sky.dailyForecast : []
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

        Row {
            width: parent.width
            height: 14
            spacing: 4
            GohuText {
                width: Math.max(1,parent.width*0.67)
                height: parent.height
                text: "WEATHER // CONDITIONS + HOURLY + DAILY"
                color: Colors.cyan
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            QuietText {
                width: Math.max(1,parent.width*0.31)
                height: parent.height
                text: panel.currentReady ? "WEATHER ONLINE" : "CURRENT WAITING"
                color: panel.currentReady ? Colors.cyan : Colors.orange
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 8
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: currentBand
            objectName: "weather-w10-current-air-band"
            width: parent.width
            height: 54
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Row {
                anchors.fill: parent
                anchors.margins: 3
                spacing: 3
                Item {
                    width: Math.max(1,(parent.width-12)*0.25)
                    height: parent.height
                    GohuText {
                        text: "CURRENT // CONDITIONS"
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                    GohuText {
                        anchors.top: parent.top
                        anchors.topMargin: 13
                        text: panel.currentReady
                            ? panel.reading(panel.sky.weatherService.tempF,"°F") : "--°F"
                        font.pixelSize: 20
                        color: Colors.orange
                    }
                    GohuText {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: panel.currentReady && panel.sky
                            ? panel.sky.conditionState.icon : "?"
                        font.pixelSize: 26
                        color: panel.currentReady && panel.sky
                            ? panel.sky.iconColor(panel.sky.conditionState.color)
                            : Colors.white
                    }
                    QuietText {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        text: panel.currentReady
                            ? String(panel.sky.weatherService.condition||"--").toUpperCase()
                            : "NO OBSERVATION"
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                }
                Repeater {
                    model: [
                        {label:"AIR QUALITY", key:"air"},
                        {label:"HUMIDITY",key:"humidity"},
                        {label:"WIND",key:"wind"}
                    ]
                    delegate: Item {
                        required property var modelData
                        width: Math.max(1,(currentBand.width-26)*0.19)
                        height: currentBand.height-6
                        QuietText {
                            text: modelData.label
                            width: parent.width
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                        GohuText {
                            anchors.top: parent.top
                            anchors.topMargin: 17
                            width: parent.width
                            font.pixelSize: 13
                            color: Colors.white
                            elide: Text.ElideRight
                            text: modelData.key==="air"
                                  ? (panel.airReady
                                     ? panel.reading(panel.sky.weatherService.aqi,"")
                                     : "--")
                                  : modelData.key==="humidity"
                                    ? (panel.currentReady
                                       ? panel.reading(panel.sky.humidityValue,"%") : "--")
                                    : (panel.currentReady
                                       ? panel.reading(panel.sky.windMphValue," MPH") : "--")
                        }
                        QuietText {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            font.pixelSize: 8
                            elide: Text.ElideRight
                            text: modelData.key==="air"
                                  ? (panel.airReady
                                     ? String(panel.sky.weatherService.aqiLabel||"AQI")
                                     : "WAITING")
                                  : modelData.key==="humidity"
                                    ? "RELATIVE"
                                    : (panel.currentReady
                                       ? String(panel.sky.weatherService.windDirection||"")
                                       : "WIND --")
                        }
                    }
                }
                Item {
                    width: Math.max(1,(currentBand.width-20)*0.17)
                    height: currentBand.height-6
                    QuietText { text: "PRESSURE"; font.pixelSize: 8; color: Colors.cyan }
                    GohuText {
                        anchors.top: parent.top
                        anchors.topMargin: 17
                        font.pixelSize: 11
                        color: Colors.white
                        text: panel.currentReady
                              ? panel.reading(panel.sky.pressureValue," hPa") : "--"
                    }
                    QuietText {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        font.pixelSize: 8
                        elide: Text.ElideRight
                        text: panel.currentReady
                              ? "VIS " + panel.reading(panel.sky.visibilityValue," mi")
                              : "VIS --"
                    }
                }
            }
        }

        Rectangle {
            id: hourlyBand
            objectName: "weather-w10-hourly-band"
            width: parent.width
            height: 77
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
                    model: Math.min(6,panel.hourlyRows.length)
                    delegate: Rectangle {
                        id: hourCell
                        required property int index
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
                        GohuText {
                            anchors.top: parent.top
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: String(hourCell.entry.timeLabel||"--") + " "
                                  +panel.reading(hourCell.entry.tempF,"°F")
                            color: Colors.white
                            font.pixelSize: 9
                        }
                        Item {
                            width: parent.width
                            height: 34
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent
                                text: hourCell.weatherState.icon
                                font.pixelSize: 32
                                color: panel.colorFor(hourCell.weatherState)
                                visible: hourCell.artwork==="weather"
                            }
                            WeatherCelestialGlyph {
                                anchors.centerIn: parent
                                width: 32
                                height: 32
                                mode: hourCell.artwork
                                weatherKind: WeatherCyclePolicy.nightKind(hourCell.weatherState)
                                solar: hourCell.solarCycle.solar
                                moonPhase: hourCell.solarCycle.moonPhase
                                ink: panel.colorFor(hourCell.weatherState)
                                visible: hourCell.artwork!=="weather"
                            }
                        }
                        QuietText {
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 9
                            width: parent.width
                            text: panel.rainLabel(hourCell.entry.chanceRain)
                            horizontalAlignment: Text.AlignHCenter
                            font.pixelSize: 7
                            color: Colors.cyan
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 3
                            height: 4
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
            height: Math.max(1,panel.height - 14 - 54 - 77 - 11 - bands.spacing*4)
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta

            GohuText {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 3
                text: "FORECAST // DAILY"
                font.pixelSize: 9
                color: Colors.orange
            }
            Row {
                id: dayCards
                anchors.top: parent.top
                anchors.topMargin: 15
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 3
                spacing: 3
                Repeater {
                    model: Math.min(3,panel.dailyRows.length)
                    delegate: Rectangle {
                        id: dayCell
                        required property int index
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
                        GohuText {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: 3
                            text: String(dayCell.entry.date||"--")
                                  +"  "+panel.reading(dayCell.entry.maxTempF,"°")
                                  +" / "+panel.reading(dayCell.entry.minTempF,"°F")
                            font.pixelSize: 9
                            color: Colors.white
                        }
                        QuietText {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.topMargin: 15
                            anchors.leftMargin: 3
                            width: parent.width-6
                            text: "SUN "+String(dayCell.entry.sunrise||"--")
                                  +" → "+String(dayCell.entry.sunset||"--")
                            font.pixelSize: 7
                            elide: Text.ElideRight
                        }
                        Item {
                            anchors.centerIn: parent
                            width: 45
                            height: 44
                            Text {
                                anchors.centerIn: parent
                                text: dayCell.weatherState.icon
                                font.pixelSize: 42
                                color: panel.colorFor(dayCell.weatherState)
                                visible: dayCell.artwork==="weather"
                            }
                            WeatherCelestialGlyph {
                                anchors.centerIn: parent
                                width: 43
                                height: 43
                                mode: dayCell.artwork
                                solar: dayCell.solarCycle.solar
                                moonPhase: dayCell.solarCycle.moonPhase
                                ink: panel.colorFor(dayCell.weatherState)
                                visible: dayCell.artwork!=="weather"
                            }
                        }
                        QuietText {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.leftMargin: 3
                            anchors.bottomMargin: 7
                            text: panel.rainLabel(dayCell.entry.chanceRain)
                            font.pixelSize: 8
                        }
                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.right: parent.right
                            anchors.rightMargin: 3
                            anchors.bottomMargin: 8
                            width: 48
                            height: 5
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: (parent.width-2)
                                       *panel.chanceRatio(dayCell.entry.chanceRain)
                                color: Colors.orange
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
