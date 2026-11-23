import QtQuick
import "../components"
import "FinanceBankingAccountsPolicy.js" as Accounts
import "FinanceBankingProviderPolicy.js" as ProviderPolicy

// Banking M3: one-person manual account session; completely separate from
// CSV M1/M2 and any provider/auth/Actual service. No file, Process or network.
Item {
    id: manager
    property bool active: false
    property var session: Accounts.emptyState()
    property string view: "overview" // overview | provider | detail
    property string selectedId: ""
    property string selectedProviderId: ""
    property string detailReturnView: "overview"
    property int providerIndex: 0
    property int productIndex: 0
    property string direction: "out"
    property bool createOpen: false
    property bool deleteArmed: false
    property bool clearDemoArmed: false
    property string message: ""
    readonly property var providerChoices: Accounts.providers()
    readonly property var selectedProvider: providerChoices[providerIndex]
    readonly property var productChoices: selectedProvider.products
    readonly property var review: Accounts.snapshot(session)
    readonly property var selected: review.ok
        ? review.accounts.find(function(a){return a.id===selectedId;}) || null : null

    signal returnToTopRequested()
    width: parent ? parent.width : 0
    implicitHeight: layout.implicitHeight

    onProviderIndexChanged: productIndex=0
    onViewChanged: {
        deleteArmed=false;
        clearDemoArmed=false;
        returnToTopRequested();
    }
    onSelectedIdChanged: {
        deleteArmed=false;
        direction="out";
    }
    function createAccount() {
        const res=Accounts.addAccount(session,{
            providerId:selectedProvider.id,
            productId:productChoices[productIndex].id,
            nickname:nicknameInput.text,
            openingText:openingInput.text
        });
        if(!res.ok) {
            message=res.error;
            return false;
        }
        session=res.state;
        selectedId=res.account.id;
        detailReturnView="overview";
        createOpen=false;
        nicknameInput.text="";
        openingInput.text="";
        message="MANUAL ACCOUNT CREATED // NOT CONNECTED // SESSION ONLY";
        view="detail";
        return true;
    }
    function loadDemo() {
        if(session.mode!=="empty") {
            message="CLEAR EXISTING SESSION BEFORE LOADING A FICTIONAL DEMO";
            return false;
        }
        const res=Accounts.sampleDemo();
        if(!res.ok){message=res.error;return false;}
        session=res.state;
        createOpen=false;
        clearDemoArmed=false;
        message="FICTIONAL DEMO LOADED // ALL BALANCES AND ACTIVITY ARE EXAMPLES";
        returnToTopRequested();
        return true;
    }
    function clearDemo() {
        if(session.mode!=="demo")return false;
        if(!clearDemoArmed){
            clearDemoArmed=true;
            message="CLICK CLEAR DEMO AGAIN TO REMOVE ALL FICTIONAL RECORDS";
            return false;
        }
        session=Accounts.emptyState();
        selectedId="";
        view="overview";
        createOpen=false;
        clearDemoArmed=false;
        message="FICTIONAL DEMO CLEARED";
        return true;
    }
    function showAccount(id) {
        if(!review.ok || !review.accounts.some(function(a){return a.id===id;}))
            return false;
        detailReturnView="overview";
        selectedId=id;
        message="";
        view="detail";
        return true;
    }
    function openProvider(id) {
        if(!ProviderPolicy.isProviderId(id))return false;
        selectedProviderId=id;
        message="";
        view="provider";
        return true;
    }
    function showProviderAccount(id) {
        if(!review.ok || !review.accounts.some(function(a){
            return a.id===id && a.providerId===selectedProviderId;
        }))return false;
        if(!showAccount(id))return false;
        detailReturnView="provider";
        return true;
    }
    function addTransaction() {
        const res=Accounts.addEntry(session,{
            accountId:selectedId,
            date:dateInput.text,
            description:descriptionInput.text,
            amountText:amountInput.text,
            direction:direction
        });
        if(!res.ok) {
            message=res.error;
            return false;
        }
        session=res.state;
        descriptionInput.text="";
        amountInput.text="";
        message="MANUAL ACTIVITY ADDED // NOT A BANK TRANSACTION OR RECEIPT";
        return true;
    }
    function undoLast() {
        if(!session.entries.length
           ||session.entries[session.entries.length-1].accountId!==selectedId) {
            message="ONLY THE MOST RECENT SESSION TRANSACTION CAN BE UNDONE HERE";
            return false;
        }
        const res=Accounts.undoLastEntry(session);
        if(!res.ok){message=res.error;return false;}
        session=res.state;
        message="LAST MANUAL TRANSACTION UNDONE // NO BANK DATA CHANGED";
        return true;
    }
    function removeCurrent() {
        if(!selected || session.mode!=="manual")return false;
        if(selected.transactionCount>0){
            message="ACCOUNT CONTAINS TRANSACTIONS // CANNOT DELETE";
            return false;
        }
        if(!deleteArmed) {
            deleteArmed=true;
            message="CLICK DELETE AGAIN TO REMOVE THIS EMPTY MANUAL ACCOUNT";
            return false;
        }
        const res=Accounts.removeEmptyAccount(session,selectedId);
        if(!res.ok){message=res.error;return false;}
        session=res.state;
        selectedId="";
        deleteArmed=false;
        message="EMPTY MANUAL ACCOUNT REMOVED";
        view=detailReturnView;
        return true;
    }

    Column {
        id: layout
        width: manager.width
        spacing: 8

        GohuText {
            width: parent.width
            text: manager.view==="provider" ? "ACCOUNTS // PROVIDER WORKSPACE"
                : "ACCOUNTS // MANUAL DIRECTORY"
            font.pixelSize: 12
            font.bold: true
            color: Colors.magenta
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: manager.session.mode==="demo"
                  ? "FICTIONAL DEMO // NO REAL MONEY // NOTHING CONNECTED"
                  : "LOCAL SESSION ONLY // USD // NO BANK CONNECTION // NOT SAVED"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }

        Column {
            width: parent.width
            spacing: 7
            visible: manager.view==="overview"
            GohuText {
                width: parent.width
                text: manager.review.accountCount+" ACCOUNTS  //  "
                    +manager.review.transactionCount+" MANUAL/DEMO TRANSACTIONS"
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: manager.review.combinedBalanceCents!==null
                    ? (manager.session.mode==="demo"
                        ? "FICTIONAL COMBINED TOTAL // ":"COMBINED MANUAL ESTIMATE // ")
                        +Accounts.money(manager.review.combinedBalanceCents)
                    : manager.review.accountCount===0
                      ? "NO MANUAL BALANCES ADDED"
                      : "PARTIAL KNOWN TOTAL // "+Accounts.money(manager.review.knownBalanceSubtotalCents)
                        +" // "+manager.review.unknownBalanceCount+" UNKNOWN"
                font.pixelSize: 11
                font.bold: true
                color: manager.review.combinedBalanceCents===null
                       ? Colors.orange:Colors.omnitrix
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "MONEY OUT "+Accounts.money(manager.review.outCents)
                    +" // MONEY IN "+Accounts.money(manager.review.inCents)
                    +" // NOT VERIFIED INCOME OR SPENDING"
                font.pixelSize: 9
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "PROVIDER WORKSPACES // INDIVIDUAL POST-APOLLO MINI-APPS"
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: ProviderPolicy.providers()
                delegate: ActionButton {
                    required property var modelData
                    width: layout.width
                    height: 29
                    label: "OPEN "+modelData.name.toUpperCase()+" WORKSPACE"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    onLeftClicked: manager.openProvider(modelData.id)
                }
            }
            Row {
                width: parent.width
                spacing: 5
                ActionButton {
                    width: (parent.width-5)/2
                    height: 30
                    label: manager.createOpen?"CANCEL NEW ACCOUNT":"ADD MANUAL ACCOUNT"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: manager.session.mode!=="demo"
                    onLeftClicked: {
                        manager.createOpen=!manager.createOpen;
                        manager.message="";
                    }
                }
                ActionButton {
                    width: (parent.width-5)/2
                    height: 30
                    label: manager.session.mode==="demo"
                           ? manager.clearDemoArmed?"CONFIRM CLEAR DEMO":"CLEAR DEMO"
                           : "LOAD FICTIONAL DEMO"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    available: manager.session.mode==="empty"
                               || manager.session.mode==="demo"
                    onLeftClicked: {
                        if(manager.session.mode==="demo")manager.clearDemo();
                        else manager.loadDemo();
                    }
                }
            }
            Column {
                width: parent.width
                spacing: 6
                visible: manager.createOpen && manager.session.mode!=="demo"
                ActionButton {
                    width: parent.width
                    height: 28
                    label: "PROVIDER // "+manager.selectedProvider.name.toUpperCase()
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    onLeftClicked: manager.providerIndex=
                        (manager.providerIndex+1)%manager.providerChoices.length
                }
                ActionButton {
                    width: parent.width
                    height: 28
                    label: "PRODUCT // "+manager.productChoices[manager.productIndex].name.toUpperCase()
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    available: manager.productChoices.length>1
                    onLeftClicked: manager.productIndex=
                        (manager.productIndex+1)%manager.productChoices.length
                }
                GohuText {
                    width: parent.width
                    text: "NICKNAME // YOUR LABEL (NOT A BANK LOGIN)"
                    font.pixelSize: 9
                    color: Colors.white
                }
                Rectangle {
                    width: parent.width
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: nicknameInput
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        maximumLength: 42
                        activeFocusOnPress: true
                    }
                }
                GohuText {
                    width: parent.width
                    text: "OPENING BALANCE USD // OPTIONAL // BLANK MEANS UNKNOWN"
                    font.pixelSize: 9
                    color: Colors.white
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: openingInput
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 28
                    label: "CREATE MANUAL ACCOUNT"
                    labelPixelSize: 9
                    accentColor: Colors.omnitrix
                    onLeftClicked: manager.createAccount()
                }
            }
            GohuText {
                width: parent.width
                text: manager.session.mode==="empty"
                      ? "NO ACCOUNTS YET // ADD YOUR OWN LABEL OR LOAD FICTIONAL EXAMPLES"
                      : manager.session.mode==="demo"
                        ? "EXAMPLES ONLY // CLEAR DEMO BEFORE ENTERING YOUR OWN ACCOUNTS"
                        : "YOUR MANUAL ACCOUNTS // SELECT ONE TO VIEW OR RECORD ACTIVITY"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: manager.review.ok?manager.review.accounts:[]
                delegate: Rectangle {
                    id: accountCard
                    required property var modelData
                    width: layout.width
                    height: accountCardContents.implicitHeight+12
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        id: accountCardContents
                        x: 6
                        y: 6
                        width: accountCard.width-12
                        spacing: 4
                        GohuText {
                            width: parent.width
                            text: modelData.providerName.toUpperCase()
                                +" // "+modelData.productName.toUpperCase()
                            font.pixelSize: 9
                            color: Colors.cyan
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.nickname
                            font.pixelSize: 11
                            font.bold: true
                            color: Colors.white
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.balanceCents===null
                                  ? "BALANCE UNKNOWN" :
                                  (manager.session.mode==="demo"?"FICTIONAL BALANCE ":"MANUAL ESTIMATE ")
                                  +Accounts.money(modelData.balanceCents)
                            font.pixelSize: 11
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
                            onLeftClicked: manager.showAccount(modelData.id)
                        }
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 7
            visible: manager.view==="provider"
            ActionButton {
                width: parent.width
                height: 28
                label: "BACK TO ALL ACCOUNTS"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: manager.view="overview"
            }
            FinanceBankingProviderPane {
                width: parent.width
                providerId: manager.selectedProviderId
                accountSnapshot: manager.review
                onAccountRequested: function(accountId) {
                    manager.showProviderAccount(accountId);
                }
                onReturnToTopRequested: manager.returnToTopRequested()
            }
        }

        Column {
            width: parent.width
            spacing: 7
            visible: manager.view==="detail"
            ActionButton {
                width: parent.width
                height: 28
                label: manager.detailReturnView==="provider"
                       ? "BACK TO PROVIDER WORKSPACE":"BACK TO ALL ACCOUNTS"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: manager.view=manager.detailReturnView
            }
            GohuText {
                width: parent.width
                text: manager.selected ? manager.selected.providerName.toUpperCase()
                      +" // "+manager.selected.productName.toUpperCase() : "NO ACCOUNT SELECTED"
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: manager.selected?manager.selected.nickname:""
                font.pixelSize: 13
                font.bold: true
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: !manager.selected?"NO RECORD"
                    : manager.selected.balanceCents===null
                      ? "BALANCE UNKNOWN // NO OPENING BALANCE"
                      : (manager.session.mode==="demo"?"FICTIONAL BALANCE // "
                         :"MANUAL BALANCE ESTIMATE // ")
                        +Accounts.money(manager.selected.balanceCents)
                font.pixelSize: 12
                color: manager.selected&&manager.selected.balanceCents!==null
                       ? Colors.omnitrix:Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: manager.selected
                      ? "NET MANUAL CHANGE "+Accounts.money(manager.selected.netChangeCents)
                        +" // "+manager.selected.transactionCount+" ENTRIES" : ""
                font.pixelSize: 9
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Column {
                width: parent.width
                spacing: 6
                visible: manager.session.mode==="manual"
                         && manager.selected!==null
                GohuText {
                    width: parent.width
                    text: "ADD MANUAL ACTIVITY // NO MONEY WILL MOVE"
                    font.pixelSize: 10
                    color: Colors.magenta
                    textFormat: Text.PlainText
                }
                Row {
                    width: parent.width
                    spacing: 5
                    ActionButton {
                        width: (parent.width-5)/2
                        height: 29
                        label: "MONEY OUT"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        selected: manager.direction==="out"
                        onLeftClicked: manager.direction="out"
                    }
                    ActionButton {
                        width: (parent.width-5)/2
                        height: 29
                        label: "MONEY IN"
                        labelPixelSize: 9
                        accentColor: Colors.omnitrix
                        selected: manager.direction==="in"
                        onLeftClicked: manager.direction="in"
                    }
                }
                GohuText {
                    width: parent.width
                    text: "DATE // YYYY-MM-DD"
                    font.pixelSize: 9
                    color: Colors.white
                }
                Rectangle {
                    width: parent.width
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: dateInput
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        text: Qt.formatDate(new Date(),"yyyy-MM-dd")
                        selectByMouse: true
                        activeFocusOnPress: true
                    }
                }
                GohuText {
                    width: parent.width
                    text: "DESCRIPTION // WHAT WAS IT?"
                    font.pixelSize: 9
                    color: Colors.white
                }
                Rectangle {
                    width: parent.width
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: descriptionInput
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                        maximumLength: 120
                    }
                }
                GohuText {
                    width: parent.width
                    text: "AMOUNT USD // POSITIVE NUMBER, E.G. 15.25"
                    font.pixelSize: 9
                    color: Colors.white
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: amountInput
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 29
                    label: "ADD TO MANUAL ACTIVITY"
                    labelPixelSize: 9
                    accentColor: Colors.omnitrix
                    onLeftClicked: manager.addTransaction()
                }
                ActionButton {
                    width: parent.width
                    height: 28
                    label: "UNDO LAST MANUAL TRANSACTION"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    available: manager.session.entries.length>0
                               && manager.session.entries[manager.session.entries.length-1].accountId
                                  ===manager.selectedId
                    onLeftClicked: manager.undoLast()
                }
                ActionButton {
                    width: parent.width
                    height: 28
                    label: manager.deleteArmed
                           ? "CONFIRM DELETE EMPTY ACCOUNT":"DELETE EMPTY MANUAL ACCOUNT"
                    labelPixelSize: 9
                    accentColor: manager.deleteArmed?Colors.red:Colors.orange
                    available: manager.selected!==null
                               && manager.selected.transactionCount===0
                    onLeftClicked: manager.removeCurrent()
                }
            }
            GohuText {
                width: parent.width
                text: manager.session.mode==="demo"
                    ? "FICTIONAL ACTIVITY ONLY // CLEAR DEMO TO START A MANUAL SESSION"
                    : "MONEY IN IS NOT VERIFIED INCOME; MONEY OUT CAN INCLUDE TRANSFERS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "RECENT ACTIVITY // LATEST 12 // SESSION ONLY"
                font.pixelSize: 10
                color: Colors.cyan
            }
            Repeater {
                model: manager.selected?manager.selected.recent:[]
                delegate: Rectangle {
                    required property var modelData
                    width: layout.width
                    height: activityBlock.implicitHeight+10
                    border.width: 1
                    border.color: Colors.cyan
                    color: Colors.black
                    Column {
                        id: activityBlock
                        x: 5
                        y: 5
                        width: parent.width-10
                        spacing: 3
                        GohuText {
                            width: parent.width
                            text: modelData.date+" // "+Accounts.money(modelData.amountCents)
                            font.pixelSize: 10
                            color: modelData.amountCents<0?Colors.orange:Colors.omnitrix
                            textFormat: Text.PlainText
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
                visible: manager.selected!==null&&manager.selected.transactionCount===0
                text: "NO MANUAL ACTIVITY RECORDED"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
            }
        }

        GohuText {
            width: parent.width
            visible: !!manager.message
            text: manager.message
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "ACCOUNT LABELS ARE NOT AUTHENTICATED // NO BANK LOGIN, ACCOUNT SYNC, PAYMENT, STOCK TRADE OR BORROW ACTION"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
