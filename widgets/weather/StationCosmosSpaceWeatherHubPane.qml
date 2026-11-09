import QtQuick
import "../../components"
import "../../services/weather/WeatherRuntimePolicy.js" as RuntimePolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// COSMOS C4 // SPACE is a real directory of source-backed instruments.
// The original scrollable SPACE // ALL remains in INDEX unchanged.
Rectangle {
    id: spaceHub
    color: Colors.black
    clip: true

    property var spaceService: null
    property var weatherService: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0
    // The last COSMOS page is a summary + service report. Directory mode
    // preserves the previous eight instrument links without a separate page.
    property string viewMode: "dashboard"
    // Isolated native tests can inspect the presentation without NOAA calls.
    // Production defaults to true; only the displayed SPACE page owns feeds.
    property bool activateLiveFeeds: true
    property string selectedServiceId: "space-kp"
    // One pre-existing SPACE source owner, hidden visually, active only
    // while the SPACE end-page is mounted. No duplicate NOAA fetchers.
    StationSpace {
        id: statusOwner
        objectName: "cosmos-c42-source-only-space-owner"
        width: 1
        height: 1
        opacity: 0
        visible: spaceHub.visible && spaceHub.activateLiveFeeds
        sourceOnly: true
        subjectRoute: "cosmos/space-weather/full"
        spaceService: spaceHub.spaceService
        weatherService: spaceHub.weatherService
        liveHistoryStore: spaceHub.liveHistoryStore
        runtimeNowMs: spaceHub.runtimeNowMs
    }
    readonly property var runtimeRows: statusOwner.runtimeRows
    readonly property var runtimeSummary: RuntimePolicy.summarizeRows(runtimeRows)
    readonly property var currentRuntime: {
        const rows = runtimeRows || [];
        for (let i=0;i<rows.length;i++)
            if (rows[i].id === selectedServiceId) return rows[i];
        return rows.length ? rows[0] : null;
    }
    readonly property string serviceBrief: {
        const current = currentRuntime;
        if (!current) return "NO SERVICE RECORDS";
        const reports = statusOwner.runtimeBriefs || {};
        const brief = String(reports[current.id] || "");
        return brief !== "" ? brief
            : current.transport === "INACTIVE"
            ? "SOURCE INACTIVE // VIEW-SCOPED"
            : "NO CURRENT PROVIDER REPORT // " + RuntimePolicy.rowStateLabel(current);
    }
    function metricText(ready, value, digits, suffix) {
        return displayValue(ready, value, digits, suffix);
    }
    function statusColor(row) {
        switch (RuntimePolicy.statusToken(row)) {
        case "red": return Colors.red;
        case "yellow": return Colors.yellow;
        case "orange": return Colors.orange;
        case "magenta": return Colors.magenta;
        case "blue": return Colors.blue;
        case "green": return Colors.green;
        case "cyan": return Colors.cyan;
        default: return Colors.white;
        }
    }
    signal routeRequested(string path)

    function displayValue(ready, value, precision, suffix) {
        if (!ready || value === null || value === undefined
                || !isFinite(Number(value)))
            return "--";
        return Number(value).toFixed(precision) + suffix;
    }

    function availability(id, ready, loading, error, received, observed, cache) {
        const row = RuntimePolicy.displayRow(id, {
            active:true, ready:!!ready, loading:!!loading,
            errorText:error||"", receivedAt:received,
            observedAt:observed, usingCache:!!cache
        }, runtimeNowMs);
        return String(row.availability || "UNAVAILABLE").replace(/_/g," ");
    }

    readonly property var categories: [
        {title:"SOLAR WIND + IMF",
         value:displayValue(spaceService && spaceService.solarWindReady,
              spaceService ? spaceService.solarWindSpeed : null,0," KM/S"),
         detail:availability("space-wind",
             spaceService && spaceService.solarWindReady,
             spaceService && spaceService.solarWindLoading,
             spaceService ? spaceService.solarWindErrorText : "",
             spaceService ? spaceService.solarWindLastUpdated : null,
             spaceService ? spaceService.solarWindTime : null,
             spaceService && spaceService.usingPersistentSolarWindCache),
         route:"cosmos/space-weather/solar-wind",color:Colors.yellow},
        {title:"GEOMAGNETIC",
         value:"KP " + displayValue(spaceService && spaceService.kpReady,
              spaceService ? spaceService.kp : null,1,""),
         detail:availability("space-kp",
             spaceService && spaceService.kpReady,
             spaceService && spaceService.kpLoading,
             spaceService ? spaceService.kpErrorText : "",
             spaceService ? spaceService.kpLastUpdated : null,
             spaceService ? spaceService.kpTime : null,
             spaceService && spaceService.usingPersistentKpCache),
         route:"cosmos/space-weather/geomagnetic",color:Colors.cyan},
        {title:"AURORA // OVATION",
         value:"MODEL + LOCAL CELL",
         detail:"NOAA // OPEN TO LOAD FORECAST",
         route:"cosmos/space-weather/aurora",color:Colors.magenta},
        {title:"FORECASTS",
         value:"KP + STORM OUTLOOK",
         detail:"PREDICTIONS // OPEN NOAA MODEL",
         route:"cosmos/space-weather/forecasts",color:Colors.yellow},
        {title:"BULLETINS",
         value:"WATCHES + WARNINGS",
         detail:"PUBLISHED ALERTS // OPEN FEED",
         route:"cosmos/space-weather/bulletins",color:Colors.orange},
        {title:"HISTORY",
         value:"WIND / BZ / KP",
         detail:"OBSERVATION HISTORY // OPEN",
         route:"cosmos/space-weather/history",color:Colors.cyan},
        {title:"SUN // SOLAR ACTIVITY",
         value:displayValue(spaceService && spaceService.solarFluxReady,
              spaceService ? spaceService.solarFlux : null,0," SFU"),
         detail:"SUVI / X-RAY / FLARES / SOLAR CYCLE",
         route:"cosmos/sun/activity",color:Colors.orange},
        {title:"SPACE // ALL",
         value:"COMPLETE REFERENCE",
         detail:"ALL ORIGINAL NOAA INSTRUMENTS",
         route:"cosmos/space-weather/full",color:Colors.magenta}
    ]

    // C42 // Compact overview, all 11 true runtime states, and the
    // retained original directory. No whole-page scroll.
    Column {
        id: hubBody
        objectName: "cosmos-c42-space-dashboard"
        anchors.fill: parent
        anchors.margins: HeaderGeometry.inset
        spacing: HeaderGeometry.ruleToContent

        Row {
            id: mainHeader
            objectName: "cosmos-c44-space-title"
            width: parent.width
            height: HeaderGeometry.titleHeight
            spacing: 4
            GohuText {
                width: Math.max(1,parent.width-126)
                height: parent.height
                text: "COSMOS // SPACE WEATHER"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            QuietText {
                width: 122
                height: parent.height
                text: "READY // " + spaceHub.runtimeSummary.ready
                      + "/" + spaceHub.runtimeSummary.total
                color: Colors.cyan
                font.pixelSize: 9
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }
        Item {
            id: headerSpacer
            width: parent.width
            height: HeaderGeometry.columnHeaderGap()
        }
        Row {
            id: viewRail
            objectName: "cosmos-c42-space-view-modes"
            width: parent.width
            height: HeaderGeometry.tabHeight
            spacing: HeaderGeometry.tabSpacing
            Repeater {
                model: [
                    {label:"DASHBOARD",kind:"dashboard"},
                    {label:"DIRECTORY",kind:"directory"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: HeaderGeometry.buttonWidth(viewRail.width,2)
                    height: HeaderGeometry.tabHeight
                    label: modelData.label
                    labelPixelSize: 9
                    contentPadding: 0
                    selected: spaceHub.viewMode === modelData.kind
                    accentColor: Colors.cyan
                    onClicked: spaceHub.viewMode = modelData.kind
                }
            }
        }
        Item {
            id: dividerSlot
            objectName: "cosmos-c44-space-divider-slot"
            width: parent.width
            height: HeaderGeometry.columnRuleSlotHeight()
            Rectangle {
                objectName: "cosmos-c44-space-divider"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: HeaderGeometry.ruleHeight
                color: Colors.cyan
            }
        }
        Row {
            id: metrics
            objectName: "cosmos-c42-space-metrics"
            visible: spaceHub.viewMode === "dashboard"
            width: parent.width
            height: visible ? 34 : 0
            spacing: 3
            readonly property var values: [
                {label:"KP",value:spaceHub.metricText(
                    spaceHub.spaceService && spaceHub.spaceService.kpReady,
                    spaceHub.spaceService ? spaceHub.spaceService.kp : null,1,"")},
                {label:"WIND",value:spaceHub.metricText(
                    spaceHub.spaceService && spaceHub.spaceService.solarWindReady,
                    spaceHub.spaceService ? spaceHub.spaceService.solarWindSpeed : null,
                    0," KM/S")},
                {label:"BZ // IMF",value:spaceHub.metricText(
                    spaceHub.spaceService && spaceHub.spaceService.magneticFieldReady,
                    spaceHub.spaceService ? spaceHub.spaceService.magneticFieldBz : null,
                    1," nT")},
                {label:"F10.7",value:spaceHub.metricText(
                    spaceHub.spaceService && spaceHub.spaceService.solarFluxReady,
                    spaceHub.spaceService ? spaceHub.spaceService.solarFlux : null,
                    0," SFU")}
            ]
            Repeater {
                model: metrics.values
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(metrics.width-3*metrics.spacing)/4)
                    height: metrics.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 1
                        QuietText {
                            width: parent.width
                            height: 10
                            text: modelData.label
                            color: Colors.cyan
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            height: 17
                            text: modelData.value
                            color: Colors.white
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
        Item {
            id: serviceArea
            objectName: "cosmos-c42-space-services"
            visible: spaceHub.viewMode !== "directory"
            width: parent.width
            height: visible ? Math.max(1,hubBody.height
                - mainHeader.height - headerSpacer.height
                - viewRail.height - dividerSlot.height
                - metrics.height - serviceReport.height - footer.height
                - 7*hubBody.spacing) : 0
            Column {
                anchors.fill: parent
                spacing: 2
                Row {
                    width: parent.width
                    height: 14
                    QuietText {
                        width: parent.width*0.46
                        height: parent.height
                        text: "SERVICES " + spaceHub.runtimeSummary.total
                            + " // READY " + spaceHub.runtimeSummary.ready
                            + " // STALE " + spaceHub.runtimeSummary.stale
                        font.pixelSize: 8
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                    QuietText {
                        width: parent.width*0.54
                        height: parent.height
                        text: "FRESHNESS // RX / OBS // CADENCE"
                        font.pixelSize: 8
                        color: Colors.cyan
                        horizontalAlignment: Text.AlignRight
                        elide: Text.ElideRight
                    }
                }
                Item {
                    id: runtimeList
                    objectName: "cosmos-c42-runtime-rows"
                    width: parent.width
                    height: Math.max(1,serviceArea.height-16)
                    Column {
                        anchors.fill: parent
                        spacing: 0
                        Repeater {
                            model: spaceHub.runtimeRows
                            delegate: Rectangle {
                                id: runtimeItem
                                required property var modelData
                                width: runtimeList.width
                                height: Math.max(1,runtimeList.height
                                    / Math.max(1,spaceHub.runtimeRows.length))
                                color: spaceHub.selectedServiceId === modelData.id
                                    ? Colors.dark : Colors.black
                                border.width: 1
                                border.color: spaceHub.selectedServiceId === modelData.id
                                    ? Colors.magenta : Colors.blue
                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: 3
                                    anchors.rightMargin: 3
                                    spacing: 3
                                    GohuText {
                                        width: Math.max(1,parent.width*0.32)
                                        height: parent.height
                                        verticalAlignment: Text.AlignVCenter
                                        text: runtimeItem.modelData.label
                                        font.pixelSize: 8
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        width: Math.max(1,parent.width*0.25)
                                        height: parent.height
                                        verticalAlignment: Text.AlignVCenter
                                        text: RuntimePolicy.rowStateLabel(runtimeItem.modelData)
                                        font.pixelSize: 8
                                        color: spaceHub.statusColor(runtimeItem.modelData)
                                        elide: Text.ElideRight
                                    }
                                    SecondaryText {
                                        width: Math.max(1,parent.width*0.27)
                                        height: parent.height
                                        verticalAlignment: Text.AlignVCenter
                                        text: RuntimePolicy.rowAgeLabel(runtimeItem.modelData)
                                        font.pixelSize: 8
                                        elide: Text.ElideRight
                                    }
                                    QuietText {
                                        width: Math.max(1,parent.width*0.12)
                                        height: parent.height
                                        verticalAlignment: Text.AlignVCenter
                                        text: RuntimePolicy.cadenceLabel(runtimeItem.modelData)
                                        horizontalAlignment: Text.AlignRight
                                        color: Colors.cyan
                                        font.pixelSize: 8
                                        elide: Text.ElideRight
                                    }
                                }
                                TapHandler {
                                    onTapped: spaceHub.selectedServiceId =
                                        runtimeItem.modelData.id
                                }
                                HoverHandler {
                                    cursorShape: Qt.PointingHandCursor
                                }
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            id: serviceReport
            objectName: "cosmos-c42-selected-service-report"
            visible: spaceHub.viewMode !== "directory"
            width: parent.width
            height: visible ? 38 : 0
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta
            Column {
                anchors.fill: parent
                anchors.margins: 3
                spacing: 2
                QuietText {
                    width: parent.width
                    height: 11
                    text: "REPORT // "
                        + (spaceHub.currentRuntime ? spaceHub.currentRuntime.label : "--")
                        + " // " + (spaceHub.currentRuntime
                            ? RuntimePolicy.rowAgeLabel(spaceHub.currentRuntime) : "RX --")
                    color: Colors.magenta
                    font.pixelSize: 8
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    height: 12
                    text: spaceHub.serviceBrief
                    color: Colors.white
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
            }
        }
        Item {
            id: directoryArea
            objectName: "cosmos-c42-space-directory"
            visible: spaceHub.viewMode === "directory"
            width: parent.width
            height: visible ? Math.max(1,hubBody.height
                - mainHeader.height - headerSpacer.height
                - viewRail.height - dividerSlot.height - footer.height
                - 5*hubBody.spacing) : 0
            Grid {
                id: cardsGrid
                anchors.fill: parent
                columns: 2
                rowSpacing: 4
                columnSpacing: 4
                Repeater {
                    model: spaceHub.categories
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(1,(cardsGrid.width-cardsGrid.columnSpacing)/2)
                        height: Math.max(1,(cardsGrid.height-3*cardsGrid.rowSpacing)/4)
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.color
                        Column {
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 2
                            GohuText {
                                width: parent.width
                                height: 12
                                text: modelData.title
                                font.pixelSize: 9
                                color: modelData.color
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width
                                height: 15
                                text: modelData.value
                                font.pixelSize: 12
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                            QuietText {
                                width: parent.width
                                height: 13
                                text: modelData.detail
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                        TapHandler {
                            onTapped: spaceHub.routeRequested(modelData.route)
                        }
                        HoverHandler {
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }
        }
        QuietText {
            id: footer
            width: parent.width
            height: 12
            text: spaceHub.viewMode === "directory"
                ? "ORIGINAL INSTRUMENT ROUTES // CLICK TILE FOR SOURCE DETAIL"
                : "RX = LOCAL RECEIVE AGE // OBS = PROVIDER SAMPLE AGE // SELECT A SERVICE FOR ITS REPORT"
            font.pixelSize: 8
            color: Colors.cyan
            elide: Text.ElideRight
        }
    }
}
