import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M17: no-account worldwide equity identity search. No prices or orders.
Rectangle {
    id: discovery
    property bool active: false
    signal exitRequested()
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true

    FinanceServices.FinanceStockDiscoveryService {
        id: finder
        monitoring: discovery.active
    }
    function searchNow() {
        if (finder.search(queryInput.text)) resultScroll.contentY=0;
    }

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: returnButton.left
        anchors.rightMargin: 6
        text: "GLOBAL STOCK SEARCH // OPENFIGI"
        font.pixelSize: 12
        font.bold: true
        color: Colors.cyan
        elide: Text.ElideRight
    }
    ActionButton {
        id: returnButton
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 9
        width: 94
        height: 27
        label: "HISTORY"
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
                if (finder.nextPage()) resultScroll.contentY=0;
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
    Flickable {
        id: resultScroll
        anchors.top: summary.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.bottom: footer.top
        anchors.bottomMargin: 7
        contentWidth: width
        contentHeight: results.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        Column {
            id: results
            width: Math.max(0,resultScroll.width-22)
            spacing: 6
            Repeater {
                model: finder.ready ? finder.snapshot.items : []
                delegate: Rectangle {
                    required property var modelData
                    width: results.width
                    height: 76
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
                }
            }
        }
    }
    NeonScrollBar {
        id: discoveryScrollBar
        flickable: resultScroll
        mountingParent: discovery
        geometryMode: "viewport"
        handleStyle: "bar"
        rightInset: 2
    }
    GohuText {
        id: footer
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: "IDENTITIES ONLY // NO PRICE FEED LINKED // FREE SEARCH LIMIT 5/MIN"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: Colors.orange
        wrapMode: Text.WordWrap
    }
}
