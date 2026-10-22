import QtQuick
import Quickshell
import Quickshell.Networking
import Quickshell.Services.Mpris
import "../weather/WeatherDockPolicy.js" as WeatherPolicy
import "ApolloHubSystemPolicy.js" as SystemPolicy
import "ApolloHubNetworkPolicy.js" as NetworkPolicy
import "ApolloHubMediaPolicy.js" as MediaPolicy

// ApolloHubW live-data bridge. This owns NO weather fetch, subprocess,
// credentials, writable controls, or duplicate WeatherService instance.
// The shell/owner supplies existing WeatherService and SystemTelemetry objects.
// QML bindings keep the snapshot live when that provider changes.
Scope {
    id: bridge

    property var weatherSource: null
    property var systemSource: null

    // The B5 uptime reader lives in its own nonvisual read-only component.
    // Preserve bridge safety contracts: no filesystem or process API here.
    ApolloHubUptimeSource {
        id: uptimeSource
    }
    readonly property var uptimeSnapshot: uptimeSource.snapshot
    // Optional reference to the existing Network dock, not another collector.
    property var networkDockSource: null

    // Existing Hi-Fi controller/adapter instances are injected by their
    // owners. No second controller, player selection or CLI polling here.
    property var mediaControllerSource: null
    // The existing Media dock's MPD status observer remains operational even
    // when the full deck is closed. Read-only scalar observation only.
    property var mpdDockSource: null
    property string selectedMprisBusName: ""
    // A 2s dock reading can arrive AFTER the last 5s Hub clock tick.
    // Advance the projection clock on each complete, coherent observation,
    // otherwise knownAge() sees a future timestamp and falsely rejects it.
    onMpdDockSourceChanged: bridge.observationNowMs = Date.now()
    Connections {
        target: bridge.mpdDockSource
        function onHubMpdObservationChanged() {
            if (bridge.mpdDockSource && bridge.mpdDockSource.hubMpdObservation)
                bridge.observationNowMs = Date.now();
        }
    }
    property double mediaObservedAtMs: 0
    onMediaControllerSourceChanged: mediaObservedAtMs = 0
    Connections {
        target: bridge.mediaControllerSource
        function onSnapshotChanged() {
            // Search/selection can also change source.snapshot. Only a
            // successful controller snapshot response proves observation.
            if (bridge.mediaControllerSource
                    && bridge.mediaControllerSource.pendingAction === "snapshot"
                    && bridge.mediaControllerSource.errorText === "") {
                bridge.observationNowMs = Date.now();
                bridge.mediaObservedAtMs = bridge.observationNowMs;
            }
        }
    }

    // Atomic observation avoids separate state/title/timestamp notifications
    // being assembled into a hybrid status during a QML binding reevaluation.
    readonly property var dockMpdObservation:
        mpdDockSource ? mpdDockSource.hubMpdObservation : null
    readonly property var mpdSnapshot: MediaPolicy.mpdSnapshot(
        mediaControllerSource !== null,
        mediaControllerSource ? mediaControllerSource.snapshot : null,
        mediaControllerSource ? mediaControllerSource.errorText : "",
        mediaObservedAtMs, observationNowMs, bridge.dockMpdObservation)

    // MPRIS is an in-process Quickshell singleton. Playerctld is only a
    // repeater. No automatic player selection, even when exactly one exists.
    readonly property var mprisPlayers: Mpris.players.values.filter(function(p) {
        return p && p.dbusName
               && p.dbusName.indexOf("org.mpris.MediaPlayer2.playerctld") !== 0;
    })
    readonly property var selectedMprisPlayer: mprisPlayers.find(function(p) {
        return p.dbusName === bridge.selectedMprisBusName;
    }) || null
    readonly property var mprisSnapshot: MediaPolicy.mprisSnapshot({
        selectedBusName: selectedMprisBusName,
        playerCount: mprisPlayers.length,
        player: selectedMprisPlayer ? {
            identity: selectedMprisPlayer.identity,
            title: selectedMprisPlayer.trackTitle,
            artist: selectedMprisPlayer.trackArtist,
            album: selectedMprisPlayer.trackAlbum,
            playbackState:
                selectedMprisPlayer.playbackState === MprisPlaybackState.Playing
                ? "playing"
                : selectedMprisPlayer.playbackState === MprisPlaybackState.Paused
                  ? "paused"
                  : selectedMprisPlayer.playbackState === MprisPlaybackState.Stopped
                    ? "stopped" : "unknown"
        } : null
    })
    readonly property var mediaSnapshot: ({
        mpd: bridge.mpdSnapshot,
        mpris: bridge.mprisSnapshot
    })

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
                    && !bridge.systemSource.errorText) {
                // The sample may complete between minute-clock ticks.
                // Advance both timestamps together to avoid false staleness.
                bridge.observationNowMs = Date.now();
                bridge.systemObservedAtMs = bridge.observationNowMs;
            }
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
        // Clock-only freshness check; does not poll MPD, MPRIS or a CLI.
        interval: 5000
        repeat: true
        running: bridge.mediaControllerSource !== null || bridge.mpdDockSource !== null
        onTriggered: bridge.observationNowMs = Date.now()
    }
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
