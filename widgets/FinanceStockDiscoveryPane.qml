import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M17: no-account worldwide equity identity search. No prices or orders.
Item {
    id: discovery
    implicitHeight: footer.y + footer.height + 8
    property bool active: false
    property bool priceOptionsOpen: false
    signal exitRequested()
    signal quotaRequested()
    signal historyChosen(var identity, var listing, var snapshot)
    onActiveChanged: {
        if (!active) priceOptionsOpen = false;
    }
    function inspectPrice(item) {
        if (!active || finder.loading || !finder.ready || !item
                || !finder.snapshot.items.some(function(row) {
                    return row.figi===item.figi
                        && row.ticker===item.ticker
                        && row.exchCode===item.exchCode
                        && row.name===item.name;
                })) return false;
        priceOptionsOpen=true;
        if (!globalPrices.inspectInstrument(item)) {
            priceOptionsOpen=false;
            return false;
        }
        return true;
    }

    FinanceServices.FinanceStockDiscoveryService {
        id: finder
        monitoring: discovery.active
    }
    function searchNow() {
        if (finder.search(queryInput.text)) priceOptionsOpen=false;
    }

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: quotaButton.left
        anchors.rightMargin: 6
        text: "CONTROLS // GLOBAL STOCK SEARCH"
        font.pixelSize: 12
        font.bold: true
        color: Colors.cyan
        elide: Text.ElideRight
    }
    ActionButton {
        id: quotaButton
        anchors.top: returnButton.top
        anchors.right: returnButton.left
        anchors.rightMargin: 5
        width: 74
        height: 27
        label: "QUOTA"
        labelPixelSize: 9
        accentColor: Colors.orange
        onLeftClicked: discovery.quotaRequested()
    }
    ActionButton {
        id: returnButton
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 9
        width: 94
        height: 27
        label: "HIDE"
        labelPixelSize: 9
        accentColor: Colors.magenta
        onLeftClicked: discovery.exitRequested()
    }
    GohuText {
        id: intro
        anchors.top: title.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: "FREE // NO LOGIN // GLOBAL LISTED EQUITIES // MANUAL SEARCH ONLY"
        font.pixelSize: 9
        textFormat: Text.PlainText
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
    Rectangle {
        id: queryFrame
        anchors.top: intro.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        height: 34
        color: Colors.dark
        border.color: queryInput.activeFocus ? Colors.magenta : Colors.cyan
        border.width: 1
        GohuText {
            anchors.fill: parent
            anchors.margins: 8
            visible: queryInput.text.length===0
            text: "Company or ticker, e.g. ASML, SONY, APPLE"
            color: Colors.orange
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        TextInput {
            id: queryInput
            anchors.fill: parent
            anchors.margins: 8
            color: Colors.white
            font.pixelSize: 12
            maximumLength: 80
            selectByMouse: true
            clip: true
            verticalAlignment: TextInput.AlignVCenter
            onAccepted: discovery.searchNow()
        }
    }
    Row {
        id: controls
        anchors.top: queryFrame.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        height: 29
        spacing: 6
        ActionButton {
            width: (controls.width - 6)/2
            height: 27
            label: finder.loading ? "SEARCHING" : "SEARCH"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: discovery.active && !finder.loading
                && queryInput.text.trim().length>=2
            onLeftClicked: discovery.searchNow()
        }
        ActionButton {
            width: (controls.width - 6)/2
            height: 27
            label: "NEXT PAGE"
            labelPixelSize: 10
            accentColor: Colors.magenta
            available: discovery.active && finder.canNext && !finder.loading
            onLeftClicked: {
                if (finder.nextPage()) discovery.priceOptionsOpen=false;
            }
        }
    }
    GohuText {
        id: status
        anchors.top: controls.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: finder.message
        textFormat: Text.PlainText
        font.pixelSize: 9
        wrapMode: Text.WordWrap
        color: finder.state==="failed" ? Colors.red : Colors.orange
    }
    GohuText {
        id: summary
        anchors.top: status.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: finder.ready
            ? ("QUERY "+finder.snapshot.query+" // RESULTS THIS PAGE "
                +finder.snapshot.items.length
                +" // FETCHED "+finder.snapshot.retrievedAt)
            : "OPENFIGI / NO RESULTS LOADED"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: Colors.cyan
        elide: Text.ElideRight
    }
    Item {
        id: resultScroll
        anchors.top: summary.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        visible: !discovery.priceOptionsOpen
        height: visible ? results.implicitHeight : 0
        Column {
            id: results
            width: resultScroll.width
            spacing: 6
            Repeater {
                model: finder.ready ? finder.snapshot.items : []
                delegate: Rectangle {
                    required property var modelData
                    width: results.width
                    height: 105
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        id: listing
                        anchors.top: parent.top
                        anchors.topMargin: 6
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        text: modelData.ticker+" // "+modelData.exchCode
                        textFormat: Text.PlainText
                        color: Colors.cyan
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    GohuText {
                        id: company
                        anchors.top: listing.bottom
                        anchors.topMargin: 4
                        anchors.left: listing.left
                        anchors.right: listing.right
                        text: modelData.name
                        textFormat: Text.PlainText
                        color: Colors.white
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                    GohuText {
                        anchors.top: company.bottom
                        anchors.topMargin: 4
                        anchors.left: listing.left
                        anchors.right: listing.right
                        text: modelData.securityType+" // FIGI "+modelData.figi
                        textFormat: Text.PlainText
                        color: Colors.orange
                        font.pixelSize: 9
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 5
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        width: 132
                        height: 25
                        label: "PRICE OPTIONS"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        available: discovery.active && finder.ready
                            && !finder.loading
                        onLeftClicked: discovery.inspectPrice(modelData)
                    }
                }
            }
        }
    }
    FinanceGlobalPricePane {
        id: globalPrices
        objectName: "marketInlineEodhdControls"
        anchors.top: summary.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible ? implicitHeight : 0
        visible: discovery.priceOptionsOpen
        active: discovery.active && discovery.priceOptionsOpen
        onExitRequested: discovery.priceOptionsOpen = false
        onHistoryChosen: function(identity, listing, snapshot) {
            if (discovery.active && discovery.priceOptionsOpen)
                discovery.historyChosen(identity,listing,snapshot);
        }
    }
    GohuText {
        id: footer
        anchors.top: discovery.priceOptionsOpen ? globalPrices.bottom : resultScroll.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: "OPENFIGI IDENTITIES // PRICE OPTIONS USE OPTIONAL FREE EODHD KEY"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
}
