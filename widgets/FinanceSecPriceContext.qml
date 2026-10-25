import QtQuick
import "../components"

// SEC M5. Market-context disclosure view, not a chart of causation.
// Prices are from EODHD and refer to exchange closing sessions.
Item {
    id: context
    property var filing: null
    property var priceFeed: null
    readonly property var marketSnapshot: priceFeed && priceFeed.state === "ready"
        ? priceFeed.snapshot : null
    readonly property var bars: marketSnapshot && Array.isArray(marketSnapshot.bars) ? marketSnapshot.bars : []
    readonly property bool hasPair: marketSnapshot && marketSnapshot.previous && marketSnapshot.next
    implicitHeight: contents.implicitHeight
    onMarketSnapshotChanged: sparkline.requestPaint()

    Column {
        id: contents
        width: parent.width
        spacing: 9

        Row {
            width: parent.width
            height: 28
            spacing: 10
            ActionButton {
                id: loadButton
                width: 120
                height: 28
                label: priceFeed && priceFeed.loading ? "READING"
                    : context.marketSnapshot ? "REFRESH PRICE" : "PRICE CONTEXT"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: context.filing && priceFeed && priceFeed.monitoring
                    && !priceFeed.loading
                onLeftClicked: priceFeed.inspect(context.filing)
            }
            GohuText {
                width: Math.max(0, parent.width - loadButton.width - 10)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
                color: Colors.orange
                text: priceFeed && priceFeed.secFeed
                    && priceFeed.secFeed.selectedCik === "0000789019"
                    ? "MSFT // DEMO ACCESS TRIAL"
                    : priceFeed && priceFeed.secFeed
                    && priceFeed.secFeed.selectedCik === "0001045810"
                    ? "NVDA // TOKEN-GATED"
                    : "AAPL // DEMO ACCESS"
                elide: Text.ElideRight
            }
        }
        GohuText {
            width: parent.width
            text: priceFeed ? priceFeed.message : "PRICE READER NOT CONNECTED"
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: priceFeed && priceFeed.state === "failed" ? Colors.red : Colors.orange
            font.pixelSize: 9
        }

        GohuText {
            width: parent.width
            visible: !!context.marketSnapshot
            text: context.marketSnapshot ? context.marketSnapshot.symbol + " // " + context.marketSnapshot.priceBasis
                + " // EODHD HISTORICAL" : ""
            textFormat: Text.PlainText
            font.pixelSize: 11
            color: Colors.cyan
        }
        GohuText {
            width: parent.width
            visible: !!context.marketSnapshot
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            color: Colors.orange
            text: context.marketSnapshot && context.marketSnapshot.delivery
                ? "PATH " + context.marketSnapshot.delivery.via
                    + " // " + context.marketSnapshot.delivery.state
                    + (context.marketSnapshot.delivery.cachedAt
                        ? "\nCACHED AT " + context.marketSnapshot.delivery.cachedAt : "")
                    + "\nSERVED AT " + context.marketSnapshot.delivery.servedAt
                : "DELIVERY PATH UNVERIFIED"
        }
        GohuText {
            width: parent.width
            visible: !!context.marketSnapshot
            text: context.marketSnapshot
                ? "SEC FILED: " + context.marketSnapshot.filingDate
                  + "\nPRIOR CLOSE: " + (context.marketSnapshot.previous
                      ? "$" + context.marketSnapshot.previous.price.toFixed(2)
                          + " (" + context.marketSnapshot.previous.date + ")" : "UNAVAILABLE")
                  + "\nNEXT CLOSE: " + (context.marketSnapshot.next
                      ? "$" + context.marketSnapshot.next.price.toFixed(2)
                          + " (" + context.marketSnapshot.next.date + ")" : "NOT YET AVAILABLE")
                  + "\nNEXT VS PRIOR: " + (context.marketSnapshot.changePct === null
                      ? "N/A" : context.marketSnapshot.changePct.toFixed(2) + "%")
                : ""
            textFormat: Text.PlainText
            font.pixelSize: 10
            color: Colors.white
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: visible ? 104 : 0
            visible: context.bars.length >= 2
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Canvas {
                id: sparkline
                anchors.fill: parent
                anchors.margins: 8
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0,0,width,height);
                    const points = context.bars;
                    if (!points || points.length < 2 || width < 5 || height < 5)
                        return;
                    const values = points.map(function(p) { return p.price; });
                    const low = Math.min.apply(null,values);
                    const high = Math.max.apply(null,values);
                    const range = Math.max(high-low,0.00001);
                    ctx.beginPath();
                    for (let i=0; i<points.length; i++) {
                        const x = i*(width-1)/(points.length-1);
                        const y = (height-1) - (values[i]-low)/range*(height-1);
                        if (i===0) ctx.moveTo(x,y);
                        else ctx.lineTo(x,y);
                    }
                    ctx.strokeStyle = "#55CFCA";
                    ctx.lineWidth = 1.6;
                    ctx.stroke();
                    // Observational filing date position, not a claim about
                    // when this information became available intraday.
                    let index = points.findIndex(function(p) {
                        return p.date >= context.marketSnapshot.filingDate;
                    });
                    if (index >= 0) {
                        const px = index*(width-1)/(points.length-1);
                        ctx.beginPath();
                        ctx.moveTo(px,0);
                        ctx.lineTo(px,height);
                        ctx.strokeStyle = "#ED981A";
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            visible: !!context.marketSnapshot
            text: "LINE = DAILY CLOSING PRICE // ORANGE = FILING-DATE POSITION"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "Closing sessions do not establish a filing reaction. Same-day close, filing acceptance time, news, splits and other events may matter. Third-party prices may be adjusted or delayed."
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
    }
}
