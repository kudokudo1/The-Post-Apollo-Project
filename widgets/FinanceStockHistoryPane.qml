import QtQuick
import "../components"

// Market STOCKS M9: stand-alone dated EOD view, not an SEC filing inspector.
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
        anchors.topMargin: 13
        anchors.left: parent.left
        anchors.right: parent.right
        text: "REFERENCE DATE // NOT AN SEC FILING DATE"
        textFormat: Text.PlainText
        font.pixelSize: 10
        color: Colors.orange
    }
    FinanceDateInput {
        id: dateInput
        anchors.top: dateLabel.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        value: stocks.stockFeed ? stocks.stockFeed.referenceDate : ""
        fallbackDate: stocks.stockFeed ? stocks.stockFeed.referenceDate : ""
        canEdit: !!stocks.stockFeed && !stocks.stockFeed.loading
        onValueEdited: function(value) {
            if (stocks.stockFeed) stocks.stockFeed.selectReferenceDate(value);
        }
    }
    Row {
        id: fetchControls
        anchors.top: dateInput.bottom
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
                : stocks.snapshot ? "REFRESH PRICE" : "LOAD HISTORY"
            labelPixelSize: 9
            accentColor: Colors.magenta
            available: stocks.stockFeed && stocks.stockFeed.monitoring
                && !stocks.stockFeed.loading
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
                text: "Select an issuer and a past reference date. The window spans 10 calendar days before and up to 14 days after the anchor, limited to dates already elapsed. This is NOT an event study."
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
                    ? "REFERENCE " + stocks.snapshot.filingDate
                        + "\nPRIOR SESSION " + (stocks.snapshot.previous
                            ? stocks.snapshot.previous.date + " // $"
                                + stocks.snapshot.previous.price.toFixed(2) : "UNAVAILABLE")
                        + "\nFOLLOWING SESSION " + (stocks.snapshot.next
                            ? stocks.snapshot.next.date + " // $"
                                + stocks.snapshot.next.price.toFixed(2) : "UNAVAILABLE")
                        + "\nNEXT VS PRIOR " + (stocks.snapshot.changePct === null
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
                        const anchor = stocks.snapshot.filingDate;
                        const index = bars.findIndex(function(x){ return x.date >= anchor; });
                        if (index >= 0) {
                            const x = index*(width-1)/(bars.length-1);
                            ctx.beginPath();
                            ctx.moveTo(x,0);
                            ctx.lineTo(x,height);
                            ctx.strokeStyle = "#ED981A";
                            ctx.lineWidth = 1;
                            ctx.stroke();
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                visible: stocks.priceBars.length >= 2
                text: "CYAN = DAILY CLOSE // ORANGE = REFERENCE DATE POSITION"
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                text: "Historical closes are not live quotes. The reference date is a comparison anchor, not a disclosure or evidence of a price reaction. Existing EODHD demo/key limits still apply."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
            }
        }
    }
}
