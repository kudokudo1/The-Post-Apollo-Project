import QtQuick
import "../components"

// SEC M3 selected document presentation. Pure UI; fetches only on INSPECT.
Item {
    id: inspector
    property var filing: null
    property var secFeed: null
    property var documentFeed: null
    readonly property bool supported: filing
        && ["4", "4/A", "8-K", "8-K/A"].indexOf(filing.form) >= 0
    readonly property var details: documentFeed && documentFeed.state === "ready"
        ? documentFeed.snapshot : null

    GohuText {
        id: heading
        anchors.top: parent.top
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: inspectButton.left
        anchors.rightMargin: 8
        text: filing ? filing.category : "SELECT A DISCLOSURE"
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    ActionButton {
        id: inspectButton
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 8
        width: 84
        height: 28
        label: documentFeed && documentFeed.loading ? "READING" : "INSPECT"
        labelPixelSize: 9
        accentColor: Colors.orange
        available: inspector.supported && documentFeed
            && documentFeed.monitoring && !documentFeed.loading
            && !inspector.details
        onLeftClicked: documentFeed.inspect(inspector.filing)
    }

    GohuText {
        id: status
        anchors.top: heading.bottom
        anchors.topMargin: 15
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        text: !filing ? "NO FILING SELECTED"
            : !inspector.supported ? "INDEX ONLY // DOCUMENT PARSER NOT AVAILABLE FOR THIS FORM"
            : documentFeed ? documentFeed.message : "DOCUMENT READER NOT CONNECTED"
        textFormat: Text.PlainText
        font.pixelSize: 9
        color: documentFeed && documentFeed.state === "failed" ? Colors.red : Colors.orange
        wrapMode: Text.WordWrap
    }

    Flickable {
        id: scroller
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: status.bottom
        anchors.bottom: parent.bottom
        anchors.margins: 9
        anchors.topMargin: 10
        contentWidth: width
        contentHeight: contents.height
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: contents
            width: scroller.width
            spacing: 10

            GohuText {
                width: parent.width
                text: filing ? "FORM " + filing.form + " // FILED " + filing.filedAt : ""
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: filing && filing.acceptedAt ? "ACCEPTED " + filing.acceptedAt : ""
                font.pixelSize: 9
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: "OFFICIAL SEC FILING URL"
                font.pixelSize: 10
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                text: inspector.details ? inspector.details.documentUrl
                    : filing ? filing.documentUrl : ""
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                font.pixelSize: 9
                color: Colors.cyan
            }

            GohuText {
                width: parent.width
                visible: inspector.details && inspector.details.kind === "form4"
                text: "FORM 4 // NON-DERIVATIVE TRANSACTIONS"
                font.pixelSize: 11
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                visible: inspector.details && inspector.details.kind === "form4"
                text: inspector.details && inspector.details.owners
                    ? "REPORTING OWNER(S): " + inspector.details.owners.join(", ")
                    : ""
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.white
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: inspector.details && inspector.details.kind === "form4"
                    ? inspector.details.transactions : []
                delegate: Rectangle {
                    id: transactionRow
                    required property var modelData
                    width: contents.width
                    height: transactionText.implicitHeight + 16
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        id: transactionText
                        anchors.top: parent.top
                        anchors.topMargin: 8
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        font.pixelSize: 10
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        text: transactionRow.modelData.kind
                            + " [" + transactionRow.modelData.code + "] // "
                            + transactionRow.modelData.date + "\n"
                            + transactionRow.modelData.security + "\n"
                            + "SHARES " + (transactionRow.modelData.shares || "N/A")
                            + " // PRICE " + (transactionRow.modelData.pricePerShare || "N/A")
                            + " // A/D " + transactionRow.modelData.acquiredDisposed
                            + (transactionRow.modelData.estimatedNotional
                                ? "\nEST. NOTIONAL " + transactionRow.modelData.estimatedNotional
                                : "")
                    }
                }
            }

            GohuText {
                width: parent.width
                visible: inspector.details && inspector.details.kind === "form8k"
                text: "8-K // REPORTED ITEM CLASSIFICATIONS"
                font.pixelSize: 11
                color: Colors.magenta
            }
            Repeater {
                model: inspector.details && inspector.details.kind === "form8k"
                    ? inspector.details.events : []
                delegate: Rectangle {
                    id: itemRow
                    required property var modelData
                    width: contents.width
                    height: eventText.implicitHeight + 16
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        id: eventText
                        anchors.top: parent.top
                        anchors.topMargin: 8
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        font.pixelSize: 10
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        text: "ITEM " + itemRow.modelData.item
                            + " // " + itemRow.modelData.category
                            + "\nSOURCE: " + itemRow.modelData.source
                            + (itemRow.modelData.excerpt
                                ? "\nNEAR HEADING: " + itemRow.modelData.excerpt : "")
                    }
                }
            }

            GohuText {
                width: parent.width
                text: inspector.details ? inspector.details.disclaimer
                    : "INDEX ONLY // Choose INSPECT for supported 4 and 8-K filings. No signal strength inferred."
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
            }
        }
    }
}
