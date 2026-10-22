import QtQuick
import "../../components"
import "StationHomePolicy.js" as StationHomePolicy

Rectangle {
    id: home

    property var weatherService: null
    property var spaceService: null

    readonly property bool weatherReady:
        weatherService && weatherService.ready
    readonly property bool aqiReady:
        weatherService && weatherService.aqiReady
    readonly property bool spaceReady:
        spaceService && spaceService.ready

    readonly property real temperatureValue:
        weatherReady ? Number(weatherService.tempF) : 0
    readonly property real humidityValue:
        weatherReady ? Number(weatherService.humidity) : 0
    readonly property real windValue:
        weatherReady ? Number(weatherService.windMph) : 0
    readonly property real aqiValue:
        aqiReady ? Number(weatherService.aqi) : 0
    readonly property real uvValue:
        weatherReady ? Number(weatherService.uvIndex) : -1
    readonly property real kpValue:
        spaceService && spaceService.kpReady
        ? Number(spaceService.kp) : 0

    readonly property var nextForecast:
        weatherService
        && Array.isArray(weatherService.hourlyForecast)
        && weatherService.hourlyForecast.length > 0
        ? weatherService.hourlyForecast[0]
        : null

    readonly property real nextRainChance:
        nextForecast && Number(nextForecast.chanceRain) >= 0
        ? Number(nextForecast.chanceRain) : 0

    readonly property var watchItem: StationHomePolicy.chooseRelevant({
        "weatherReady": weatherReady,
        "aqiReady": aqiReady,
        "spaceReady": spaceReady,
        "aqi": weatherService ? weatherService.aqi : -1,
        "aqiLabel": weatherService ? weatherService.aqiLabel : "",
        "uvIndex": weatherService ? weatherService.uvIndex : -1,
        "hourlyForecast":
            weatherService ? weatherService.hourlyForecast : [],
        "kp": spaceService ? spaceService.kp : -1,
        "kpLabel": spaceService ? spaceService.kpLabel : "",
        "solarWindSpeed":
            spaceService ? spaceService.solarWindSpeed : -1,
        "bz":
            spaceService && spaceService.magneticFieldReady
            ? spaceService.magneticFieldBz : 999,
        "spaceError": spaceService ? spaceService.errorText : ""
    })

    function clamp01(value) {
        const number = Number(value);
        if (!isFinite(number))
            return 0;
        return Math.max(0, Math.min(1, number));
    }

    function uvLabel(value) {
        const number = Number(value);
        if (!isFinite(number) || number < 0)
            return "UNKNOWN";
        if (number >= 8)
            return "VERY HIGH";
        if (number >= 6)
            return "HIGH";
        if (number >= 3)
            return "MODERATE";
        return "LOW";
    }

    function sourceAccent(source) {
        const key = String(source || "");
        if (key === "ground")
            return Colors.green;
        if (key === "space")
            return Colors.magenta;
        if (key === "sky")
            return Colors.cyan;
        return Colors.orange;
    }

    function sourceMeterFill(source) {
        const key = String(source || "");
        if (key === "ground")
            return Colors.green;
        if (key === "space")
            return Colors.magenta;
        return Colors.orange;
    }

    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14

        Row {
            width: parent.width
            height: 28

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: "⌂  HOME"
                font.pixelSize: 24
                color: Colors.magenta
            }

            Item {
                width: parent.width - 255
                height: 1
            }

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: "AUTO SNAPSHOT"
                font.pixelSize: 12
                color: Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SNAPSHOT // NOW"
        }

        Row {
            width: parent.width
            height: 118
            spacing: 12

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "CURRENT WEATHER"
                valueText:
                    home.weatherReady
                    ? weatherService.tempF + "°F" : "--°F"
                detailText:
                    home.weatherReady
                    ? String(weatherService.condition || "UNKNOWN").toUpperCase()
                    : "WEATHER OFFLINE"
                footerText:
                    home.weatherReady
                    ? "FEELS " + weatherService.feelsLikeF + "°F"
                    : "WAITING FOR SOURCE"
                accentColor: Colors.cyan
                valueColor: Colors.orange
                meterVisible: home.weatherReady
                meterValue: home.clamp01(home.temperatureValue / 120)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "NEXT HOURS"
                valueText:
                    home.nextForecast
                    && Number(home.nextForecast.tempF) > -900
                    ? Math.round(Number(home.nextForecast.tempF)) + "°F"
                    : "--°F"
                detailText:
                    home.nextForecast
                    ? String(home.nextForecast.timeLabel || "--")
                      + " // "
                      + String(
                          home.nextForecast.condition || "FORECAST"
                        ).toUpperCase()
                    : "FORECAST UNAVAILABLE"
                footerText:
                    home.nextForecast
                    ? "RAIN "
                      + Math.round(home.nextRainChance)
                      + "%"
                    : "RAIN --"
                accentColor: Colors.cyan
                valueColor: Colors.orange
                meterVisible: home.nextForecast !== null
                meterValue: home.clamp01(home.nextRainChance / 100)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 24) / 3
                height: parent.height

                title: "AIR QUALITY"
                valueText:
                    home.aqiReady
                    ? "AQI " + weatherService.aqi : "AQI --"
                detailText:
                    home.aqiReady
                    ? String(weatherService.aqiLabel || "UNKNOWN").toUpperCase()
                    : "AIR QUALITY OFFLINE"
                footerText:
                    home.aqiReady && Number(weatherService.pm25) >= 0
                    ? "PM2.5 "
                      + Number(weatherService.pm25).toFixed(1)
                      + " µg/m³"
                    : "PM2.5 --"
                accentColor: Colors.green
                valueColor: Colors.white
                meterVisible: home.aqiReady
                meterValue: home.clamp01(home.aqiValue / 500)
                meterFillColor: Colors.green
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "QUICK // CONDITIONS"
        }

        Row {
            width: parent.width
            height: 106
            spacing: 12

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "HUMIDITY"
                valueText:
                    home.weatherReady
                    ? weatherService.humidity + "%" : "--%"
                detailText: "SKY"
                accentColor: Colors.cyan
                meterVisible: home.weatherReady
                meterValue: home.clamp01(home.humidityValue / 100)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "WIND"
                valueText:
                    home.weatherReady
                    ? weatherService.windMph + " MPH"
                    : "-- MPH"
                detailText:
                    home.weatherReady
                    ? String(weatherService.windDirection || "--")
                    : "SKY"
                accentColor: Colors.cyan
                meterVisible: home.weatherReady
                meterValue: home.clamp01(home.windValue / 50)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "UV INDEX"
                valueText:
                    home.uvValue >= 0
                    ? String(Math.round(home.uvValue)) : "--"
                detailText: home.uvLabel(home.uvValue)
                accentColor: Colors.cyan
                meterVisible: home.uvValue >= 0
                meterValue: home.clamp01(home.uvValue / 11)
                meterFillColor: Colors.orange
            }

            StationHomeMetricCard {
                width: (parent.width - 36) / 4
                height: parent.height

                title: "SPACE WEATHER"
                valueText:
                    spaceService && spaceService.kpReady
                    ? "KP " + spaceService.kpText : "KP --"
                detailText:
                    spaceService && spaceService.kpReady
                    ? spaceService.kpLabel : "SPACE FEED PARTIAL"
                accentColor: Colors.magenta
                meterVisible:
                    spaceService && spaceService.kpReady
                meterValue: home.clamp01(home.kpValue / 9)
                meterFillColor: Colors.magenta
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "AUTO // RELEVANT"
        }

        StationHomeMetricCard {
            width: parent.width
            height: 118

            title: home.watchItem.title
            valueText: home.watchItem.value
            detailText: home.watchItem.detail
            footerText:
                home.watchItem.rank > 0
                ? "AUTO PROMOTED // "
                  + String(home.watchItem.source).toUpperCase()
                : "AUTO WATCH // NO HIGHER PRIORITY CONDITION"
            accentColor: home.sourceAccent(home.watchItem.source)
            valueColor:
                home.watchItem.rank >= 85
                ? Colors.red
                : home.watchItem.rank >= 65
                  ? Colors.orange
                  : home.watchItem.rank >= 45
                    ? Colors.yellow
                    : Colors.white
            meterVisible: home.watchItem.meterValue > 0
            meterValue: home.watchItem.meterValue
            meterFillColor:
                home.sourceMeterFill(home.watchItem.source)
        }
    }
}
