import QtQuick
import "../components"

// Account overview backed solely by the current authenticated Actual snapshot.
// Account creation/rename and bank reconciliation require separate guarded APIs.
Item {
    id: accountsPane
    property var snapshot: null
    property string selectedAccountId: ""
    signal newTransactionRequested()
    readonly property var accountRows: snapshot && Array.isArray(snapshot.accounts)
        ? snapshot.accounts : []
    readonly property var selectedAccount: {
        const rows=accountRows.filter(function(a){return a && a.id===selectedAccountId;});
        return rows.length===1 ? rows[0] : null;
    }
    readonly property var transactions: {
        if(!snapshot || !Array.isArray(snapshot.transactions)
                || !selectedAccount)return [];
        return snapshot.transactions.filter(function(t){
            return t && t.accountId===selectedAccountId;
        });
    }
    width: parent ? parent.width : 0
    height: body.implicitHeight
    onSnapshotChanged: {
        if(selectedAccountId && !accountRows.some(function(a){
            return a && a.id===selectedAccountId;
        }))selectedAccountId="";
    }
    Column {
        id: body
        width: accountsPane.width
        spacing: 7
        GohuText {
            width: parent.width
            text: "ACCOUNTS"
            font.pixelSize: 12
            color: Colors.omnitrix
        }
        GohuText {
            width: parent.width
            text: "BALANCES FROM ACTUAL // "+accountsPane.accountRows.length+" ACCOUNTS"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: accountsPane.accountRows
            delegate: ActionButton {
                required property var modelData
                width: body.width
                height: 32
                label: modelData.name+"  "+(modelData.balanceCents<0?"-":"")
                    +"$"+(Math.abs(modelData.balanceCents)/100).toFixed(2)
                labelPixelSize: 10
                accentColor: accountsPane.selectedAccountId===modelData.id
                    ? Colors.magenta : Colors.omnitrix
                trackLabelGlowLocally: true
                onLeftClicked: {
                    accountsPane.selectedAccountId=
                        accountsPane.selectedAccountId===modelData.id?"":modelData.id;
                }
            }
        }
        GohuText {
            width: parent.width
            visible: !!accountsPane.selectedAccount
            text: accountsPane.selectedAccount
                ? accountsPane.selectedAccount.name+" // RECENT MONTHLY ACTIVITY" : ""
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        Repeater {
            model: accountsPane.selectedAccount ? accountsPane.transactions : []
            delegate: Rectangle {
                required property var modelData
                width: body.width
                height: 36
                color: Colors.black
                border.color: Colors.cyan
                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.leftMargin: 5
                    anchors.topMargin: 3
                    width: parent.width-10
                    text: modelData.date+"  "+modelData.description
                    textFormat: Text.PlainText
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 5
                    anchors.bottomMargin: 2
                    text: (modelData.amountCents<0?"-":"")
                        +"$"+(Math.abs(modelData.amountCents)/100).toFixed(2)
                    textFormat: Text.PlainText
                    font.pixelSize: 9
                    color: modelData.amountCents<0 ? Colors.orange : Colors.omnitrix
                }
            }
        }
        GohuText {
            width: parent.width
            visible: !!accountsPane.selectedAccount && accountsPane.transactions.length===0
            text: "NO RECENT TRANSACTIONS IN THE DISPLAYED MONTH"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 28
            label: "NEW TRANSACTION"
            labelPixelSize: 9
            accentColor: Colors.orange
            trackLabelGlowLocally: true
            available: accountsPane.accountRows.length>0
            onLeftClicked: accountsPane.newTransactionRequested()
        }
        GohuText {
            width: parent.width
            text: "ACCOUNT CREATION / RENAME AND OPENING-BALANCE CORRECTION ARE NOT ACTIVE YET"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
