import QtQuick
import Quickshell
import Quickshell.Networking
import "../weather/WeatherDockPolicy.js" as WeatherPolicy
import "ApolloHubSystemPolicy.js" as SystemPolicy
import "ApolloHubNetworkPolicy.js" as NetworkPolicy

// ApolloHubW live-data bridge. This owns NO weather fetch, subprocess,
// credentials, writable controls, or duplicate WeatherService instance.
// The shell/owner supplies existing WeatherService and SystemTelemetry objects.
// QML bindings keep the snapshot live when that provider changes.
Scope {
    id: bridge

    property var weatherSource: null
    property var systemSource: null
    // Optional reference to the existing Network dock, not another collector.
    property var networkDockSource: null

    // Read the same Quickshell.Networking singleton already used by
    // modules/Network.qml. No second nmcli/iw/ethtool loop, and no writes.
    readonly property var networkDevices:
        Networking.devices ? Networking.devices.values : []
    readonly property var wifiNetworkDevice:
        networkDevices.find(function(device) {
            return device && device.type === DeviceType.Wifi;
        }) || null
    readonly property var ethernetNetworkDevice:
        networkDevices.find(function(device) {
            return device && device.type === DeviceType.Ethernet;
        }) || null
    readonly property var activeWifiNetwork:
        wifiNetworkDevice && wifiNetworkDevice.networks
        ? wifiNetworkDevice.networks.values.find(function(network) {
            return network && network.connected === true;
        }) || null : null
    readonly property var networkSnapshot: NetworkPolicy.snapshot({
        devicesKnown: !!Networking.devices,
        wifiPresent: wifiNetworkDevice !== null,
        wifiConnected: wifiNetworkDevice !== null
                       && (wifiNetworkDevice.connected === true
                           || activeWifiNetwork !== null),
        wifiInterface: wifiNetworkDevice ? wifiNetworkDevice.name : "",
        wifiName: activeWifiNetwork ? activeWifiNetwork.name : "",
        wifiSignal: activeWifiNetwork ? activeWifiNetwork.signalStrength : null,
        ethernetPresent: ethernetNetworkDevice !== null,
        ethernetConnected: ethernetNetworkDevice !== null
                           && ethernetNetworkDevice.connected === true,
        ethernetInterface: ethernetNetworkDevice
                           ? ethernetNetworkDevice.name : "",
        wifiLinkSpeedMbps: networkDockSource
                           ? networkDockSource.observedWifiLinkMbps : -1
    })

    property double observationNowMs: Date.now()
    // Only observations completed AFTER attachment are known to be recent.
    property double systemObservedAtMs: 0

    onSystemSourceChanged: systemObservedAtMs = 0
    Connections {
        target: bridge.systemSource
        // Starting a new sample invalidates the previous live reading.
        function onLoadingChanged() {
            if (bridge.systemSource && bridge.systemSource.loading)
                bridge.systemObservedAtMs = 0;
        }
        function onRefreshed() {
            if (bridge.systemSource && !bridge.systemSource.loading
                    && !bridge.systemSource.errorText)
                bridge.systemObservedAtMs = Date.now();
        }
    }

    readonly property bool systemConnected: systemSource !== null
    readonly property bool systemLoading:
        systemConnected && systemSource.loading
    readonly property string systemError:
        systemConnected ? String(systemSource.errorText || "") : ""
    readonly property var systemRows:
        systemConnected && Array.isArray(systemSource.systemRows)
        ? systemSource.systemRows : []
    // Source rows are reduced to harmless scalar values. The existing
    // SystemTelemetry instance retains sole ownership of hardware collection.
    readonly property var systemSnapshot: SystemPolicy.snapshot(
        systemConnected, systemLoading, systemError, systemRows,
        systemObservedAtMs, observationNowMs)

    // Timestamp freshness must age even when the provider is quiet.
    // This is one cheap clock tick per minute, NOT network/service polling.
    onWeatherSourceChanged: observationNowMs = Date.now()
    Timer {
        interval: 60000
        repeat: true
        running: bridge.weatherSource !== null || bridge.systemSource !== null
        onTriggered: bridge.observationNowMs = Date.now()
    }

    readonly property bool weatherConnected: weatherSource !== null
    readonly property bool weatherLoading: weatherConnected && weatherSource.loading
    readonly property string weatherError:
        weatherConnected ? String(weatherSource.errorText || "") : ""
    readonly property double weatherUpdatedMs:
        weatherConnected && weatherSource.lastUpdated
        ? Number(weatherSource.lastUpdated.getTime()) : 0

    // Share the *existing* dock's freshness rule: max one hour old with
    // five minutes of forward-clock tolerance. Never present stale data as live.
    readonly property bool weatherFresh:
        weatherConnected && weatherSource.ready && weatherError === ""
        && WeatherPolicy.fresh(weatherUpdatedMs, observationNowMs)
    readonly property int weatherAgeMinutes:
        weatherUpdatedMs > 0 && observationNowMs >= weatherUpdatedMs
        ? Math.floor((observationNowMs - weatherUpdatedMs) / 60000) : -1

    readonly property string weatherState: {
        if (!weatherConnected) return "disconnected";
        if (weatherFresh) return "ready";
        if (weatherLoading) return "loading";
        if (weatherError !== "") return "error";
        if (weatherSource.ready) return "stale";
        return "unavailable";
    }

    // WeatherService stores Fahrenheit strings. Conversion is presentation-
    // only and reuses the Weather dock's formatter, never a second request.
    readonly property string temperatureF:
        WeatherPolicy.formatTemperature(
            weatherConnected ? weatherSource.tempF : null, weatherFresh, false)
    readonly property string temperatureC:
        WeatherPolicy.formatTemperature(
            weatherConnected ? weatherSource.tempF : null, weatherFresh, true)
    readonly property string feelsLikeF:
        WeatherPolicy.formatTemperature(
            weatherConnected ? weatherSource.feelsLikeF : null, weatherFresh, false)
    readonly property string feelsLikeC:
        WeatherPolicy.formatTemperature(
            weatherConnected ? weatherSource.feelsLikeF : null, weatherFresh, true)
    readonly property string condition:
        weatherFresh ? String(weatherSource.condition || "UNKNOWN") : "UNKNOWN"
    readonly property string humidity:
        weatherFresh ? String(weatherSource.humidity || "--") : "--"
    readonly property string windMph:
        weatherFresh ? String(weatherSource.windMph || "--") : "--"
    readonly property string windDirection:
        weatherFresh ? String(weatherSource.windDirection || "--") : "--"
    readonly property real uvIndex:
        weatherFresh && isFinite(Number(weatherSource.uvIndex))
        && Number(weatherSource.uvIndex) >= 0
        ? Number(weatherSource.uvIndex) : -1

    // Air quality has a separate update/error timeline. A successful
    // weather observation never implies AQI is available or healthy.
    readonly property string airQualityError:
        weatherConnected ? String(weatherSource.aqiErrorText || "") : ""
    readonly property double airQualityUpdatedMs:
        weatherConnected && weatherSource.aqiLastUpdated
        ? Number(weatherSource.aqiLastUpdated.getTime()) : 0
    readonly property bool airQualityFresh:
        weatherConnected && weatherSource.aqiReady && airQualityError === ""
        && WeatherPolicy.fresh(airQualityUpdatedMs, observationNowMs)
    readonly property string airQualityState: {
        if (!weatherConnected) return "disconnected";
        if (airQualityFresh) return "ready";
        if (weatherSource.aqiLoading) return "loading";
        if (airQualityError !== "") return "error";
        if (weatherSource.aqiReady) return "stale";
        return "unavailable";
    }
    readonly property int airQualityIndex:
        airQualityFresh && isFinite(Number(weatherSource.aqi))
        && Number(weatherSource.aqi) >= 0
        ? Math.round(Number(weatherSource.aqi)) : -1
    readonly property string airQualityLabel:
        airQualityFresh ? String(weatherSource.aqiLabel || "UNKNOWN") : "UNKNOWN"

    // Single consumer contract. Modules can bind to weatherSnapshot without
    // importing WeatherService or knowing its private fetch implementation.
    readonly property var weatherSnapshot: ({
        state: bridge.weatherState,
        connected: bridge.weatherConnected,
        loading: bridge.weatherLoading,
        fresh: bridge.weatherFresh,
        error: bridge.weatherError,
        updatedMs: bridge.weatherUpdatedMs,
        ageMinutes: bridge.weatherAgeMinutes,
        temperatureF: bridge.temperatureF,
        temperatureC: bridge.temperatureC,
        feelsLikeF: bridge.feelsLikeF,
        feelsLikeC: bridge.feelsLikeC,
        condition: bridge.condition,
        humidity: bridge.humidity,
        windMph: bridge.windMph,
        windDirection: bridge.windDirection,
        uvIndex: bridge.uvIndex,
        airQuality: {
            state: bridge.airQualityState,
            fresh: bridge.airQualityFresh,
            error: bridge.airQualityError,
            updatedMs: bridge.airQualityUpdatedMs,
            index: bridge.airQualityIndex,
            label: bridge.airQualityLabel
        }
    })
}
