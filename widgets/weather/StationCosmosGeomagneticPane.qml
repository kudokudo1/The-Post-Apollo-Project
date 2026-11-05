import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy

// COSMOS C4 // Kp and its NOAA storm context, without the unrelated
// solar-wind/flux hero from the original mixed SPACE // ALL report.
Rectangle {
    id: geomagnetic
    color: Colors.black
    clip: true

    property var spaceService: null
    property var weatherService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    function kpReading() {
        if (!spaceService || !spaceService.kpReady
                || !isFinite(Number(spaceService.kp))
                || Number(spaceService.kp) < 0)
            return "--";
        return Number(spaceService.kp).toFixed(1);
    }

    readonly property string kpAvailability: {
        const row = RuntimePolicy.displayRow("space-kp",{
            active:true,
            ready:spaceService && spaceService.kpReady,
            loading:spaceService && spaceService.kpLoading,
            errorText:spaceService ? spaceService.kpErrorText : "",
            receivedAt:spaceService ? spaceService.kpLastUpdated : null,
            observedAt:spaceService ? spaceService.kpTime : null,
            usingCache:spaceService
                && spaceService.usingPersistentKpCache
        },runtimeNowMs);
        return String(row.availability || "UNAVAILABLE").replace(/_/g," ");
    }

    Row {
        id: kpHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        height: 82
        spacing: 12

        Rectangle {
            width: 135
            height: 77
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            Column {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3
                SecondaryText {
                    text: "PLANETARY // KP"
                    font.pixelSize: 10
                }
                GohuText {
                    text: geomagnetic.kpReading()
                    color: Colors.white
                    font.pixelSize: 29
                }
            }
        }
        Column {
            width: Math.max(1,kpHeader.width-135-kpHeader.spacing-115)
            spacing: 6
            GohuText {
                text: "GEOMAGNETIC // LIVE + HISTORY"
                color: Colors.magenta
                font.pixelSize: 12
                width: parent.width
                elide: Text.ElideRight
            }
            QuietText {
                text: geomagnetic.kpAvailability
                color: Colors.cyan
                font.pixelSize: 10
            }
            QuietText {
                text: "NOAA PUBLISHED KP // 3-HOUR BINS"
                font.pixelSize: 9
            }
        }
        ActionButton {
            width: 115
            height: 29
            label: "SPACE // ALL"
            labelPixelSize: 10
            onClicked: geomagnetic.routeRequested("cosmos/space-weather/full")
        }
    }

    StationSpace {
        anchors.top: kpHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        subjectRoute: "cosmos/space-weather/geomagnetic"
        spaceService: geomagnetic.spaceService
        weatherService: geomagnetic.weatherService
        liveHistoryStore: geomagnetic.liveHistoryStore
        runtimeNowMs: geomagnetic.runtimeNowMs
    }
}
