import QtQuick
import "../../components"
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy

// W14 // WEATHER presentation-only instrument deck.
// One SKY owner, one live/cached forecast; no provider, timer or weather logic.
// Built as three related instruments, NOT a grid of equally weighted cards.
Rectangle {
    id: terminal
    objectName: "weather-w14-instrument-terminal"
    property var sky: null
    color: Colors.black
    clip: true

    readonly property bool currentReady: Boolean(sky && sky.weatherReady)
    readonly property bool airReady: Boolean(sky && sky.aqiReady)
    readonly property var hourlyRows: sky && sky.weatherService &&
        sky.weatherService.forecastReady && sky.hourlyForecast
        ? sky.hourlyForecast : []
    readonly property var dailyRows: sky && sky.weatherService &&
        sky.weatherService.forecastReady && sky.dailyForecast
        ? sky.dailyForecast : []
    readonly property real budget: Math.max(1,height-19-12-8)
    readonly property real currentHeight: Math.max(1,Math.round(budget*0.37))
    readonly property real hourlyHeight: Math.max(1,Math.round(budget*0.45))
    readonly property real dailyHeight: Math.max(1,budget-currentHeight-hourlyHeight)
    readonly property alias currentItem: currentPanel
    readonly property alias hourlyItem: hourlyPanel
    readonly property alias dailyItem: dailyPanel
    readonly property alias hourRepeater: hourlyRepeater
    readonly property alias dayCardsRepeater: dailyRepeater
    readonly property alias footerItem: inspectStatus
    readonly property alias headingItem: heading
    readonly property alias headingTitle: headingText

    function read(value,unit) {
        if(value===undefined || value===null || String(value).trim()==="")
            return "--";
        const n=Number(value);
        return isFinite(n) && n>-900 && n<100000
            ? Math.round(n)+(unit||"") : "--";
    }
    function rainChance(value) {
        if(value===undefined || value===null || String(value).trim()==="")
            return "--";
        const n=Number(value);
        return isFinite(n) && n>=0 && n<=100
            ? Math.round(n)+"%" : "--";
    }
    function fraction(value) {
        if(value===undefined || value===null || String(value).trim()==="")
            return 0;
        const n=Number(value);
        return isFinite(n) && n>=0 && n<=100 ? n/100 : 0;
    }
    function status(entry) {
        return sky ? sky.iconState(entry.condition,entry.weatherCode,false)
                   : {icon:"?",color:"white"};
    }
    function ink(entry) {
        return sky ? sky.iconColor(status(entry).color) : Colors.white;
    }
    function dateLabel(value) {
        const date=String(value||"");
        return /^\d{4}-\d{2}-\d{2}$/.test(date)
            ? date.slice(5).replace("-","/") : "DATE --";
    }

    Column {
        id: deck
        anchors.fill: parent
        spacing: 2

        Item {
            id: heading
            objectName: "weather-w14-header-context"
            width: parent.width
            height: 19
            GohuText {
                id: headingText
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(1,parent.width-160)
                text: "WEATHER // LIVE CONDITIONS"
                color: Colors.cyan
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            GohuText {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 150
                horizontalAlignment: Text.AlignRight
                text: terminal.currentReady ? "OBSERVED // ONLINE" : "OBSERVATION // WAITING"
                color: terminal.currentReady ? Colors.omnitrix : Colors.orange
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Colors.cyan
            }
        }

        Item {
            id: currentPanel
            objectName: "weather-w14-current-focus"
            width: parent.width
            height: terminal.currentHeight
            readonly property alias mainGlyph: mainWeatherIcon
            readonly property alias mainTemperature: temperature
            readonly property alias weatherMeters: metricRepeater

            Rectangle {
                width: 3
                height: parent.height-4
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.orange
            }
            Item {
                id: largeCurrent
                x: 7
                width: parent.width*0.45-9
                height: parent.height
                SecondaryText {
                    id: currentLabel
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    width: parent.width
                    height: 13
                    text: "NOW // "+ (terminal.currentReady
                          ? String(terminal.sky.weatherService.condition||"UNKNOWN").toUpperCase()
                          : "WAITING FOR OBSERVATION")
                    color: Colors.orange
                    opacity: 1
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                GohuText {
                    id: temperature
                    objectName: "weather-w14-primary-temperature"
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: terminal.currentReady
                          ? terminal.read(terminal.sky.weatherService.tempF,"°F") : "--°F"
                    font.pixelSize: 37
                    color: Colors.orange
                }
                SafeDropShadow {
                    anchors.fill: temperature
                    safeSource: temperature
                    radius: 9
                    samples: 17
                    opacity: 0.48
                    color: Colors.orange
                    requestedVisible: terminal.currentReady
                    z: -1
                }
                // W15 // Reuse the exact pre-W14 StationSky glyph family.
                // Keep this instrument's size/position, not the W14 Canvas art.
                Item {
                    id: mainWeatherIcon
                    objectName: "weather-w15-original-current-icon"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    // Keep the original artwork while making the primary
                    // observation symbol the dominant icon of this band.
                    width: Math.max(75,Math.min(104,currentPanel.height+16,
                                     largeCurrent.width*0.50))
                    height: width
                    Text {
                        id: originalConditionGlyph
                        anchors.centerIn: parent
                        text: terminal.sky ? terminal.sky.conditionState.icon : "?"
                        font.pixelSize: Math.max(78,mainWeatherIcon.width+8)
                        color: terminal.sky
                               ? terminal.sky.iconColor(terminal.sky.conditionState.color)
                               : Colors.orange
                        visible: !terminal.currentReady || !terminal.sky
                                 || terminal.sky.currentCelestialMode==="weather"
                    }
                    WeatherCelestialGlyph {
                        id: originalCelestialGlyph
                        anchors.centerIn: parent
                        width: parent.width
                        height: parent.height
                        scale: 1.14
                        mode: terminal.sky ? terminal.sky.currentCelestialMode : "moon"
                        weatherKind: terminal.sky
                                     ? WeatherCyclePolicy.nightKind(terminal.sky.conditionState)
                                     : "clear"
                        solar: terminal.sky ? terminal.sky.skyCycle.solar : "day"
                        moonPhase: terminal.sky
                                   ? terminal.sky.skyCycle.moonPhase : "unknown"
                        ink: terminal.sky
                             ? terminal.sky.iconColor(terminal.sky.conditionState.color)
                             : Colors.orange
                        visible: terminal.currentReady && terminal.sky
                                 && terminal.sky.currentCelestialMode!=="weather"
                    }
                }
                SafeDropShadow {
                    anchors.fill: mainWeatherIcon
                    safeSource: mainWeatherIcon
                    radius: 10
                    samples: 17
                    opacity: 0.38
                    color: Colors.orange
                    requestedVisible: terminal.currentReady
                    z: -1
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    width: parent.width
                    text: terminal.currentReady
                          ? "FEELS "+terminal.read(terminal.sky.weatherService.feelsLikeF,"°F")
                          : "FEELS --°F"
                    font.pixelSize: 11
                    color: Colors.yellow
                }
            }

            Rectangle {
                x: parent.width*0.45
                width: 1
                y: 7
                height: parent.height-14
                color: Colors.cyan
                opacity: 0.65
            }

            Grid {
                id: telemetry
                x: parent.width*0.45+7
                width: parent.width*0.55-10
                height: parent.height
                columns: 2
                rowSpacing: 2
                columnSpacing: 9
                Repeater {
                    id: metricRepeater
                    model: [
                        {name:"AIR QUALITY",key:"air",accent:Colors.magenta},
                        {name:"HUMIDITY",key:"humidity",accent:Colors.cyan},
                        {name:"WIND // MPH",key:"wind",accent:Colors.yellow},
                        {name:"PRESSURE",key:"pressure",accent:Colors.blue}
                    ]
                    delegate: Item {
                        id: metric
                        required property var modelData
                        width: (telemetry.width-telemetry.columnSpacing)/2
                        height: Math.max(1,(telemetry.height-telemetry.rowSpacing)/2)
                        readonly property alias meter: readingBar
                        readonly property alias readoutRow: metricValueRow
                        readonly property bool valid: modelData.key==="air"
                            ? terminal.airReady : terminal.currentReady
                        readonly property real ratio: !terminal.sky ? 0
                            : modelData.key==="air" ? terminal.sky.aqiMeter
                            : modelData.key==="humidity" ? terminal.sky.humidityMeter
                            : modelData.key==="wind" ? terminal.sky.windMeter
                            : 0

                        GohuText {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            text: metric.modelData.name
                            font.pixelSize: metric.height<40 ? 9 : 10
                            color: metric.modelData.accent
                        }
                        Row {
                            id: metricValueRow
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.topMargin: metric.height<40 ? 9 : 11
                            spacing: 2
                            GohuText {
                                objectName: "weather-w14-wind-bearing-arrow"
                                visible: metric.modelData.key==="wind"
                                text: "↑"
                                width: visible ? 14 : 0
                                color: Colors.yellow
                                font.pixelSize: 14
                                rotation: terminal.currentReady && terminal.sky
                                    ? terminal.sky.windAngle(
                                        terminal.sky.weatherService.windDirection)
                                    : 0
                            }
                            GohuText {
                                text: metric.modelData.key==="air"
                                      ? (metric.valid
                                         ? terminal.read(terminal.sky.weatherService.aqi,"")
                                         : "--")
                                      : metric.modelData.key==="humidity"
                                        ? (metric.valid
                                           ? terminal.read(terminal.sky.humidityValue,"%") : "--")
                                      : metric.modelData.key==="wind"
                                        ? (metric.valid
                                           ? terminal.read(terminal.sky.windValue,"") + " "
                                             +String(terminal.sky.weatherService.windDirection||"")
                                           : "--")
                                      : (metric.valid && terminal.sky.pressureValue>=0
                                         ? terminal.read(terminal.sky.pressureValue," hPa")
                                         : "--")
                                font.pixelSize: metric.modelData.key==="pressure" ? 11
                                                : (metric.height<40 ? 13 : 14)
                                color: Colors.white
                            }
                        }
                        Rectangle {
                            id: readingBar
                            visible: metric.modelData.key!=="pressure"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            // W19 // A reading meter belongs with its value,
                            // centered in the free cell space, not as the bottom divider.
                            y: Math.min(metric.height-height-1,
                               metricValueRow.y+metricValueRow.height
                               +Math.max(2,(metric.height-metricValueRow.y
                                  -metricValueRow.height-height)/2))
                            height: visible ? (metric.height<40 ? 6 : 7) : 0
                            color: Colors.black
                            border.width: 1
                            border.color: metric.modelData.accent
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: Math.max(0,(parent.width-2)* (metric.valid?metric.ratio:0))
                                color: metric.modelData.accent
                            }
                        }
                        GohuText {
                            visible: metric.modelData.key==="pressure"
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 1
                            text: terminal.currentReady && terminal.sky.visibilityValue>=0
                                  ? "VIS "+terminal.read(terminal.sky.visibilityValue," MI") : "VIS --"
                            font.pixelSize: 9
                            color: Colors.cyan
                        }
                    }
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.orange
                opacity: 0.7
            }
        }

        Item {
            id: hourlyPanel
            objectName: "weather-w14-hourly-timeline"
            width: parent.width
            height: terminal.hourlyHeight

            Item {
                id: hourlyHeader
                width: parent.width
                height: 14
                GohuText {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "NEXT 6 FORECAST TIMES"
                    color: Colors.orange
                    font.pixelSize: 12
                }
                GohuText {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: "RAIN CHANCE // EACH LISTED PERIOD"
                    font.pixelSize: 9
                    color: Colors.cyan
                }
            }
            Rectangle {
                anchors.top: hourlyHeader.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
                opacity: 0.6
            }
            Row {
                id: hourTimeline
                objectName: "weather-w14-connected-six-hour-timeline"
                anchors.top: hourlyHeader.bottom
                anchors.topMargin: 2
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 1
                Repeater {
                    id: hourlyRepeater
                    model: Math.min(6,terminal.hourlyRows.length)
                    delegate: Item {
                        id: hour
                        required property int index
                        readonly property var entry: terminal.hourlyRows[index] || ({})
                        readonly property var forecastState: terminal.status(entry)
                        readonly property var cycle:
                            WeatherCyclePolicy.forecast(entry.date,entry.time,terminal.dailyRows)
                        readonly property string art:
                            WeatherCyclePolicy.artworkFor(forecastState,cycle)
                        readonly property bool selected:
                            terminal.sky && terminal.sky.inspectedHourIndex===index
                        readonly property alias glyph: hourGlyph
                        readonly property alias rainMeter: hourRain
                        readonly property alias timeItem: forecastTime
                        readonly property alias instrumentRegion: hourInstrumentRegion
                        readonly property alias readingStack: hourInstrumentStack
                        readonly property alias temperatureItem: hourTemperature
                        readonly property alias chanceItem: hourChance
                        width: (hourTimeline.width-5)/6
                        height: hourTimeline.height

                        Rectangle {
                            visible: index>0
                            x: 0
                            y: 8
                            width: 1
                            height: parent.height-14
                            color: Colors.cyan
                            opacity: 0.36
                        }
                        Rectangle {
                            anchors.fill: parent
                            visible: hour.selected
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta
                        }
                        Item {
                            anchors.fill: parent
                            anchors.leftMargin: 3
                            anchors.rightMargin: 3
                            // The date/time owns the top; the instrument is
                            // vertically centered in all remaining space.
                            GohuText {
                                id: forecastTime
                                anchors.top: parent.top
                                width: parent.width
                                height: 10
                                font.pixelSize: 10
                                color: Colors.yellow
                                horizontalAlignment: Text.AlignHCenter
                                text: terminal.dateLabel(hour.entry.date)+" "+
                                      String(hour.entry.timeLabel||"--")
                            }
                            Item {
                                id: hourInstrumentRegion
                                objectName: "weather-w15-centered-hour-region"
                                anchors.top: forecastTime.bottom
                                anchors.bottom: parent.bottom
                                width: parent.width
                                Column {
                                    id: hourInstrumentStack
                                    objectName: "weather-w15-centered-hour-stack"
                                    anchors.centerIn: parent
                                    width: parent.width
                                    // Compact slots need the whole existing
                                    // glyph/reading/meter group, not overflow.
                                    spacing: hourInstrumentRegion.height<75 ? 0 : 2
                                    Item {
                                        id: hourGlyph
                                        objectName: "weather-w15-original-hour-icon"
                                        width: Math.max(28,Math.min(38,
                                               hourInstrumentRegion.height-41))
                                        height: width
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        Text {
                                            anchors.centerIn: parent
                                            text: hour.forecastState.icon
                                            font.pixelSize: Math.max(40,hourGlyph.width+7)
                                            color: terminal.ink(hour.entry)
                                            visible: hour.art==="weather"
                                        }
                                        WeatherCelestialGlyph {
                                            anchors.centerIn: parent
                                            width: parent.width
                                            height: parent.height
                                            scale: 1.18
                                            mode: hour.art
                                            weatherKind: WeatherCyclePolicy.nightKind(
                                                hour.forecastState)
                                            solar: hour.cycle.solar
                                            moonPhase: hour.cycle.moonPhase
                                            ink: terminal.ink(hour.entry)
                                            visible: hour.art!=="weather"
                                        }
                                    }
                                    GohuText {
                                        id: hourTemperature
                                        width: parent.width
                                        height: 16
                                        font.pixelSize: 16
                                        color: Colors.white
                                        horizontalAlignment: Text.AlignHCenter
                                        text: terminal.read(hour.entry.tempF,"°F")
                                    }
                                    // W19 // The meter is between temperature and
                                    // its matching chance, never a tile divider.
                                    Rectangle {
                                        id: hourRain
                                        width: parent.width-6
                                        height: 6
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan
                                        Rectangle {
                                            x: 1
                                            y: 1
                                            height: Math.max(0,parent.height-2)
                                            width: Math.max(0,(parent.width-2)
                                                   *terminal.fraction(hour.entry.chanceRain))
                                            color: Colors.orange
                                        }
                                    }
                                    GohuText {
                                        id: hourChance
                                        width: parent.width
                                        height: 10
                                        font.pixelSize: 10
                                        color: Colors.cyan
                                        horizontalAlignment: Text.AlignHCenter
                                        text: terminal.rainChance(hour.entry.chanceRain)
                                    }
                                }
                            }
                        }
                        TapHandler {
                            onTapped: {
                                if(terminal.sky) terminal.sky.inspectedHourIndex=index;
                            }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
                GohuText {
                    visible: terminal.hourlyRows.length===0
                    anchors.verticalCenter: parent.verticalCenter
                    text: "HOURLY FORECAST // WAITING FOR SOURCE"
                    color: Colors.orange
                    font.pixelSize: 11
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }
        }

        Item {
            id: dailyPanel
            objectName: "weather-w14-three-day-outlook"
            width: parent.width
            height: terminal.dailyHeight

            GohuText {
                id: dailyTitle
                anchors.left: parent.left
                anchors.top: parent.top
                text: "THREE-DAY OUTLOOK // PEAK RAIN CHANCE"
                color: Colors.magenta
                font.pixelSize: 10
            }
            Row {
                id: days
                objectName: "weather-w14-daily-summary-strip"
                anchors.top: dailyTitle.bottom
                anchors.topMargin: 2
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                spacing: 3
                Repeater {
                    id: dailyRepeater
                    model: Math.min(3,terminal.dailyRows.length)
                    delegate: Item {
                        id: day
                        required property int index
                        readonly property var entry: terminal.dailyRows[index]||({})
                        readonly property var dayState: terminal.status(entry)
                        readonly property var cycle:
                            WeatherCyclePolicy.atLocal(entry.date,720,terminal.dailyRows)
                        readonly property string art:
                            WeatherCyclePolicy.artworkFor(dayState,cycle)
                        width: (days.width-6)/3
                        height: days.height
                        readonly property alias rainMeter: dayRainMeter
                        readonly property alias temperatureItem: dayTemperature
                        readonly property alias chanceItem: dayChance
                        Rectangle {
                            visible: index>0
                            x: 0
                            height: parent.height
                            width: 1
                            color: Colors.magenta
                            opacity: 0.6
                        }
                        Item {
                            id: dayGlyph
                            objectName: "weather-w15-original-daily-icon"
                            width: Math.max(20,Math.min(30,day.height))
                            height: width
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent
                                text: day.dayState.icon
                                font.pixelSize: Math.max(34,dayGlyph.width+5)
                                color: terminal.ink(day.entry)
                                visible: day.art==="weather"
                            }
                            WeatherCelestialGlyph {
                                anchors.centerIn: parent
                                width: parent.width
                                height: parent.height
                                scale: 1.15
                                mode: day.art
                                weatherKind: WeatherCyclePolicy.nightKind(day.dayState)
                                solar: day.cycle.solar
                                moonPhase: day.cycle.moonPhase
                                ink: terminal.ink(day.entry)
                                visible: day.art!=="weather"
                            }
                        }
                        Column {
                            anchors.left: dayGlyph.right
                            anchors.leftMargin: 3
                            anchors.right: parent.right
                            anchors.rightMargin: 2
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 0
                            GohuText {
                                id: dayTemperature
                                height: 12
                                text: terminal.dateLabel(day.entry.date)+"  "+
                                      terminal.read(day.entry.maxTempF,"°")
                                      +"/"+terminal.read(day.entry.minTempF,"°F")
                                font.pixelSize: 11
                                color: Colors.white
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            // W19 // Same percentage-to-length scale and ink
                            // as each hourly rain meter, now for daily peak chance.
                            Rectangle {
                                id: dayRainMeter
                                objectName: "weather-w19-daily-rain-meter"
                                width: Math.max(0,parent.width-6)
                                height: 6
                                anchors.horizontalCenter: parent.horizontalCenter
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                                Rectangle {
                                    x: 1
                                    y: 1
                                    height: Math.max(0,parent.height-2)
                                    width: Math.max(0,(parent.width-2)
                                          *terminal.fraction(day.entry.chanceRain))
                                    color: Colors.orange
                                }
                            }
                            GohuText {
                                id: dayChance
                                height: 9
                                text: terminal.rainChance(day.entry.chanceRain)
                                      +" PEAK RAIN CHANCE"
                                font.pixelSize: 9
                                color: Colors.cyan
                                width: parent.width
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
                GohuText {
                    visible: terminal.dailyRows.length===0
                    text: "DAILY FORECAST // WAITING FOR SOURCE"
                    color: Colors.orange
                    font.pixelSize: 11
                }
            }
        }

        Item {
            id: inspectStatus
            objectName: "weather-w14-forecast-inspector-footer"
            width: parent.width
            height: 12
            GohuText {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                font.pixelSize: 9
                color: Colors.yellow
                elide: Text.ElideRight
                text: terminal.sky && terminal.sky.inspectedHour
                    ? "SELECTED // "+terminal.dateLabel(terminal.sky.inspectedHour.date)
                      +" "+String(terminal.sky.inspectedHour.timeLabel||"")
                      +" // "+String(terminal.sky.inspectedHour.condition||"")
                      +" // "+ (terminal.sky.inspectedHourMetrics.length>0
                               ? terminal.sky.inspectedHourMetrics[0].title+" "+
                                 terminal.sky.inspectedHourMetrics[0].value : "")
                    : terminal.currentReady
                      ? "CURRENT OBSERVATION // LISTED TIMES & DAYS ARE FORECASTS"
                      : "OBSERVATION WAITING // FORECAST SOURCE INDEPENDENT"
            }
        }
    }
}
