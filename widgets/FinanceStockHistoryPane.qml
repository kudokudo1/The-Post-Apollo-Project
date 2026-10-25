import QtQuick
import "../components"

// Market STOCKS M10: inclusive historical range, not an SEC event study.
// No request until the operator presses LOAD HISTORY.
Item {
    id: stocks
    property var stockFeed: null
    readonly property var snapshot: stockFeed && stockFeed.ready
        ? stockFeed.snapshot : null
    readonly property var priceBars: snapshot && Array.isArray(snapshot.bars)
        ? snapshot.bars : []
    onPriceBarsChanged: priceCanvas.requestPaint()

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

    GohuText {
        id: dateLabel
        anchors.top: issuers.bottom
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.right: parent.right
        text: "HISTORICAL RANGE // INCLUSIVE // MAX 180 DAYS"
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
        height: sideBySide ? 66 : 136
        Column {
            id: fromGroup
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
                : stocks.snapshot ? "REFRESH RANGE" : "LOAD RANGE"
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
                text: "Select an issuer and START/END dates, then LOAD RANGE. Dates are inclusive; only actual trading sessions appear."
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
                    ? "REQUESTED " + stocks.snapshot.from + " to " + stocks.snapshot.to
                        + "\nSESSIONS " + stocks.snapshot.bars.length
                        + "\nFIRST CLOSE " + (stocks.snapshot.first
                            ? stocks.snapshot.first.date + " // $"
                                + stocks.snapshot.first.price.toFixed(2) : "UNAVAILABLE")
                        + "\nLAST CLOSE " + (stocks.snapshot.last
                            ? stocks.snapshot.last.date + " // $"
                                + stocks.snapshot.last.price.toFixed(2) : "UNAVAILABLE")
                        + "\nLAST VS FIRST " + (stocks.snapshot.changePct === null
                            ? "N/A" : stocks.snapshot.changePct.toFixed(2) + "%")
                    : ""
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.white
            }
            Rectangle {
                width: parent.width
                height: visible ? 174 : 0
                visible: stocks.priceBars.length >= 2
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

                    }
                }
            }
            GohuText {
                width: parent.width
                visible: stocks.priceBars.length >= 2
                text: "CYAN = ACTUAL DAILY CLOSES // SELECTED RANGE IS INCLUSIVE"
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
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
