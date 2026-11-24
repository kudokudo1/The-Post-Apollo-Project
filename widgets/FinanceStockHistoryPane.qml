import QtQuick
import "../components"
import "FinanceStockModePolicy.js" as StockModePolicy
import "FinanceStockChartPointPolicy.js" as ChartPointPolicy
import "FinanceStockRangeAnalysisPolicy.js" as RangeAnalysisPolicy

// Market STOCKS M14: one-step BACK TO RANGE restores previously loaded chart.
Item {
    id: stocks
    property var stockFeed: null
    property bool discoveryOpen: false
    property bool quotaOpen: false
    onVisibleChanged: {
        if (!visible) {
            discoveryOpen = false;
            quotaOpen = false;
        }
    }
    readonly property var snapshot: stockFeed && stockFeed.ready
        ? stockFeed.snapshot : null
    readonly property var priceBars: snapshot && Array.isArray(snapshot.bars)
        ? snapshot.bars : []
    readonly property bool dayMode: stockFeed && stockFeed.displayMode === "day"
    readonly property var dayResult: dayMode && snapshot
        ? StockModePolicy.daySession(snapshot, stockFeed.dayDate) : null
    property int selectedPointIndex: -1
    // M30: a private in-memory pin, tied to the exact loaded snapshot object.
    // Never save a bare index across range, issuer, date or mode transitions.
    property int pinnedPointIndex: -1
    property var pinnedSnapshot: null
    property var savedIntervalSnapshot: null
    property int savedIntervalA: -1
    property int savedIntervalB: -1
    // M28: local session-only display choice; never changes provider readers.
    property bool showAverages: false
    readonly property var inspectedPoint: !dayMode
        ? ChartPointPolicy.selectedBar(priceBars, selectedPointIndex) : null
    // M26: recompute locally only from the current, loaded RANGE snapshot.
    // No QML service, provider request, local file, timer or persistent state.
    readonly property var rangeAnalysis: !dayMode && snapshot
        && stockFeed && snapshot.cik === stockFeed.selectedCik
        && snapshot.from === stockFeed.startDate
        && snapshot.to === stockFeed.endDate
        ? RangeAnalysisPolicy.summarizeRange(snapshot) : null
    readonly property var averageOverlay: !dayMode && showAverages
        && priceBars.length >= 5 && rangeAnalysis !== null
        ? RangeAnalysisPolicy.movingAverageSeries(snapshot) : null
    // M29: descriptive SMA5/SMA20 relationship for the loaded RANGE only.
    readonly property var averageRelationship: averageOverlay !== null
        ? RangeAnalysisPolicy.movingAverageRelationship(snapshot) : null
    onShowAveragesChanged: priceCanvas.requestPaint()
    onAverageOverlayChanged: priceCanvas.requestPaint()
    // M27: selected chart session to LAST LOADED range session, never now.
    // Follows existing point/issuer/date invalidation and spends no API call.
    readonly property var selectedCloseComparison: rangeAnalysis !== null
        && selectedPointIndex >= 0
        ? RangeAnalysisPolicy.compareSelectedToLast(snapshot, selectedPointIndex)
        : null
    readonly property bool pinValid: !dayMode && rangeAnalysis !== null
        && pinnedSnapshot !== null && pinnedSnapshot === snapshot
        && pinnedPointIndex >= 0 && pinnedPointIndex < priceBars.length
    readonly property var pinnedPoint: pinValid
        ? ChartPointPolicy.selectedBar(priceBars, pinnedPointIndex) : null
    readonly property var pinnedPairComparison: pinValid
        && selectedPointIndex >= 0
        && selectedPointIndex !== pinnedPointIndex
        ? RangeAnalysisPolicy.comparePinnedRangeSessions(
            snapshot, pinnedPointIndex, selectedPointIndex) : null
    // M31: the real closing-price path between the two M30 chart choices.
    // Reuses exact snapshot/selection validity; no data access or new state.
    readonly property var pinnedInterval: pinnedPairComparison !== null
        ? RangeAnalysisPolicy.summarizePinnedInterval(
            snapshot, pinnedPointIndex, selectedPointIndex) : null

    readonly property bool savedIntervalValid: rangeAnalysis !== null
        && savedIntervalSnapshot !== null && savedIntervalSnapshot === snapshot
    onSavedIntervalValidChanged: {
        if (!savedIntervalValid) clearSavedInterval();
    }
    readonly property var intervalComparison: savedIntervalValid && pinnedInterval !== null
        ? RangeAnalysisPolicy.compareHistoricalIntervals(snapshot, savedIntervalA,
            savedIntervalB, pinnedPointIndex, selectedPointIndex) : null
    // M34: use the existing same-snapshot A/B comparison validity.
    readonly property var normalizedComparison: intervalComparison !== null
        ? RangeAnalysisPolicy.normalizedIntervalChart(snapshot, savedIntervalA,
            savedIntervalB, pinnedPointIndex, selectedPointIndex) : null
    function clearSavedInterval() {
        savedIntervalSnapshot = null;
        savedIntervalA = -1;
        savedIntervalB = -1;
    }
    function saveCurrentInterval() {
        if (pinnedInterval === null) return;
        savedIntervalA = pinnedPointIndex;
        savedIntervalB = selectedPointIndex;
        savedIntervalSnapshot = snapshot;
    }
    function clearPinnedComparison() {
        pinnedPointIndex = -1;
        pinnedSnapshot = null;
    }
    function pinCurrentPoint() {
        if (dayMode || rangeAnalysis === null || inspectedPoint === null)
            return;
        pinnedSnapshot = snapshot;
        pinnedPointIndex = selectedPointIndex;
    }
    onSnapshotChanged: clearPinnedComparison()
    onRangeAnalysisChanged: {
        if (rangeAnalysis === null) clearPinnedComparison();
    }
    onPinnedPointIndexChanged: priceCanvas.requestPaint()
    onPinValidChanged: priceCanvas.requestPaint()

    function inspectChartPoint(x, y) {
        if (dayMode || !snapshot || priceBars.length < 2
                || priceCanvas.width < 5 || priceCanvas.height < 5)
            return;
        const index = ChartPointPolicy.nearestPoint(priceBars,
            priceCanvas.width, priceCanvas.height, x, y, 18);
        // Tapping the selected point again, or empty chart area, clears it.
        selectedPointIndex = index === selectedPointIndex ? -1 : index;
    }
    onPriceBarsChanged: {
        selectedPointIndex = -1;
        clearSavedInterval();
        clearPinnedComparison();
        priceCanvas.requestPaint();
    }
    onDayModeChanged: {
        clearSavedInterval();
        selectedPointIndex = -1;
        clearPinnedComparison();
        priceCanvas.requestPaint();
    }
    onSelectedPointIndexChanged: priceCanvas.requestPaint()

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.right: discoveryToggle.left
        anchors.rightMargin: 7
        text: "STOCKS // HISTORICAL DAILY PRICES"
        color: Colors.cyan
        font.pixelSize: 13
        font.bold: true
        elide: Text.ElideRight
    }
    ActionButton {
        id: discoveryToggle
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: quotaToggle.left
        anchors.rightMargin: 6
        width: 121
        height: 28
        label: "GLOBAL SEARCH"
        labelPixelSize: 9
        accentColor: Colors.magenta
        onLeftClicked: {
            stocks.quotaOpen = false;
            stocks.discoveryOpen = true;
        }
    }
    ActionButton {
        id: quotaToggle
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        width: 112
        height: 28
        label: "QUOTA STATUS"
        labelPixelSize: 9
        accentColor: Colors.orange
        onLeftClicked: {
            stocks.discoveryOpen = false;
            stocks.quotaOpen = true;
        }
    }
    Grid {
        id: issuers
        anchors.top: title.bottom
        anchors.topMargin: 13
        anchors.left: parent.left
        anchors.right: parent.right
        columns: width >= 590 ? 6 : 3
        height: columns === 6 ? 30 : 62
        columnSpacing: 6
        rowSpacing: 6
        Repeater {
            model: StockModePolicy.stockItems()
            delegate: ActionButton {
                required property var modelData
                width: Math.max(0, (issuers.width - (issuers.columns - 1) * 6)
                    / issuers.columns)
                height: 28
                label: modelData.symbol
                labelPixelSize: 10
                selected: stocks.stockFeed
                    && stocks.stockFeed.selectedCik === modelData.cik
                accentColor: Colors.cyan
                onLeftClicked: {
                    if (stocks.stockFeed)
                        stocks.stockFeed.selectIssuer(modelData.cik);
                }
            }
        }
    }

    Row {
        id: modeControls
        anchors.top: issuers.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28
        spacing: 6
        ActionButton {
            width: 92
            height: 27
            label: "DAY"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: stocks.dayMode
            available: stocks.stockFeed && !stocks.stockFeed.loading
            onLeftClicked: {
                if (stocks.stockFeed) stocks.stockFeed.selectMode("day");
            }
        }
        ActionButton {
            width: 92
            height: 27
            label: "RANGE"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: !stocks.dayMode
            available: stocks.stockFeed && !stocks.stockFeed.loading
            onLeftClicked: {
                if (stocks.stockFeed) stocks.stockFeed.selectMode("range");
            }
        }
    }
    Row {
        id: rangePresets
        anchors.top: modeControls.bottom
        anchors.topMargin: visible ? 8 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !stocks.dayMode
        height: visible ? 27 : 0
        spacing: 6
        Repeater {
            model: [
                {days:7,label:"7D"},
                {days:30,label:"30D"},
                {days:90,label:"90D"},
                {days:180,label:"180D"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(0, (rangePresets.width - 18) / 4)
                height: 26
                label: modelData.label
                labelPixelSize: 10
                accentColor: Colors.cyan
                selected: stocks.stockFeed
                    && stocks.stockFeed.rangeDays === modelData.days - 1
                    && stocks.stockFeed.endDate === stocks.stockFeed.dateOffset(0)
                available: stocks.stockFeed && stocks.stockFeed.monitoring
                    && !stocks.stockFeed.loading
                onLeftClicked: {
                    if (stocks.stockFeed)
                        stocks.stockFeed.selectPresetRange(modelData.days);
                }
            }
        }
    }
    GohuText {
        id: dateLabel
        anchors.top: rangePresets.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.right: parent.right
        text: stocks.dayMode
            ? "SINGLE DAY // WEEKENDS/HOLIDAYS MAY HAVE NO SESSION"
            : "HISTORICAL RANGE // INCLUSIVE // MAX 180 DAYS"
        font.pixelSize: 10
        color: Colors.orange
    }
    Item {
        id: dateControls
        anchors.top: dateLabel.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        readonly property bool sideBySide: width >= 640
        height: stocks.dayMode ? 66 : (sideBySide ? 66 : 136)
        Column {
            id: dayGroup
            visible: stocks.dayMode
            anchors.left: parent.left
            anchors.top: parent.top
            width: parent.width
            spacing: 4
            GohuText {
                text: "DAY DATE"
                font.pixelSize: 9
                color: Colors.cyan
            }
            FinanceDateInput {
                width: parent.width
                height: 48
                value: stocks.stockFeed ? stocks.stockFeed.dayDate : ""
                fallbackDate: stocks.stockFeed ? stocks.stockFeed.dayDate : ""
                canEdit: !!stocks.stockFeed && !stocks.stockFeed.loading
                onValueEdited: function(value) {
                    if (stocks.stockFeed) stocks.stockFeed.selectDayDate(value);
                }
            }
        }
        Column {
            id: fromGroup
            visible: !stocks.dayMode
            anchors.top: parent.top
            anchors.left: parent.left
            width: dateControls.sideBySide ? (dateControls.width-12)/2 : dateControls.width
            spacing: 4
            GohuText {
                text: "START DATE"
                font.pixelSize: 9
                color: Colors.cyan
            }
            FinanceDateInput {
                width: parent.width
                height: 48
                value: stocks.stockFeed ? stocks.stockFeed.startDate : ""
                fallbackDate: stocks.stockFeed ? stocks.stockFeed.startDate : ""
                canEdit: !!stocks.stockFeed && !stocks.stockFeed.loading
                onValueEdited: function(value) {
                    if(stocks.stockFeed) stocks.stockFeed.selectStartDate(value);
                }
            }
        }
        Column {
            visible: !stocks.dayMode
            anchors.top: dateControls.sideBySide ? parent.top : fromGroup.bottom
            anchors.topMargin: dateControls.sideBySide ? 0 : 8
            anchors.left: dateControls.sideBySide ? fromGroup.right : parent.left
            anchors.leftMargin: dateControls.sideBySide ? 12 : 0
            width: dateControls.sideBySide ? (dateControls.width-12)/2 : dateControls.width
            spacing: 4
            GohuText {
                text: "END DATE"
                font.pixelSize: 9
                color: Colors.cyan
            }
            FinanceDateInput {
                width: parent.width
                height: 48
                value: stocks.stockFeed ? stocks.stockFeed.endDate : ""
                fallbackDate: stocks.stockFeed ? stocks.stockFeed.endDate : ""
                canEdit: !!stocks.stockFeed && !stocks.stockFeed.loading
                onValueEdited: function(value) {
                    if(stocks.stockFeed) stocks.stockFeed.selectEndDate(value);
                }
            }
        }
    }
    Row {
        id: fetchControls
        anchors.top: dateControls.bottom
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.right: parent.right
        height: 30
        spacing: 8
        ActionButton {
            id: load
            width: 122
            height: 28
            label: stocks.stockFeed && stocks.stockFeed.loading ? "READING"
                : stocks.dayMode
                    ? (stocks.snapshot ? "REFRESH DAY" : "LOAD DAY")
                    : (stocks.snapshot ? "REFRESH RANGE" : "LOAD RANGE")
            labelPixelSize: 9
            accentColor: Colors.magenta
            available: stocks.stockFeed && stocks.stockFeed.monitoring
                && stocks.stockFeed.validSelection && !stocks.stockFeed.loading
            onLeftClicked: {
                if (stocks.stockFeed) stocks.stockFeed.refresh();
            }
        }
        GohuText {
            width: Math.max(0,fetchControls.width - load.width - 8)
            height: fetchControls.height
            verticalAlignment: Text.AlignVCenter
            text: stocks.stockFeed
                ? stocks.stockFeed.selectedCik === "0001045810"
                    ? "NVDA // TOKEN REQUIRED"
                  : stocks.stockFeed.selectedCik === "0000789019"
                    ? "MSFT // DEMO TRIAL"
                  : stocks.stockFeed.selectedCik === "0000320193"
                    ? "AAPL // DEMO"
                    : StockModePolicy.stockSymbol(stocks.stockFeed.selectedCik)
                      + " // TOKEN REQUIRED"
                : "NO STOCK SOURCE"
            font.pixelSize: 9
            color: Colors.orange
            elide: Text.ElideRight
        }
    }
    GohuText {
        id: status
        anchors.top: fetchControls.bottom
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.right: parent.right
        text: stocks.stockFeed ? stocks.stockFeed.message
            : "STOCK HISTORY SOURCE UNAVAILABLE"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: stocks.stockFeed && stocks.stockFeed.state === "failed"
            ? Colors.red : Colors.orange
        wrapMode: Text.WordWrap
    }
    Flickable {
        id: scroll
        anchors.top: status.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: body
            // Reserve an unobstructed right gutter for the proportional rail.
            width: Math.max(0, scroll.width - 24)
            spacing: 13
            GohuText {
                width: parent.width
                text: stocks.dayMode
                    ? "Choose a calendar day and LOAD DAY. Weekends and market holidays may return NO TRADING SESSION."
                    : "Select an issuer and START/END dates, or choose 7D/30D/90D/180D ending today. Then LOAD RANGE. Only actual trading sessions appear."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                visible: !!stocks.snapshot
                text: stocks.snapshot
                    ? stocks.snapshot.symbol + " // " + stocks.snapshot.priceBasis
                        + " // SOURCE EODHD EOD"
                        + "\nPATH " + stocks.snapshot.delivery.via + " // "
                            + stocks.snapshot.delivery.state
                        + "\nSERVED " + stocks.snapshot.delivery.servedAt
                        + (stocks.snapshot.delivery.cachedAt
                            ? "\nCACHED " + stocks.snapshot.delivery.cachedAt : "")
                        + (stocks.snapshot.derivedFromRange
                            ? "\nDAY SOURCE // PREVIOUSLY LOADED RANGE // NO NEW REQUEST"
                            : "")
                        + (stocks.snapshot.restoredFromDay
                            ? "\nRANGE SOURCE // RESTORED FROM MEMORY // NO NEW REQUEST"
                            : "")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: !!stocks.snapshot
                text: stocks.snapshot
                    ? (stocks.dayMode
                        ? "REQUESTED DAY " + stocks.stockFeed.dayDate
                          + "\nSESSION " + (stocks.dayResult
                              && stocks.dayResult.state === "session" ? "AVAILABLE"
                              : stocks.dayResult && stocks.dayResult.state === "no-session"
                                  ? "NO TRADING SESSION" : "INVALID DATA")
                          + "\nCLOSE " + (stocks.dayResult && stocks.dayResult.state === "session"
                              ? "$" + stocks.dayResult.close.toFixed(2) : "N/A")
                        : "REQUESTED " + stocks.snapshot.from + " to " + stocks.snapshot.to
                          + "\nSESSIONS " + stocks.snapshot.bars.length
                          + "\nFIRST CLOSE " + (stocks.snapshot.first
                              ? stocks.snapshot.first.date + " // $"
                                  + stocks.snapshot.first.price.toFixed(2) : "UNAVAILABLE")
                          + "\nLAST CLOSE " + (stocks.snapshot.last
                              ? stocks.snapshot.last.date + " // $"
                                  + stocks.snapshot.last.price.toFixed(2) : "UNAVAILABLE")
                          + "\nLAST VS FIRST " + (stocks.snapshot.changePct === null
                              ? "N/A" : stocks.snapshot.changePct.toFixed(2) + "%"))
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.white
            }
            Rectangle {
                objectName: "marketRangeAnalysisPanel"
                width: parent.width
                visible: !stocks.dayMode && stocks.rangeAnalysis !== null
                height: visible ? analysisCopy.implicitHeight + analysisNote.implicitHeight + 30 : 0
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    id: analysisCopy
                    objectName: "marketRangeAnalysisSummary"
                    anchors.top: parent.top
                    anchors.topMargin: 8
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    text: stocks.rangeAnalysis
                        ? ("RANGE MOVEMENT // LOADED " + stocks.rangeAnalysis.priceBasis
                            + "\nHIGH $" + stocks.rangeAnalysis.high.price.toFixed(2)
                            + " // " + stocks.rangeAnalysis.high.date
                            + "\nLOW $" + stocks.rangeAnalysis.low.price.toFixed(2)
                            + " // " + stocks.rangeAnalysis.low.date
                            + "\nMAX PEAK-TO-TROUGH DROP "
                            + stocks.rangeAnalysis.maxDrawdownPct.toFixed(2) + "%"
                            + " // " + stocks.rangeAnalysis.peak.date
                            + " TO " + stocks.rangeAnalysis.trough.date
                            + "\nSESSION STEPS // UP " + stocks.rangeAnalysis.upSteps
                            + " / DOWN " + stocks.rangeAnalysis.downSteps
                            + " / FLAT " + stocks.rangeAnalysis.flatSteps
                            + "\nBIGGEST UP STEP "
                            + (stocks.rangeAnalysis.largestUpPct === null ? "N/A"
                               : "+" + stocks.rangeAnalysis.largestUpPct.toFixed(2) + "%")
                            + " // BIGGEST DOWN STEP "
                            + (stocks.rangeAnalysis.largestDownPct === null ? "N/A"
                               : stocks.rangeAnalysis.largestDownPct.toFixed(2) + "%"))
                        : ""
                    textFormat: Text.PlainText
                    font.pixelSize: 11
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    id: analysisNote
                    objectName: "marketRangeAnalysisScope"
                    anchors.top: analysisCopy.bottom
                    anchors.topMargin: 7
                    anchors.left: analysisCopy.left
                    anchors.right: analysisCopy.right
                    text: "OBSERVED CLOSE-TO-CLOSE SESSIONS ONLY // "
                        + "NOT INTRADAY EXTREMES OR A VOLATILITY FORECAST // "
                        + "NO NEW REQUEST"
                    textFormat: Text.PlainText
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.WordWrap
                }
            }
            ActionButton {
                id: backToRange
                visible: stocks.dayMode && stocks.stockFeed
                    && stocks.stockFeed.canReturnToRange
                width: 136
                height: visible ? 28 : 0
                label: "BACK TO RANGE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: stocks.stockFeed && stocks.stockFeed.canReturnToRange
                onLeftClicked: {
                    if (stocks.stockFeed) stocks.stockFeed.returnToRange();
                }
            }
            ActionButton {
                id: averageToggle
                objectName: "marketMovingAverageToggle"
                visible: !stocks.dayMode && stocks.rangeAnalysis !== null
                    && stocks.priceBars.length >= 5
                width: 180
                height: visible ? 30 : 0
                label: stocks.showAverages ? "HIDE 5/20 SMA" : "SHOW 5/20 SMA"
                labelPixelSize: 10
                accentColor: Colors.orange
                selected: stocks.showAverages
                available: visible
                onLeftClicked: stocks.showAverages = !stocks.showAverages
            }
            Rectangle {
                width: parent.width
                height: visible ? 174 : 0
                visible: !stocks.dayMode && stocks.priceBars.length >= 2
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Canvas {
                    id: priceCanvas
                    anchors.fill: parent
                    anchors.margins: 9
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const bars = stocks.priceBars;
                        if (!bars || bars.length < 2 || width < 5 || height < 5)
                            return;
                        const nums = bars.map(function(x) { return x.price; });
                        const low = Math.min.apply(null,nums);
                        const high = Math.max.apply(null,nums);
                        const spread = Math.max(high-low,0.00001);
                        ctx.beginPath();
                        for (let i=0;i<bars.length;++i) {
                            const x = i*(width-1)/(bars.length-1);
                            const y = (height-1) - (nums[i]-low)/spread*(height-1);
                            if (i===0) ctx.moveTo(x,y);
                            else ctx.lineTo(x,y);
                        }
                        ctx.strokeStyle = "#55CFCA";
                        ctx.lineWidth = 1.6;
                        ctx.stroke();

                        // M28: optional trailing closing-session SMA overlays.
                        // Share the same x/y scale as cyan prices; no new source.
                        const moving = stocks.averageOverlay;
                        if (moving) {
                            const drawAverage = function(points,color) {
                                if (!points || points.length < 1) return;
                                ctx.beginPath();
                                for (let k=0;k<points.length;k++) {
                                    const a=points[k];
                                    const x=a.index*(width-1)/(bars.length-1);
                                    const y=(height-1)-(a.price-low)/spread*(height-1);
                                    if (k===0) ctx.moveTo(x,y);
                                    else ctx.lineTo(x,y);
                                }
                                ctx.strokeStyle=color;
                                ctx.lineWidth=2;
                                ctx.stroke();
                            };
                            drawAverage(moving.sma5,"#ED981A");
                            drawAverage(moving.sma20,"#D8CAFF");
                        }

                        // Small windows keep every point visible; long histories
                        // remain legible without painting 132 overlapping dots.
                        if (bars.length <= 32) {
                            ctx.fillStyle = "#55CFCA";
                            for (let i=0;i<bars.length;++i) {
                                const point = ChartPointPolicy.pointAt(
                                    bars, width, height, i);
                                if (!point) continue;
                                ctx.beginPath();
                                ctx.arc(point.x, point.y, 2.3, 0, Math.PI * 2);
                                ctx.fill();
                            }
                        }
                        // Pinned A survives deselecting B, but never survives
                        // changing the underlying loaded RANGE or DAY mode.
                        if (stocks.pinnedPoint !== null) {
                            const p = ChartPointPolicy.pointAt(
                                bars, width, height, stocks.pinnedPointIndex);
                            if (p) {
                                ctx.beginPath();
                                ctx.moveTo(p.x,0);
                                ctx.lineTo(p.x,height);
                                ctx.strokeStyle="#F2D24D";
                                ctx.lineWidth=1;
                                ctx.stroke();
                                ctx.beginPath();
                                ctx.arc(p.x,p.y,3.5,0,Math.PI*2);
                                ctx.fillStyle="#F2D24D";
                                ctx.fill();
                            }
                        }
                        if (stocks.inspectedPoint !== null) {
                            const point = ChartPointPolicy.pointAt(
                                bars, width, height, stocks.selectedPointIndex);
                            if (point) {
                                ctx.strokeStyle = "#C74EC7";
                                ctx.lineWidth = 1;
                                ctx.beginPath();
                                ctx.moveTo(point.x, 0);
                                ctx.lineTo(point.x, height);
                                ctx.stroke();
                                ctx.beginPath();
                                ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
                                ctx.fillStyle = "#ED981A";
                                ctx.fill();
                                ctx.strokeStyle = "#C74EC7";
                                ctx.lineWidth = 1.8;
                                ctx.stroke();
                            }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: !stocks.dayMode && stocks.priceBars.length >= 2
                        acceptedButtons: Qt.LeftButton
                        onClicked: function(mouse) {
                            stocks.inspectChartPoint(mouse.x, mouse.y);
                        }
                    }
                }
            }
            GohuText {
                objectName: "marketMovingAverageSummary"
                width: parent.width
                visible: stocks.averageOverlay !== null
                text: stocks.averageOverlay
                    ? ("TRAILING SESSION AVERAGES // "
                        + stocks.averageOverlay.priceBasis
                        + "\nORANGE SMA 5 // $"
                        + stocks.averageOverlay.latest5.toFixed(2)
                        + "\nLILAC SMA 20 // "
                        + (stocks.averageOverlay.latest20 === null
                            ? "N/A // NEED 20 LOADED SESSIONS"
                            : "$" + stocks.averageOverlay.latest20.toFixed(2))
                        + "\nLOADED SESSIONS ONLY // NO NEW REQUEST"
                        + "\nNOT A LIVE QUOTE OR TRADE SIGNAL")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
            }
            GohuText {
                objectName: "marketMovingAverageRelationship"
                width: parent.width
                visible: stocks.averageRelationship !== null
                text: stocks.averageRelationship
                    ? (stocks.averageRelationship.state === "insufficient"
                        ? ("SMA 5 VS SMA 20 // INSUFFICIENT LOADED HISTORY"
                            + "\nNEED 20 OBSERVED SESSIONS // HAVE "
                            + stocks.averageRelationship.sessions
                            + "\nNO AUTO-FETCH // NOT A TRADE SIGNAL")
                        : ("SMA 5 VS SMA 20 // HISTORICAL RELATIONSHIP"
                            + "\nLATEST " + stocks.averageRelationship.latestDate
                            + " // SMA 5 " + stocks.averageRelationship.latestSide
                            + " SMA 20"
                            + "\nSPREAD SMA 5 MINUS SMA 20 "
                            + (stocks.averageRelationship.spreadPrice < 0 ? "-$" : "+$")
                            + Math.abs(stocks.averageRelationship.spreadPrice).toFixed(2)
                            + " // " + (stocks.averageRelationship.spreadPct > 0 ? "+" : "")
                            + stocks.averageRelationship.spreadPct.toFixed(2) + "%"
                            + "\nOBSERVED SIDE CHANGES "
                            + stocks.averageRelationship.sideChanges
                            + " // MOVED ABOVE " + stocks.averageRelationship.movedAbove
                            + " / BELOW " + stocks.averageRelationship.movedBelow
                            + "\nLAST OBSERVED SIDE CHANGE "
                            + (stocks.averageRelationship.lastChange
                                ? stocks.averageRelationship.lastChange.date
                                    + " // SMA 5 MOVED "
                                    + stocks.averageRelationship.lastChange.direction
                                : "NONE IN LOADED RANGE")
                            + "\nCLOSE-BASED ONLY // NOT A LIVE QUOTE OR TRADE SIGNAL"))
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: !stocks.dayMode && stocks.priceBars.length >= 2
                text: "CYAN = DAILY CLOSES // CLICK A DATA POINT TO INSPECT // ORANGE DOT = SELECTED B // YELLOW = PINNED A"
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                visible: !stocks.dayMode && stocks.inspectedPoint !== null
                text: stocks.inspectedPoint
                    ? "SELECTED SESSION // " + stocks.inspectedPoint.date
                      + "\n" + stocks.snapshot.priceBasis + " // $"
                      + stocks.inspectedPoint.price.toFixed(2)
                      + " // " + stocks.snapshot.symbol
                    : ""
                textFormat: Text.PlainText
                font.pixelSize: 11
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            Rectangle {
                objectName: "marketSelectedCloseComparisonPanel"
                width: parent.width
                visible: !stocks.dayMode && stocks.selectedCloseComparison !== null
                height: visible ? selectedComparisonText.implicitHeight + 24 : 0
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    id: selectedComparisonText
                    objectName: "marketSelectedCloseComparisonText"
                    anchors.top: parent.top
                    anchors.topMargin: 11
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    text: stocks.selectedCloseComparison
                        ? ("SELECTED VS LAST LOADED CLOSE // "
                            + stocks.selectedCloseComparison.priceBasis
                            + "\nSELECTED " + stocks.selectedCloseComparison.selected.date
                            + " // $" + stocks.selectedCloseComparison.selected.price.toFixed(2)
                            + "\nLAST " + stocks.selectedCloseComparison.last.date
                            + " // $" + stocks.selectedCloseComparison.last.price.toFixed(2)
                            + "\nCHANGE " + (stocks.selectedCloseComparison.deltaPrice > 0 ? "+" : "")
                            + "$" + stocks.selectedCloseComparison.deltaPrice.toFixed(2)
                            + " // " + (stocks.selectedCloseComparison.deltaPct > 0 ? "+" : "")
                            + stocks.selectedCloseComparison.deltaPct.toFixed(2) + "%"
                            + "\nOBSERVED SESSION STEPS "
                            + stocks.selectedCloseComparison.sessionSteps
                            + "\nNOT A LIVE QUOTE // NO NEW REQUEST")
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.white
                }
            }
            Row {
                id: pinnedActions
                objectName: "marketPinnedSessionActions"
                width: parent.width
                visible: !stocks.dayMode && stocks.rangeAnalysis !== null
                    && (stocks.inspectedPoint !== null || stocks.pinValid)
                height: visible ? 30 : 0
                spacing: 8
                ActionButton {
                    objectName: "marketPinSessionButton"
                    visible: stocks.inspectedPoint !== null
                    width: 132
                    height: 29
                    label: "PIN AS A"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: visible && stocks.rangeAnalysis !== null
                    onLeftClicked: stocks.pinCurrentPoint()
                }
                ActionButton {
                    objectName: "marketClearPinButton"
                    visible: stocks.pinValid
                    width: 116
                    height: 29
                    label: "CLEAR PIN A"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: stocks.pinValid
                    onLeftClicked: stocks.clearPinnedComparison()
                }
            }
            GohuText {
                objectName: "marketPinnedSessionHint"
                width: parent.width
                visible: stocks.pinValid
                text: stocks.pinnedPoint
                    ? ("PINNED A // " + stocks.pinnedPoint.date + " // $"
                        + stocks.pinnedPoint.price.toFixed(2)
                        + "\nCLICK ANOTHER CHART CLOSE TO CHOOSE B. "
                        + "YELLOW = PINNED A // ORANGE = SELECTED B.")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
            }
            Rectangle {
                objectName: "marketPinnedPairComparisonPanel"
                width: parent.width
                visible: stocks.pinnedPairComparison !== null
                height: visible ? pinnedPairText.implicitHeight + 22 : 0
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    id: pinnedPairText
                    objectName: "marketPinnedPairComparisonText"
                    anchors.top: parent.top
                    anchors.topMargin: 9
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    text: stocks.pinnedPairComparison
                        ? ("PINNED A VS SELECTED B // "
                            + stocks.pinnedPairComparison.priceBasis
                            + "\nA " + stocks.pinnedPairComparison.start.date
                            + " // $" + stocks.pinnedPairComparison.start.price.toFixed(2)
                            + "\nB " + stocks.pinnedPairComparison.end.date
                            + " // $" + stocks.pinnedPairComparison.end.price.toFixed(2)
                            + "\nB MINUS A // "
                            + (stocks.pinnedPairComparison.deltaPrice < 0 ? "-$" : "+$")
                            + Math.abs(stocks.pinnedPairComparison.deltaPrice).toFixed(2)
                            + " // "
                            + (stocks.pinnedPairComparison.deltaPct > 0 ? "+" : "")
                            + stocks.pinnedPairComparison.deltaPct.toFixed(2) + "%"
                            + "\nOBSERVED SESSION STEPS "
                            + stocks.pinnedPairComparison.observedSteps
                            + " // " + stocks.pinnedPairComparison.order
                            + "\nLOADED CLOSES ONLY // NO NEW REQUEST")
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.white
                }
            }
            Rectangle {
                objectName: "marketPinnedIntervalAnalysisPanel"
                width: parent.width
                visible: stocks.pinnedInterval !== null
                height: visible ? pinnedIntervalText.implicitHeight + 22 : 0
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    id: pinnedIntervalText
                    objectName: "marketPinnedIntervalAnalysisText"
                    anchors.top: parent.top
                    anchors.topMargin: 9
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    text: stocks.pinnedInterval
                        ? ("BETWEEN PINNED A AND B // CHRONOLOGICAL LOADED CLOSES"
                            + "\n" + stocks.pinnedInterval.from.date
                            + " TO " + stocks.pinnedInterval.to.date
                            + " // " + stocks.pinnedInterval.sessions
                            + " OBSERVED SESSIONS"
                            + "\nHIGHEST CLOSE $"
                            + stocks.pinnedInterval.high.price.toFixed(2)
                            + " // " + stocks.pinnedInterval.high.date
                            + "\nLOWEST CLOSE $"
                            + stocks.pinnedInterval.low.price.toFixed(2)
                            + " // " + stocks.pinnedInterval.low.date
                            + "\nMAX PEAK-TO-TROUGH CLOSE DECLINE "
                            + stocks.pinnedInterval.maxDrawdownPct.toFixed(2) + "%"
                            + (stocks.pinnedInterval.drawdownPeak
                                ? " // " + stocks.pinnedInterval.drawdownPeak.date
                                    + " TO " + stocks.pinnedInterval.drawdownTrough.date
                                : " // NONE OBSERVED")
                            + "\nSESSION STEPS // UP "
                            + stocks.pinnedInterval.upSteps
                            + " / DOWN " + stocks.pinnedInterval.downSteps
                            + " / FLAT " + stocks.pinnedInterval.flatSteps
                            + "\nEARLIER TO LATER EVEN IF B PRECEDES A"
                            + " // NO NEW REQUEST")
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.white
                }
            }
            Row {
                width: parent.width
                visible: stocks.pinnedInterval !== null || stocks.savedIntervalValid
                height: visible ? 30 : 0
                spacing: 6
                ActionButton {
                    width: 132
                    height: 29
                    label: "SAVE INTERVAL 1"
                    visible: stocks.pinnedInterval !== null
                    available: visible
                    onLeftClicked: stocks.saveCurrentInterval()
                }
                ActionButton {
                    width: 112
                    height: 29
                    label: "CLEAR INTERVAL"
                    visible: stocks.savedIntervalValid
                    available: visible
                    onLeftClicked: stocks.clearSavedInterval()
                }
            }
            GohuText {
                objectName: "marketIntervalComparison"
                width: parent.width
                visible: stocks.savedIntervalValid
                text: !stocks.savedIntervalValid ? "" : stocks.intervalComparison
                    ? ("INTERVAL 1 VS CURRENT A/B // CHRONOLOGICAL CLOSE RETURNS"
                        + "\n1 // " + stocks.intervalComparison.first.from.date
                        + " TO " + stocks.intervalComparison.first.to.date
                        + " // " + stocks.intervalComparison.firstReturnPct.toFixed(2) + "%"
                        + " // " + stocks.intervalComparison.first.observedSteps + " STEPS"
                        + "\n2 // " + stocks.intervalComparison.second.from.date
                        + " TO " + stocks.intervalComparison.second.to.date
                        + " // " + stocks.intervalComparison.secondReturnPct.toFixed(2) + "%"
                        + " // " + stocks.intervalComparison.second.observedSteps + " STEPS"
                        + "\nRETURN DIFFERENCE (2 MINUS 1) "
                        + stocks.intervalComparison.returnGapPoints.toFixed(2) + " PERCENTAGE POINTS"
                        + "\nMAX CLOSE DRAWDOWN // 1 "
                        + stocks.intervalComparison.first.maxDrawdownPct.toFixed(2) + "% // 2 "
                        + stocks.intervalComparison.second.maxDrawdownPct.toFixed(2) + "%"
                        + (stocks.intervalComparison.overlaps ? "\nINTERVALS OVERLAP" : "\nINTERVALS DO NOT OVERLAP")
                        + "\nRAW RETURNS // NOT TIME-NORMALIZED // NO NEW REQUEST"
                        + "\nGEOMETRIC CHANGE PER OBSERVED STEP"
                        + "\n1 // " + (stocks.intervalComparison.firstStepPct === null
                            ? "N/A" : stocks.intervalComparison.firstStepPct.toFixed(4) + "%")
                        + " // 2 // " + (stocks.intervalComparison.secondStepPct === null
                            ? "N/A" : stocks.intervalComparison.secondStepPct.toFixed(4) + "%")
                        + "\nSTEP CHANGE DIFFERENCE (2 MINUS 1) "
                        + (stocks.intervalComparison.stepGapPoints === null
                            ? "N/A" : stocks.intervalComparison.stepGapPoints.toFixed(4)
                                + " PERCENTAGE POINTS")
                        + (stocks.intervalComparison.sameStepCount
                            ? "\nSAME OBSERVED STEP COUNT"
                            : "\nDIFFERENT OBSERVED STEP COUNTS")
                        + "\nOBSERVED CLOSE TRANSITIONS ONLY // NOT CALENDAR TIME"
                        + " // NOT A FORECAST")
                    : "INTERVAL 1 SAVED // CHOOSE ANOTHER A/B PAIR"
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: stocks.normalizedComparison !== null
                text: "NORMALIZED INTERVALS // START = 100"
                color: Colors.cyan
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: stocks.normalizedComparison !== null
                text: stocks.normalizedComparison
                    ? ("CYAN = INTERVAL 1 // MAGENTA = INTERVAL 2"
                        + "\nINDEX HIGH " + stocks.normalizedComparison.high.toPrecision(5)
                        + " // LOW " + stocks.normalizedComparison.low.toPrecision(5)
                        + " // REFERENCE 100")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.white
            }
            Rectangle {
                objectName: "marketNormalizedIntervalChart"
                width: parent.width
                visible: stocks.normalizedComparison !== null
                height: visible ? 174 : 0
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Canvas {
                    id: normalizedCanvas
                    anchors.fill: parent
                    anchors.margins: 9
                    property var plot: stocks.normalizedComparison
                    onPlotChanged: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onVisibleChanged: { if (visible) requestPaint(); }
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const chart = plot;
                        if (!chart || width < 5 || height < 5) return;
                        const pointAt = function(p) {
                            return RangeAnalysisPolicy.normalizedChartPoint(
                                chart, p, width, height);
                        };
                        const base = pointAt({step:0,value:100});
                        if (!base) return;
                        ctx.beginPath();
                        ctx.moveTo(0,base.y);
                        ctx.lineTo(width-1,base.y);
                        ctx.strokeStyle = "#808080";
                        ctx.lineWidth = 1;
                        ctx.stroke();
                        const draw = function(points,color) {
                            ctx.beginPath();
                            for (let i=0; i<points.length; i++) {
                                const p = pointAt(points[i]);
                                if (!p) return;
                                if (i===0) ctx.moveTo(p.x,p.y);
                                else ctx.lineTo(p.x,p.y);
                            }
                            ctx.strokeStyle=color;
                            ctx.lineWidth=1.8;
                            ctx.stroke();
                            const last = pointAt(points[points.length-1]);
                            if (!last) return;
                            ctx.beginPath();
                            ctx.arc(last.x,last.y,3,0,Math.PI*2);
                            ctx.fillStyle=color;
                            ctx.fill();
                        };
                        draw(chart.first,"#55CFCA");
                        draw(chart.second,"#C74EC7");
                    }
                }
            }
            GohuText {
                objectName: "marketNormalizedIntervalLegend"
                width: parent.width
                visible: stocks.normalizedComparison !== null
                text: stocks.normalizedComparison
                    ? ("OBSERVED STEPS // 0 TO " + stocks.normalizedComparison.maxSteps
                        + "\n1 ENDS AT STEP " + (stocks.normalizedComparison.first.length-1)
                        + " // INDEX "
                        + stocks.normalizedComparison.first[stocks.normalizedComparison.first.length-1].value.toPrecision(5)
                        + "\n2 ENDS AT STEP " + (stocks.normalizedComparison.second.length-1)
                        + " // INDEX "
                        + stocks.normalizedComparison.second[stocks.normalizedComparison.second.length-1].value.toPrecision(5)
                        + "\nEACH LINE STOPS AT ITS LAST OBSERVED CLOSE"
                        + " // NOT CALENDAR TIME // NO NEW REQUEST")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
            }
            ActionButton {
                id: openSelectedInDay
                visible: !stocks.dayMode && stocks.inspectedPoint !== null
                width: 136
                height: visible ? 28 : 0
                label: "OPEN IN DAY"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: stocks.stockFeed && stocks.stockFeed.monitoring
                    && stocks.stockFeed.ready && !stocks.stockFeed.loading
                    && stocks.inspectedPoint !== null
                onLeftClicked: {
                    if (stocks.stockFeed && stocks.inspectedPoint)
                        stocks.stockFeed.openRangePointInDay(
                            stocks.selectedPointIndex, stocks.inspectedPoint.date);
                }
            }
            GohuText {
                width: parent.width
                text: "Historical closes are not live quotes or a price-reaction study. Adjusted prices can be recomputed after dividends and splits. EODHD demo/key limits still apply."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }

    FinanceStockDiscoveryPane {
        id: worldwideSearch
        anchors.fill: parent
        visible: stocks.discoveryOpen
        active: stocks.discoveryOpen && stocks.visible
            && stocks.stockFeed && stocks.stockFeed.monitoring
        z: 20
        onExitRequested: stocks.discoveryOpen = false
    }

    FinanceMarketQuotaStatusPane {
        id: localQuotaStatus
        anchors.fill: parent
        visible: stocks.quotaOpen
        active: stocks.quotaOpen && stocks.visible
            && stocks.stockFeed && stocks.stockFeed.monitoring
        z: 25
        onExitRequested: stocks.quotaOpen = false
    }

    // Finance uses the ordinary bar, not the Git/Hospital star family.
    // Mount on the visible pane host and follow the Flickable's viewport.
    NeonScrollBar {
        id: stockHistoryScrollBar
        flickable: scroll
        mountingParent: stocks
        geometryMode: "viewport"
        handleStyle: "bar"
        rightInset: 2
    }
}
