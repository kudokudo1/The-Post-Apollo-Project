import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M18: scoped, manual EODHD free-tier price candidate and daily close viewer.
// Never substitutes EODHD's symbol/currency for OpenFIGI's FIGI/exchange.
Rectangle {
    id: priceView
    property bool active: false
    property bool alphaOpen: false
    signal exitRequested()
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true

    FinanceServices.FinanceGlobalPriceService {
        id: priceFeed
        monitoring: priceView.active
        onSnapshotChanged: historyChart.requestPaint()
    }
    function inspectInstrument(item) {
        const ok=priceFeed.chooseIdentity(item);
        if (ok) {
            alphaOpen=false;
            viewport.contentY=0;
        }
        return ok;
    }
    GohuText {
        id: heading
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: backButton.left
        anchors.rightMargin: 6
        text: "FREE DAILY PRICE OPTIONS // EODHD"
        font.pixelSize: 12
        font.bold: true
        color: Colors.cyan
        elide: Text.ElideRight
    }
    ActionButton {
        id: backButton
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 9
        width: 108
        height: 28
        label: "BACK TO SEARCH"
        labelPixelSize: 8
        accentColor: Colors.magenta
        onLeftClicked: priceView.exitRequested()
    }
    GohuText {
        id: footer
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: "EODHD FREE 20/DAY // PANEL ATTEMPTS "
            +priceFeed.requestsThisRuntime+"/20 (NOT ACCOUNT BALANCE)"
            +(priceFeed.sharedQuota
                ? "\nLOCAL SHARED RESERVED "+priceFeed.sharedQuota.reserved
                    +"/"+priceFeed.sharedQuota.limit+" // "+priceFeed.sharedQuota.utcDay
                : "\nLOCAL SHARED RESERVATION NOT YET READ")
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }
    Flickable {
        id: viewport
        anchors.top: heading.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.bottom: footer.top
        anchors.bottomMargin: 8
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: body
            width: Math.max(0,viewport.width-23)
            spacing: 10
            GohuText {
                width: parent.width
                text: "OPENFIGI SELECTION // IDENTITY ONLY"
                color: Colors.orange
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: priceFeed.identity
                    ? (priceFeed.identity.name+" // "+priceFeed.identity.ticker
                        +" @ "+priceFeed.identity.exchCode
                        +"\nFIGI "+priceFeed.identity.figi)
                    : "NO INSTRUMENT SELECTED"
                textFormat: Text.PlainText
                color: Colors.white
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "SECOND FREE PROVIDER // INDEPENDENT 25/DAY KEY"
                color: Colors.orange
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 30
                label: "ALPHA VANTAGE // FREE PRICE OPTIONS"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: priceView.active && !!priceFeed.identity
                onLeftClicked: {
                    if (!priceView.active || !priceFeed.identity) return;
                    priceView.alphaOpen=true;
                    if (!alphaPane.inspectInstrument(priceFeed.identity))
                        priceView.alphaOpen=false;
                }
            }
            GohuText {
                width: parent.width
                text: "1 // EODHD LISTINGS (SEPARATE FREE KEY REQUIRED)"
                color: Colors.cyan
                font.pixelSize: 10
            }
            ActionButton {
                width: body.width
                height: 30
                label: priceFeed.state==="looking" ? "SEARCHING EODHD"
                    : "FIND EODHD PRICE LISTINGS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: priceView.active && priceFeed.identity!==null
                    && !priceFeed.loading
                onLeftClicked: {
                    if (priceFeed.lookup()) viewport.contentY=0;
                }
            }
            GohuText {
                width: body.width
                text: priceFeed.message
                textFormat: Text.PlainText
                color: priceFeed.state==="failed" ? Colors.red : Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            GohuText {
                width: body.width
                text: "2 // COMPARE COMPANY / COUNTRY / EXCHANGE. A TICKER ALONE IS NOT PROOF."
                textFormat: Text.PlainText
                color: Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }
            Repeater {
                model: priceFeed.candidates
                delegate: Rectangle {
                    required property var modelData
                    width: body.width
                    height: 100
                    color: Colors.dark
                    border.width: 1
                    border.color: priceFeed.selectedListing
                        && priceFeed.selectedListing.symbol===modelData.symbol
                        ? Colors.magenta : Colors.cyan
                    GohuText {
                        id: candidateName
                        anchors.top: parent.top
                        anchors.topMargin: 6
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        text: modelData.symbol+" // "+modelData.name
                        textFormat: Text.PlainText
                        font.pixelSize: 10
                        color: Colors.cyan
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    GohuText {
                        id: candidateLocation
                        anchors.top: candidateName.bottom
                        anchors.topMargin: 6
                        anchors.left: candidateName.left
                        anchors.right: candidateName.right
                        text: modelData.country+" // "+modelData.currency
                            +" // "+modelData.type
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.white
                        elide: Text.ElideRight
                    }
                    GohuText {
                        anchors.top: candidateLocation.bottom
                        anchors.topMargin: 6
                        anchors.left: candidateName.left
                        anchors.right: selectCandidate.left
                        anchors.rightMargin: 6
                        text: modelData.isin ? "ISIN "+modelData.isin
                            : "ISIN NOT PROVIDED"
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        id: selectCandidate
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 6
                        width: 88
                        height: 25
                        label: "SELECT"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        available: !priceFeed.loading && priceView.active
                        selected: priceFeed.selectedListing
                            && priceFeed.selectedListing.symbol===modelData.symbol
                        onLeftClicked: priceFeed.chooseListing(modelData)
                    }
                }
            }
            GohuText {
                width: body.width
                visible: priceFeed.selectedListing!==null
                text: priceFeed.selectedListing
                    ? "YOUR EODHD CHOICE // "+priceFeed.selectedListing.symbol
                        +"\n"+priceFeed.selectedListing.name
                        +" // "+priceFeed.selectedListing.country
                        +" // "+priceFeed.selectedListing.currency
                        +"\nNOT FIGI VERIFIED // CHECK BOTH LISTINGS"
                    : ""
                color: Colors.magenta
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: body.width
                text: "3 // SELECT DAYS // MANUAL LOAD ONLY"
                font.pixelSize: 10
                color: Colors.cyan
            }
            Row {
                id: presets
                width: body.width
                height: 28
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
                        width: Math.max(0,(presets.width-18)/4)
                        height: 26
                        label: modelData.label
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        selected: priceFeed.presetDays===modelData.days
                        available: priceView.active && priceFeed.selectedListing
                            && !priceFeed.loading
                        onLeftClicked: priceFeed.selectPreset(modelData.days)
                    }
                }
            }
            ActionButton {
                width: body.width
                height: 31
                label: priceFeed.state==="loading" ? "READING EODHD"
                    : "LOAD SELECTED DAILY HISTORY"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: priceView.active && priceFeed.selectedListing
                    && !priceFeed.loading
                onLeftClicked: priceFeed.loadHistory()
            }
            GohuText {
                width: body.width
                text: priceFeed.ready
                    ? (priceFeed.snapshot.symbol+" // "+priceFeed.snapshot.currency
                        +" // "+priceFeed.snapshot.priceBasis
                        +"\nSOURCE EODHD EOD // "+priceFeed.snapshot.from
                        +" TO "+priceFeed.snapshot.to
                        +"\nSESSIONS "+priceFeed.snapshot.bars.length
                        +" // FETCHED "+priceFeed.snapshot.retrievedAt
                        +"\nFIRST "+(priceFeed.snapshot.first
                            ? priceFeed.snapshot.first.date+" "+
                                priceFeed.snapshot.first.price.toFixed(2)
                            : "N/A")
                        +" // LAST "+(priceFeed.snapshot.last
                            ? priceFeed.snapshot.last.date+" "+
                                priceFeed.snapshot.last.price.toFixed(2)
                            : "N/A")
                        +"\nCHANGE "+(priceFeed.snapshot.changePct===null
                            ? "N/A" : priceFeed.snapshot.changePct.toFixed(2)+"%"))
                    : "NO GLOBAL PRICE HISTORY LOADED"
                textFormat: Text.PlainText
                color: priceFeed.ready ? Colors.cyan : Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            Rectangle {
                width: body.width
                height: visible ? 166 : 0
                visible: priceFeed.ready && priceFeed.snapshot.bars.length>=2
                color: Colors.black
                border.color: Colors.cyan
                border.width: 1
                Canvas {
                    id: historyChart
                    anchors.fill: parent
                    anchors.margins: 10
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const bars=priceFeed.ready ? priceFeed.snapshot.bars : [];
                        if(bars.length<2 || width<5 || height<5)return;
                        const prices=bars.map(function(row){return row.price;});
                        const low=Math.min.apply(null,prices);
                        const high=Math.max.apply(null,prices);
                        const span=Math.max(0.00001,high-low);
                        ctx.beginPath();
                        for(let i=0;i<bars.length;i++) {
                            const x=i*(width-1)/(bars.length-1);
                            const y=(height-1)-(prices[i]-low)/span*(height-1);
                            if(i===0)ctx.moveTo(x,y);
                            else ctx.lineTo(x,y);
                        }
                        ctx.lineWidth=1.6;
                        ctx.strokeStyle="#55CFCA";
                        ctx.stroke();
                    }
                }
            }
            GohuText {
                width: body.width
                text: "HISTORICAL CLOSES ONLY // CURRENCY FROM EODHD SEARCH, NOT PRICE API"
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
    onActiveChanged: {
        if (!active) alphaOpen=false;
        if (active && priceFeed.ready) historyChart.requestPaint();
    }
    FinanceAlphaVantageFreePane {
        id: alphaPane
        anchors.fill: parent
        visible: priceView.alphaOpen
        active: priceView.active && priceView.alphaOpen
        z: 30
        onExitRequested: priceView.alphaOpen=false
    }
    NeonScrollBar {
        id: priceScrollBar
        flickable: viewport
        mountingParent: priceView
        geometryMode: "viewport"
        handleStyle: "bar"
        rightInset: 2
    }
}
