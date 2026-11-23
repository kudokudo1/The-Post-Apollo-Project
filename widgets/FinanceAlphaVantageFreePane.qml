import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M19: explicitly selected Alpha Vantage free-tier raw daily closes.
// This is a different price feed, not a fallback/match from EODHD or OpenFIGI.
Rectangle {
    id: avPane
    property bool active: false
    signal exitRequested()
    color: Colors.black
    border.color: Colors.magenta
    border.width: 1
    clip: true

    FinanceServices.FinanceAlphaVantageFreeService {
        id: av
        monitoring: avPane.active
        onSnapshotChanged: avChart.requestPaint()
    }
    function inspectInstrument(item) {
        const chosen=av.chooseIdentity(item);
        if(chosen)avScroll.contentY=0;
        return chosen;
    }
    GohuText {
        id: heading
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.right: backButton.left
        anchors.rightMargin: 5
        text: "ALPHA VANTAGE // FREE DAILY PRICES"
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
        anchors.rightMargin: 8
        width: 113
        height: 28
        label: "BACK TO EODHD"
        labelPixelSize: 9
        accentColor: Colors.magenta
        onLeftClicked: avPane.exitRequested()
    }
    GohuText {
        id: footer
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: "25/DAY FREE // LOCAL PANEL ATTEMPTS "
            +av.requestsThisRuntime+"/25 (NOT ACCOUNT REMAINING)"
        textFormat: Text.PlainText
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
    Flickable {
        id: avScroll
        anchors.top: heading.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.bottom: footer.top
        anchors.bottomMargin: 9
        contentWidth: width
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: content
            width: Math.max(0,avScroll.width-23)
            spacing: 11
            GohuText {
                width: parent.width
                text: av.identity
                    ? (av.identity.name+" // "+av.identity.ticker
                        +" @ "+av.identity.exchCode
                        +"\nOPENFIGI "+av.identity.figi)
                    : "NO OPENFIGI IDENTITY SELECTED"
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "ALTERNATE FREE SOURCE // SEARCH USES AN INDEPENDENT FREE API KEY"
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }
            ActionButton {
                width: parent.width
                height: 30
                label: av.state==="looking" ? "SEARCHING ALPHA VANTAGE"
                    : "FIND ALPHA VANTAGE LISTINGS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: avPane.active && !!av.identity && !av.loading
                    && av.remainingRuntimeAllowance>0
                onLeftClicked: {
                    if(av.lookup())avScroll.contentY=0;
                }
            }
            GohuText {
                width: parent.width
                text: av.message
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: av.state==="failed" || av.state==="quota" ? Colors.red
                    : Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "CHOOSE A LISTING // CHECK COMPANY, REGION, CURRENCY & SYMBOL"
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
            }
            Repeater {
                model: av.candidates
                delegate: Rectangle {
                    required property var modelData
                    width: content.width
                    height: 94
                    color: Colors.dark
                    border.width: 1
                    border.color: av.selectedListing
                        && av.selectedListing.symbol===modelData.symbol
                        ? Colors.magenta : Colors.cyan
                    GohuText {
                        id: company
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.top: parent.top
                        anchors.topMargin: 6
                        text: modelData.symbol+" // "+modelData.name
                        textFormat: Text.PlainText
                        color: Colors.cyan
                        font.pixelSize: 10
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    GohuText {
                        anchors.left: company.left
                        anchors.right: company.right
                        anchors.top: company.bottom
                        anchors.topMargin: 6
                        text: modelData.region+" // "+modelData.currency
                            +" // "+modelData.type
                        textFormat: Text.PlainText
                        color: Colors.white
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 6
                        width: 82
                        height: 26
                        label: "SELECT"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        available: avPane.active && !av.loading
                        selected: av.selectedListing
                            && av.selectedListing.symbol===modelData.symbol
                        onLeftClicked: av.chooseListing(modelData)
                    }
                }
            }
            GohuText {
                width: parent.width
                visible: !!av.selectedListing
                text: av.selectedListing
                    ? "ALPHA LISTING // "+av.selectedListing.symbol
                        +"\n"+av.selectedListing.name+" // "
                        +av.selectedListing.region+" // "+av.selectedListing.currency
                        +"\nNOT VERIFIED AS SAME OPENFIGI INSTRUMENT"
                    : ""
                textFormat: Text.PlainText
                color: Colors.magenta
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "CHOOSE CALENDAR RANGE // 100 MOST RECENT TRADING SESSIONS MAX"
                color: Colors.cyan
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                id: presets
                width: content.width
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
                        selected: av.presetDays===modelData.days
                        available: avPane.active && !!av.selectedListing
                            && !av.loading
                        onLeftClicked: av.selectPreset(modelData.days)
                    }
                }
            }
            ActionButton {
                width: content.width
                height: 30
                label: av.state==="loading" ? "READING COMPACT HISTORY"
                    : "LOAD ALPHA VANTAGE DAILY CLOSES"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: avPane.active && !!av.selectedListing
                    && !av.loading && av.remainingRuntimeAllowance>0
                onLeftClicked: av.loadHistory()
            }
            GohuText {
                width: content.width
                text: av.ready
                    ? (av.snapshot.symbol+" // "+av.snapshot.currency
                        +" // UNADJUSTED CLOSE"
                        +"\nSOURCE ALPHA VANTAGE // "+av.snapshot.from
                        +" TO "+av.snapshot.to
                        +"\nRETURNED "+av.snapshot.returnedBars
                        +" MOST RECENT SESSIONS // IN RANGE "+av.snapshot.bars.length
                        +"\nFIRST "+(av.snapshot.first
                            ? av.snapshot.first.date+" "+av.snapshot.first.price.toFixed(2)
                            : "N/A")+" // LAST "+(av.snapshot.last
                            ? av.snapshot.last.date+" "+av.snapshot.last.price.toFixed(2)
                            : "N/A")
                        +"\nCHANGE "+(av.snapshot.changePct===null
                            ? "N/A" : av.snapshot.changePct.toFixed(2)+"%")
                        +(av.snapshot.compactMayBeTruncated
                            ? "\nWARNING // 100-SESSION LIMIT MAY OMIT EARLIER DATES"
                            : "")
                        +"\nFETCHED "+av.snapshot.retrievedAt)
                    : "NO ALPHA VANTAGE HISTORY LOADED"
                color: av.ready ? Colors.cyan : Colors.orange
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: content.width
                height: visible ? 166 : 0
                visible: av.ready && av.snapshot.bars.length>=2
                color: Colors.black
                border.color: Colors.cyan
                border.width: 1
                Canvas {
                    id: avChart
                    anchors.fill: parent
                    anchors.margins: 10
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx=getContext("2d");
                        ctx.clearRect(0,0,width,height);
                        const bars=av.ready ? av.snapshot.bars : [];
                        if(!bars || bars.length<2 || width<5 || height<5)return;
                        const values=bars.map(function(x){return x.price;});
                        const lo=Math.min.apply(null,values);
                        const hi=Math.max.apply(null,values);
                        const span=Math.max(0.00001,hi-lo);
                        ctx.beginPath();
                        for(let i=0;i<bars.length;i++) {
                            const x=i*(width-1)/(bars.length-1);
                            const y=(height-1)-(values[i]-lo)/span*(height-1);
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
                width: content.width
                text: "CURRENCY FROM ALPHA SEARCH LISTING, NOT DAILY API. "
                    +"RAW CLOSES MAY JUMP AT SPLITS / DIVIDENDS."
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
    }
    onActiveChanged: {
        if(active && av.ready)avChart.requestPaint();
    }
    NeonScrollBar {
        id: avScrollBar
        flickable: avScroll
        mountingParent: avPane
        geometryMode: "viewport"
        handleStyle: "bar"
        rightInset: 2
    }
}
