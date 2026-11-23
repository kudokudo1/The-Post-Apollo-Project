import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// M21 status only. Never launches provider APIs, reserves quota or resets DB.
Rectangle {
    id: quotaPane
    objectName: "marketQuotaRealPane"
    property bool active: false
    // M25: compact layouts keep all quota semantics visible without clipped copy.
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
        text: "LOCAL FREE API // QUOTA STATUS"
        textFormat: Text.PlainText
        color: Colors.cyan
        font.bold: true
        font.pixelSize: 13
        elide: Text.ElideRight
    }
    ActionButton {
        id: backButton
        objectName: "marketQuotaBackButton"
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.right: parent.right
        anchors.rightMargin: 9
        width: 112
        height: 32
        label: "BACK TO STOCKS"
        labelPixelSize: 10
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
        text: "TWO LOCAL PRICE READERS ONLY // "
            +"NOT ACCOUNT BALANCE // NO API CALLS // NO QUOTA RESET"
        textFormat: Text.PlainText
        color: Colors.orange
        wrapMode: Text.WordWrap
        font.pixelSize: 10
    }
    Flickable {
        id: scroll
        anchors.top: title.bottom
        anchors.topMargin: 10
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
            spacing: 12
            GohuText {
                width: parent.width
                text: "LOCAL SQLITE RESERVATIONS // NO PROVIDER REQUESTS"
                textFormat: Text.PlainText
                color: Colors.orange
                wrapMode: Text.WordWrap
                font.pixelSize: 11
            }
            ActionButton {
                width: body.width
                height: 34
                objectName: "marketQuotaRefreshButton"
                label: localQuota.loading ? "READING LOCAL STATUS"
                    : "REFRESH LOCAL STATUS"
                labelPixelSize: 11
                accentColor: Colors.cyan
                available: quotaPane.active && !localQuota.loading
                onLeftClicked: localQuota.refresh()
            }
            GohuText {
                width: body.width
                text: localQuota.message
                textFormat: Text.PlainText
                color: localQuota.unknown ? Colors.orange : Colors.cyan
                font.pixelSize: 12
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
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            Grid {
                id: grid
                objectName: "marketQuotaProviderGrid"
                width: body.width
                columns: width >= 560 ? 2 : 1
                rowSpacing: 8
                columnSpacing: 8
                Repeater {
                    model: localQuota.snapshot ? localQuota.snapshot.providers : [
                        {provider:"eodhd",limit:20,reserved:null,recordState:"unknown"},
                        {provider:"alpha-vantage",limit:25,reserved:null,recordState:"unknown"}
                    ]
                    delegate: Rectangle {
                        objectName: "marketQuotaProviderCard"
                        required property var modelData
                        width: Math.max(0,(grid.width - (grid.columns-1)*8)/grid.columns)
                        height: 142
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
                            font.pixelSize: 13
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
                            font.pixelSize: 12
                        }
                        Rectangle {
                            id: barBackground
                            anchors.top: number.bottom
                            anchors.topMargin: 8
                            anchors.left: number.left
                            anchors.right: number.right
                            height: 10
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
                            objectName: "marketQuotaProviderContext"
                            text: modelData.recordState==="known"
                                ? ("LOCAL UNRESERVED "+(modelData.limit-modelData.reserved)
                                    +" // OTHER APP USE UNKNOWN")
                                : "NO USAGE CONCLUSION // NO ZERO ASSUMED"
                            textFormat: Text.PlainText
                            color: Colors.orange
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
            GohuText {
                width: body.width
                text: "ZERO LOCAL RESERVED DOES NOT MEAN ZERO PROVIDER USAGE. "
                    +"LEGACY SIX-STOCK READER, OTHER DEVICES AND OUTSIDE "
                    +"REQUESTS ARE EXCLUDED."
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: body.width
                text: "MISSING, BUSY OR UNTRUSTED LEDGER = UNKNOWN. "
                    +"NO DATABASE CREATE, RESET OR REPAIR. REFRESH TO RECHECK."
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 11
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
