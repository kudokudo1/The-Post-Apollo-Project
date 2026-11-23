import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M21 status only. Never launches provider APIs, reserves quota or resets DB.
Rectangle {
    id: quotaPane
    objectName: "marketQuotaRealPane"
    property bool active: false
    signal exitRequested()
    color: Colors.black
    border.width: 1
    border.color: Colors.cyan
    clip: true

    FinanceServices.FinanceMarketQuotaStatusService {
        id: localQuota
        monitoring: quotaPane.active
    }

    GohuText {
        id: title
        anchors.top: parent.top
        anchors.topMargin: 11
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: backButton.left
        anchors.rightMargin: 5
        text: "FREE PRICE API // LOCAL QUOTA STATUS"
        textFormat: Text.PlainText
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 12
        elide: Text.ElideRight
    }
    ActionButton {
        id: backButton
        objectName: "marketQuotaBackButton"
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 9
        width: 98
        height: 29
        label: "BACK TO STOCKS"
        labelPixelSize: 9
        accentColor: Colors.magenta
        onLeftClicked: quotaPane.exitRequested()
    }
    GohuText {
        id: footer
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 10
        text: "POST-APOLLO'S TWO GLOBAL PRICE READERS ONLY // "
            +"NOT ACCOUNT BALANCE // NO API CALLS // NO QUOTA RESET"
        textFormat: Text.PlainText
        color: Colors.orange
        wrapMode: Text.WordWrap
        font.pixelSize: 9
    }
    Flickable {
        id: scroll
        anchors.top: title.bottom
        anchors.topMargin: 13
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.bottom: footer.top
        anchors.bottomMargin: 7
        contentWidth: width
        contentHeight: body.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        Column {
            id: body
            width: Math.max(0,scroll.width-20)
            spacing: 11
            GohuText {
                width: parent.width
                text: "READS THE LOCAL SQLite LEDGER // NEVER CONTACTS EODHD OR ALPHA"
                textFormat: Text.PlainText
                color: Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }
            ActionButton {
                width: body.width
                height: 30
                objectName: "marketQuotaRefreshButton"
                label: localQuota.loading ? "READING LOCAL STATUS"
                    : "REFRESH LOCAL STATUS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: quotaPane.active && !localQuota.loading
                onLeftClicked: localQuota.refresh()
            }
            GohuText {
                width: body.width
                text: localQuota.message
                textFormat: Text.PlainText
                color: localQuota.unknown ? Colors.orange : Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: body.width
                text: localQuota.snapshot
                    ? ("UTC DAY "+localQuota.snapshot.utcDay
                        +" // "+localQuota.snapshot.ledgerState.toUpperCase())
                    : "NO LOCAL QUOTA SNAPSHOT LOADED"
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Grid {
                id: grid
                width: body.width
                columns: width >= 500 ? 2 : 1
                rowSpacing: 8
                columnSpacing: 8
                Repeater {
                    model: localQuota.snapshot ? localQuota.snapshot.providers : [
                        {provider:"eodhd",limit:20,reserved:null,recordState:"unknown"},
                        {provider:"alpha-vantage",limit:25,reserved:null,recordState:"unknown"}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: Math.max(0,(grid.width - (grid.columns-1)*8)/grid.columns)
                        height: 112
                        color: Colors.dark
                        border.width: 1
                        border.color: modelData.recordState==="known"
                            ? Colors.cyan : Colors.orange
                        GohuText {
                            id: providerTitle
                            anchors.top: parent.top
                            anchors.topMargin: 8
                            anchors.left: parent.left
                            anchors.leftMargin: 9
                            anchors.right: parent.right
                            anchors.rightMargin: 9
                            text: modelData.provider==="eodhd" ? "EODHD" : "ALPHA VANTAGE"
                            textFormat: Text.PlainText
                            font.pixelSize: 12
                            font.bold: true
                            color: Colors.cyan
                        }
                        GohuText {
                            id: number
                            objectName: "marketQuotaReservedLabel"
                            anchors.top: providerTitle.bottom
                            anchors.topMargin: 7
                            anchors.left: providerTitle.left
                            anchors.right: providerTitle.right
                            text: modelData.recordState==="known"
                                ? ("LOCAL RESERVED "+modelData.reserved
                                    +" / "+modelData.limit)
                                : "LOCAL RESERVED UNKNOWN"
                            textFormat: Text.PlainText
                            color: modelData.recordState==="known" ? Colors.white
                                : Colors.orange
                            font.pixelSize: 10
                        }
                        Rectangle {
                            id: barBackground
                            anchors.top: number.bottom
                            anchors.topMargin: 8
                            anchors.left: number.left
                            anchors.right: number.right
                            height: 8
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Rectangle {
                                width: modelData.recordState==="known"
                                    ? Math.max(0, (barBackground.width-2)
                                        *modelData.reserved/modelData.limit)
                                    : 0
                                height: parent.height-2
                                anchors.left: parent.left
                                anchors.leftMargin: 1
                                anchors.verticalCenter: parent.verticalCenter
                                color: Colors.orange
                            }
                        }
                        GohuText {
                            anchors.top: barBackground.bottom
                            anchors.topMargin: 5
                            anchors.left: number.left
                            anchors.right: number.right
                            text: modelData.recordState==="known"
                                ? ("LOCAL UNRESERVED "+(modelData.limit-modelData.reserved)
                                    +" // OTHER APP USE UNKNOWN")
                                : "NO USAGE CONCLUSION // NO ZERO ASSUMED"
                            textFormat: Text.PlainText
                            color: Colors.orange
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
            GohuText {
                width: body.width
                text: "ZERO LOCAL RESERVED DOES NOT MEAN ZERO PROVIDER USAGE. "
                    +"THE LEGACY SIX-STOCK READER, OTHER DEVICES AND OUTSIDE "
                    +"REQUESTS ARE NOT INCLUDED."
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: body.width
                text: "IF THE LEDGER IS MISSING, BUSY OR UNTRUSTED, "
                    +"STATUS REMAINS UNKNOWN. THIS SCREEN NEVER CREATES, "
                    +"RESETS OR REPAIRS THE DATABASE. PRESS REFRESH TO RECHECK."
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
    NeonScrollBar {
        id: quotaScrollBar
        flickable: scroll
        mountingParent: quotaPane
        geometryMode: "viewport"
        handleStyle: "bar"
        rightInset: 2
    }
}
