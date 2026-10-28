import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "../../services/weather/SolarCyclePolicy.js" as SolarCyclePolicy
import "StationSolarImagePolicy.js" as SolarImagePolicy

Rectangle {
    id: space

    property var spaceService: null

    property string solarImageMode: "195"
    property string solarImageUrl: ""
    property double solarImageLastLoadedMs: 0
    property string solarImageError: ""
    readonly property var solarImageInfo:
        SolarImagePolicy.modeInfo(solarImageMode)
    readonly property bool solarImageReady:
        solarImage.status === Image.Ready
    readonly property bool solarImageLoading:
        solarImage.status === Image.Loading

    // OVATION's gridded model fetch exists only while SPACE is instantiated.
    WeatherServices.AuroraService {
        id: auroraService
        active: space.visible
    }

    WeatherServices.SolarFlareService {
        id: flareService
        active: space.visible
    }

    WeatherServices.XrayFluxService {
        id: xrayService
        active: space.visible
    }

    WeatherServices.SwpcAlertService {
        id: alertService
        active: space.visible
    }

    WeatherServices.SolarCycleService {
        id: solarCycleService
        active: space.visible
    }

    function bulletinColor(kind) {
        if (kind === "ALERT")
            return Colors.magenta;
        if (kind === "WARNING")
            return Colors.orange;
        if (kind === "WATCH")
            return Colors.yellow;
        if (kind === "CANCELLATION")
            return Colors.cyan;
        return Colors.white;
    }

    // Event classes are measured GOES X-ray peaks, not alert severity.
    function flareClassColor(letter) {
        if (letter === "X")
            return Colors.magenta;
        if (letter === "M")
            return Colors.orange;
        if (letter === "C")
            return Colors.yellow;
        if (letter === "B")
            return Colors.cyan;
        return Colors.white;
    }

    readonly property bool spaceReady: spaceService && spaceService.ready
    readonly property bool spaceLoading: spaceService && spaceService.loading

    readonly property real kpValue:
        spaceService && spaceService.kp >= 0 ? Number(spaceService.kp) : 0
    readonly property var kpHistory:
        spaceService && Array.isArray(spaceService.kpHistory)
        ? spaceService.kpHistory : []
    readonly property var kpHistorySummary:
        spaceService ? spaceService.kpHistorySummary
                     : ({
                           bins: 0, hours: 0, maxKp: -1, averageKp: -1,
                           activeBins: 0, stormBins: 0, latestDelta: 0,
                           latestA: -1, latestStationCount: -1,
                           minStationCount: -1
                       })
    readonly property real solarWindValue:
        spaceService && spaceService.solarWindSpeed >= 0
        ? Number(spaceService.solarWindSpeed) : 0
    readonly property real bzValue:
        spaceService && spaceService.magneticFieldReady
        ? Number(spaceService.magneticFieldBz) : 0
    readonly property real btValue:
        spaceService && spaceService.magneticFieldReady
        ? Number(spaceService.magneticFieldBt) : -1
    readonly property real solarFluxValue:
        spaceService && spaceService.solarFlux >= 0
        ? Number(spaceService.solarFlux) : 0

    // Normalized live NOAA telemetry scales preserved from the original page.
    readonly property real kpMeter:
        Math.max(0, Math.min(1, kpValue / 9))
    readonly property real solarWindMeter:
        Math.max(0, Math.min(1, solarWindValue / 1000))
    readonly property real bzMeter:
        Math.max(0, Math.min(1, Math.abs(bzValue) / 20))
    readonly property real btMeter:
        Math.max(0, Math.min(1, btValue / 20))
    readonly property real solarFluxMeter:
        Math.max(0, Math.min(1, solarFluxValue / 300))

    readonly property color kpColor: {
        if (!spaceService || !spaceService.kpReady)
            return Colors.white;
        if (kpValue < 4)
            return Colors.cyan;
        if (kpValue < 5)
            return Colors.yellow;
        if (kpValue < 6)
            return Colors.orange;
        return Colors.red;
    }

    function kpHistoryColor(value) {
        const reading = Number(value);
        if (!isFinite(reading) || reading < 0)
            return Colors.white;
        if (reading < 4)
            return Colors.cyan;
        if (reading < 5)
            return Colors.yellow;
        if (reading < 6)
            return Colors.orange;
        return Colors.red;
    }

    function signedKpDelta(value) {
        const reading = Number(value);
        if (!isFinite(reading))
            return "--";
        return (reading > 0 ? "+" : "") + reading.toFixed(2);
    }

    readonly property color solarWindColor: {
        if (!spaceService || !spaceService.solarWindReady)
            return Colors.white;
        if (solarWindValue < 500)
            return Colors.cyan;
        if (solarWindValue < 650)
            return Colors.yellow;
        if (solarWindValue < 800)
            return Colors.orange;
        return Colors.red;
    }

    readonly property color bzColor: {
        if (!spaceService || !spaceService.magneticFieldReady)
            return Colors.white;
        if (bzValue <= -10)
            return Colors.red;
        if (bzValue <= -5)
            return Colors.orange;
        if (bzValue < 0)
            return Colors.yellow;
        return Colors.cyan;
    }

    function shortSampleTime(value) {
        const text = String(value || "");
        if (text.length === 0)
            return "--";

        return text.replace("T", " ").replace("Z", "").slice(5, 16);
    }

    function solarCycleReceiveLabel() {
        if (!solarCycleService.lastUpdated
                || typeof solarCycleService.lastUpdated.getTime !== "function")
            return "--";
        const millis = solarCycleService.lastUpdated.getTime();
        if (!isFinite(millis) || millis <= 0)
            return "--";
        const iso = new Date(millis).toISOString();
        return iso.slice(5, 10) + " " + iso.slice(11, 16) + "Z";
    }

    function solarImageReceiveLabel() {
        if (solarImageLastLoadedMs <= 0)
            return "--";
        const iso = new Date(solarImageLastLoadedMs).toISOString();
        return iso.slice(5, 10) + " " + iso.slice(11, 16) + "Z";
    }

    function refreshSolarImage() {
        solarImageError = "";
        solarImageUrl = "";
        Qt.callLater(function() {
            space.solarImageUrl = SolarImagePolicy.imageUrl(
                space.solarImageMode,
                Date.now()
            );
        });
    }

    function selectSolarImageMode(mode) {
        const next = SolarImagePolicy.cleanMode(mode);
        if (solarImageMode === next && solarImageUrl !== "")
            return;
        solarImageMode = next;
        refreshSolarImage();
    }

    Timer {
        id: solarImageRefreshClock
        interval: 300000
        repeat: true
        running: space.visible
        onTriggered: space.refreshSolarImage()
    }

    Component.onCompleted: refreshSolarImage()

    readonly property color meterBorderColor: Colors.cyan
    readonly property color meterFillColor: Colors.magenta

    color: Colors.black

    // Compact observatory view: promote the existing NOAA readings without
    // introducing another refresh, provider, or invented severity scale.
    // The original instruments stay in place. Scroll SPACE itself if the
    // new model forecast extends beyond the station's fixed-height viewport.
    Flickable {
        id: spaceScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, spaceContent.y + spaceContent.implicitHeight + 12)

        Column {
            id: spaceContent
            x: 20
            y: 12
            width: Math.max(0, spaceScroll.width - 40)
            spacing: 10

            Row {
            width: parent.width

            GohuText {
                text: "✦  SPACE"
                font.pixelSize: 24
                color: Colors.magenta
            }

            Item {
                width: parent.width - 315
                height: 1
            }

            GohuText {
                text: space.spaceReady
                      ? "SPACE WEATHER ONLINE"
                      : space.spaceLoading
                        ? "RECEIVING"
                        : "OFFLINE"
                font.pixelSize: 12
                color: space.spaceReady ? Colors.cyan : Colors.orange
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR // GEOMAGNETIC"
        }

        Row {
            width: parent.width
            spacing: 14

            Rectangle {
                id: kpInstrument
                width: 236
                height: 184
                color: Colors.dark
                border.width: 1
                border.color: space.meterBorderColor

                SecondaryText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.margins: 12
                    text: "PLANETARY // KP INDEX"
                    font.pixelSize: 11
                }

                // Glow behind the live Kp value, respecting the established
                // warning palette and the SafeDropShadow teardown behavior.
                SafeDropShadow {
                    anchors.fill: kpHeroReading
                    safeSource: kpHeroReading
                    requestedVisible: spaceService && spaceService.kpReady
                    radius: 11
                    samples: 21
                    horizontalOffset: 0
                    verticalOffset: 0
                    transparentBorder: true
                    opacity: 0.72
                    color: space.kpColor
                }

                GohuText {
                    id: kpHeroReading
                    anchors.top: parent.top
                    anchors.topMargin: 29
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: spaceService ? spaceService.kpText : "--"
                    font.pixelSize: 74
                    color: space.kpColor
                }

                GohuText {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: kpTrack.top
                    anchors.bottomMargin: 11
                    text: spaceService ? spaceService.kpLabel : "OFFLINE"
                    font.pixelSize: 12
                    color: space.kpColor
                }

                Rectangle {
                    id: kpTrack
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    height: 9
                    color: Colors.black
                    border.width: 1
                    border.color: space.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.kpMeter
                        height: parent.height - 4
                        color: space.meterFillColor
                    }
                }
            }

            Row {
                width: Math.max(0, parent.width - kpInstrument.width - parent.spacing)
                spacing: 14

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "SOLAR WIND"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? spaceService.solarWindText : "-- KM/S"
                        font.pixelSize: 28
                        color: space.solarWindColor
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.solarWindMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    QuietText {
                        text: "STREAM SPEED"
                        font.pixelSize: 10
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "IMF BZ"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService ? spaceService.bzText : "-- nT"
                        font.pixelSize: 28
                        color: space.bzColor
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.bzMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    GohuText {
                        width: parent.width
                        text: spaceService ? spaceService.bzLabel : "OFFLINE"
                        font.pixelSize: 11
                        color: space.bzColor
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 2 * parent.spacing) / 3)
                    spacing: 9

                    SecondaryText {
                        text: "F10.7 FLUX"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? spaceService.solarFluxText : "-- SFU"
                        font.pixelSize: 28
                        color: Colors.white
                    }

                    Rectangle {
                        width: parent.width - 10
                        height: 9
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4) * space.solarFluxMeter
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }

                    QuietText {
                        text: "10.7 CM RADIO FLUX"
                        font.pixelSize: 10
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR CYCLE // NOAA MONTHLY PREDICTION"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 10

                GohuText {
                    text: solarCycleService.loading
                          ? "RECEIVING"
                          : solarCycleService.failed
                            ? (solarCycleService.ready
                               ? "DEGRADED" : "OFFLINE")
                            : solarCycleService.ready
                              ? "MODEL READY"
                              : "WAITING"
                    font.pixelSize: 10
                    color: solarCycleService.failed
                           ? Colors.orange
                           : solarCycleService.ready
                             ? Colors.cyan : Colors.white
                }

                QuietText {
                    width: Math.max(0, parent.width - 230)
                    text: solarCycleService.ready
                          ? "LOCAL RECEIVE "
                            + space.solarCycleReceiveLabel()
                            + " // " + solarCycleService.summary.rowCount
                            + " MODEL MONTHS"
                          : "NOAA SWPC // PREDICTED SOLAR CYCLE JSON"
                    elide: Text.ElideRight
                    font.pixelSize: 9
                }

                ActionButton {
                    width: 112
                    height: 30
                    label: "REFRESH"
                    labelPixelSize: 10
                    available: !solarCycleService.loading
                    onClicked: solarCycleService.refresh(true)
                }
            }

            Row {
                width: parent.width
                spacing: 10
                visible: solarCycleService.ready

                Repeater {
                    model: [
                        {
                            "title": "MODEL SSN // "
                                     + solarCycleService.summary.modelMonth,
                            "value":
                                SolarCyclePolicy.numberText(
                                    solarCycleService.summary.predictedSsn, 1
                                ),
                            "detail":
                                solarCycleService.summary.exactMonth
                                ? "TARGET MONTH // "
                                  + solarCycleService.summary.targetMonth
                                : "NEAREST AVAILABLE // TARGET "
                                  + solarCycleService.summary.targetMonth,
                            "accent": Colors.magenta
                        },
                        {
                            "title": "SSN RANGE",
                            "value":
                                solarCycleService.summary.ssnRangeValid
                                ? SolarCyclePolicy.rangeText(
                                      solarCycleService.summary.lowSsn,
                                      solarCycleService.summary.highSsn,
                                      1
                                  )
                                : "INVALID",
                            "detail": "PUBLISHED LOW–HIGH",
                            "accent":
                                solarCycleService.summary.ssnRangeValid
                                ? Colors.cyan : Colors.orange
                        },
                        {
                            "title": "MODEL F10.7",
                            "value":
                                SolarCyclePolicy.numberText(
                                    solarCycleService.summary.predictedFlux, 1
                                ) + " SFU",
                            "detail":
                                solarCycleService.summary.fluxRangeValid
                                ? "RANGE "
                                  + SolarCyclePolicy.rangeText(
                                        solarCycleService.summary.lowFlux,
                                        solarCycleService.summary.highFlux,
                                        1
                                    ) + " SFU"
                                : "SOURCE RANGE INVALID",
                            "accent":
                                solarCycleService.summary.fluxRangeValid
                                ? Colors.yellow : Colors.orange
                        },
                        {
                            "title": "CURVE PEAK",
                            "value":
                                SolarCyclePolicy.numberText(
                                    solarCycleService.summary.peakPredictedSsn,
                                    1
                                ),
                            "detail":
                                solarCycleService.summary.peakMonth !== ""
                                ? solarCycleService.summary.peakMonth
                                : "MONTH --",
                            "accent": Colors.orange
                        }
                    ]

                    delegate: StationHomeMetricCard {
                        required property var modelData
                        width: (spaceContent.width - 3 * 10) / 4
                        height: 88
                        title: modelData.title
                        valueText: modelData.value
                        detailText: modelData.detail
                        accentColor: modelData.accent
                        valueColor: Colors.white
                        meterVisible: false
                    }
                }
            }

            QuietText {
                visible: solarCycleService.ready
                         && !solarCycleService.summary.exactMonth
                width: parent.width
                text: "NO EXACT MODEL ROW FOR CURRENT UTC MONTH // SHOWING "
                      + solarCycleService.summary.modelMonth
                      + " // NOT RELABELED AS CURRENT"
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                visible: solarCycleService.ready
                         && (!solarCycleService.summary.ssnRangeValid
                             || !solarCycleService.summary.fluxRangeValid)
                width: parent.width
                text: "NOAA PUBLISHED AN INVALID LOW/HIGH RANGE // POINT ESTIMATE RETAINED // RANGE NOT REPAIRED"
                font.pixelSize: 9
                color: Colors.orange
            }

            Row {
                width: parent.width
                spacing: 16
                visible: solarCycleService.ready

                GohuText {
                    text: "LIVE F10.7 // "
                          + (spaceService
                             ? spaceService.solarFluxText : "-- SFU")
                    font.pixelSize: 11
                    color: Colors.cyan
                }

                QuietText {
                    text:
                        solarCycleService.summary.nextMonth !== ""
                        ? "NEXT MODEL // "
                          + solarCycleService.summary.nextMonth
                          + " // SSN "
                          + SolarCyclePolicy.numberText(
                                solarCycleService.summary.nextPredictedSsn, 1
                            )
                        : "NEXT MODEL // --"
                    font.pixelSize: 9
                }
            }

            QuietText {
                visible: solarCycleService.failed
                width: parent.width
                text: solarCycleService.errorText
                font.pixelSize: 9
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                text: "MONTHLY PREDICTION CURVE // LIVE F10.7 ABOVE IS A SEPARATE OBSERVATION WITH A DIFFERENT CADENCE // NOT A MODEL-ERROR CALCULATION"
                font.pixelSize: 9
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "GEOMAGNETIC // KP 72-HOUR HISTORY"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 10

                Repeater {
                    model: [
                        {
                            "title": "MAX // 72H",
                            "value": space.kpHistorySummary.maxKp >= 0
                                     ? space.kpHistorySummary.maxKp.toFixed(2)
                                     : "--",
                            "detail": "HIGHEST PUBLISHED BIN"
                        },
                        {
                            "title": "AVG // 72H",
                            "value": space.kpHistorySummary.averageKp >= 0
                                     ? space.kpHistorySummary.averageKp.toFixed(2)
                                     : "--",
                            "detail": "24 × 3H WINDOW"
                        },
                        {
                            "title": "ACTIVE / STORM",
                            "value": space.kpHistorySummary.activeBins
                                     + " / "
                                     + space.kpHistorySummary.stormBins,
                            "detail": "KP≥4 / KP≥5 BINS"
                        },
                        {
                            "title": "LATEST // Δ",
                            "value": space.signedKpDelta(
                                space.kpHistorySummary.latestDelta
                            ),
                            "detail": space.kpHistorySummary.latestStationCount >= 0
                                      ? "A "
                                        + space.kpHistorySummary.latestA
                                        + " // STATIONS "
                                        + space.kpHistorySummary.latestStationCount
                                      : "A -- // STATIONS --"
                        }
                    ]

                    delegate: StationHomeMetricCard {
                        required property var modelData
                        width: (spaceContent.width - 3 * 10) / 4
                        height: 88
                        title: modelData.title
                        valueText: modelData.value
                        detailText: modelData.detail
                        accentColor: Colors.magenta
                        valueColor: Colors.white
                        meterVisible: false
                    }
                }
            }

            Row {
                id: kpHistoryBars
                width: parent.width
                height: 92
                spacing: 3

                Repeater {
                    model: space.kpHistory

                    delegate: Column {
                        required property var modelData
                        width: (kpHistoryBars.width
                                - 23 * kpHistoryBars.spacing) / 24
                        height: parent.height
                        spacing: 3

                        Item {
                            width: parent.width
                            height: 68

                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                width: Math.max(5, parent.width - 5)
                                height: 4 + 60 * modelData.level
                                color: space.kpHistoryColor(modelData.kp)
                                opacity: 0.9
                            }
                        }

                        QuietText {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: index % 4 === 0
                                  ? modelData.timeLabel.slice(6, 9)
                                  : ""
                            font.pixelSize: 7
                        }
                    }
                }
            }

            Row {
                width: parent.width

                QuietText {
                    text: space.kpHistory.length > 0
                          ? "START "
                            + space.kpHistory[0].timeLabel
                          : "START -- UTC"
                    font.pixelSize: 9
                }

                Item {
                    width: Math.max(0, parent.width - 330)
                    height: 1
                }

                QuietText {
                    text: space.kpHistory.length > 0
                          ? "LATEST "
                            + space.kpHistory[
                                space.kpHistory.length - 1
                              ].timeLabel
                          : "LATEST -- UTC"
                    font.pixelSize: 9
                }
            }

            QuietText {
                width: parent.width
                text: "NOAA PLANETARY K-INDEX // 3-HOUR PUBLISHED BINS // SAME EXISTING 5-MIN FETCH // NO NEW REQUEST"
                font.pixelSize: 9
                color: Colors.cyan
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "FIELD // SOURCE TIMES"
        }

        Row {
            width: parent.width
            spacing: 14

            Column {
                width: 180
                spacing: 6

                SecondaryText {
                    text: "IMF BT"
                    font.pixelSize: 11
                }

                GohuText {
                    text: space.btValue >= 0
                          ? space.btValue.toFixed(1) + " nT"
                          : "-- nT"
                    font.pixelSize: 30
                    color: Colors.white
                }

                Rectangle {
                    width: 158
                    height: 9
                    color: Colors.black
                    border.width: 1
                    border.color: space.meterBorderColor

                    Rectangle {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: (parent.width - 4) * space.btMeter
                        height: parent.height - 4
                        color: space.meterFillColor
                    }
                }

                QuietText {
                    text: "TOTAL FIELD"
                    font.pixelSize: 10
                }
            }

            Row {
                width: Math.max(0, parent.width - 180 - parent.spacing)
                spacing: 10

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "KP SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.kpTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "WIND SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.solarWindTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "IMF SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(
                                    spaceService.magneticFieldTime
                                )
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 3 * parent.spacing) / 4)
                    spacing: 6

                    SecondaryText {
                        text: "FLUX SAMPLE"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: spaceService
                              ? space.shortSampleTime(spaceService.solarFluxTime)
                              : "--"
                        font.pixelSize: 12
                        color: Colors.cyan
                    }
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR IMAGER // NOAA SWPC SUVI"
        }

        Row {
            width: parent.width
            height: 342
            spacing: 14

            Rectangle {
                width: 342
                height: 342
                color: Colors.dark
                border.width: 1
                border.color: space.solarImageReady
                              ? Colors.magenta : Colors.cyan
                clip: true

                Image {
                    id: solarImage
                    anchors.fill: parent
                    anchors.margins: 4
                    source: space.solarImageUrl
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: false
                    smooth: true

                    onStatusChanged: {
                        if (status === Image.Ready) {
                            space.solarImageLastLoadedMs = Date.now();
                            space.solarImageError = "";
                        } else if (status === Image.Error) {
                            space.solarImageError =
                                "SUVI IMAGE LOAD FAILED";
                        }
                    }
                }

                GohuText {
                    anchors.centerIn: parent
                    visible: space.solarImageLoading
                             || space.solarImageUrl === ""
                    text: space.solarImageUrl === ""
                          ? "PREPARING SUVI"
                          : "RECEIVING SUVI"
                    font.pixelSize: 12
                    color: Colors.orange
                }

                GohuText {
                    anchors.centerIn: parent
                    visible: solarImage.status === Image.Error
                    text: "IMAGE UNAVAILABLE"
                    font.pixelSize: 12
                    color: Colors.orange
                }
            }

            Column {
                width: Math.max(0, parent.width - 342 - parent.spacing)
                height: parent.height
                spacing: 10

                Row {
                    width: parent.width
                    spacing: 8

                    ModeButton {
                        width: 132
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected: space.solarImageMode === "195"
                        labelText: "195 Å"
                        labelFontSize: 10
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            space.selectSolarImageMode("195")
                    }

                    ModeButton {
                        width: 154
                        height: 32
                        textOnly: true
                        horizontalContent: true
                        bordered: false
                        selected: space.solarImageMode === "map"
                        labelText: "THERMAL MAP"
                        labelFontSize: 10
                        idlePrimaryColor: Colors.cyan
                        selectedPrimaryColor: Colors.magenta
                        perimeterGlowColor: Colors.orange
                        onTriggered:
                            space.selectSolarImageMode("map")
                    }

                    ActionButton {
                        width: 104
                        height: 30
                        label: "REFRESH"
                        labelPixelSize: 10
                        available: !space.solarImageLoading
                        onClicked: space.refreshSolarImage()
                    }
                }

                GohuText {
                    width: parent.width
                    text: space.solarImageInfo.title
                    elide: Text.ElideRight
                    font.pixelSize: 18
                    color: Colors.white
                }

                SecondaryText {
                    width: parent.width
                    text: space.solarImageInfo.detail
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                }

                Rectangle {
                    width: parent.width
                    height: 92
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 5

                        GohuText {
                            text: "NOAA SWPC // SUVI PRIMARY"
                            font.pixelSize: 11
                            color: Colors.cyan
                        }

                        QuietText {
                            text: "LATEST ENDPOINT // ONE SELECTED IMAGE"
                            font.pixelSize: 9
                        }

                        QuietText {
                            text: "LOCAL RECEIVE // "
                                  + space.solarImageReceiveLabel()
                            font.pixelSize: 9
                        }

                        QuietText {
                            text: space.solarImageError !== ""
                                  ? space.solarImageError
                                  : space.solarImageLoading
                                    ? "SOURCE // RECEIVING"
                                    : space.solarImageReady
                                      ? "SOURCE // IMAGE READY"
                                      : "SOURCE // WAITING"
                            font.pixelSize: 9
                            color: space.solarImageError !== ""
                                   ? Colors.orange : Colors.white
                        }
                    }
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "195 Å // WARM CORONAL PLASMA FOR GLOBAL STRUCTURE, ACTIVE REGIONS + CORONAL HOLES"
                    font.pixelSize: 9
                    color: Colors.magenta
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "THERMAL MAP // NOAA SWPC SUVI TEMPERATURE-MAP PRODUCT // DISPLAY IMAGE, NOT A LOCAL TEMPERATURE READING"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "5-MIN VIEW-SCOPED REFRESH // NO FRAME ARCHIVE // LOCAL RECEIVE TIME IS NOT SPACECRAFT OBSERVATION TIME"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "AURORA // 30-90 MIN FORECAST"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 228
                    height: 122
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "BOREALIS // NORTH PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 28
                        text: auroraService.ready
                              ? Math.round(auroraService.northPeak) + "%" : "--%"
                        font.pixelSize: 39
                        color: auroraService.forecastFresh
                               ? Colors.magenta : Colors.white
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4)
                                   * (auroraService.ready
                                      ? auroraService.northPeak / 100 : 0)
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }
                }

                Rectangle {
                    width: 228
                    height: 122
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "AUSTRALIS // SOUTH PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 28
                        text: auroraService.ready
                              ? Math.round(auroraService.southPeak) + "%" : "--%"
                        font.pixelSize: 39
                        color: auroraService.forecastFresh
                               ? Colors.magenta : Colors.white
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4)
                                   * (auroraService.ready
                                      ? auroraService.southPeak / 100 : 0)
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }
                }

                Column {
                    width: Math.max(0, parent.width - 456 - 2 * parent.spacing)
                    spacing: 8

                    SecondaryText {
                        text: "MODEL VALID // UTC"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: auroraService.ready
                              ? auroraService.forecastLabel : "-- UTC"
                        font.pixelSize: 17
                        color: Colors.white
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: auroraService.failed
                              ? "FETCH ERROR // LAST DATA"
                              : auroraService.loading && !auroraService.ready
                                ? "RECEIVING"
                                : auroraService.forecastFresh
                                  ? "MODEL CURRENT"
                                  : auroraService.ready ? "MODEL STALE"
                                    : "UNAVAILABLE"
                        font.pixelSize: 11
                        color: auroraService.forecastFresh
                               ? Colors.cyan : Colors.orange
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "OBS " + (auroraService.ready
                                       ? auroraService.observationLabel : "-- UTC")
                        font.pixelSize: 10
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "NOAA OVATION GRID // HIGHEST CELL PER HEMISPHERE // NOT LOCAL VISIBILITY"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR // LIVE X-RAY FLUX"
        }

        Column {
            width: parent.width
            spacing: 7

            Row {
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 225
                    height: 142
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "LONG BAND // 0.1-0.8 NM"
                        font.pixelSize: 11
                    }

                    GohuText {
                        id: xrayEquivalentReading
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 33
                        text: xrayService.ready
                              ? xrayService.classEquivalent.label : "--"
                        font.pixelSize: 39
                        color: xrayService.sampleFresh
                               ? space.flareClassColor(
                                     xrayService.classEquivalent.letter
                                 ) : Colors.white
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 30
                        text: xrayService.ready
                              ? xrayService.fluxLong.toExponential(2) + " W/m²"
                              : "-- W/m²"
                        font.pixelSize: 12
                        color: Colors.white
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 10
                        height: 8
                        color: Colors.black
                        border.width: 1
                        border.color: space.meterBorderColor

                        Rectangle {
                            x: 2
                            anchors.verticalCenter: parent.verticalCenter
                            width: (parent.width - 4)
                                   * (xrayService.ready
                                      ? Math.max(0, Math.min(1,
                                          (Math.log(xrayService.fluxLong)
                                           / Math.LN10 + 9) / 5))
                                      : 0)
                            height: parent.height - 4
                            color: space.meterFillColor
                        }
                    }
                }

                Column {
                    width: 194
                    spacing: 8

                    SecondaryText {
                        text: "SHORT BAND // 0.05-0.4 NM"
                        font.pixelSize: 11
                    }

                    GohuText {
                        text: xrayService.ready && xrayService.fluxShort > 0
                              ? xrayService.fluxShort.toExponential(2)
                              : "--"
                        font.pixelSize: 21
                        color: Colors.white
                    }

                    QuietText {
                        text: "W/m² // PRIMARY GOES"
                        font.pixelSize: 10
                    }

                    GohuText {
                        text: xrayService.ready ? xrayService.satellite : "--"
                        font.pixelSize: 13
                        color: Colors.cyan
                    }

                    QuietText {
                        text: "SAMPLE " + (xrayService.ready
                                          ? xrayService.sampleUtc : "-- UTC")
                        font.pixelSize: 10
                    }

                    GohuText {
                        text: xrayService.failed
                              ? (xrayService.ready
                                 ? "FETCH FAILED // LAST DATA"
                                 : "FETCH FAILED // NO DATA")
                              : xrayService.loading && !xrayService.ready
                                ? "RECEIVING"
                                : xrayService.sampleFresh ? "SAMPLE CURRENT"
                                  : xrayService.ready ? "SAMPLE STALE"
                                    : "UNAVAILABLE"
                        font.pixelSize: 11
                        color: xrayService.sampleFresh
                               ? Colors.cyan : Colors.orange
                    }
                }

                Column {
                    width: Math.max(0, parent.width - 225 - 194
                                    - 2 * parent.spacing)
                    spacing: 5

                    SecondaryText {
                        text: "LONG BAND // LAST 6 HOURS"
                        font.pixelSize: 11
                    }

                    Item {
                        width: parent.width
                        height: 83

                        Row {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            spacing: 4

                            Repeater {
                                model: xrayService.ready ? xrayService.trend : []

                                delegate: Rectangle {
                                    required property var modelData
                                    width: Math.max(5, (parent.width
                                                       - 11 * parent.spacing) / 12)
                                    height: 5 + 58 * modelData.level
                                    color: space.flareClassColor(
                                               modelData.classLetter
                                           )
                                    opacity: xrayService.sampleFresh ? 1 : 0.45
                                }
                            }
                        }
                    }

                    QuietText {
                        text: "30-MIN SAMPLES // LOG SCALE"
                        font.pixelSize: 9
                    }
                }
            }

            QuietText {
                width: parent.width
                text: "GOES XRS // 1-MIN OBSERVATIONS // FLUX-CLASS EQUIVALENT, NOT A FLARE ALERT"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SOLAR // GOES X-RAY FLARES"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 14

                Rectangle {
                    width: 235
                    height: 125
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "LATEST DETECTED // PEAK"
                        font.pixelSize: 11
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 30
                        text: flareService.ready && flareService.latest
                              ? flareService.latest.classLabel : "--"
                        font.pixelSize: 36
                        color: flareService.ready && flareService.latest
                               ? space.flareClassColor(flareService.latest.classLetter)
                               : Colors.white
                    }

                    QuietText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        text: flareService.ready && flareService.latest
                              ? flareService.latest.peakUtc : "PEAK TIME --"
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    width: 235
                    height: 125
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    SecondaryText {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: "OBSERVED // LAST 24H"
                        font.pixelSize: 11
                    }

                    Row {
                        anchors.top: parent.top
                        anchors.topMargin: 36
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 14

                        Column {
                            spacing: 6

                            GohuText {
                                text: flareService.ready
                                      ? String(flareService.count24h) : "--"
                                font.pixelSize: 30
                                color: Colors.cyan
                            }

                            QuietText {
                                text: "ALL"
                                font.pixelSize: 10
                            }
                        }

                        Column {
                            spacing: 6

                            GohuText {
                                text: flareService.ready
                                      ? String(flareService.cPlus24h) : "--"
                                font.pixelSize: 30
                                color: Colors.yellow
                            }

                            QuietText {
                                text: "C / M / X"
                                font.pixelSize: 10
                            }
                        }
                    }
                }

                Column {
                    width: Math.max(0, parent.width - 470 - 2 * parent.spacing)
                    spacing: 8

                    SecondaryText {
                        text: "EVENT FEED // NOAA GOES"
                        font.pixelSize: 11
                    }

                    GohuText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: flareService.failed
                              ? (flareService.ready
                                 ? "REQUEST FAILED // SAVED EVENTS"
                                 : "REQUEST FAILED // NO DATA")
                              : flareService.loading && !flareService.ready
                                ? "RECEIVING"
                                : flareService.ready ? "EVENTS RECEIVED"
                                  : "UNAVAILABLE"
                        font.pixelSize: 12
                        color: flareService.failed ? Colors.orange
                               : flareService.ready ? Colors.cyan : Colors.white
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: flareService.ready
                              ? "FETCHED "
                                + Qt.formatDateTime(flareService.lastUpdated, "hh:mm")
                                + " LOCAL"
                              : "--"
                        font.pixelSize: 10
                    }

                    QuietText {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "EVENT PEAKS // NOT LIVE X-RAY FLUX"
                        font.pixelSize: 10
                    }
                }
            }

            Row {
                id: flareEventRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: flareService.ready ? flareService.events : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (flareEventRow.width
                                            - 2 * flareEventRow.spacing) / 3)
                        height: 102
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 5

                            Row {
                                spacing: 10

                                GohuText {
                                    text: modelData.classLabel
                                    font.pixelSize: 21
                                    color: space.flareClassColor(modelData.classLetter)
                                }

                                QuietText {
                                    text: modelData.satellite
                                    font.pixelSize: 10
                                }
                            }

                            GohuText {
                                text: "PEAK " + modelData.peakUtc
                                font.pixelSize: 11
                                color: Colors.white
                            }

                            QuietText {
                                text: modelData.ended ? "END REPORTED" : "END NOT REPORTED"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !flareService.ready || flareService.events.length === 0
                text: flareService.failed ? flareService.errorText
                      : flareService.loading ? "LOADING GOES EVENTS"
                      : flareService.ready ? "NO VALID FLARE PEAKS IN 7-DAY FEED"
                        : "GOES DATA UNAVAILABLE"
                font.pixelSize: 11
            }

            QuietText {
                width: parent.width
                text: "GOES XRS // LAST 7D EVENTS // OBSERVATIONS, NOT ALERTS OR PREDICTIONS"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "GEOMAGNETIC // WATCH-DAY OUTLOOK"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 16

                SecondaryText {
                    text: "NOAA // UTC FORECAST DAYS"
                    font.pixelSize: 11
                }

                GohuText {
                    text: alertService.ready && alertService.fresh
                          && alertService.watchForecast.forecastDayCount > 0
                          ? String(alertService.watchForecast.projectedDays)
                            + " G1+ DAYS FORECAST"
                          : "-- G1+ DAYS"
                    font.pixelSize: 11
                    color: Colors.yellow
                }

                QuietText {
                    text: alertService.ready
                          ? String(alertService.watchForecast.unresolvedCount)
                            + " UNPARSED WATCH ITEMS"
                          : "FORECAST PENDING"
                    font.pixelSize: 10
                }
            }

            Row {
                id: watchForecastRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: alertService.ready && alertService.fresh
                           ? alertService.watchForecast.days : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (watchForecastRow.width
                                            - 2 * watchForecastRow.spacing) / 3)
                        height: 116
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.level >= 3 ? Colors.magenta
                                      : modelData.level >= 2 ? Colors.orange
                                        : modelData.level >= 1 ? Colors.yellow
                                          : Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 7

                            Row {
                                width: parent.width
                                spacing: 8

                                GohuText {
                                    text: modelData.dateUtc
                                    font.pixelSize: 12
                                    color: Colors.white
                                }

                                GohuText {
                                    text: modelData.levelLabel
                                    font.pixelSize: 15
                                    color: modelData.level >= 3 ? Colors.magenta
                                           : modelData.level >= 2 ? Colors.orange
                                             : modelData.level >= 1 ? Colors.yellow
                                               : Colors.cyan
                                }
                            }

                            GohuText {
                                width: parent.width
                                height: 33
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                text: modelData.subject
                                font.pixelSize: 11
                                color: Colors.white
                            }

                            QuietText {
                                text: modelData.productId + " // WATCH FORECAST"
                                font.pixelSize: 10
                            }

                            QuietText {
                                text: "NOT OBSERVED STORM"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !alertService.ready || !alertService.fresh
                         || alertService.watchForecast.forecastDayCount === 0
                width: parent.width
                text: !alertService.ready
                      ? "WAITING FOR NOAA WATCH PRODUCTS"
                      : !alertService.fresh
                        ? "WATCH OUTLOOK STALE // FORECAST HIDDEN"
                        : "NO CURRENT WATCH-DAY PRODUCTS FOUND // NOT AN ALL CLEAR"
                font.pixelSize: 11
            }

            QuietText {
                width: parent.width
                text: "NOAA WATCH FORECAST // SUPERSESSION + CANCELLATION // NOT AN ALL CLEAR"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "NOAA // WARNING VALIDITY REVIEW"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 16

                SecondaryText {
                    text: "EXPLICIT VALIDITY WINDOWS"
                    font.pixelSize: 11
                }

                GohuText {
                    text: alertService.ready
                          ? String(alertService.validity.windowCount)
                            + " OPEN // NOT VERIFIED ACTIVE"
                          : "-- OPEN"
                    font.pixelSize: 11
                    color: alertService.fresh ? Colors.yellow : Colors.orange
                }

                QuietText {
                    text: alertService.ready
                          ? String(alertService.validity.uncertainCount)
                            + " UNRESOLVED IN WARNING REVIEW"
                          : "ASSESSMENT PENDING"
                    font.pixelSize: 10
                }
            }

            Row {
                id: warningWindowRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: alertService.ready && alertService.fresh
                           ? alertService.validity.windows : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (warningWindowRow.width
                                            - 2 * warningWindowRow.spacing) / 3)
                        height: 108
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.yellow

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6

                            GohuText {
                                text: "WINDOW OPEN // " + modelData.productId
                                font.pixelSize: 12
                                color: Colors.yellow
                            }

                            GohuText {
                                width: parent.width
                                height: 36
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                                text: modelData.subject
                                font.pixelSize: 11
                                color: Colors.white
                            }

                            QuietText {
                                text: "UNTIL " + modelData.untilUtc
                                font.pixelSize: 10
                            }

                            QuietText {
                                text: "VERIFY WITH NOAA"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !alertService.ready || !alertService.fresh
                         || alertService.validity.windowCount === 0
                width: parent.width
                text: !alertService.ready
                      ? "WAITING FOR NOAA BULLETIN FEED"
                      : !alertService.fresh
                        ? "REVIEW STALE // DO NOT INFER CURRENT WARNING STATUS"
                        : "NO OPEN EXPLICIT WARNING WINDOWS FOUND // NOT AN ALL CLEAR"
                font.pixelSize: 11
            }

            QuietText {
                width: parent.width
                text: "SWPC WARNING WINDOW CHECK // CANCELLATIONS + EXTENSIONS // NOT ACTIVE STATUS"
                font.pixelSize: 10
            }
        }

        StationSectionDivider {
            width: parent.width
            title: "SPACE WEATHER // NOAA BULLETINS"
        }

        Column {
            width: parent.width
            spacing: 8

            Row {
                width: parent.width
                spacing: 16

                SecondaryText {
                    text: "OFFICIAL WATCHES // WARNINGS // ALERTS"
                    font.pixelSize: 11
                }

                GohuText {
                    text: alertService.ready
                          ? String(alertService.count48h) + " ISSUED // 48H"
                          : "-- ISSUED // 48H"
                    font.pixelSize: 11
                    color: Colors.cyan
                }

                GohuText {
                    text: alertService.failed
                          ? (alertService.ready
                             ? "FETCH FAILED // SAVED ITEMS"
                             : "FETCH FAILED // NO DATA")
                          : alertService.loading && !alertService.ready
                            ? "RECEIVING"
                            : alertService.fresh
                              ? "FEED CURRENT"
                              : alertService.ready ? "FEED STALE"
                                : "UNAVAILABLE"
                    font.pixelSize: 11
                    color: alertService.fresh ? Colors.cyan : Colors.orange
                }
            }

            Row {
                id: bulletinRow
                width: parent.width
                spacing: 10

                Repeater {
                    model: alertService.ready ? alertService.bulletins : []

                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0, (bulletinRow.width
                                            - 2 * bulletinRow.spacing) / 3)
                        height: 140
                        color: Colors.dark
                        border.width: 1
                        border.color: space.bulletinColor(modelData.kind)

                        Column {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 7

                            Row {
                                width: parent.width
                                spacing: 8

                                GohuText {
                                    text: modelData.kind
                                    font.pixelSize: 14
                                    color: space.bulletinColor(modelData.kind)
                                }

                                GohuText {
                                    text: modelData.scale !== ""
                                          ? modelData.scale : ""
                                    font.pixelSize: 14
                                    color: Colors.white
                                }
                            }

                            GohuText {
                                width: parent.width
                                height: 46
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 3
                                text: modelData.subject
                                font.pixelSize: 12
                                color: Colors.white
                            }

                            QuietText {
                                text: "ISSUED " + modelData.issueUtc
                                font.pixelSize: 10
                            }

                            QuietText {
                                text: modelData.productId
                                      + (modelData.code !== ""
                                         ? " // " + modelData.code : "")
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            QuietText {
                visible: !alertService.ready || alertService.bulletins.length === 0
                text: alertService.failed ? alertService.errorText
                      : alertService.loading ? "LOADING NOAA BULLETINS"
                      : alertService.ready ? "NO NEW NOAA BULLETINS IN 48H"
                        : "NOAA BULLETIN FEED UNAVAILABLE"
                font.pixelSize: 11
            }

            QuietText {
                width: parent.width
                text: "NOAA SWPC // RECENT ISSUED BULLETINS // NOT NECESSARILY ACTIVE"
                font.pixelSize: 10
            }
        }

        QuietText {
            text: "NOAA SWPC // FOUR LIVE PRODUCTS // INDEPENDENT SAMPLE TIMES"
            font.pixelSize: 11
        }
        }
    }

    NeonScrollBar {
        flickable: spaceScroll
        handleStyle: "star"
        geometryHost: space
        visible: scrollable
    }
}
