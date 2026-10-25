import QtQuick
import "../components"
import "FinanceStockModePolicy.js" as StockModePolicy
import "FinanceStockChartPointPolicy.js" as ChartPointPolicy

// Market STOCKS M12: chart-session selection in RANGE, without new price reads.
Item {
    id: stocks
    property var stockFeed: null
    readonly property var snapshot: stockFeed && stockFeed.ready
        ? stockFeed.snapshot : null
    readonly property var priceBars: snapshot && Array.isArray(snapshot.bars)
        ? snapshot.bars : []
    readonly property bool dayMode: stockFeed && stockFeed.displayMode === "day"
    readonly property var dayResult: dayMode && snapshot
        ? StockModePolicy.daySession(snapshot, stockFeed.dayDate) : null
    property int selectedPointIndex: -1
    readonly property var inspectedPoint: !dayMode
        ? ChartPointPolicy.selectedBar(priceBars, selectedPointIndex) : null

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
        priceCanvas.requestPaint();
    }
    onDayModeChanged: {
        selectedPointIndex = -1;
        priceCanvas.requestPaint();
    }
    onSelectedPointIndexChanged: priceCanvas.requestPaint()

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.right: parent.right
        text: "STOCKS // HISTORICAL DAILY PRICES"
        color: Colors.cyan
        font.pixelSize: 13
        font.bold: true
        elide: Text.ElideRight
    }
    Row {
        id: issuers
        anchors.top: title.bottom
        anchors.topMargin: 13
        anchors.left: parent.left
        anchors.right: parent.right
        height: 30
        spacing: 6
        Repeater {
            model: [
                {cik:"0000320193",symbol:"AAPL"},
                {cik:"0000789019",symbol:"MSFT"},
                {cik:"0001045810",symbol:"NVDA"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: Math.max(58, (issuers.width - 12) / 3)
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
    GohuText {
        id: dateLabel
        anchors.top: modeControls.bottom
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
                  : "AAPL // DEMO"
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
            width: scroll.width
            spacing: 13
            GohuText {
                width: parent.width
                text: stocks.dayMode
                    ? "Choose a calendar day and LOAD DAY. Weekends and market holidays may return NO TRADING SESSION."
                    : "Select an issuer and START/END dates, then LOAD RANGE. Dates are inclusive; only actual trading sessions appear."
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
                width: parent.width
                visible: !stocks.dayMode && stocks.priceBars.length >= 2
                text: "CYAN = DAILY CLOSES // CLICK A DATA POINT TO INSPECT // ORANGE = SELECTED"
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
}
