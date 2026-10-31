import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "../../services/weather/SeismicPolicy.js" as SeismicPolicy
import "../../services/weather/NwpsRiverPolicy.js" as RiverPolicy
import "../../services/weather/NdbcMarinePolicy.js" as MarinePolicy
import "../../services/weather/CoopsCoastalPolicy.js" as CoastalPolicy
import "StationGroundPollenPolicy.js" as PollenDetails
import "StationGroundEnvironmentPolicy.js" as EnvironmentPolicy

Rectangle {
    id: ground

    property var weatherService: null
    property var nwsAlertSource: null

    readonly property bool nwsConfigured:
        nwsAlertSource && nwsAlertSource.configured
    readonly property bool nwsReady:
        nwsAlertSource && nwsAlertSource.ready
    readonly property bool nwsLoading:
        nwsAlertSource && nwsAlertSource.loading
    readonly property string nwsErrorText:
        nwsAlertSource ? String(nwsAlertSource.errorText || "") : ""
    readonly property var officialAlerts:
        nwsAlertSource && Array.isArray(nwsAlertSource.alertList)
        ? nwsAlertSource.alertList : []

    // View-scoped service: no USGS polling while GROUND is unmounted.
    WeatherServices.SeismicService {
        id: quakeService
        active: ground.visible
    }

    WeatherServices.NwpsRiverService {
        id: riverService
        active: ground.visible
        latitude: weatherService ? weatherService.latitude : ""
        longitude: weatherService ? weatherService.longitude : ""
    }

    WeatherServices.NdbcMarineService {
        id: marineService
        active: ground.visible
        latitude: weatherService ? weatherService.latitude : ""
        longitude: weatherService ? weatherService.longitude : ""
    }

    WeatherServices.CoopsCoastalService {
        id: coastalService
        active: ground.visible
        latitude: weatherService ? weatherService.latitude : ""
        longitude: weatherService ? weatherService.longitude : ""
    }

    function distanceLabel(latitude, longitude) {
        const km = SeismicPolicy.distanceKm(
            weatherService ? weatherService.latitude : "",
            weatherService ? weatherService.longitude : "",
            latitude, longitude
        );
        return km >= 0 ? Math.round(km) + " KM FROM FIX" : "DISTANCE --";
    }

    function riverCategoryColor(category) {
        const id = category ? String(category.id || "") : "";
        switch (id) {
        case "major": return Colors.red;
        case "moderate": return Colors.orange;
        case "minor": return Colors.yellow;
        case "action": return Colors.cyan;
        case "none": return Colors.green;
        default: return Colors.white;
        }
    }

    function riverTrendColor(direction) {
        switch (String(direction || "")) {
        case "RISING": return Colors.orange;
        case "FALLING": return Colors.cyan;
        case "STEADY": return Colors.green;
        default: return Colors.white;
        }
    }

    function heatBandColor(id) {
        switch (String(id || "")) {
        case "caution": return Colors.yellow;
        case "extreme-caution": return Colors.orange;
        case "danger": return Colors.red;
        case "extreme-danger": return Colors.magenta;
        case "below": return Colors.cyan;
        default: return Colors.white;
        }
    }

    function marineSampleAge() {
        if (!marineService.station)
            return "--";
        const millis = Number(marineService.station.sampleMillis);
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const age = Math.max(0, Math.floor((Date.now() - millis) / 60000));
        return age < 60 ? age + "m"
            : Math.floor(age / 60) + "h " + (age % 60) + "m";
    }

    function marineTempLabel(value) {
        const celsius = Number(value);
        if (!isFinite(celsius))
            return "--";
        const fahrenheit = MarinePolicy.celsiusToF(celsius);
        return celsius.toFixed(1) + "°C // "
            + fahrenheit.toFixed(1) + "°F";
    }

    function marineWindLabel(value) {
        const speed = Number(value);
        if (!isFinite(speed))
            return "--";
        const mph = MarinePolicy.metersPerSecondToMph(speed);
        return speed.toFixed(1) + " m/s // "
            + mph.toFixed(1) + " mph";
    }

    function marineWaveLabel(value) {
        const meters = Number(value);
        if (!isFinite(meters))
            return "--";
        const feet = MarinePolicy.metersToFeet(meters);
        return meters.toFixed(1) + " m // "
            + feet.toFixed(1) + " ft";
    }

    function coastalSampleAge() {
        if (!coastalService.waterLevel)
            return "--";
        const millis = Number(coastalService.waterLevel.sampleMillis);
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const age = Math.max(0, Math.floor((Date.now() - millis) / 60000));
        return age < 60 ? age + "m"
            : Math.floor(age / 60) + "h " + (age % 60) + "m";
    }

    function coastalPredictionColor(high) {
        if (high === true)
            return Colors.orange;
        if (high === false)
            return Colors.cyan;
        return Colors.white;
    }

    function riverReceiveAge() {
        if (!riverService.lastUpdated
                || typeof riverService.lastUpdated.getTime !== "function")
            return "--";
        const millis = riverService.lastUpdated.getTime();
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const age = Math.max(
            0,
            Math.floor((Date.now() - millis) / 60000)
        );
        return age === 0 ? "<1m" : age + "m";
    }

    function stageflowReceiveAge() {
        if (!riverService.stageflowLastUpdated
                || typeof riverService.stageflowLastUpdated.getTime
                   !== "function")
            return "--";
        const millis = riverService.stageflowLastUpdated.getTime();
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const age = Math.max(
            0,
            Math.floor((Date.now() - millis) / 60000)
        );
        return age === 0 ? "<1m" : age + "m";
    }

    readonly property var observedStageflowRows:
        riverService.stageflowReady
        ? RiverPolicy.seriesTail(
              riverService.stageflow.observed, 3
          ) : []
    readonly property var forecastStageflowRows:
        riverService.stageflowReady
        ? RiverPolicy.seriesHead(
              riverService.stageflow.forecast, 4
          ) : []

    readonly property var observedHydrographRows:
        riverService.stageflowReady
        ? RiverPolicy.seriesWindow(
              riverService.stageflow.observed, 12
          ) : []
    readonly property var observedHydrographStats:
        riverService.stageflowReady
        ? RiverPolicy.seriesStats(
              riverService.stageflow.observed, 12
          )
        : RiverPolicy.seriesStats(null, 12)
    readonly property var observedHydrographBars:
        riverService.stageflowReady
        ? RiverPolicy.normalizedSeriesBars(
              riverService.stageflow.observed, 12
          ) : []

    readonly property var heatIndexSummary:
        EnvironmentPolicy.heatIndex(
            weatherService ? weatherService.tempF : "",
            weatherService ? weatherService.humidity : ""
        )
    readonly property var fireWeatherAlertRows:
        EnvironmentPolicy.fireWeatherAlerts(officialAlerts)

    readonly property bool aqiReady: weatherService && weatherService.aqiReady
    readonly property bool aqiLoading: weatherService && weatherService.aqiLoading
    readonly property var airQualityForecast:
        weatherService ? weatherService.airQualityForecast : []
    readonly property bool airQualityForecastReady:
        weatherService && weatherService.airQualityForecastReady
    readonly property real aqiValue: aqiReady ? Number(weatherService.aqi) : 0
    readonly property real pm25Value:
        aqiReady ? Number(weatherService.pm25) : 0
    readonly property real pm10Value:
        aqiReady ? Number(weatherService.pm10) : 0

    readonly property real ozoneValue:
        weatherService ? Number(weatherService.ozone) : -1
    readonly property real nitrogenDioxideValue:
        weatherService ? Number(weatherService.nitrogenDioxide) : -1
    readonly property real carbonMonoxideValue:
        weatherService ? Number(weatherService.carbonMonoxide) : -1
    readonly property real dustValue:
        weatherService ? Number(weatherService.dust) : -1

    readonly property real ozoneAqiValue:
        weatherService ? Number(weatherService.ozoneAqi) : -1
    readonly property real nitrogenDioxideAqiValue:
        weatherService ? Number(weatherService.nitrogenDioxideAqi) : -1
    readonly property real carbonMonoxideAqiValue:
        weatherService ? Number(weatherService.carbonMonoxideAqi) : -1

    readonly property var pollenSpecies: PollenDetails.species(
        !!(aqiReady && weatherService.pollenAvailable), {
            alderPollen: weatherService ? weatherService.alderPollen : -1,
            birchPollen: weatherService ? weatherService.birchPollen : -1,
            grassPollen: weatherService ? weatherService.grassPollen : -1,
            mugwortPollen: weatherService ? weatherService.mugwortPollen : -1,
            olivePollen: weatherService ? weatherService.olivePollen : -1,
            ragweedPollen: weatherService ? weatherService.ragweedPollen : -1
        }
    )

    readonly property var pollenPeak: {
        if (!weatherService || !weatherService.pollenAvailable)
            return { "name": "UNAVAILABLE", "value": -1 };

        const entries = [
            ["ALDER", Number(weatherService.alderPollen)],
            ["BIRCH", Number(weatherService.birchPollen)],
            ["GRASS", Number(weatherService.grassPollen)],
            ["MUGWORT", Number(weatherService.mugwortPollen)],
            ["OLIVE", Number(weatherService.olivePollen)],
            ["RAGWEED", Number(weatherService.ragweedPollen)]
        ];

        let best = { "name": "UNAVAILABLE", "value": -1 };
        for (let i = 0; i < entries.length; i++) {
            if (isFinite(entries[i][1]) && entries[i][1] >= 0
                    && entries[i][1] > best.value) {
                best = { "name": entries[i][0], "value": entries[i][1] };
            }
        }
        return best;
    }

    function concentrationText(value, suffix) {
        return isFinite(value) && value >= 0
               ? value.toFixed(1) + suffix
               : "--";
    }

    function alertSeverityColor(value) {
        switch (String(value || "").toLowerCase()) {
        case "extreme": return Colors.red;
        case "severe": return Colors.orange;
        case "moderate": return Colors.yellow;
        case "minor": return Colors.cyan;
        default: return Colors.white;
        }
    }

    function alertTimeUtc(value) {
        const raw = String(value || "");
        const millis = Date.parse(raw);
        if (!isFinite(millis))
            return "--";
        const iso = new Date(millis).toISOString();
        return iso.slice(0, 10) + " " + iso.slice(11, 16) + "Z";
    }

    function nwsReceiveAge() {
        if (!nwsAlertSource || !nwsAlertSource.lastUpdated
                || typeof nwsAlertSource.lastUpdated.getTime !== "function")
            return "--";
        const millis = nwsAlertSource.lastUpdated.getTime();
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const age = Math.max(0, Math.floor((Date.now() - millis) / 60000));
        return age === 0 ? "<1m" : age + "m";
    }

    // These are normalized views of real telemetry, preserved from the
    // original combined HOME implementation.
    readonly property real aqiMeter:
        Math.max(0, Math.min(1, aqiValue / 500))
    readonly property real pm25Meter:
        Math.max(0, Math.min(1, pm25Value / 100))
    readonly property real pm10Meter:
        Math.max(0, Math.min(1, pm10Value / 150))

    // Gas bars use Open-Meteo's provider-computed U.S. AQI component
    // indices rather than inventing arbitrary concentration ceilings.
    readonly property real ozoneMeter:
        Math.max(0, Math.min(1, ozoneAqiValue / 500))
    readonly property real nitrogenDioxideMeter:
        Math.max(0, Math.min(1, nitrogenDioxideAqiValue / 500))
    readonly property real carbonMonoxideMeter:
        Math.max(0, Math.min(1, carbonMonoxideAqiValue / 500))

    function aqiSeverityColor(value) {
        const reading = Number(value);
        if (!isFinite(reading) || reading < 0 || reading > 500)
            return Colors.white;
        if (reading <= 50)
            return Colors.cyan;
        if (reading <= 100)
            return Colors.yellow;
        if (reading <= 150)
            return Colors.orange;
        return Colors.red;
    }

    readonly property color aqiColor: aqiReady
                                      ? aqiSeverityColor(aqiValue) : Colors.white

    // Only gas component AQI scores are available. This is NOT a claim
    // about the primary pollutant driving overall AQI.
    readonly property var gasLeader: {
        if (!aqiReady)
            return { "name": "UNAVAILABLE", "value": -1 };
        const indices = [
            ["OZONE", ozoneAqiValue],
            ["NO₂", nitrogenDioxideAqiValue],
            ["CO", carbonMonoxideAqiValue]
        ];
        let peak = { "name": "UNAVAILABLE", "value": -1 };
        for (let i = 0; i < indices.length; i++) {
            const index = Number(indices[i][1]);
            if (isFinite(index) && index >= 0 && index > peak.value)
                peak = { "name": indices[i][0], "value": index };
        }
        return peak;
    }

    function particulateText(value) {
        return aqiReady && isFinite(value) && value >= 0
               ? Number(value).toFixed(1) + " µg/m³" : "-- µg/m³";
    }

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.green

    color: Colors.black

    // Leave the existing forecast intact; expose new rows with a scrollbar
    // if the fixed-height window cannot contain everything at once.
    Flickable {
        id: groundScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, groundContent.y + groundContent.implicitHeight + 12)

        Column {
            id: groundContent
            x: 20
            y: 12
            width: Math.max(0, groundScroll.width - 40)
            spacing: 10

            Row {
            width: parent.width

            GohuText {
                text: "⌁  GROUND"
                font.pixelSize: 24
                color: Colors.green
            }

            Item {
                width: parent.width - 330
                height: 1
            }

            GohuText {
                text: ground.aqiReady
                      ? "ENVIRONMENT ONLINE"
                      : ground.aqiLoading
                        ? "RECEIVING"
                        : "OFFLINE"
                font.pixelSize: 12
                color: ground.aqiReady ? Colors.cyan : Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "OFFICIAL ALERTS // NWS"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 14

                SecondaryText {
                    text: "ACTIVE POINT FEED"
                    font.pixelSize: 11
                    color: Colors.green
                }

                GohuText {
                    text: !ground.nwsConfigured
                          ? "NOT CONFIGURED"
                          : ground.nwsLoading && !ground.nwsReady
                            ? "RECEIVING"
                            : ground.nwsErrorText.length > 0
                              ? (ground.nwsReady ? "DEGRADED" : "OFFLINE")
                              : ground.nwsReady
                                ? "RECEIVED " + ground.officialAlerts.length
                                : "WAITING"
                    font.pixelSize: 11
                    color: !ground.nwsConfigured ? Colors.orange
                           : ground.nwsErrorText.length > 0 ? Colors.yellow
                           : ground.nwsReady ? Colors.cyan : Colors.orange
                }

                QuietText {
                    text: ground.nwsConfigured && ground.nwsAlertSource
                          ? "PINNED " + ground.nwsAlertSource.alertPoint
                            + " // LAST SUCCESS " + ground.nwsReceiveAge()
                          : "EXPLICIT OPERATOR POINT REQUIRED"
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: !ground.nwsConfigured
                width: parent.width
                text: "SET POST_APOLLO_NWS_ALERT_POINT=LAT,LON // WEATHER FIX IS NEVER USED FOR EMERGENCY TARGETING"
                font.pixelSize: 10
            }

            QuietText {
                visible: ground.nwsConfigured
                         && ground.nwsErrorText.length > 0
                width: parent.width
                text: ground.nwsErrorText
                      + " // LAST-GOOD ALERT STATE RETAINED"
                font.pixelSize: 10
            }

            QuietText {
                visible: ground.nwsConfigured
                         && ground.nwsReady
                         && ground.officialAlerts.length === 0
                width: parent.width
                text: "NO ACTIVE NWS ALERTS LISTED FOR THE PINNED POINT"
                font.pixelSize: 11
            }

            Repeater {
                model: ground.officialAlerts

                delegate: Rectangle {
                    required property var modelData

                    width: groundContent.width
                    height: 126
                    color: Colors.dark
                    border.width: 1
                    border.color: modelData.listingState === "RECHECK PENDING"
                                  ? Colors.yellow
                                  : ground.alertSeverityColor(modelData.severity)

                    Column {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 4

                        Row {
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: Math.max(0, parent.width - 292)
                                text: String(modelData.event || "NWS ALERT").toUpperCase()
                                elide: Text.ElideRight
                                font.pixelSize: 14
                                color: ground.alertSeverityColor(modelData.severity)
                            }

                            QuietText {
                                width: 122
                                text: String(modelData.severity || "UNKNOWN").toUpperCase()
                                      + " // "
                                      + String(modelData.urgency || "UNKNOWN").toUpperCase()
                                elide: Text.ElideRight
                                font.pixelSize: 9
                            }

                            GohuText {
                                width: 140
                                text: modelData.listingState
                                horizontalAlignment: Text.AlignRight
                                font.pixelSize: 10
                                color: modelData.listingState === "RECHECK PENDING"
                                       ? Colors.yellow : Colors.green
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: modelData.headline
                                  ? modelData.headline : modelData.event
                            elide: Text.ElideRight
                            font.pixelSize: 11
                            color: Colors.white
                        }

                        QuietText {
                            width: parent.width
                            text: "AREA // " + (modelData.area || "NOT PROVIDED")
                                  + " // CERTAINTY "
                                  + String(modelData.certainty || "UNKNOWN").toUpperCase()
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: "EFFECTIVE " + ground.alertTimeUtc(modelData.effective)
                                  + " // EXPIRES " + ground.alertTimeUtc(modelData.expires)
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: "ISSUER // " + (modelData.issuer || "NWS")
                                  + " // OFFICIAL API PRODUCT, NOT FORECAST INFERENCE"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "RIVER // NOAA NWPS"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 14

                SecondaryText {
                    text: "NEARBY GAUGE"
                    font.pixelSize: 11
                    color: Colors.green
                }

                GohuText {
                    text: !riverService.configured
                          ? "LOCATION UNAVAILABLE"
                          : riverService.loading && !riverService.ready
                            ? "RECEIVING"
                            : riverService.failed
                              ? (riverService.ready
                                 ? "DEGRADED" : "OFFLINE")
                              : riverService.ready && riverService.gauge
                                ? "RECEIVED"
                                : riverService.ready
                                  ? "NO GAUGE IN SEARCH BOX"
                                  : "WAITING"
                    font.pixelSize: 11
                    color: riverService.failed ? Colors.yellow
                           : riverService.ready ? Colors.cyan
                           : Colors.orange
                }

                QuietText {
                    text: riverService.ready
                          ? "LAST SUCCESS " + ground.riverReceiveAge()
                          : "NOAA/NWS NATIONAL WATER PREDICTION SERVICE"
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: riverService.failed
                width: parent.width
                text: riverService.errorText
                      + (riverService.ready
                         ? " // LAST-GOOD GAUGE STATE RETAINED" : "")
                font.pixelSize: 10
                color: Colors.yellow
            }

            QuietText {
                visible: riverService.ready && !riverService.gauge
                width: parent.width
                text: "NO NWPS GAUGE RETURNED WITHIN THE BOUNDED WEATHER-LOCATION SEARCH"
                font.pixelSize: 10
            }

            Rectangle {
                visible: riverService.ready && !!riverService.gauge
                width: parent.width
                height: 154
                color: Colors.dark
                border.width: 1
                border.color:
                    riverService.gauge
                    ? ground.riverCategoryColor(
                          riverService.gauge.observedCategory
                      )
                    : Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5

                    Row {
                        width: parent.width
                        spacing: 10

                        GohuText {
                            width: Math.max(0, parent.width - 270)
                            text: riverService.gauge
                                  ? riverService.gauge.name
                                  : ""
                            elide: Text.ElideRight
                            font.pixelSize: 14
                            color: Colors.white
                        }

                        GohuText {
                            width: 260
                            horizontalAlignment: Text.AlignRight
                            text: riverService.gauge
                                  ? Math.round(
                                        riverService.gauge.distanceKm
                                    ) + " KM FROM WEATHER FIX"
                                  : ""
                            font.pixelSize: 10
                            color: Colors.cyan
                        }
                    }

                    QuietText {
                        width: parent.width
                        text: riverService.gauge
                              ? "LID // " + riverService.gauge.lid
                                + (riverService.gauge.state
                                   ? " // " + riverService.gauge.state : "")
                                + (riverService.gauge.wfo
                                   ? " // WFO "
                                     + riverService.gauge.wfo : "")
                                + (riverService.gauge.rfc
                                   ? " // RFC "
                                     + riverService.gauge.rfc : "")
                              : ""
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 72
                            color: Colors.black
                            border.width: 1
                            border.color: riverService.gauge
                                          ? ground.riverCategoryColor(
                                                riverService.gauge
                                                .observedCategory
                                            )
                                          : Colors.cyan

                            Column {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                SecondaryText {
                                    text: "OBSERVED // PRIMARY"
                                    font.pixelSize: 9
                                }

                                GohuText {
                                    text: riverService.gauge
                                          ? RiverPolicy.readingText(
                                                riverService.gauge
                                                .observedPrimary,
                                                riverService.gauge
                                                .primaryUnits
                                            )
                                          : "--"
                                    font.pixelSize: 16
                                    color: Colors.white
                                }

                                GohuText {
                                    text: riverService.gauge
                                          ? "CATEGORY // "
                                            + riverService.gauge
                                              .observedCategory.label
                                          : "CATEGORY // --"
                                    font.pixelSize: 10
                                    color: riverService.gauge
                                           ? ground.riverCategoryColor(
                                                 riverService.gauge
                                                 .observedCategory
                                             )
                                           : Colors.white
                                }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 12) / 2
                            height: 72
                            color: Colors.black
                            border.width: 1
                            border.color: riverService.gauge
                                          ? ground.riverCategoryColor(
                                                riverService.gauge
                                                .forecastCategory
                                            )
                                          : Colors.cyan

                            Column {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                SecondaryText {
                                    text: "FORECAST // PRIMARY"
                                    font.pixelSize: 9
                                }

                                GohuText {
                                    text: riverService.gauge
                                          ? RiverPolicy.readingText(
                                                riverService.gauge
                                                .forecastPrimary,
                                                riverService.gauge
                                                .primaryUnits
                                            )
                                          : "--"
                                    font.pixelSize: 16
                                    color: Colors.white
                                }

                                GohuText {
                                    text: riverService.gauge
                                          ? "CATEGORY // "
                                            + riverService.gauge
                                              .forecastCategory.label
                                          : "CATEGORY // --"
                                    font.pixelSize: 10
                                    color: riverService.gauge
                                           ? ground.riverCategoryColor(
                                                 riverService.gauge
                                                 .forecastCategory
                                             )
                                           : Colors.white
                                }
                            }
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 6
                visible: riverService.ready
                         && riverService.nearbyGauges.length > 1

                StationSectionDivider {
                    width: parent.width
                    title: "NEARBY COMPARE // SAME NWPS SNAPSHOT"
                }

                Repeater {
                    model: riverService.nearbyGauges

                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: parent.width
                        height: 50
                        color: index === 0 ? Colors.dark : Colors.black
                        border.width: 1
                        border.color:
                            ground.riverCategoryColor(
                                modelData.observedCategory
                            )

                        Row {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 10

                            GohuText {
                                width: 22
                                text: String(index + 1)
                                font.pixelSize: 12
                                color: index === 0
                                       ? Colors.magenta : Colors.cyan
                            }

                            Column {
                                width: Math.max(0, parent.width - 540)
                                spacing: 2

                                GohuText {
                                    width: parent.width
                                    text: modelData.name
                                    elide: Text.ElideRight
                                    font.pixelSize: 10
                                    color: Colors.white
                                }

                                QuietText {
                                    width: parent.width
                                    text: modelData.lid
                                          + " // "
                                          + Math.round(
                                                modelData.distanceKm
                                            )
                                          + " KM"
                                    elide: Text.ElideRight
                                    font.pixelSize: 9
                                }
                            }

                            Column {
                                width: 150
                                spacing: 2

                                SecondaryText {
                                    text: "OBSERVED"
                                    font.pixelSize: 8
                                }

                                GohuText {
                                    text: RiverPolicy.readingText(
                                        modelData.observedPrimary,
                                        modelData.primaryUnits
                                    )
                                    elide: Text.ElideRight
                                    font.pixelSize: 10
                                    color: ground.riverCategoryColor(
                                        modelData.observedCategory
                                    )
                                }
                            }

                            Column {
                                width: 150
                                spacing: 2

                                SecondaryText {
                                    text: "FORECAST"
                                    font.pixelSize: 8
                                }

                                GohuText {
                                    text: RiverPolicy.readingText(
                                        modelData.forecastPrimary,
                                        modelData.primaryUnits
                                    )
                                    elide: Text.ElideRight
                                    font.pixelSize: 10
                                    color: ground.riverCategoryColor(
                                        modelData.forecastCategory
                                    )
                                }
                            }

                            QuietText {
                                width: 170
                                text: modelData.observedCategory.label
                                      + " // "
                                      + modelData.forecastCategory.label
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }
                        }
                    }
                }

                QuietText {
                    width: parent.width
                    text: "PROXIMITY COMPARISON ONLY // DIFFERENT RIVERS / TRIBUTARIES MAY NOT BE HYDROLOGICALLY COMPARABLE"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: riverService.ready && !!riverService.gauge

                StationSectionDivider {
                    width: parent.width
                    title: "FLOOD CONTEXT // IMPACTS + CRESTS"
                }

                Row {
                    width: parent.width
                    spacing: 12

                    GohuText {
                        text: riverService.contextLoading
                              ? "RECEIVING"
                              : riverService.contextFailed
                                ? (riverService.contextReady
                                   ? "DEGRADED" : "UNAVAILABLE")
                                : riverService.contextReady
                                  ? "RECEIVED"
                                  : "WAITING"
                        font.pixelSize: 10
                        color: riverService.contextFailed
                               ? Colors.yellow
                               : riverService.contextReady
                                 ? Colors.cyan : Colors.orange
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 110)
                        text: riverService.contextReady
                              ? "LID " + riverService.contextGaugeId
                                + " // COUNTY "
                                + (riverService.gaugeContext.county || "--")
                                + (riverService.gaugeContext.usgsId
                                   ? " // USGS "
                                     + riverService.gaugeContext.usgsId
                                   : "")
                              : "NWPS /GAUGES/{LID} METADATA"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                QuietText {
                    visible: riverService.contextFailed
                    width: parent.width
                    text: riverService.contextErrorText
                          + (riverService.contextReady
                             ? " // LAST-GOOD CONTEXT RETAINED" : "")
                    font.pixelSize: 9
                    color: Colors.yellow
                }

                Row {
                    width: parent.width
                    spacing: 8
                    visible: riverService.contextReady
                             && riverService.gaugeContext.thresholds.length > 0

                    Repeater {
                        model: riverService.gaugeContext.thresholds

                        delegate: Rectangle {
                            required property var modelData
                            width: 155
                            height: 54
                            color: Colors.dark
                            border.width: 1
                            border.color: ground.riverCategoryColor(
                                {"id": modelData.id}
                            )

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 3

                                SecondaryText {
                                    text: modelData.label + " THRESHOLD"
                                    font.pixelSize: 8
                                }

                                GohuText {
                                    text: modelData.stage !== null
                                          ? RiverPolicy.readingText(
                                                modelData.stage,
                                                riverService.gaugeContext
                                                    .stageUnits
                                            )
                                          : RiverPolicy.readingText(
                                                modelData.flow,
                                                riverService.gaugeContext
                                                    .flowUnits
                                            )
                                    font.pixelSize: 12
                                    color: ground.riverCategoryColor(
                                        {"id": modelData.id}
                                    )
                                }
                            }
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: 5
                    visible: riverService.contextReady
                             && riverService.gaugeContext.impacts.length > 0

                    GohuText {
                        text: "OFFICIAL FLOOD IMPACT STATEMENTS // "
                              + riverService.gaugeContext.impacts.length
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    Repeater {
                        model: riverService.gaugeContext.impacts.slice(0, 4)

                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 52
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.orange

                            Row {
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 10

                                GohuText {
                                    width: 105
                                    text: RiverPolicy.readingText(
                                        modelData.stage,
                                        riverService.gaugeContext.stageUnits
                                    )
                                    font.pixelSize: 11
                                    color: Colors.orange
                                }

                                QuietText {
                                    width: Math.max(0, parent.width - 115)
                                    text: modelData.statement
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    font.pixelSize: 9
                                }
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 12
                    visible: riverService.contextReady
                             && (riverService.gaugeContext.recentCrests.length > 0
                                 || riverService.gaugeContext.historicCrests.length > 0)

                    Column {
                        width: (parent.width - 12) / 2
                        spacing: 4

                        GohuText {
                            text: "RECENT CRESTS"
                            font.pixelSize: 10
                            color: Colors.cyan
                        }

                        Repeater {
                            model: riverService.gaugeContext.recentCrests.slice(0, 4)

                            delegate: QuietText {
                                required property var modelData
                                width: parent.width
                                text: modelData.occurredLabel
                                      + " // "
                                      + RiverPolicy.crestReading(
                                            modelData,
                                            riverService.gaugeContext.stageUnits,
                                            riverService.gaugeContext.flowUnits
                                        )
                                      + (modelData.preliminary
                                         ? " // " + modelData.preliminary
                                         : "")
                                elide: Text.ElideRight
                                font.pixelSize: 9
                            }
                        }
                    }

                    Column {
                        width: (parent.width - 12) / 2
                        spacing: 4

                        GohuText {
                            text: "HISTORIC CRESTS"
                            font.pixelSize: 10
                            color: Colors.magenta
                        }

                        Repeater {
                            model: riverService.gaugeContext.historicCrests.slice(0, 4)

                            delegate: QuietText {
                                required property var modelData
                                width: parent.width
                                text: modelData.occurredLabel
                                      + " // "
                                      + RiverPolicy.crestReading(
                                            modelData,
                                            riverService.gaugeContext.stageUnits,
                                            riverService.gaugeContext.flowUnits
                                        )
                                      + (modelData.oldDatum
                                         ? " // OLD DATUM" : "")
                                elide: Text.ElideRight
                                font.pixelSize: 9
                            }
                        }
                    }
                }

                QuietText {
                    visible: riverService.contextReady
                    width: parent.width
                    text: "NWPS OFFICIAL GAUGE METADATA // IMPACT STATEMENTS + CREST RECORDS ARE LOCATION-SPECIFIC"
                          + (riverService.gaugeContext.inundationAvailable
                             ? " // INUNDATION PRODUCT AVAILABLE"
                             : "")
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            Column {
                width: parent.width
                spacing: 7
                visible: riverService.ready && !!riverService.gauge

                StationSectionDivider {
                    width: parent.width
                    title: "STAGEFLOW // OBSERVED + OFFICIAL FORECAST"
                }

                Row {
                    width: parent.width
                    spacing: 12

                    GohuText {
                        text: riverService.stageflowLoading
                              ? "RECEIVING"
                              : riverService.stageflowFailed
                                ? (riverService.stageflowReady
                                   ? "DEGRADED" : "UNAVAILABLE")
                                : riverService.stageflowReady
                                  ? "RECEIVED"
                                  : "WAITING"
                        font.pixelSize: 10
                        color: riverService.stageflowFailed
                               ? Colors.yellow
                               : riverService.stageflowReady
                                 ? Colors.cyan : Colors.orange
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 110)
                        text: riverService.stageflowReady
                              ? "LID "
                                + riverService.stageflowGaugeId
                                + " // LAST SUCCESS "
                                + ground.stageflowReceiveAge()
                              : "NWPS /GAUGES/{LID}/STAGEFLOW"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                QuietText {
                    visible: riverService.stageflowFailed
                    width: parent.width
                    text: riverService.stageflowErrorText
                          + (riverService.stageflowReady
                             ? " // LAST-GOOD SERIES RETAINED" : "")
                    font.pixelSize: 9
                    color: Colors.yellow
                }

                Rectangle {
                    visible: riverService.stageflowReady
                             && ground.observedHydrographStats.available
                    width: parent.width
                    height: 104
                    color: Colors.dark
                    border.width: 1
                    border.color: ground.riverTrendColor(
                        ground.observedHydrographStats.direction
                    )

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 5

                        Row {
                            width: parent.width
                            spacing: 12

                            GohuText {
                                width: 220
                                text: "OBSERVED HYDROGRAPH // "
                                      + ground.observedHydrographStats.points
                                      + " POINTS"
                                font.pixelSize: 10
                                color: Colors.cyan
                            }

                            GohuText {
                                width: 90
                                text: ground.observedHydrographStats.direction
                                font.pixelSize: 10
                                color: ground.riverTrendColor(
                                    ground.observedHydrographStats.direction
                                )
                            }

                            QuietText {
                                width: Math.max(0, parent.width - 334)
                                horizontalAlignment: Text.AlignRight
                                text: ground.observedHydrographStats.spanHours >= 0
                                      ? ground.observedHydrographStats
                                        .spanHours.toFixed(1) + " H WINDOW"
                                      : "WINDOW --"
                                font.pixelSize: 9
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 14

                            QuietText {
                                width: 170
                                text: "MIN // "
                                      + RiverPolicy.readingText(
                                          ground.observedHydrographStats.minimum,
                                          riverService.stageflow.observed
                                              .primaryUnits
                                      )
                                font.pixelSize: 9
                            }

                            QuietText {
                                width: 170
                                text: "MAX // "
                                      + RiverPolicy.readingText(
                                          ground.observedHydrographStats.maximum,
                                          riverService.stageflow.observed
                                              .primaryUnits
                                      )
                                font.pixelSize: 9
                            }

                            QuietText {
                                width: 190
                                text: "DELTA // "
                                      + (ground.observedHydrographStats.delta
                                         !== null
                                         ? (ground.observedHydrographStats.delta
                                            >= 0 ? "+" : "")
                                           + ground.observedHydrographStats
                                             .delta.toFixed(2)
                                           + (riverService.stageflow.observed
                                              .primaryUnits
                                              ? " "
                                                + riverService.stageflow
                                                  .observed.primaryUnits
                                              : "")
                                         : "--")
                                font.pixelSize: 9
                            }
                        }

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 3

                            Repeater {
                                model: ground.observedHydrographBars

                                delegate: Item {
                                    required property var modelData
                                    width: Math.max(
                                        3,
                                        (parent.width
                                         - Math.max(
                                             0,
                                             ground.observedHydrographBars
                                             .length - 1
                                           ) * 3)
                                        / Math.max(
                                            1,
                                            ground.observedHydrographBars
                                            .length
                                          )
                                    )
                                    height: parent.height

                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        width: parent.width
                                        height: Math.max(
                                            4,
                                            parent.height
                                            * (0.2
                                               + 0.8
                                                 * modelData.fraction)
                                        )
                                        color: Colors.cyan
                                    }
                                }
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 12
                    visible: riverService.stageflowReady

                    Rectangle {
                        width: (parent.width - 12) / 2
                        height: 150
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 5

                            GohuText {
                                text: "OBSERVED // LAST "
                                      + ground.observedStageflowRows.length
                                color: Colors.cyan
                                font.pixelSize: 11
                            }

                            QuietText {
                                width: parent.width
                                text: riverService.stageflow.observed.available
                                      ? riverService.stageflow.observed
                                        .primaryName
                                        + (riverService.stageflow.observed
                                           .primaryUnits
                                           ? " // "
                                             + riverService.stageflow.observed
                                               .primaryUnits
                                           : "")
                                      : "NO OBSERVED SERIES RETURNED"
                                elide: Text.ElideRight
                                font.pixelSize: 9
                            }

                            Repeater {
                                model: ground.observedStageflowRows

                                delegate: Row {
                                    required property var modelData
                                    width: parent.width
                                    spacing: 8

                                    QuietText {
                                        width: 116
                                        text: modelData.validLabel
                                        elide: Text.ElideRight
                                        font.pixelSize: 9
                                    }

                                    GohuText {
                                        width: Math.max(
                                            0, parent.width - 124
                                        )
                                        text: RiverPolicy.pointReading(
                                            riverService.stageflow.observed,
                                            modelData
                                        )
                                        elide: Text.ElideRight
                                        font.pixelSize: 10
                                        color: Colors.white
                                    }
                                }
                            }

                            QuietText {
                                visible:
                                    riverService.stageflow.observed.available
                                    && ground.observedStageflowRows.length === 0
                                text: "NO VALID OBSERVED POINTS"
                                font.pixelSize: 9
                            }
                        }
                    }

                    Rectangle {
                        width: (parent.width - 12) / 2
                        height: 150
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 5

                            GohuText {
                                text: "OFFICIAL FORECAST // NEXT "
                                      + ground.forecastStageflowRows.length
                                color: Colors.magenta
                                font.pixelSize: 11
                            }

                            QuietText {
                                width: parent.width
                                text: riverService.stageflow.forecast.available
                                      ? riverService.stageflow.forecast
                                        .primaryName
                                        + (riverService.stageflow.forecast
                                           .primaryUnits
                                           ? " // "
                                             + riverService.stageflow.forecast
                                               .primaryUnits
                                           : "")
                                      : "NO OFFICIAL FORECAST SERIES RETURNED"
                                elide: Text.ElideRight
                                font.pixelSize: 9
                            }

                            Repeater {
                                model: ground.forecastStageflowRows

                                delegate: Row {
                                    required property var modelData
                                    width: parent.width
                                    spacing: 8

                                    QuietText {
                                        width: 116
                                        text: modelData.validLabel
                                        elide: Text.ElideRight
                                        font.pixelSize: 9
                                    }

                                    GohuText {
                                        width: Math.max(
                                            0, parent.width - 124
                                        )
                                        text: RiverPolicy.pointReading(
                                            riverService.stageflow.forecast,
                                            modelData
                                        )
                                        elide: Text.ElideRight
                                        font.pixelSize: 10
                                        color: Colors.white
                                    }
                                }
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 12
                    visible: riverService.stageflowReady

                    QuietText {
                        width: (parent.width - 12) / 2
                        text: "OBS ISSUED // "
                              + riverService.stageflow.observed.issuedLabel
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }

                    QuietText {
                        width: (parent.width - 12) / 2
                        text: "FORECAST ISSUED // "
                              + riverService.stageflow.forecast.issuedLabel
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: Colors.magenta
                    }
                }

                QuietText {
                    width: parent.width
                    text: "OBSERVED AND FORECAST SERIES ARE SEPARATE NWPS PRODUCTS // FORECAST VALUES ARE PREDICTIONS, NOT MEASUREMENTS"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            QuietText {
                width: parent.width
                text: "BOUNDED WEATHER-LOCATION PROXIMITY LOOKUP // INFORMATIONAL ONLY // DOES NOT CHANGE THE EXPLICIT NWS ALERT TARGET"
                font.pixelSize: 9
            }

            QuietText {
                width: parent.width
                text: "STAGE IS RELATIVE TO THE GAUGE DATUM // NEARBY GAUGE ≠ YOUR PROPERTY // NOT A FLOOD WARNING"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "MARINE // NOAA NDBC"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 12

                GohuText {
                    text: !marineService.configured
                          ? "LOCATION UNAVAILABLE"
                          : marineService.loading && !marineService.ready
                            ? "RECEIVING"
                            : marineService.failed
                              ? (marineService.ready
                                 ? "DEGRADED" : "OFFLINE")
                              : marineService.ready && marineService.station
                                ? "RECEIVED"
                                : marineService.ready
                                  ? "NO REPORTING STATION"
                                  : "WAITING"
                    font.pixelSize: 10
                    color: marineService.failed
                           ? Colors.yellow
                           : marineService.ready && marineService.station
                             ? Colors.cyan : Colors.orange
                }

                QuietText {
                    width: Math.max(0, parent.width - 150)
                    text: marineService.station
                          ? "STATION "
                            + marineService.station.stationId
                            + " // "
                            + Math.round(
                                  marineService.station.distanceKm
                              )
                            + " KM FROM WEATHER FIX"
                            + " // SAMPLE "
                            + marineService.station.sampleUtc
                          : "NDBC LATEST OBSERVATIONS // ALL REPORTING STATIONS"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: marineService.failed
                width: parent.width
                text: marineService.errorText
                      + (marineService.ready
                         ? " // LAST-GOOD MARINE STATE RETAINED" : "")
                font.pixelSize: 9
                color: Colors.yellow
            }

            Rectangle {
                visible: marineService.ready && !!marineService.station
                width: parent.width
                height: 164
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 7

                    Row {
                        width: parent.width
                        spacing: 12

                        GohuText {
                            width: 180
                            text: marineService.station
                                  ? "NDBC "
                                    + marineService.station.stationId
                                  : "NDBC --"
                            font.pixelSize: 13
                            color: Colors.cyan
                        }

                        QuietText {
                            width: 190
                            text: "AGE // " + ground.marineSampleAge()
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: Math.max(0, parent.width - 394)
                            horizontalAlignment: Text.AlignRight
                            text: "REPORTING STATIONS // "
                                  + marineService.reportingStations
                            font.pixelSize: 9
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        Column {
                            width: 180
                            spacing: 4
                            SecondaryText {
                                text: "WAVES // SIGNIFICANT"
                                font.pixelSize: 8
                            }
                            GohuText {
                                text: ground.marineWaveLabel(
                                    marineService.station.waveHeightM
                                )
                                font.pixelSize: 11
                                color: Colors.cyan
                            }
                            QuietText {
                                text: "DPD "
                                      + MarinePolicy.numericLabel(
                                            marineService.station
                                                .dominantPeriodS,
                                            1, " s"
                                        )
                                      + " // APD "
                                      + MarinePolicy.numericLabel(
                                            marineService.station
                                                .averagePeriodS,
                                            1, " s"
                                        )
                                font.pixelSize: 8
                            }
                        }

                        Column {
                            width: 220
                            spacing: 4
                            SecondaryText {
                                text: "WIND"
                                font.pixelSize: 8
                            }
                            GohuText {
                                text: ground.marineWindLabel(
                                    marineService.station.windSpeedMs
                                )
                                font.pixelSize: 11
                                color: Colors.white
                            }
                            QuietText {
                                text: "DIR "
                                      + MarinePolicy.numericLabel(
                                            marineService.station
                                                .windDirection,
                                            0, "°T"
                                        )
                                      + " // GUST "
                                      + ground.marineWindLabel(
                                            marineService.station.gustMs
                                        )
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }
                        }

                        Column {
                            width: 210
                            spacing: 4
                            SecondaryText {
                                text: "WATER"
                                font.pixelSize: 8
                            }
                            GohuText {
                                text: ground.marineTempLabel(
                                    marineService.station.waterTempC
                                )
                                font.pixelSize: 11
                                color: Colors.blue
                            }
                            QuietText {
                                text: "TIDE "
                                      + MarinePolicy.numericLabel(
                                            marineService.station.tideFt,
                                            2, " ft"
                                        )
                                font.pixelSize: 8
                            }
                        }

                        Column {
                            width: 210
                            spacing: 4
                            SecondaryText {
                                text: "AIR"
                                font.pixelSize: 8
                            }
                            GohuText {
                                text: ground.marineTempLabel(
                                    marineService.station.airTempC
                                )
                                font.pixelSize: 11
                                color: Colors.orange
                            }
                            QuietText {
                                text: "PRES "
                                      + MarinePolicy.numericLabel(
                                            marineService.station.pressureHpa,
                                            1, " hPa"
                                        )
                                      + " // DEW "
                                      + ground.marineTempLabel(
                                            marineService.station.dewpointC
                                        )
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 12

                        QuietText {
                            width: 250
                            text: "MEAN WAVE DIR // "
                                  + MarinePolicy.numericLabel(
                                        marineService.station
                                            .meanWaveDirection,
                                        0, "°T"
                                    )
                            font.pixelSize: 8
                        }

                        QuietText {
                            width: 200
                            text: "VIS // "
                                  + MarinePolicy.numericLabel(
                                        marineService.station.visibilityNm,
                                        1, " nmi"
                                    )
                            font.pixelSize: 8
                        }

                        QuietText {
                            width: Math.max(0, parent.width - 474)
                            text: "SOURCE METRIC // CONVERSIONS SHOWN FOR DISPLAY"
                            horizontalAlignment: Text.AlignRight
                            font.pixelSize: 8
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "NEAREST REPORTING NDBC-HOSTED STATION // DISTANCE IS GEOGRAPHIC, NOT COASTAL RELEVANCE // MISSING SENSOR FIELDS STAY UNAVAILABLE"
                font.pixelSize: 9
                color: Colors.orange
            }
        }


        StationSectionDivider {
            width: parent.width
            title: "COAST // NOAA CO-OPS"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 12

                GohuText {
                    text: !coastalService.configured
                          ? "LOCATION UNAVAILABLE"
                          : coastalService.loading
                            && !coastalService.ready
                            ? "RECEIVING"
                            : coastalService.ready
                              && (coastalService.waterFailed
                                  || coastalService.tideFailed)
                                ? "DEGRADED"
                                : coastalService.ready
                                  ? "RECEIVED"
                                  : coastalService.failed
                                    ? "OFFLINE" : "WAITING"
                    font.pixelSize: 10
                    color: coastalService.ready
                           ? Colors.cyan
                           : coastalService.failed
                             ? Colors.yellow : Colors.orange
                }

                QuietText {
                    width: Math.max(0, parent.width - 150)
                    text: coastalService.waterStation
                          ? "WATER "
                            + coastalService.waterStation.id
                            + " // "
                            + Math.round(
                                  coastalService.waterStation.distanceKm
                              )
                            + " KM"
                            + (coastalService.tideStation
                               ? "   TIDES "
                                 + coastalService.tideStation.id
                                 + " // "
                                 + Math.round(
                                       coastalService.tideStation.distanceKm
                                   )
                                 + " KM"
                               : "")
                          : "NOAA CO-OPS WATER LEVEL + TIDE-PREDICTION CATALOGS"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: coastalService.failed
                         || coastalService.waterFailed
                         || coastalService.tideFailed
                width: parent.width
                text: [
                    coastalService.errorText,
                    coastalService.waterErrorText,
                    coastalService.tideErrorText
                ].filter(function(value) {
                    return String(value || "").length > 0;
                }).join(" // ")
                font.pixelSize: 9
                color: Colors.yellow
            }

            Row {
                width: parent.width
                spacing: 12

                Rectangle {
                    width: 350
                    height: 164
                    color: Colors.dark
                    border.width: 1
                    border.color: coastalService.waterReady
                                  ? Colors.cyan : Colors.orange

                    Column {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 6

                        SecondaryText {
                            text: "OBSERVED WATER LEVEL"
                            font.pixelSize: 9
                        }

                        GohuText {
                            text: coastalService.waterReady
                                  && coastalService.waterLevel
                                  ? CoastalPolicy.feetLabel(
                                        coastalService.waterLevel.value
                                    )
                                  : "--"
                            font.pixelSize: 22
                            color: Colors.cyan
                        }

                        QuietText {
                            width: parent.width
                            text: coastalService.waterStation
                                  ? coastalService.waterStation.name
                                    + " // "
                                    + coastalService.waterStation.id
                                  : "WAITING FOR NEAREST WATER-LEVEL STATION"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: coastalService.waterStation
                                  ? "DATUM "
                                    + CoastalPolicy.observationDatum(
                                          coastalService.waterStation
                                      )
                                    + " // DIST "
                                    + Math.round(
                                          coastalService.waterStation.distanceKm
                                      )
                                    + " KM"
                                  : "DATUM -- // DIST --"
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: coastalService.waterReady
                                  && coastalService.waterLevel
                                  ? "SAMPLE "
                                    + coastalService.waterLevel.sampleUtc
                                    + " // AGE "
                                    + ground.coastalSampleAge()
                                  : "SAMPLE --"
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: coastalService.waterReady
                                  && coastalService.waterLevel
                                  ? coastalService.waterLevel.qualityLabel
                                  : "QUALITY --"
                            font.pixelSize: 8
                            color: Colors.orange
                        }
                    }
                }

                Rectangle {
                    width: Math.max(0, parent.width - 362)
                    height: 164
                    color: Colors.dark
                    border.width: 1
                    border.color: coastalService.tideReady
                                  ? Colors.magenta : Colors.orange

                    Column {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 6

                        SecondaryText {
                            text: "TIDE PREDICTIONS // NEXT HIGH + LOW"
                            font.pixelSize: 9
                        }

                        QuietText {
                            width: parent.width
                            text: coastalService.tideStation
                                  ? coastalService.tideStation.name
                                    + " // "
                                    + coastalService.tideStation.id
                                    + " // "
                                    + Math.round(
                                          coastalService.tideStation.distanceKm
                                      )
                                    + " KM"
                                  : "WAITING FOR NEAREST TIDE STATION"
                            elide: Text.ElideRight
                            font.pixelSize: 9
                        }

                        Row {
                            id: tidePredictionRow
                            width: parent.width
                            spacing: 7

                            Repeater {
                                model: coastalService.tideReady
                                       ? coastalService.tidePredictions.slice(
                                             0, 4
                                         ) : []

                                delegate: Rectangle {
                                    required property var modelData
                                    width: Math.max(
                                        0,
                                        (tidePredictionRow.width
                                         - 3 * tidePredictionRow.spacing) / 4
                                    )
                                    height: 92
                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        ground.coastalPredictionColor(
                                            modelData.high
                                        )

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 4

                                        GohuText {
                                            text: modelData.label
                                            font.pixelSize: 9
                                            color:
                                                ground.coastalPredictionColor(
                                                    modelData.high
                                                )
                                        }

                                        GohuText {
                                            text: CoastalPolicy.feetLabel(
                                                modelData.value
                                            )
                                            font.pixelSize: 11
                                            color: Colors.white
                                        }

                                        QuietText {
                                            text: modelData.sampleUtc
                                            elide: Text.ElideRight
                                            font.pixelSize: 8
                                        }
                                    }
                                }
                            }
                        }

                        QuietText {
                            visible: !coastalService.tideReady
                                     || coastalService.tidePredictions.length
                                        === 0
                            width: parent.width
                            text: coastalService.tideFailed
                                  ? coastalService.tideErrorText
                                  : "NO UPCOMING HIGH / LOW PREDICTIONS IN CURRENT WINDOW"
                            font.pixelSize: 9
                            color: coastalService.tideFailed
                                   ? Colors.yellow : Colors.white
                        }
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "OBSERVATION STATION AND TIDE STATION MAY DIFFER // BOTH ARE CHOSEN BY GEOGRAPHIC PROXIMITY TO THE WEATHER FIX"
                font.pixelSize: 9
            }

            QuietText {
                width: parent.width
                text: "MLLW DATUM IS USED FOR COASTAL TIDE PREDICTIONS // OBSERVED WATER LEVEL USES MLLW, LWD OR STND ACCORDING TO STATION TYPE"
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                text: "NEAREST CO-OPS STATION ≠ LOCAL COAST // HEIGHT IS STATION-REFERENCED // NOT A STORM-SURGE OR FLOOD-IMPACT CLAIM"
                font.pixelSize: 9
                color: Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "HEAT + FIRE WEATHER // NWS CONTEXT"
        }

        Row {
            width: parent.width
            spacing: 12

            Rectangle {
                width: 360
                height: 112
                color: Colors.dark
                border.width: 1
                border.color: ground.heatBandColor(
                    ground.heatIndexSummary.band.id
                )

                Column {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 5

                    SecondaryText {
                        text: "NWS HEAT INDEX // SHADE"
                        font.pixelSize: 9
                    }

                    Row {
                        width: parent.width
                        spacing: 14

                        GohuText {
                            width: 112
                            text: ground.heatIndexSummary.available
                                  ? ground.heatIndexSummary.valueF.toFixed(1)
                                    + "°F"
                                  : "--"
                            font.pixelSize: 22
                            color: ground.heatBandColor(
                                ground.heatIndexSummary.band.id
                            )
                        }

                        GohuText {
                            width: Math.max(0, parent.width - 126)
                            text: ground.heatIndexSummary.band.label
                            elide: Text.ElideRight
                            font.pixelSize: 11
                            color: ground.heatBandColor(
                                ground.heatIndexSummary.band.id
                            )
                        }
                    }

                    QuietText {
                        width: parent.width
                        text: ground.heatIndexSummary.available
                              ? ground.heatIndexSummary.method
                                + " // T "
                                + weatherService.tempF + "°F // RH "
                                + weatherService.humidity + "%"
                              : "TEMPERATURE / HUMIDITY UNAVAILABLE"
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }

                    QuietText {
                        width: parent.width
                        text: "NWS HEAT INDEX IS FOR SHADE // DIRECT SUN CAN FEEL HOTTER"
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }
            }

            Rectangle {
                width: Math.max(0, parent.width - 372)
                height: 112
                color: Colors.dark
                border.width: 1
                border.color: ground.fireWeatherAlertRows.length > 0
                              ? Colors.red : Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 5

                    SecondaryText {
                        text: "FIRE WEATHER // OFFICIAL + LOCAL OBS"
                        font.pixelSize: 9
                    }

                    GohuText {
                        width: parent.width
                        text: ground.fireWeatherAlertRows.length > 0
                              ? ground.fireWeatherAlertRows.length
                                + " OFFICIAL NWS PRODUCT"
                                + (ground.fireWeatherAlertRows.length === 1
                                   ? "" : "S")
                              : "NO MATCHING FIRE PRODUCT IN ALERT FEED"
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: ground.fireWeatherAlertRows.length > 0
                               ? Colors.red : Colors.cyan
                    }

                    QuietText {
                        width: parent.width
                        text: "RH "
                              + (weatherService
                                 ? weatherService.humidity : "--")
                              + "% // WIND "
                              + (weatherService
                                 ? weatherService.windMph : "--")
                              + " MPH // TEMP "
                              + (weatherService
                                 ? weatherService.tempF : "--")
                              + "°F"
                        font.pixelSize: 9
                    }

                    QuietText {
                        width: parent.width
                        text: "LOCAL WEATHER VALUES ARE DESCRIPTIVE ONLY // RED FLAG CRITERIA VARY BY NWS OFFICE + FUEL STATE"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 5
            visible: ground.fireWeatherAlertRows.length > 0

            Repeater {
                model: ground.fireWeatherAlertRows.slice(0, 3)

                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 58
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.red

                    Column {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 3

                        GohuText {
                            width: parent.width
                            text: String(
                                modelData.event
                                || modelData.headline
                                || "FIRE WEATHER PRODUCT"
                            ).toUpperCase()
                            elide: Text.ElideRight
                            font.pixelSize: 10
                            color: Colors.red
                        }

                        QuietText {
                            width: parent.width
                            text: "EFFECTIVE "
                                  + ground.alertTimeUtc(
                                        modelData.effective
                                    )
                                  + " // EXPIRES "
                                  + ground.alertTimeUtc(
                                        modelData.expires
                                    )
                            elide: Text.ElideRight
                            font.pixelSize: 8
                        }
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "AIR // PARTICULATES"
        }

        // One large instrument, two particulate measurements and the
        // highest available gas AQI component. No invented measurement.
        Row {
            width: parent.width
            spacing: 14

            Rectangle {
                id: airQualityInstrument
                width: 248
                height: 166
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                SecondaryText {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.margins: 12
                    text: "U.S. AIR QUALITY INDEX"
                    font.pixelSize: 11
                }

                // Draw the halo behind its AQI glyph, not over the number.
                SafeDropShadow {
                    anchors.fill: aqiReadingText
                    safeSource: aqiReadingText
                    requestedVisible: ground.aqiReady
                    radius: 10
                    samples: 19
                    horizontalOffset: 0
                    verticalOffset: 0
                    transparentBorder: true
                    opacity: 0.68
                    color: ground.aqiColor
                }

                GohuText {
                    id: aqiReadingText
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 29
                    text: ground.aqiReady ? String(weatherService.aqi) : "--"
                    font.pixelSize: 68
                    color: ground.aqiColor
                }

                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: aqiTrack.top
                    anchors.bottomMargin: 9
                    text: ground.aqiReady ? weatherService.aqiLabel : "OFFLINE"
                    font.pixelSize: 12
                    color: ground.aqiColor
                }

                Rectangle {
                    id: aqiTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    height: 9
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.aqiMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 158
                spacing: 10

                SecondaryText {
                    text: "PM2.5 // FINE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.particulateText(ground.pm25Value)
                    font.pixelSize: 19
                    color: Colors.white
                }

                Rectangle {
                    width: 144
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.pm25Meter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }

                QuietText {
                    text: "FINE PARTICLES"
                    font.pixelSize: 10
                }
            }

            Column {
                width: 158
                spacing: 10

                SecondaryText {
                    text: "PM10 // COARSE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.particulateText(ground.pm10Value)
                    font.pixelSize: 19
                    color: Colors.white
                }

                Rectangle {
                    width: 144
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.pm10Meter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }

                QuietText {
                    text: "COARSE PARTICLES"
                    font.pixelSize: 10
                }
            }

            Column {
                width: Math.max(0, parent.width - 248 - 158 - 158 - 3 * parent.spacing)
                spacing: 8

                SecondaryText {
                    text: "TOP GAS SUBINDEX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.gasLeader.name
                    font.pixelSize: 18
                    color: Colors.green
                }

                GohuText {
                    text: ground.gasLeader.value >= 0
                          ? Math.round(ground.gasLeader.value) + " AQI" : "-- AQI"
                    font.pixelSize: 19
                    color: Colors.white
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "OF OZONE / NO₂ / CO"
                    font.pixelSize: 9
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "GASES // POLLEN"
        }

        Row {
            spacing: 14

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "OZONE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.ozoneValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.ozoneMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "NO₂"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.nitrogenDioxideValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 115
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.nitrogenDioxideMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 150
                spacing: 5

                SecondaryText {
                    text: "CO"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.carbonMonoxideValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }

                Rectangle {
                    width: 125
                    height: 8
                    color: Colors.black
                    border.width: 1
                    border.color: ground.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * ground.carbonMonoxideMeter
                        height: parent.height - 4
                        color: ground.meterFillColor
                    }
                }
            }

            Column {
                width: 135
                spacing: 5

                SecondaryText {
                    text: "DUST"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.concentrationText(
                        ground.dustValue, " µg/m³"
                    )
                    font.pixelSize: 16
                    color: Colors.white
                }
            }

            Column {
                width: 170
                spacing: 5

                SecondaryText {
                    text: "POLLEN // PEAK"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.pollenPeak.value >= 0
                          ? ground.pollenPeak.value.toFixed(1) + " gr/m³"
                          : "N/A"
                    font.pixelSize: 16
                    color: ground.pollenPeak.value >= 0
                           ? Colors.green : Colors.white
                }

                QuietText {
                    text: ground.pollenPeak.name
                    font.pixelSize: 10
                }
            }
        }

        // The peak is only a summary. Show the six already-received
        // per-species readings without requesting a second pollen source.
        StationSectionDivider {
            width: parent.width
            title: "POLLEN // SPECIES"
        }

        Row {
            width: parent.width
            spacing: 8
            visible: ground.pollenSpecies.length > 0

            Repeater {
                model: ground.pollenSpecies

                delegate: Column {
                    required property var modelData
                    width: (groundContent.width - 5 * 8) / 6
                    spacing: 5

                    SecondaryText {
                        text: modelData.name
                        font.pixelSize: 10
                    }

                    GohuText {
                        width: parent.width
                        text: modelData.label
                        font.pixelSize: 13
                        color: modelData.available ? Colors.green : Colors.white
                        elide: Text.ElideRight
                    }
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 10
            text: ground.pollenSpecies.length > 0
                  ? "OPEN-METEO // CURRENT CONCENTRATION IN GRAINS/M³ // -- = NO READING, NOT ZERO"
                  : "POLLEN SPECIES UNAVAILABLE FOR THIS PROVIDER / LOCATION"
        }

        StationSectionDivider {
            width: parent.width
            title: "AIR // NEXT 12 HOURS"
        }

        Column {
            width: parent.width
            spacing: 4

            Row {
                width: parent.width
                spacing: 8

                Repeater {
                    model: ground.airQualityForecastReady
                           ? ground.airQualityForecast : []

                    delegate: Column {
                        required property var modelData
                        width: 116
                        spacing: 4

                        SecondaryText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.label
                            font.pixelSize: 11
                        }

                        GohuText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.aqi >= 0
                                  ? Math.round(modelData.aqi) + " AQI" : "-- AQI"
                            font.pixelSize: 22
                            color: ground.aqiSeverityColor(modelData.aqi)
                        }

                        Rectangle {
                            width: parent.width - 12
                            anchors.horizontalCenter: parent.horizontalCenter
                            height: 7
                            color: Colors.black
                            border.width: 1
                            border.color: ground.meterBorderColor

                            Rectangle {
                                x: 2
                                anchors.verticalCenter: parent.verticalCenter
                                width: (parent.width - 4)
                                       * (modelData.aqi >= 0
                                          ? Math.max(0, Math.min(1, modelData.aqi / 500))
                                          : 0)
                                height: parent.height - 4
                                color: ground.aqiSeverityColor(modelData.aqi)
                            }
                        }

                        QuietText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.pm25 >= 0
                                  ? "PM2.5 " + modelData.pm25.toFixed(1)
                                  : "PM2.5 --"
                            font.pixelSize: 10
                        }
                    }
                }
            }

            QuietText {
                visible: !ground.airQualityForecastReady
                text: "FORECAST UNAVAILABLE // CURRENT AIR QUALITY REMAINS ABOVE"
                font.pixelSize: 11
            }

            QuietText {
                text: "OPEN-METEO MODEL // LOCAL HOURS // 2H STEPS // PM2.5 IN µg/m³"
                font.pixelSize: 9
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SEISMIC // WORLDWIDE 24H"
        }

        Column {
            width: parent.width
            spacing: 5

            Row {
                spacing: 12

                SecondaryText {
                    text: "USGS // M2.5+"
                    font.pixelSize: 11
                    color: Colors.green
                }

                QuietText {
                    text: quakeService.failed
                          ? "FEED ERROR // PREVIOUS EVENTS MAY BE STALE"
                          : quakeService.loading && !quakeService.ready
                            ? "RECEIVING"
                            : quakeService.ready ? "LATEST PUBLISHED EVENTS"
                              : "OFFLINE"
                    font.pixelSize: 10
                }
            }

            Row {
                id: seismicEventRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: quakeService.ready ? quakeService.events : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (seismicEventRow.width
                                            - 2 * seismicEventRow.spacing) / 3)
                        height: 112
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            Row {
                                width: parent.width
                                spacing: 8

                                GohuText {
                                    text: "M " + modelData.magnitude.toFixed(1)
                                    font.pixelSize: 23
                                    color: Colors.green
                                }

                                QuietText {
                                    text: modelData.utc
                                    font.pixelSize: 10
                                }
                            }

                            GohuText {
                                width: parent.width
                                elide: Text.ElideRight
                                text: modelData.place
                                font.pixelSize: 12
                                color: Colors.white
                            }

                            QuietText {
                                text: modelData.depthKm >= 0
                                      ? "DEPTH " + modelData.depthKm.toFixed(1) + " KM"
                                      : "DEPTH --"
                                font.pixelSize: 10
                            }

                            QuietText {
                                text: ground.distanceLabel(
                                    modelData.latitude, modelData.longitude
                                )
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !quakeService.ready || quakeService.events.length === 0
                text: quakeService.failed ? quakeService.errorText
                      : quakeService.loading ? "LOADING USGS EVENTS"
                      : quakeService.ready ? "NO M2.5+ EVENTS IN FEED"
                        : "USGS DATA UNAVAILABLE"
                font.pixelSize: 11
            }

            QuietText {
                text: "USGS GEOJSON // MOST RECENT GLOBAL EVENTS // NOT AN EARTHQUAKE WARNING"
                font.pixelSize: 9
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "ENVIRONMENT // SOURCE"
        }

        Row {
            width: parent.width
            spacing: 22

            Column {
                width: 248
                spacing: 5

                SecondaryText {
                    text: "POSITION // WEATHER FIX"
                    font.pixelSize: 11
                }

                GohuText {
                    text: "LAT " + (weatherService && weatherService.latitude !== ""
                                   ? weatherService.latitude : "--")
                          + "   LON " + (weatherService && weatherService.longitude !== ""
                                      ? weatherService.longitude : "--")
                    font.pixelSize: 12
                    color: Colors.white
                }
            }

            Column {
                width: Math.max(0, parent.width - 270)
                spacing: 5

                SecondaryText {
                    text: "AIR QUALITY // SAMPLE"
                    font.pixelSize: 11
                }

                GohuText {
                    text: ground.aqiReady && weatherService.airQualitySourceTime !== ""
                          ? weatherService.airQualitySourceTime : "--"
                    font.pixelSize: 12
                    color: Colors.white
                }
            }
        }
        }
    }

    NeonScrollBar {
        flickable: groundScroll
        handleStyle: "star"
        geometryHost: ground
        visible: scrollable
    }
}
