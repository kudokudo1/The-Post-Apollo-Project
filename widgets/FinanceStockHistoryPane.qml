import QtQuick
import "../components"
import "FinanceStockModePolicy.js" as StockModePolicy
import "FinanceStockChartPointPolicy.js" as ChartPointPolicy
import "FinanceStockRangeAnalysisPolicy.js" as RangeAnalysisPolicy

// Market STOCKS M14: one-step BACK TO RANGE restores previously loaded chart.
Item {
    id: stocks
    property var stockFeed: null
    property bool discoveryOpen: true
    property bool quotaOpen: false
    // M41: presentation only. Both research views retain the same data and
    // controls; changing views must not change the provider or selections.
    property string researchView: "price"
    // M42: disclosure is not a mode or a data action.
    property bool controlsExpanded: false
    function toggleResearchControls() {
        controlsExpanded = !controlsExpanded;
        if (controlsExpanded) scroll.contentY = 0;
    }
    function selectResearchView(view) {
        if ((view !== "price" && view !== "compare") || researchView === view) return;
        researchView = view;
        scroll.contentY = 0;
    }
    onVisibleChanged: {
        if (!visible) {
            discoveryOpen = false;
            quotaOpen = false;
        } else if (!globalHistoryActive) {
            discoveryOpen = true;
        }
    }
    // M46b: one worldwide stock universe. Legacy service is retained only
    // as the existing Finance monitoring/lifecycle witness, not a price source.
    property var globalHistory: null
    property string globalHandoffMessage: ""
    readonly property bool globalHistoryActive: globalHistory !== null
    readonly property var snapshot: globalHistory
    function acceptGlobalHistory(identity, listing, data) {
        if (!discoveryOpen || !visible || !stockFeed || !stockFeed.monitoring) return false;
        const captured=RangeAnalysisPolicy.captureGlobalHistory(identity,listing,data);
        if (!captured) {
            globalHandoffMessage="GLOBAL HISTORY REFUSED // INVALID DATA OR LISTING";
            discoveryOpen=false;
            scroll.contentY=0;
            return false;
        }
        dayDate="";
        globalHistory=captured;
        if (captured.from===captured.to) dayDate=captured.from;
        globalHandoffMessage="";
        controlsExpanded=false;
        researchView=stockReference !== null && stockReference.identity ? "compare" : "price";
        discoveryOpen=false;
        scroll.contentY=0;
        return true;
    }
    function openControls() {
        if (!visible || !stockFeed || !stockFeed.monitoring) return;
        stocks.quotaOpen = false;
        globalHandoffMessage = "";
        discoveryOpen = !discoveryOpen;
        if (discoveryOpen) scroll.contentY = 0;
    }
    function openQuotaStatus() {
        if (!visible || !stockFeed || !stockFeed.monitoring) return;
        stocks.discoveryOpen = false;
        quotaOpen = true;
    }
    // DAY is an in-memory view of an actual loaded close. Never infer an
    // unobserved session from a calendar date, especially for compact data.
    property string dayDate: ""
    function openLoadedDay(index) {
        if (!globalHistoryActive || !Number.isInteger(index)
                || index < 0 || index >= priceBars.length) return false;
        dayDate=priceBars[index].date;
        return true;
    }
    function returnToRange() { dayDate=""; }
    readonly property string priceUnit: globalHistoryActive ? globalHistory.currency+" " : ""
    readonly property string historySource: globalHistoryActive
        ? (globalHistory.source === "eodhd-eod" ? "EODHD" : "ALPHA VANTAGE")
        : ""
    readonly property var priceBars: snapshot && Array.isArray(snapshot.bars)
        ? snapshot.bars : []
    readonly property bool dayMode: globalHistoryActive && dayDate.length > 0
    readonly property var dayResult: dayMode && snapshot
        ? StockModePolicy.loadedGlobalDay(snapshot, dayDate) : null
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
        && RangeAnalysisPolicy.retainedGlobalRange(snapshot)
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
    // M35: cursor is local to this comparison, never carried across a new pair.
    property int normalizedSelectedStep: -1
    readonly property var normalizedStepDetail: normalizedComparison !== null
        ? RangeAnalysisPolicy.inspectNormalizedStep(normalizedComparison,
            normalizedSelectedStep) : null
    onNormalizedComparisonChanged: normalizedSelectedStep = -1
    // M36: explicitly retained comparison reference, separate from M30/M32
    // same-snapshot pins. Survives issuer changes, never persists to disk.
    property var stockReference: null
    readonly property var crossStockComparison: stockReference !== null
        && rangeAnalysis !== null
        ? (stockReference.identity
            ? RangeAnalysisPolicy.compareGlobalStockReferences(stockReference,snapshot)
            : {state:"reference-kind-mismatch"})
        : null
    // M37: chart is derived only from the ready M36 matched-date result.
    readonly property var crossStockChart: RangeAnalysisPolicy.crossStockNormalizedChart(crossStockComparison)
    // M38: selection belongs to the exact current cross-stock comparison.
    property int crossStockSelectedStep: -1
    readonly property var crossStockDateDetail: crossStockChart !== null
        ? RangeAnalysisPolicy.inspectCrossStockDate(crossStockComparison,
            crossStockSelectedStep) : null
    onCrossStockChartChanged: crossStockSelectedStep = -1
    // M39: cumulative leadership uses only the same matched close dates.
    readonly property var crossStockLeadership: crossStockChart !== null
        ? RangeAnalysisPolicy.summarizeCrossStockLeadership(crossStockComparison) : null
    // M40: optional zero-centered gap chart; shares M38's selected date.
    property bool showCrossStockGap: false
    readonly property var crossStockGap: crossStockChart !== null
        ? RangeAnalysisPolicy.crossStockGapChart(crossStockComparison) : null
    function saveStockReference() {
        if (rangeAnalysis === null) return;
        const captured=RangeAnalysisPolicy.captureGlobalStockReference(snapshot);
        if (captured) stockReference=captured;
    }
    function clearStockReference() { stockReference=null; }
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
        if (scroll) scroll.contentY = 0;
        clearSavedInterval();
        selectedPointIndex = -1;
        clearPinnedComparison();
        priceCanvas.requestPaint();
    }
    onSelectedPointIndexChanged: priceCanvas.requestPaint()

    Row {
        id: stockCommandRail
        objectName: "marketStockCommandRail"
        anchors.top: parent.top
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        height: 29
        spacing: 5
        ActionButton {
            objectName: "marketUnifiedControls"
            width: Math.max(0,(stockCommandRail.width-2*stockCommandRail.spacing)/3)
            height: 28
            label: "CONTROLS"
            labelPixelSize: 9
            selected: stocks.discoveryOpen
            accentColor: Colors.magenta
            available: stocks.stockFeed && stocks.stockFeed.monitoring
            onLeftClicked: stocks.openControls()
        }
        ActionButton {
            objectName: "marketResearchControlsToggle"
            width: Math.max(0,(stockCommandRail.width-2*stockCommandRail.spacing)/3)
            height: 28
            label: stocks.controlsExpanded ? "HIDE DETAILS" : "DETAILS"
            labelPixelSize: 9
            accentColor: Colors.orange
            selected: stocks.controlsExpanded
            onLeftClicked: stocks.toggleResearchControls()
        }
        ActionButton {
            width: Math.max(0,(stockCommandRail.width-2*stockCommandRail.spacing)/3)
            height: 28
            label: "QUOTA STATUS"
            labelPixelSize: 9
            accentColor: Colors.orange
            available: stocks.stockFeed && stocks.stockFeed.monitoring
            onLeftClicked: stocks.openQuotaStatus()
        }
    }
    Row {
        id: modeControls
        objectName: "marketDayRangeRail"
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28
        spacing: 6
        ActionButton {
            width: Math.max(0,(modeControls.width-modeControls.spacing)/2)
            height: 27
            label: "DAY"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: stocks.dayMode
            available: stocks.priceBars.length > 0 && !stocks.dayMode
            onLeftClicked: stocks.openLoadedDay(stocks.inspectedPoint !== null
                ? stocks.selectedPointIndex : stocks.priceBars.length-1)
        }
        ActionButton {
            width: Math.max(0,(modeControls.width-modeControls.spacing)/2)
            height: 27
            label: "RANGE"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: !stocks.dayMode
            available: stocks.dayMode
            onLeftClicked: stocks.returnToRange()
        }
    }
    Row {
        id: researchRail
        objectName: "marketResearchViewRail"
        anchors.bottom: modeControls.top
        anchors.bottomMargin: visible ? 4 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !stocks.dayMode
        height: visible ? 29 : 0
        spacing: 6
        ActionButton {
            objectName: "marketResearchPriceView"
            width: Math.max(0,(researchRail.width-researchRail.spacing)/2)
            height: 28
            label: "PRICE / INTERVALS"
            labelPixelSize: 10
            accentColor: Colors.cyan
            selected: stocks.researchView === "price"
            onLeftClicked: stocks.selectResearchView("price")
        }
        ActionButton {
            objectName: "marketResearchCompareView"
            width: Math.max(0,(researchRail.width-researchRail.spacing)/2)
            height: 28
            label: "CROSS-STOCK"
            labelPixelSize: 10
            accentColor: Colors.magenta
            selected: stocks.researchView === "compare"
            available: true
            onLeftClicked: stocks.selectResearchView("compare")
        }
    }
    Flickable {
        id: scroll
        anchors.top: stockCommandRail.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: researchRail.top
        anchors.bottomMargin: 5
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: body
            // Reserve an unobstructed right gutter for the proportional rail.
            width: Math.max(0, scroll.width - 24)
            spacing: 8
            // M46b correction: controls participate in the same scroll layout
            // as the loaded charts; no covering layer or second viewport.
            FinanceStockDiscoveryPane {
                id: worldwideSearch
                objectName: "marketInlineStockControls"
                width: parent.width
                height: visible ? implicitHeight : 0
                visible: stocks.discoveryOpen
                // Disclosure is not the lifetime of an authorized read session.
                // Closing controls retains their validated, in-memory selections.
                sessionActive: stocks.visible && !!stocks.stockFeed && stocks.stockFeed.monitoring
                active: stocks.discoveryOpen && sessionActive
                onExitRequested: stocks.discoveryOpen = false
                onQuotaRequested: stocks.openQuotaStatus()
                onHistoryChosen: function(identity, listing, snapshot) {
                    stocks.acceptGlobalHistory(identity,listing,snapshot);
                }
            }
            GohuText {
                objectName: "marketCompactSelection"
                width: parent.width
                text: stocks.globalHistoryActive
                    ? (stocks.globalHistory.listing.name + " // " + stocks.globalHistory.symbol
                        + " // " + stocks.globalHistory.listing.venue + " // " + stocks.globalHistory.currency
                        + "\n" + stocks.globalHistory.from + " TO " + stocks.globalHistory.to)
                    : "NO STOCK SELECTED // OPEN CONTROLS"
                color: Colors.cyan
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                id: status
                width: parent.width
                text: stocks.globalHandoffMessage || (stocks.globalHistoryActive
                    ? ("GLOBAL HISTORY // " + stocks.historySource
                        + " // LOADED RANGE ONLY"
                        + (stocks.globalHistory.bars.length === 0 ? " // NO SESSIONS" : "")
                        + "\nUSER-CHOSEN LISTING // FIGI MATCH NOT VERIFIED"
                        + (stocks.globalHistory.compactMayBeTruncated
                            ? "\nWARNING // COMPACT HISTORY MAY OMIT EARLIER DATES" : "")
                        + "\nCONTROLS TO LOAD ANOTHER RANGE // COMPARE MATCHING PROVIDER, CURRENCY, BASIS AND WINDOW")
                    : "CHOOSE A WORLDWIDE STOCK AND PROVIDER IN CONTROLS")
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: stocks.globalHandoffMessage.length > 0 ? Colors.red : Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                objectName: "marketGlobalHistoryProvenance"
                width: parent.width
                visible: stocks.globalHistoryActive && stocks.controlsExpanded
                text: stocks.globalHistoryActive
                    ? ("OPENFIGI SEARCH IDENTITY " + stocks.globalHistory.identity.figi
                        + " // " + stocks.globalHistory.identity.name
                        + "\nPROVIDER LISTING CHOSEN BY USER // FIGI MATCH NOT VERIFIED"
                        + "\n" + stocks.globalHistory.listing.venue + " // CURRENCY FROM "
                        + stocks.globalHistory.currencySource
                        + "\nRETRIEVED " + stocks.globalHistory.retrievedAt)
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                visible: !!stocks.snapshot
                text: stocks.snapshot
                    ? (stocks.dayMode
                        ? "LOADED DAY " + stocks.dayDate
                          + "\nSESSION " + (stocks.dayResult
                              && stocks.dayResult.state === "session" ? "AVAILABLE"
                              : stocks.dayResult && stocks.dayResult.state === "no-session"
                                  ? "NO TRADING SESSION" : stocks.dayResult && stocks.dayResult.state === "unavailable"
                                      ? "SESSION NOT COVERED BY COMPACT HISTORY" : "INVALID DATA")
                          + "\nCLOSE " + (stocks.dayResult && stocks.dayResult.state === "session"
                              ? stocks.priceUnit + stocks.dayResult.close.toFixed(2) : "N/A")
                          + (stocks.snapshot.from===stocks.snapshot.to
                              ? "\nDAY SOURCE // EXPLICIT PROVIDER DATE REQUEST"
                              : "\nDAY SOURCE // PREVIOUSLY LOADED RANGE // NO NEW REQUEST")
                        : !stocks.controlsExpanded
                            ? (stocks.snapshot.symbol + " // " + stocks.snapshot.priceBasis
                                + " // " + stocks.historySource
                                + "\n" + stocks.snapshot.bars.length + " SESSIONS // LAST "
                                + (stocks.snapshot.last ? stocks.priceUnit + stocks.snapshot.last.price.toFixed(2) : "N/A")
                                + " // " + (stocks.snapshot.changePct === null
                                    ? "N/A" : stocks.snapshot.changePct.toFixed(2) + "% FIRST TO LAST"))
                            : stocks.snapshot.symbol + " // " + stocks.snapshot.priceBasis
                          + "\nREQUESTED " + stocks.snapshot.from + " to " + stocks.snapshot.to
                          + "\nSESSIONS " + stocks.snapshot.bars.length
                          + "\nFIRST CLOSE " + (stocks.snapshot.first
                              ? stocks.snapshot.first.date + " // " + stocks.priceUnit
                                  + stocks.snapshot.first.price.toFixed(2) : "UNAVAILABLE")
                          + "\nLAST CLOSE " + (stocks.snapshot.last
                              ? stocks.snapshot.last.date + " // " + stocks.priceUnit
                                  + stocks.snapshot.last.price.toFixed(2) : "UNAVAILABLE")
                          + "\nLAST VS FIRST " + (stocks.snapshot.changePct === null
                              ? "N/A" : stocks.snapshot.changePct.toFixed(2) + "%"))
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.white
            }
            Column {
                objectName: "marketResearchCrossStockSection"
                width: parent.width
                visible: !stocks.dayMode && stocks.researchView === "compare"
                height: visible ? implicitHeight : 0
                spacing: 13
                GohuText {
                    width: parent.width
                    visible: stocks.stockReference === null
                    text: "CROSS-STOCK // LOAD A RANGE AND SAVE STOCK REF, THEN LOAD ANOTHER STOCK WITH THE SAME DATE WINDOW"
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.orange
                }
                Row {
                    width: parent.width
                    visible: !stocks.dayMode && (stocks.rangeAnalysis !== null || stocks.stockReference !== null)
                    height: visible ? 30 : 0
                    spacing: 6
                    ActionButton {
                        width: 146
                        height: 29
                        label: "SAVE STOCK REF"
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        visible: stocks.rangeAnalysis !== null
                        available: visible && stocks.priceBars.length >= 2
                        onLeftClicked: stocks.saveStockReference()
                    }
                    ActionButton {
                        width: 110
                        height: 29
                        label: "CLEAR REF"
                        labelPixelSize: 10
                        accentColor: Colors.orange
                        visible: stocks.stockReference !== null
                        available: visible
                        onLeftClicked: stocks.clearStockReference()
                    }
                }
                GohuText {
                    objectName: "marketCrossStockComparison"
                    width: parent.width
                    visible: !stocks.dayMode && stocks.stockReference !== null
                    text: {
                        const ref=stocks.stockReference;
                        if (!ref) return "";
                        const header="STOCK REF // " + ref.symbol + " // " + ref.priceBasis
                            + (ref.identity ? "\n" + ref.listing.venue + " // " + ref.currency + " // "
                                + (ref.source==="eodhd-eod" ? "EODHD" : "ALPHA VANTAGE")
                                + " // FIGI MATCH NOT VERIFIED"
                                + (ref.compactMayBeTruncated ? " // COMPACT COVERAGE MAY BE TRUNCATED" : "") : "")
                            + "\nREQUESTED " + ref.from + " TO " + ref.to
                            + "\nRETRIEVED " + ref.retrievedAt;
                        const d=stocks.crossStockComparison;
                        if (!d) return header + "\nLOAD ANOTHER STOCK WITH SAME DATE WINDOW";
                        if (d.state === "same-stock") return header + "\nSELECT ANOTHER STOCK AND LOAD RANGE";
                        if (d.state === "window-mismatch") return header + "\nDATE WINDOW MISMATCH // MATCH REQUESTED DATES";
                        if (d.state === "basis-mismatch") return header + "\nPRICE BASIS MISMATCH // COMPARISON UNAVAILABLE";
                        if (d.state === "provider-mismatch") return header + "\nPROVIDER MISMATCH // CHOOSE SAME PROVIDER";
                        if (d.state === "currency-mismatch") return header + "\nCURRENCY MISMATCH // NO FX CONVERSION";
                        if (d.state === "reference-kind-mismatch") return header + "\nLEGACY AND GLOBAL REFERENCES CANNOT BE MIXED";
                        if (d.state === "insufficient") return header + "\nNEED TWO COMMON CLOSE DATES // HAVE " + d.matched;
                        if (d.state !== "ready") return header + "\nCOMPARISON UNAVAILABLE";
                        return header
                            + "\nCURRENT " + d.currentSymbol + " // RETRIEVED " + d.currentRetrievedAt
                            + (d.providerSource ? "\n" + d.currentVenue + " // " + d.currency
                                + (d.currentTruncated ? " // COMPACT COVERAGE MAY BE TRUNCATED" : "") : "")
                            + "\nCOMMON CLOSE DATES " + d.from + " TO " + d.to
                            + " // " + d.matched + " MATCHED"
                            + "\n" + d.referenceSymbol + " // " + d.referencePct.toFixed(2) + "%"
                            + " // " + d.currentSymbol + " // " + d.currentPct.toFixed(2) + "%"
                            + "\nCURRENT MINUS REF " + d.gapPoints.toFixed(2) + " PERCENTAGE POINTS"
                            + "\nUNMATCHED CLOSES // REF " + d.referenceUnmatched
                            + " // CURRENT " + d.currentUnmatched
                            + "\nHISTORICAL CLOSE MOVEMENT // NO FILL // NO NEW REQUEST";
                    }
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.cyan
                }
                GohuText {
                    width: parent.width
                    visible: stocks.crossStockChart !== null
                    text: stocks.crossStockChart
                        ? ("CROSS-STOCK CHART // FIRST COMMON CLOSE = 100"
                            + "\nCYAN = " + stocks.crossStockChart.referenceSymbol
                            + " // MAGENTA = " + stocks.crossStockChart.currentSymbol
                            + "\n" + stocks.crossStockChart.priceBasis
                            + " // INDEX HIGH " + stocks.crossStockChart.high.toPrecision(5)
                            + " // LOW " + stocks.crossStockChart.low.toPrecision(5))
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.cyan
                }
                Rectangle {
                    objectName: "marketCrossStockNormalizedChart"
                    width: parent.width
                    visible: stocks.crossStockChart !== null
                    height: visible ? 174 : 0
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Canvas {
                        id: crossStockCanvas
                        anchors.fill: parent
                        anchors.margins: 9
                        property var plot: stocks.crossStockChart
                        property var dateDetail: stocks.crossStockDateDetail
                        onDateDetailChanged: requestPaint()
                        onPlotChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        onVisibleChanged: { if (visible) requestPaint(); }
                        onPaint: {
                            const ctx=getContext("2d");
                            ctx.clearRect(0,0,width,height);
                            const chart=plot;
                            if (!chart || width < 5 || height < 5) return;
                            const pointAt=function(p) {
                                return RangeAnalysisPolicy.normalizedChartPoint(chart,p,width,height);
                            };
                            const base=pointAt({step:0,value:100});
                            if (!base) return;
                            ctx.beginPath();
                            ctx.moveTo(0,base.y);
                            ctx.lineTo(width-1,base.y);
                            ctx.strokeStyle="#808080";
                            ctx.lineWidth=1;
                            ctx.stroke();
                            function draw(points,color) {
                                ctx.beginPath();
                                for (let i=0;i<points.length;i++) {
                                    const p=pointAt(points[i]);
                                    if (!p) return;
                                    if (i===0) ctx.moveTo(p.x,p.y);
                                    else ctx.lineTo(p.x,p.y);
                                }
                                ctx.strokeStyle=color;
                                ctx.lineWidth=1.8;
                                ctx.stroke();
                                const last=pointAt(points[points.length-1]);
                                if (!last) return;
                                ctx.beginPath();
                                ctx.arc(last.x,last.y,3,0,Math.PI*2);
                                ctx.fillStyle=color;
                                ctx.fill();
                            }
                            draw(chart.first,"#55CFCA");
                            draw(chart.second,"#C74EC7");
                            const selected=dateDetail;
                            if (selected) {
                                const pos=pointAt(selected.reference);
                                if (!pos) return;
                                ctx.beginPath();
                                ctx.moveTo(pos.x,0);
                                ctx.lineTo(pos.x,height-1);
                                ctx.strokeStyle="#F2D24D";
                                ctx.lineWidth=1;
                                ctx.stroke();
                                function mark(observation,color) {
                                    const p=pointAt(observation);
                                    if (!p) return;
                                    ctx.beginPath();
                                    ctx.arc(p.x,p.y,4,0,Math.PI*2);
                                    ctx.fillStyle=color;
                                    ctx.fill();
                                    ctx.strokeStyle="#F2D24D";
                                    ctx.lineWidth=1.5;
                                    ctx.stroke();
                                }
                                mark(selected.reference,"#55CFCA");
                                mark(selected.current,"#C74EC7");
                            }
                        }
                        MouseArea {
                            objectName: "marketCrossStockDatePicker"
                            anchors.fill: parent
                            enabled: stocks.crossStockChart !== null
                            acceptedButtons: Qt.LeftButton
                            onClicked: function(mouse) {
                                const step=RangeAnalysisPolicy.normalizedStepAtX(
                                    crossStockCanvas.plot, crossStockCanvas.width,
                                    Math.min(mouse.x,crossStockCanvas.width-1));
                                stocks.crossStockSelectedStep =
                                    step === stocks.crossStockSelectedStep ? -1 : step;
                            }
                        }
                    }
                }
                GohuText {
                    objectName: "marketCrossStockChartLegend"
                    width: parent.width
                    visible: stocks.crossStockChart !== null
                    text: stocks.crossStockChart
                        ? (stocks.crossStockChart.from + " TO " + stocks.crossStockChart.to
                            + " // " + stocks.crossStockChart.first.length + " COMMON CLOSE DATES"
                            + "\n" + stocks.crossStockChart.referenceSymbol
                            + " // FINAL INDEX "
                            + stocks.crossStockChart.first[stocks.crossStockChart.maxSteps].value.toPrecision(5)
                            + "\n" + stocks.crossStockChart.currentSymbol
                            + " // FINAL INDEX "
                            + stocks.crossStockChart.second[stocks.crossStockChart.maxSteps].value.toPrecision(5)
                            + "\nEQUAL SPACING BY COMMON OBSERVATION // NOT CALENDAR TIME"
                            + "\nUNMATCHED CLOSES EXCLUDED // NO NEW REQUEST")
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.orange
                }
                GohuText {
                    objectName: "marketCrossStockDateDetail"
                    width: parent.width
                    visible: stocks.crossStockChart !== null
                    text: {
                        const d=stocks.crossStockDateDetail;
                        if (!d) return "CLICK CROSS-STOCK CHART TO INSPECT A COMMON CLOSE DATE";
                        function describe(p) {
                            return p.symbol + " // " + (p.currency === "USD" ? "$" : p.currency + " ") + p.price.toFixed(2)
                                + " // INDEX " + p.value.toPrecision(6)
                                + " // " + p.changePct.toFixed(4) + "% FROM START";
                        }
                        return "COMMON CLOSE DATE " + d.date + " // " + d.priceBasis
                            + "\n" + describe(d.reference)
                            + "\n" + describe(d.current)
                            + "\nCURRENT MINUS REF // " + d.gapPoints.toFixed(4)
                            + " PERCENTAGE POINTS"
                            + "\nBASE DATE " + d.from
                            + " // LOADED CLOSES ONLY // CLICK AGAIN TO CLEAR";
                    }
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.white
                }
                GohuText {
                    objectName: "marketCrossStockLeadership"
                    width: parent.width
                    visible: stocks.crossStockLeadership !== null
                    text: {
                        const d=stocks.crossStockLeadership;
                        if (!d) return "";
                        function symbolFor(leader) {
                            return leader === "REFERENCE" ? d.referenceSymbol
                                : leader === "CURRENT" ? d.currentSymbol : "TIE";
                        }
                        function advantage(a) {
                            return a ? (a.advantagePoints.toFixed(4)
                                + " PP // " + a.date) : "NONE OBSERVED";
                        }
                        const selected=stocks.crossStockDateDetail;
                        const observed=selected ? d.observations[selected.step] : null;
                        return "RELATIVE LEADERSHIP // FROM FIRST COMMON CLOSE"
                            + "\nLAST OBSERVED " + d.latest.date + " // " + symbolFor(d.latest.leader)
                            + "\n" + d.referenceSymbol + " LED " + d.referenceDates
                            + " // " + d.currentSymbol + " LED " + d.currentDates
                            + " // TIES " + d.tieDates + " / " + d.matched
                            + "\nLARGEST ADVANTAGE " + d.referenceSymbol + " // "
                            + advantage(d.largestReference)
                            + "\nLARGEST ADVANTAGE " + d.currentSymbol + " // "
                            + advantage(d.largestCurrent)
                            + "\nOBSERVED LEAD CHANGES " + d.changes
                            + "\nLAST CHANGE " + (d.lastChange
                                ? d.lastChange.date + " // " + symbolFor(d.lastChange.leader)
                                : "NONE OBSERVED")
                            + (observed ? "\nSELECTED " + observed.date + " // "
                                + symbolFor(observed.leader) : "")
                            + "\nTIES INCLUDE BASE DATE // CUMULATIVE, NOT DAILY WINNERS"
                            + "\nCOMMON OBSERVATIONS ONLY // NO NEW REQUEST";
                    }
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.cyan
                }
                ActionButton {
                    objectName: "marketCrossStockGapToggle"
                    width: Math.min(parent.width, 210)
                    height: visible ? 28 : 0
                    visible: stocks.crossStockGap !== null
                    available: visible
                    label: stocks.showCrossStockGap ? "HIDE GAP CHART" : "SHOW GAP CHART"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    selected: stocks.showCrossStockGap
                    onLeftClicked: stocks.showCrossStockGap = !stocks.showCrossStockGap
                }
                GohuText {
                    width: parent.width
                    visible: stocks.showCrossStockGap && stocks.crossStockGap !== null
                    text: stocks.crossStockGap
                        ? ("PERFORMANCE GAP // " + stocks.crossStockGap.currentSymbol
                            + " MINUS " + stocks.crossStockGap.referenceSymbol
                            + "\nPOSITIVE = CURRENT LEADS // NEGATIVE = REFERENCE LEADS"
                            + "\nSCALE +/- " + stocks.crossStockGap.extent.toPrecision(5)
                            + " PERCENTAGE POINTS // ZERO = EQUAL")
                        : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.cyan
                }
                Rectangle {
                    objectName: "marketCrossStockGapChart"
                    width: parent.width
                    visible: stocks.showCrossStockGap && stocks.crossStockGap !== null
                    height: visible ? 140 : 0
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Canvas {
                        id: crossStockGapCanvas
                        anchors.fill: parent
                        anchors.margins: 9
                        property var plot: stocks.crossStockGap
                        property int selectedStep: stocks.crossStockSelectedStep
                        onPlotChanged: requestPaint()
                        onSelectedStepChanged: requestPaint()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        onVisibleChanged: { if (visible) requestPaint(); }
                        onPaint: {
                            const ctx=getContext("2d");
                            ctx.clearRect(0,0,width,height);
                            const chart=plot;
                            if (!chart || width < 5 || height < 5) return;
                            const pointAt=function(p) {
                                return RangeAnalysisPolicy.crossStockGapPoint(chart,p,width,height);
                            };
                            const zero=pointAt({step:0,value:0});
                            if (!zero) return;
                            ctx.beginPath();
                            ctx.moveTo(0,zero.y);
                            ctx.lineTo(width-1,zero.y);
                            ctx.strokeStyle="#808080";
                            ctx.lineWidth=1;
                            ctx.stroke();
                            ctx.beginPath();
                            for (let i=0;i<chart.points.length;i++) {
                                const p=pointAt(chart.points[i]);
                                if (!p) return;
                                if (i===0) ctx.moveTo(p.x,p.y);
                                else ctx.lineTo(p.x,p.y);
                            }
                            ctx.strokeStyle="#ED981A";
                            ctx.lineWidth=1.8;
                            ctx.stroke();
                            if (selectedStep >= 0 && selectedStep < chart.points.length) {
                                const p=pointAt(chart.points[selectedStep]);
                                if (!p) return;
                                ctx.beginPath();
                                ctx.moveTo(p.x,0);
                                ctx.lineTo(p.x,height-1);
                                ctx.strokeStyle="#F2D24D";
                                ctx.lineWidth=1;
                                ctx.stroke();
                                ctx.beginPath();
                                ctx.arc(p.x,p.y,4,0,Math.PI*2);
                                ctx.fillStyle="#F2D24D";
                                ctx.fill();
                            }
                        }
                        MouseArea {
                            objectName: "marketCrossStockGapPicker"
                            anchors.fill: parent
                            enabled: stocks.showCrossStockGap && stocks.crossStockGap !== null
                            acceptedButtons: Qt.LeftButton
                            onClicked: function(mouse) {
                                const step=RangeAnalysisPolicy.normalizedStepAtX(
                                    crossStockGapCanvas.plot,crossStockGapCanvas.width,
                                    Math.min(mouse.x,crossStockGapCanvas.width-1));
                                stocks.crossStockSelectedStep =
                                    step === stocks.crossStockSelectedStep ? -1 : step;
                            }
                        }
                    }
                }
                GohuText {
                    objectName: "marketCrossStockGapDetail"
                    width: parent.width
                    visible: stocks.showCrossStockGap && stocks.crossStockGap !== null
                    text: {
                        const d=stocks.crossStockGap;
                        if (!d) return "";
                        const step=stocks.crossStockSelectedStep;
                        const p=step>=0 && step<d.points.length ? d.points[step] : d.points[d.maxSteps];
                        return (step>=0 ? "SELECTED " : "LAST OBSERVED ") + p.date
                            + " // GAP " + p.value.toFixed(4) + " PP"
                            + "\n" + d.from + " TO " + d.to
                            + " // " + d.points.length + " COMMON CLOSE DATES"
                            + "\nCLICK EITHER CHART // SHARED CURSOR"
                            + "\nCUMULATIVE GAP // NOT DAILY RETURNS OR CALENDAR SPACING";
                    }
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 10
                    color: Colors.white
                }
            }
            Column {
                objectName: "marketResearchPriceSection"
                width: parent.width
                visible: stocks.dayMode || stocks.researchView === "price"
                height: visible ? implicitHeight : 0
                spacing: 13
                Rectangle {
                    objectName: "marketRangeAnalysisPanel"
                    width: parent.width
                    visible: !stocks.dayMode && stocks.rangeAnalysis !== null && stocks.controlsExpanded
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
                                + "\nHIGH " + stocks.priceUnit + stocks.rangeAnalysis.high.price.toFixed(2)
                                + " // " + stocks.rangeAnalysis.high.date
                                + "\nLOW " + stocks.priceUnit + stocks.rangeAnalysis.low.price.toFixed(2)
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
                    visible: stocks.dayMode
                    width: 136
                    height: visible ? 28 : 0
                    label: "BACK TO RANGE"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    available: stocks.dayMode
                    onLeftClicked: stocks.returnToRange()
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
                        onVisibleChanged: { if (visible) requestPaint(); }
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
                            + "\nORANGE SMA 5 // " + stocks.priceUnit
                            + stocks.averageOverlay.latest5.toFixed(2)
                            + "\nLILAC SMA 20 // "
                            + (stocks.averageOverlay.latest20 === null
                                ? "N/A // NEED 20 LOADED SESSIONS"
                                : stocks.priceUnit + stocks.averageOverlay.latest20.toFixed(2))
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
                                + (stocks.averageRelationship.spreadPrice < 0 ? "-" : "+") + stocks.priceUnit
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
                          + "\n" + stocks.snapshot.priceBasis + " // " + stocks.priceUnit
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
                                + " // " + stocks.priceUnit + stocks.selectedCloseComparison.selected.price.toFixed(2)
                                + "\nLAST " + stocks.selectedCloseComparison.last.date
                                + " // " + stocks.priceUnit + stocks.selectedCloseComparison.last.price.toFixed(2)
                                + "\nCHANGE " + (stocks.selectedCloseComparison.deltaPrice > 0 ? "+" : "")
                                + stocks.priceUnit + stocks.selectedCloseComparison.deltaPrice.toFixed(2)
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
                        ? ("PINNED A // " + stocks.pinnedPoint.date + " // " + stocks.priceUnit
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
                                + " // " + stocks.priceUnit + stocks.pinnedPairComparison.start.price.toFixed(2)
                                + "\nB " + stocks.pinnedPairComparison.end.date
                                + " // " + stocks.priceUnit + stocks.pinnedPairComparison.end.price.toFixed(2)
                                + "\nB MINUS A // "
                                + (stocks.pinnedPairComparison.deltaPrice < 0 ? "-" : "+") + stocks.priceUnit
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
                                + "\nHIGHEST CLOSE " + stocks.priceUnit
                                + stocks.pinnedInterval.high.price.toFixed(2)
                                + " // " + stocks.pinnedInterval.high.date
                                + "\nLOWEST CLOSE " + stocks.priceUnit
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
                        property var stepDetail: stocks.normalizedStepDetail
                        onStepDetailChanged: requestPaint()
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
                            const selected = stepDetail;
                            if (selected) {
                                const x = selected.step/chart.maxSteps*(width-1);
                                ctx.beginPath();
                                ctx.moveTo(x,0);
                                ctx.lineTo(x,height-1);
                                ctx.strokeStyle="#F2D24D";
                                ctx.lineWidth=1;
                                ctx.stroke();
                                function mark(observation,color) {
                                    if (!observation) return;
                                    const p=pointAt(observation);
                                    if (!p) return;
                                    ctx.beginPath();
                                    ctx.arc(p.x,p.y,4,0,Math.PI*2);
                                    ctx.fillStyle=color;
                                    ctx.fill();
                                    ctx.strokeStyle="#F2D24D";
                                    ctx.lineWidth=1.5;
                                    ctx.stroke();
                                }
                                mark(selected.first,"#55CFCA");
                                mark(selected.second,"#C74EC7");
                            }
                        }
                        MouseArea {
                            objectName: "marketNormalizedStepPicker"
                            anchors.fill: parent
                            enabled: stocks.normalizedComparison !== null
                            acceptedButtons: Qt.LeftButton
                            onClicked: function(mouse) {
                                const step=RangeAnalysisPolicy.normalizedStepAtX(
                                    normalizedCanvas.plot, normalizedCanvas.width,
                                    Math.min(mouse.x,normalizedCanvas.width-1));
                                stocks.normalizedSelectedStep =
                                    step === stocks.normalizedSelectedStep ? -1 : step;
                            }
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
                GohuText {
                    objectName: "marketNormalizedStepDetail"
                    width: parent.width
                    visible: stocks.normalizedComparison !== null
                    text: {
                        const d=stocks.normalizedStepDetail;
                        if (!d) return "CLICK NORMALIZED CHART TO INSPECT A SHARED STEP";
                        function describe(p) {
                            return p ? (p.date + " // INDEX " + p.value.toPrecision(6)
                                + " // " + p.changePct.toFixed(4) + "% FROM START")
                                : "N/A // INTERVAL ALREADY ENDED";
                        }
                        return "OBSERVED STEP " + d.step
                            + "\n1 // " + describe(d.first)
                            + "\n2 // " + describe(d.second)
                            + "\n2 MINUS 1 // " + (d.gapPoints === null
                                ? "N/A // NO SHARED OBSERVATION"
                                : d.gapPoints.toFixed(4) + " PERCENTAGE POINTS")
                            + "\nSAME STEP, NOT NECESSARILY SAME DATE // CLICK AGAIN TO CLEAR";
                    }
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.white
                }
                ActionButton {
                    id: openSelectedInDay
                    visible: !stocks.dayMode && stocks.inspectedPoint !== null
                    width: 136
                    height: visible ? 28 : 0
                    label: "OPEN IN DAY"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    available: stocks.globalHistoryActive && stocks.inspectedPoint !== null
                    onLeftClicked: stocks.openLoadedDay(stocks.selectedPointIndex)
                }
            }
            GohuText {
                width: parent.width
                text: "Historical closes are not live quotes or a price-reaction study. Adjusted prices can be recomputed after dividends and splits. Provider plan limits apply."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
        }
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
