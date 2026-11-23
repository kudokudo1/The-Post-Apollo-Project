import QtQuick
import "../components"
import "FinanceBankingProviderPolicy.js" as ProviderPolicy

// Banking M4: provider-specific Post-Apollo navigation over M3 manual/demo
// snapshots only. Restricted features are informative, never actionable.
Item {
    id: providerPane
    property string providerId: ""
    property var accountSnapshot: ({ok:false})
    property string sectionId: "home"
    readonly property var details: ProviderPolicy.build(
        providerId,accountSnapshot,sectionId)
    signal accountRequested(string accountId)
    implicitHeight: providerContent.implicitHeight

    onProviderIdChanged: sectionId="home"

    Column {
        id: providerContent
        width: providerPane.width
        spacing: 8

        GohuText {
            width: parent.width
            text: providerPane.details.ok
                ? providerPane.details.providerName.toUpperCase()+" // PROVIDER WORKSPACE"
                : "UNKNOWN PROVIDER // NO DATA"
            font.pixelSize: 12
            font.bold: true
            color: Colors.magenta
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "POST-APOLLO VIEW // NOT THE ORIGINAL APP // NO PROVIDER LOGIN"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
            text: providerPane.details.dataLabel+" // "
                +providerPane.details.accountCount+" CASH ACCOUNTS // "
                +providerPane.details.transactionCount+" MANUAL/DEMO ENTRIES"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
            text: providerPane.details.totalCents!==null
                ? (providerPane.accountSnapshot.mode==="demo"
                   ? "FICTIONAL PROVIDER CASH TOTAL // ":"MANUAL PROVIDER CASH ESTIMATE // ")
                   +ProviderPolicy.money(providerPane.details.totalCents)
                : providerPane.details.accountCount===0
                  ? "NO CASH ACCOUNTS RECORDED IN THIS SESSION"
                  : "PARTIAL KNOWN CASH AMOUNT // "
                    +ProviderPolicy.money(providerPane.details.knownSubtotalCents)
                    +" // "+providerPane.details.unknownCount+" UNKNOWN"
            font.pixelSize: 10
            font.bold: true
            color: providerPane.details.totalCents===null?Colors.orange:Colors.omnitrix
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "CASH ACCOUNTS ONLY // STOCKS, CREDIT AND BORROWING ARE NOT INCLUDED IN CASH TOTALS"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Grid {
            id: featuresGrid
            width: parent.width
            columns: 2
            spacing: 5
            Repeater {
                model: providerPane.details.ok?providerPane.details.features:[]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(0,(featuresGrid.width-5)/2)
                    height: 30
                    label: modelData.label
                    labelPixelSize: 9
                    accentColor: modelData.kind==="restricted"?Colors.orange:Colors.cyan
                    selected: providerPane.details.sectionId===modelData.id
                    onLeftClicked: providerPane.sectionId=modelData.id
                }
            }
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
            text: providerPane.details.sectionLabel+" // "+providerPane.details.accessLabel
            font.pixelSize: 11
            font.bold: true
            color: providerPane.details.sectionKind==="restricted"
                ? Colors.orange:Colors.omnitrix
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
            text: providerPane.details.sectionSummary
            font.pixelSize: 10
            color: Colors.white
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
                &&providerPane.details.sectionKind==="restricted"
            text: "NOT CONNECTED // FEATURE INFORMATION ONLY // OPEN THE OFFICIAL PROVIDER APP FOR REAL ACTIONS"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
                &&(providerPane.details.sectionKind==="accounts"
                    ||providerPane.details.sectionKind==="product")
                &&providerPane.details.visibleAccounts.length===0
            text: "NO MATCHING MANUAL CASH ACCOUNTS. GO BACK TO ACCOUNTS TO ADD ONE OR LOAD A FICTIONAL DEMO."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: providerPane.details.ok?providerPane.details.visibleAccounts:[]
            delegate: Rectangle {
                id: providerAccountCard
                required property var modelData
                width: providerContent.width
                height: providerAccountContents.implicitHeight+14
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: providerAccountContents
                    x: 7
                    y: 7
                    width: providerAccountCard.width-14
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: modelData.productName.toUpperCase()
                             +" // "+modelData.nickname
                        font.pixelSize: 10
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: modelData.balanceCents===null
                            ? "BALANCE UNKNOWN"
                            : (providerPane.accountSnapshot.mode==="demo"
                                ? "FICTIONAL CASH BALANCE // ":"MANUAL CASH ESTIMATE // ")
                                +ProviderPolicy.money(modelData.balanceCents)
                        font.pixelSize: 10
                        color: modelData.balanceCents===null
                             ? Colors.orange:Colors.omnitrix
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 28
                        label: "OPEN ACCOUNT DETAILS"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        onLeftClicked: providerPane.accountRequested(modelData.id)
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
                     &&providerPane.details.sectionKind==="activity"
                     &&providerPane.details.activity.length===0
            text: "NO MANUAL OR FICTIONAL ACTIVITY FOR THIS PROVIDER"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: providerPane.details.ok?providerPane.details.activity:[]
            delegate: Rectangle {
                id: providerActivityCard
                required property var modelData
                width: providerContent.width
                height: providerActivityContents.implicitHeight+12
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: providerActivityContents
                    x: 6
                    y: 6
                    width: providerActivityCard.width-12
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: modelData.date+" // "+ProviderPolicy.money(modelData.amountCents)
                            +" // "+modelData.accountNickname
                        font.pixelSize: 9
                        color: modelData.amountCents<0?Colors.orange:Colors.omnitrix
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: modelData.description
                        font.pixelSize: 9
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            text: "NO VERIFIED BALANCES, PAYMENTS, CARDS, STOCKS OR LOANS // VIEW AND NAVIGATION ONLY"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
