import QtQuick
import "../../components"
import "../../services/weather/WeatherDockPolicy.js" as WeatherDockPolicy
import "../../services/weather/WeatherCyclePolicy.js" as WeatherCyclePolicy

// W17 // Compact WEATHER instrument, not a second source or another icon family.
// Reuses the same icon classifiers, celestial geometry, source samples and
// rain probabilities as StationSky / StationWeatherInstrumentTerminal.
// Its three bands mirror the full WEATHER menu at OVERVIEW's 164px height.
Rectangle {
    id: panel
    objectName: "weather-w17-overview-mirror"
    property var weatherService: null
    property real runtimeNowMs: Date.now()
    readonly property bool currentReady: Boolean(weatherService && weatherService.ready)
    readonly property bool airReady: Boolean(weatherService && weatherService.aqiReady)
    readonly property var hourlySamples: weatherService && weatherService.forecastReady
        && weatherService.hourlyForecast ? weatherService.hourlyForecast : []
    readonly property var dailySamples: weatherService && weatherService.forecastReady
        && weatherService.dailyForecast ? weatherService.dailyForecast : []
    readonly property var observationCycle: WeatherCyclePolicy.atObservation(
        runtimeNowMs,
        weatherService ? weatherService.localObservationDateTime : "",
        weatherService ? weatherService.localObservationAnchorMs : 0,
        dailySamples)
    readonly property var currentState: currentReady
        ? conditionState(weatherService.condition, weatherService.weatherCode, true)
        : {icon:"?",color:"white",label:"WAITING"}
    readonly property string currentArt: currentReady
        ? WeatherCyclePolicy.artworkFor(currentState,observationCycle) : "weather"
    readonly property alias mainGlyph: currentIcon
    readonly property alias currentMeters: metricsRepeater
    readonly property alias hourRepeater: hourRepeater
    readonly property alias dayRepeater: dayRepeater
    readonly property alias hourlyStrip: hourStrip
    readonly property alias dailyStrip: dayStrip

    function reading(value, suffix) {
        if(value===null || value===undefined || String(value).trim()==="")
            return "--";
        const n=Number(value);
        return isFinite(n) && n>-900 && n<100000 ? Math.round(n)+(suffix||"") : "--";
    }
    function percent(value) {
        const n=Number(value);
        return value!==null && value!==undefined && String(value).trim()!==""
               && isFinite(n) && n>=0 && n<=100 ? Math.round(n)+"%" : "--";
    }
    function ratio(value, upper) {
        const n=Number(value);
        return value!==null && value!==undefined && String(value).trim()!==""
               && isFinite(n) ? Math.max(0,Math.min(1,n/upper)) : 0;
    }
    function date(value) {
        const t=String(value||"");
        return /^\d{4}-\d{2}-\d{2}$/.test(t) ? t.slice(5).replace("-","/") : "--/--";
    }
    function conditionState(condition, weatherCode, current) {
        // The exact pre-W14 classification used by StationSky.
        const now=runtimeNowMs;
        return WeatherDockPolicy.classify({
            ready:true,errorText:"",weatherTimeMs:now,nowMs:now,
            weatherCode:weatherCode || "",condition:condition || "",
            windMph:current && currentReady ? weatherService.windMph : 0,
            uvIndex:current && currentReady ? weatherService.uvIndex : -1,
            aqiReady:Boolean(current && airReady),aqiErrorText:"",
            aqiTimeMs:now,aqi:current && airReady ? weatherService.aqi : -1
        });
    }
    function ink(name) {
        switch(name) {
        case "red": return Colors.red;
        case "orange": return Colors.orange;
        case "yellow": return Colors.yellow;
        case "green": return Colors.green;
        case "omnitrix": return Colors.omnitrix;
        case "cyan": return Colors.cyan;
        case "blue": return Colors.blue;
        case "magenta": return Colors.magenta;
        default: return Colors.white;
        }
    }
    function iconText(state) {
        // OVERVIEW's previously approved text-presentation lightning variant.
        return String(state.label||"").indexOf("THUNDERSTORM")>=0
            ? "⚡︎" : (state.icon || "?");
    }
    function windAngle(direction) {
        const dirs=["N","NNE","NE","ENE","E","ESE","SE","SSE",
                    "S","SSW","SW","WSW","W","WNW","NW","NNW"];
        const at=dirs.indexOf(String(direction||"").toUpperCase());
        return at<0 ? 0 : at*22.5;
    }
    readonly property var telemetry: [
        {key:"aqi",label:"AIR QUALITY",color:Colors.magenta,
         value:airReady ? reading(weatherService.aqi,"") : "--",
         valid:airReady, fraction:airReady ? ratio(weatherService.aqi,500) : 0},
        {key:"humidity",label:"HUMIDITY",color:Colors.cyan,
         value:currentReady ? reading(weatherService.humidity,"%") : "--",
         valid:currentReady,
         fraction:currentReady ? ratio(weatherService.humidity,100) : 0},
        {key:"wind",label:"WIND // MPH",color:Colors.yellow,
         value:currentReady ? reading(weatherService.windMph,"")+" "+
                   String(weatherService.windDirection||"") : "--",
         valid:currentReady,
         fraction:currentReady ? ratio(weatherService.windMph,50) : 0},
        {key:"pressure",label:"PRESSURE",color:Colors.blue,
         value:currentReady ? reading(weatherService.pressureHpa," hPa") : "--",
         valid:currentReady, fraction:0}
    ]

    // W18 // Expand the three original WEATHER bands into reclaimed space.
    // At compact 164px the original artwork/positions remain unchanged.
    readonly property real expansion: Math.max(0, height - 164)
    height: 164
    color: Colors.dark
    // Parent StationWeatherTerminalSummary already draws the outer frame.
    border.width: 0
    clip: true

    Column {
        anchors.fill: parent
        anchors.margins: 3
        spacing: 1

        Item {
            width: parent.width
            height: 12
            GohuText {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "WEATHER // NOW + FORECAST"
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: panel.currentReady ? "OBSERVED // ONLINE" : "OBSERVATION // WAITING"
                font.pixelSize: 8
                color: panel.currentReady ? Colors.omnitrix : Colors.orange
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Colors.cyan
            }
        }

        Item {
            id: nowBand
            objectName: "weather-w17-current-instrument"
            width: parent.width
            height: 52 + panel.expansion * 0.50
            Rectangle {
                width: 3
                height: parent.height-2
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.orange
            }
            Item {
                id: mainReadout
                x: 5
                width: parent.width*0.44-6
                height: parent.height
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 1
                    width: parent.width
                    font.pixelSize: Math.min(12,9 + panel.expansion * 0.018)
                    color: Colors.orange
                    text: "NOW // "+(panel.currentReady
                       ? String(panel.weatherService.condition||"UNKNOWN").toUpperCase()
                       : "WAITING")
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    font.pixelSize: Math.min(41,25 + panel.expansion * 0.10)
                    color: Colors.orange
                    text: panel.currentReady ? panel.reading(panel.weatherService.tempF,"°F") : "--°F"
                }
                Item {
                    id: currentIcon
                    objectName: "weather-w17-original-main-glyph"
                    anchors.right: parent.right
                    anchors.rightMargin: 1
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(108,47 + panel.expansion * 0.34,
                                    Math.max(47,parent.width * 0.49))
                    height: width
                    GohuText {
                        anchors.centerIn: parent
                        text: panel.iconText(panel.currentState)
                        font.pixelSize: Math.min(114,currentIcon.width + 6)
                        color: panel.ink(panel.currentState.color)
                        visible: panel.currentArt==="weather"
                    }
                    WeatherCelestialGlyph {
                        anchors.centerIn: parent
                        width: parent.width
                        height: parent.height
                        mode: panel.currentArt
                        solar: panel.observationCycle.solar
                        moonPhase: panel.observationCycle.moonPhase
                        weatherKind: WeatherCyclePolicy.nightKind(panel.currentState)
                        ink: panel.ink(panel.currentState.color)
                        visible: panel.currentArt!=="weather"
                    }
                }
                GohuText {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 1
                    width: parent.width
                    text: panel.currentReady
                        ? "FEELS "+panel.reading(panel.weatherService.feelsLikeF,"°F")
                        : "FEELS --"
                    font.pixelSize: 9
                    color: Colors.yellow
                }
            }
            Rectangle {
                x: parent.width*0.44
                width: 1
                y: 3
                height: parent.height-6
                color: Colors.cyan
                opacity: 0.65
            }
            Grid {
                id: telemetryGrid
                x: parent.width*0.44+5
                width: parent.width*0.56-7
                height: parent.height
                columns: 2
                rowSpacing: 2
                columnSpacing: 5
                Repeater {
                    id: metricsRepeater
                    model: panel.telemetry
                    delegate: Item {
                        id: metric
                        required property var modelData
                        width: Math.max(1,(telemetryGrid.width-telemetryGrid.columnSpacing)/2)
                        height: (telemetryGrid.height-telemetryGrid.rowSpacing)/2
                        readonly property alias meter: telemetryMeter
                        readonly property alias readoutRow: metricReadoutRow
                        GohuText {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            text: metric.modelData.label
                            color: metric.modelData.color
                            font.pixelSize: 8
                        }
                        Row {
                            id: metricReadoutRow
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.topMargin: (metric.modelData.key==="pressure" ? 7 : 9)
                                               + Math.min(24,panel.expansion * 0.10)
                            spacing: 1
                            GohuText {
                                visible: metric.modelData.key==="wind"
                                text: "↑"
                                font.pixelSize: 11
                                width: visible ? 10 : 0
                                color: Colors.yellow
                                rotation: panel.currentReady
                                   ? panel.windAngle(panel.weatherService.windDirection) : 0
                            }
                            GohuText {
                                text: metric.modelData.value
                                font.pixelSize: (metric.modelData.key==="pressure" ? 8 : 11)
                                                + Math.min(3,panel.expansion * 0.02)
                                color: Colors.white
                            }
                        }
                        Rectangle {
                            id: telemetryMeter
                            visible: metric.modelData.key!=="pressure"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            // W19 // Center bars between values and the cell
                            // edge, rather than using them as bottom dividers.
                            y: metric.height < 35 ? metric.height - height
                               : Math.min(metric.height-height-2,
                                  metricReadoutRow.y + metricReadoutRow.height
                                  +Math.max(2,(metric.height
                                     -metricReadoutRow.y-metricReadoutRow.height
                                     -height)/2))
                            height: visible ? (metric.height < 35 ? 4 : 6) : 0
                            color: Colors.black
                            border.width: 1
                            border.color: metric.modelData.color
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: Math.max(0,(parent.width-2)*
                                             (metric.modelData.valid ? metric.modelData.fraction : 0))
                                color: metric.modelData.color
                            }
                        }
                        GohuText {
                            visible: metric.modelData.key==="pressure"
                            anchors.bottom: parent.bottom
                            text: panel.currentReady
                                ? "VIS "+panel.reading(panel.weatherService.visibilityMiles," MI")
                                : "VIS --"
                            font.pixelSize: 7
                            color: Colors.cyan
                        }
                    }
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Colors.orange
                opacity: 0.75
            }
        }

        Item {
            width: parent.width
            height: 10
            GohuText {
                anchors.left: parent.left
                text: "NEXT 6 FORECAST TIMES"
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                anchors.right: parent.right
                text: "RAIN CHANCE // EACH PERIOD"
                font.pixelSize: 8
                color: Colors.cyan
            }
        }

        Row {
            id: hourStrip
            objectName: "weather-w17-six-hour-timeline"
            width: parent.width
            height: 45 + panel.expansion * 0.33
            spacing: 1
            Repeater {
                id: hourRepeater
                model: Math.min(6,panel.hourlySamples.length)
                delegate: Item {
                    id: hour
                    required property int index
                    readonly property var entry: panel.hourlySamples[index] || ({})
                    readonly property var state: panel.conditionState(entry.condition,entry.weatherCode,false)
                    readonly property var cycle: WeatherCyclePolicy.forecast(
                        entry.date,entry.time,panel.dailySamples)
                    readonly property string art: WeatherCyclePolicy.artworkFor(state,cycle)
                    width: (hourStrip.width-5)/6
                    height: hourStrip.height
                    readonly property alias rainMeter: hourMeter
                    readonly property alias temperatureItem: hourTemperature
                    readonly property alias chanceItem: hourChance
                    Rectangle {
                        visible: index>0
                        x: 0
                        y: 3
                        width: 1
                        height: parent.height-5
                        color: Colors.cyan
                        opacity: 0.45
                    }
                    GohuText {
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: panel.date(hour.entry.date)+" "+String(hour.entry.timeLabel||"--")
                        font.pixelSize: 7
                        color: Colors.yellow
                    }
                    // W19 // Icon, temperature, meter, chance form one
                    // centered reading. The meter cannot look like a divider.
                    Column {
                        id: hourReadingStack
                        objectName: "weather-w19-hourly-reading-stack"
                        width: parent.width
                        y: Math.max(8,8 + (hour.height-8-implicitHeight)/2)
                        spacing: hour.height>65 ? 2 : 0
                        Item {
                            id: hourIcon
                            objectName: "weather-w17-original-hourly-glyph"
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: Math.min(50,13 + Math.max(0,hour.height-45)*0.55)
                            height: width
                            GohuText {
                                anchors.centerIn: parent
                                text: panel.iconText(hour.state)
                                font.pixelSize: Math.min(54,hourIcon.width + 5)
                                color: panel.ink(hour.state.color)
                                visible: hour.art==="weather"
                            }
                            WeatherCelestialGlyph {
                                anchors.centerIn: parent
                                width: parent.width
                                height: parent.height
                                mode: hour.art
                                solar: hour.cycle.solar
                                moonPhase: hour.cycle.moonPhase
                                weatherKind: WeatherCyclePolicy.nightKind(hour.state)
                                ink: panel.ink(hour.state.color)
                                visible: hour.art!=="weather"
                            }
                        }
                        GohuText {
                            id: hourTemperature
                            width: parent.width
                            height: hour.height>65 ? 13 : 10
                            horizontalAlignment: Text.AlignHCenter
                            text: panel.reading(hour.entry.tempF,"°F")
                            font.pixelSize: hour.height>65 ? 11 : 9
                            color: Colors.white
                        }
                        Rectangle {
                            id: hourMeter
                            objectName: "weather-w17-hourly-rain-meter"
                            width: Math.max(0,parent.width-6)
                            height: hour.height>65 ? 6 : 5
                            anchors.horizontalCenter: parent.horizontalCenter
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: Math.max(0,(parent.width-2)*
                                      panel.ratio(hour.entry.chanceRain,100))
                                color: Colors.orange
                            }
                        }
                        GohuText {
                            id: hourChance
                            width: parent.width
                            height: hour.height>65 ? 10 : 8
                            horizontalAlignment: Text.AlignHCenter
                            text: panel.percent(hour.entry.chanceRain)
                            font.pixelSize: hour.height>65 ? 8 : 7
                            color: Colors.cyan
                        }
                    }
                }
            }
            GohuText {
                visible: panel.hourlySamples.length===0
                text: "HOURLY // WAITING FOR SOURCE"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        Item {
            width: parent.width
            height: 10
            GohuText {
                anchors.left: parent.left
                text: "THREE-DAY OUTLOOK"
                font.pixelSize: 9
                color: Colors.magenta
            }
            GohuText {
                anchors.right: parent.right
                text: "PEAK RAIN CHANCE"
                font.pixelSize: 8
                color: Colors.cyan
            }
        }

        Row {
            id: dayStrip
            objectName: "weather-w17-three-day-strip"
            width: parent.width
            height: 24 + panel.expansion * 0.17
            spacing: 3
            Repeater {
                id: dayRepeater
                model: Math.min(3,panel.dailySamples.length)
                delegate: Item {
                    id: day
                    required property int index
                    readonly property var entry: panel.dailySamples[index] || ({})
                    readonly property var state: panel.conditionState(entry.condition,entry.weatherCode,false)
                    readonly property var cycle: WeatherCyclePolicy.atLocal(
                        entry.date,720,panel.dailySamples)
                    readonly property string art: WeatherCyclePolicy.artworkFor(state,cycle)
                    width: (dayStrip.width-6)/3
                    height: dayStrip.height
                    readonly property alias rainMeter: dayRainMeter
                    readonly property alias temperatureItem: dayTemperature
                    readonly property alias chanceItem: dayChance
                    Rectangle {
                        visible: index>0
                        width: 1
                        height: parent.height
                        color: Colors.magenta
                        opacity: 0.55
                    }
                    Item {
                        anchors.left: parent.left
                        anchors.leftMargin: 3
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(50,20 + (dayStrip.height - 24) * 0.83)
                        height: width
                        GohuText {
                            anchors.centerIn: parent
                            text: panel.iconText(day.state)
                            font.pixelSize: Math.min(54,22 + panel.expansion * 0.17)
                            color: panel.ink(day.state.color)
                            visible: day.art==="weather"
                        }
                        WeatherCelestialGlyph {
                            anchors.fill: parent
                            mode: day.art
                            solar: day.cycle.solar
                            moonPhase: day.cycle.moonPhase
                            weatherKind: WeatherCyclePolicy.nightKind(day.state)
                            ink: panel.ink(day.state.color)
                            visible: day.art!=="weather"
                        }
                    }
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 27 + Math.min(28,panel.expansion * 0.17)
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 0
                        GohuText {
                            id: dayTemperature
                            width: parent.width
                            height: dayStrip.height>36 ? 13 : 10
                            text: panel.date(day.entry.date)+"  "+
                                  panel.reading(day.entry.maxTempF,"°")+"/"+
                                  panel.reading(day.entry.minTempF,"°F")
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        // W19 // A daily peak uses the same orange-on-cyan
                        // probability bar as the six hourly periods.
                        Rectangle {
                            id: dayRainMeter
                            objectName: "weather-w19-daily-rain-meter"
                            width: Math.max(0,parent.width-6)
                            height: dayStrip.height>36 ? 6 : 5
                            anchors.horizontalCenter: parent.horizontalCenter
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                x: 1
                                y: 1
                                height: Math.max(0,parent.height-2)
                                width: Math.max(0,(parent.width-2)*
                                      panel.ratio(day.entry.chanceRain,100))
                                color: Colors.orange
                            }
                        }
                        GohuText {
                            id: dayChance
                            width: parent.width
                            height: dayStrip.height>36 ? 10 : 8
                            text: panel.percent(day.entry.chanceRain)+" PEAK RAIN"
                            font.pixelSize: 7
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }
            GohuText {
                visible: panel.dailySamples.length===0
                text: "DAILY // WAITING FOR SOURCE"
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }
}
