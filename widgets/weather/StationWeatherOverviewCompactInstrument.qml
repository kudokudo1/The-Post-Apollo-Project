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

    height: 164
    color: Colors.dark
    border.width: 1
    border.color: Colors.cyan
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
            height: 52
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
                    font.pixelSize: 9
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
                    font.pixelSize: 25
                    color: Colors.orange
                    text: panel.currentReady ? panel.reading(panel.weatherService.tempF,"°F") : "--°F"
                }
                Item {
                    id: currentIcon
                    objectName: "weather-w17-original-main-glyph"
                    anchors.right: parent.right
                    anchors.rightMargin: 1
                    anchors.verticalCenter: parent.verticalCenter
                    width: 47
                    height: 47
                    GohuText {
                        anchors.centerIn: parent
                        text: panel.iconText(panel.currentState)
                        font.pixelSize: 49
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
                        GohuText {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            text: metric.modelData.label
                            color: metric.modelData.color
                            font.pixelSize: 8
                        }
                        Row {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.topMargin: 9
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
                                font.pixelSize: metric.modelData.key==="pressure" ? 9 : 11
                                color: Colors.white
                            }
                        }
                        Rectangle {
                            id: telemetryMeter
                            visible: metric.modelData.key!=="pressure"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 3
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
            height: 45
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
                    Item {
                        id: hourIcon
                        objectName: "weather-w17-original-hourly-glyph"
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 8
                        width: 19
                        height: 19
                        GohuText {
                            anchors.centerIn: parent
                            text: panel.iconText(hour.state)
                            font.pixelSize: 22
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
                        y: 27
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: panel.reading(hour.entry.tempF,"°F")
                        font.pixelSize: 11
                        color: Colors.white
                    }
                    GohuText {
                        y: 36
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: panel.percent(hour.entry.chanceRain)
                        font.pixelSize: 7
                        color: Colors.cyan
                    }
                    Rectangle {
                        id: hourMeter
                        objectName: "weather-w17-hourly-rain-meter"
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 3
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
            height: 24
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
                        width: 20
                        height: 20
                        GohuText {
                            anchors.centerIn: parent
                            text: panel.iconText(day.state)
                            font.pixelSize: 22
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
                        anchors.leftMargin: 27
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 0
                        GohuText {
                            width: parent.width
                            text: panel.date(day.entry.date)+"  "+
                                  panel.reading(day.entry.maxTempF,"°")+"/"+
                                  panel.reading(day.entry.minTempF,"°F")
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
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
