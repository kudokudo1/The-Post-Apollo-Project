import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

// COSMOS C3 // Focused solar-wind instrument over the existing root-owned
// SpaceService and LiveHistoryStore. No independent fetcher or cache writer.
Rectangle {
    id: wind
    color: Colors.black
    clip: true

    property var spaceService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    readonly property int historyRevision:
        liveHistoryStore ? Number(liveHistoryStore.revision) || 0 : 0
    readonly property var windSamples: {
        historyRevision;
        return liveHistoryStore
            && typeof liveHistoryStore.samples === "function"
            ? liveHistoryStore.samples("space-wind", "global", runtimeNowMs)
            : [];
    }
    readonly property var imfSamples: {
        historyRevision;
        return liveHistoryStore
            && typeof liveHistoryStore.samples === "function"
            ? liveHistoryStore.samples("space-imf", "global", runtimeNowMs)
            : [];
    }

    function reading(ready, value, digits, unit) {
        if (!ready || value === null || value === undefined
                || !isFinite(Number(value)))
            return "--";
        return Number(value).toFixed(digits) + unit;
    }

    function sourceState(id, ready, loading, error, received, observed, cache) {
        const row = RuntimePolicy.displayRow(id, {
            active: true, ready: !!ready, loading: !!loading,
            errorText: error || "", receivedAt: received,
            observedAt: observed, usingCache: !!cache
        }, runtimeNowMs);
        return String(row.availability || "UNAVAILABLE").replace(/_/g, " ");
    }

    readonly property var metrics: [
        {label: "SOLAR WIND", value: reading(
             spaceService && spaceService.solarWindReady
                 && Number(spaceService.solarWindSpeed) >= 0,
             spaceService ? spaceService.solarWindSpeed : null, 0, " KM/S"),
         state: sourceState("space-wind",
             spaceService && spaceService.solarWindReady,
             spaceService && spaceService.solarWindLoading,
             spaceService ? spaceService.solarWindErrorText : "",
             spaceService ? spaceService.solarWindLastUpdated : null,
             spaceService ? spaceService.solarWindTime : null,
             spaceService && spaceService.usingPersistentSolarWindCache),
         accent: Colors.yellow},
        {label: "IMF BZ", value: reading(
             spaceService && spaceService.magneticFieldReady,
             spaceService ? spaceService.magneticFieldBz : null, 1, " NT"),
         state: sourceState("space-imf",
             spaceService && spaceService.magneticFieldReady,
             spaceService && spaceService.magneticFieldLoading,
             spaceService ? spaceService.magneticFieldErrorText : "",
             spaceService ? spaceService.magneticFieldLastUpdated : null,
             spaceService ? spaceService.magneticFieldTime : null,
             spaceService && spaceService.usingPersistentMagneticFieldCache),
         accent: Colors.magenta},
        {label: "IMF BT", value: reading(
             spaceService && spaceService.magneticFieldReady
                 && Number(spaceService.magneticFieldBt) >= 0,
             spaceService ? spaceService.magneticFieldBt : null, 1, " NT"),
         state: sourceState("space-imf",
             spaceService && spaceService.magneticFieldReady,
             spaceService && spaceService.magneticFieldLoading,
             spaceService ? spaceService.magneticFieldErrorText : "",
             spaceService ? spaceService.magneticFieldLastUpdated : null,
             spaceService ? spaceService.magneticFieldTime : null,
             spaceService && spaceService.usingPersistentMagneticFieldCache),
         accent: Colors.cyan},
        {label: "KP // CONTEXT", value: reading(
             spaceService && spaceService.kpReady
                 && Number(spaceService.kp) >= 0,
             spaceService ? spaceService.kp : null, 1, ""),
         state: sourceState("space-kp",
             spaceService && spaceService.kpReady,
             spaceService && spaceService.kpLoading,
             spaceService ? spaceService.kpErrorText : "",
             spaceService ? spaceService.kpLastUpdated : null,
             spaceService ? spaceService.kpTime : null,
             spaceService && spaceService.usingPersistentKpCache),
         accent: Colors.orange}
    ]

    Column {
        id: windConsole
        anchors.fill: parent
        anchors.margins: 9
        spacing: 7

        Row {
            id: header
            width: parent.width
            height: 26
            spacing: 6

            GohuText {
                width: Math.max(0, header.width - 267)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "COSMOS // SOLAR WIND"
                color: Colors.magenta
                font.pixelSize: 15
                elide: Text.ElideRight
            }
            ActionButton {
                width: 111
                height: 25
                label: "GEOMAGNETIC"
                labelPixelSize: 10
                accentColor: Colors.cyan
                onClicked: wind.routeRequested("cosmos/space-weather/geomagnetic")
            }
            ActionButton {
                width: 144
                height: 25
                label: "SPACE // ALL"
                labelPixelSize: 10
                accentColor: Colors.yellow
                onClicked: wind.routeRequested("cosmos/space-weather/full")
            }
        }

        Rectangle {
            width: parent.width
            height: 2
            color: Colors.cyan
        }

        Row {
            id: metricRow
            width: parent.width
            height: 86
            spacing: 6

            Repeater {
                model: wind.metrics
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1, (metricRow.width - 3 * metricRow.spacing) / 4)
                    height: metricRow.height
                    color: Colors.dark
                    border.width: 1
                    border.color: modelData.accent

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 5
                        GohuText {
                            width: parent.width
                            text: modelData.label
                            color: modelData.accent
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.value
                            color: Colors.white
                            font.pixelSize: 20
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            text: modelData.state
                            color: Colors.cyan
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            height: 18
            text: "OBSERVED WIND + INTERPLANETARY MAGNETIC FIELD // SAME-TIME COMPARISON"
            color: Colors.yellow
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        StationInteractiveHistoryChart {
            id: windChart
            width: parent.width
            height: 258
            title: "SOLAR WIND + IMF BZ // OBSERVED HISTORY"
            leftTitle: "WIND"
            leftUnit: "KM/S"
            leftField: "solarWindSpeed"
            leftColor: Colors.yellow
            leftSamples: wind.windSamples
            rightTitle: "IMF BZ"
            rightUnit: "NT"
            rightField: "bz"
            rightColor: Colors.magenta
            rightSamples: wind.imfSamples
            runtimeNowMs: wind.runtimeNowMs
        }

        QuietText {
            width: parent.width
            height: 28
            wrapMode: Text.WordWrap
            text: "NOAA SWPC // OBSERVED SOURCE TIMES, NOT FORECASTS. "
                + "KP IS GEOMAGNETIC CONTEXT, NOT A CAUSAL ESTIMATE. "
                + "MISSING OR STALE SAMPLES ARE NOT FILLED IN."
            color: Colors.cyan
            font.pixelSize: 10
        }
    }
}
