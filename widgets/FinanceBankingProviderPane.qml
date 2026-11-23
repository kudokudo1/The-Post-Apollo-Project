import QtQuick
import "../components"
import "FinanceBankingProviderPolicy.js" as ProviderPolicy
import "FinanceBankingSessionJournalPolicy.js" as Journal

// Banking M4: provider-specific Post-Apollo navigation over M3 manual/demo
// snapshots only. Restricted features are informative, never actionable.
Item {
    id: providerPane
    property string providerId: ""
    property var accountSnapshot: ({ok:false})
    property var manualSession: ({mode:"empty",accounts:[],entries:[]})
    property string sectionId: "home"
    property string feedback: ""
    property string activityDirection: "all" // all | in | out
    property int activityAccountIndex: 0 // 0 = all; 1..N = provider account
    property int activityPageIndex: 0
    property int entryAccountIndex: 0
    property string entryDirection: "out" // out | in
    property var correctionCandidate: null
    property string correctionDirection: "out"
    property bool correctionDeleteArmed: false
    property bool showActivityBreakdown: false
    readonly property var details: ProviderPolicy.build(
        providerId,accountSnapshot,sectionId)
    readonly property var providerAccounts: details.ok ? details.allAccounts : []
    readonly property string activityAccountId: activityAccountIndex>0
        &&activityAccountIndex<=providerAccounts.length
        ? providerAccounts[activityAccountIndex-1].id : ""
    readonly property var filteredActivity: Journal.project(
        details,manualSession,{direction:activityDirection,
            accountId:activityAccountId,query:activitySearch.text,page:activityPageIndex,
            fromDate:activityFromDate.text,toDate:activityToDate.text})
    signal accountRequested(string accountId)
    signal manualEntryRequested(var draft)
    signal manualCorrectionRequested(var draft)
    signal manualDeletionRequested(var draft)
    signal returnToTopRequested()
    implicitHeight: providerContent.implicitHeight

    onProviderIdChanged: {
        sectionId="home";
        activityAccountIndex=0;
        activityPageIndex=0;
        entryAccountIndex=0;
        activityFromDate.text="";
        activityToDate.text="";
        showActivityBreakdown=false;
        clearSelectedEntry();
    }
    onSectionIdChanged: {
        activityDirection="all";
        activityAccountIndex=0;
        activityPageIndex=0;
        activityFromDate.text="";
        activityToDate.text="";
        showActivityBreakdown=false;
        clearSelectedEntry();
        returnToTopRequested();
    }
    onActivityDirectionChanged: {
        activityPageIndex=0;
        clearSelectedEntry();
    }
    onActivityAccountIndexChanged: {
        activityPageIndex=0;
        clearSelectedEntry();
    }
    onActivityPageIndexChanged: clearSelectedEntry()
    onManualSessionChanged: {
        activityPageIndex=0;
        clearSelectedEntry();
    }
    function clearAfterEntry() {
        quickDescription.text="";
        quickAmount.text="";
    }
    function clearSelectedEntry() {
        correctionCandidate=null;
        correctionDeleteArmed=false;
    }
    function chooseManualEntry(row) {
        if(!row||typeof row.id!=="string"||typeof row.accountId!=="string")
            return false;
        if(!details.ok||details.sectionKind!=="activity"
           ||manualSession.mode!=="manual"||!filteredActivity.ok
           ||!filteredActivity.rows.some(function(e){
               return e.id===row.id&&e.accountId===row.accountId
                   &&e.date===row.date&&e.description===row.description
                   &&e.amountCents===row.amountCents;
           }))return false;
        correctionCandidate={
            providerId:providerId,entryId:row.id,accountId:row.accountId,
            expectedDate:row.date,expectedDescription:row.description,
            expectedAmountCents:row.amountCents
        };
        editDate.text=row.date;
        editDescription.text=row.description;
        editAmount.text=(Math.abs(row.amountCents)/100).toFixed(2);
        correctionDirection=row.amountCents<0?"out":"in";
        correctionDeleteArmed=false;
        returnToTopRequested();
        return true;
    }
    function requestCorrection() {
        if(!correctionCandidate||manualSession.mode!=="manual"
           ||!details.ok||details.sectionKind!=="activity")return false;
        manualCorrectionRequested({
            providerId:correctionCandidate.providerId,
            entryId:correctionCandidate.entryId,
            accountId:correctionCandidate.accountId,
            expectedDate:correctionCandidate.expectedDate,
            expectedDescription:correctionCandidate.expectedDescription,
            expectedAmountCents:correctionCandidate.expectedAmountCents,
            date:editDate.text,description:editDescription.text,
            amountText:editAmount.text,direction:correctionDirection
        });
        return true;
    }
    function requestDeletion() {
        if(!correctionCandidate||manualSession.mode!=="manual"
           ||!details.ok||details.sectionKind!=="activity")return false;
        if(!correctionDeleteArmed) {
            correctionDeleteArmed=true;
            return false;
        }
        correctionDeleteArmed=false;
        manualDeletionRequested({
            providerId:correctionCandidate.providerId,
            entryId:correctionCandidate.entryId,
            accountId:correctionCandidate.accountId,
            expectedDate:correctionCandidate.expectedDate,
            expectedDescription:correctionCandidate.expectedDescription,
            expectedAmountCents:correctionCandidate.expectedAmountCents
        });
        return true;
    }
    function requestManualEntry() {
        if(!details.ok||details.sectionKind!=="activity"
           ||accountSnapshot.mode!=="manual"||providerAccounts.length===0)
            return false;
        var index=entryAccountIndex>=0&&entryAccountIndex<providerAccounts.length
            ?entryAccountIndex:0;
        manualEntryRequested({
            providerId:providerId,
            accountId:providerAccounts[index].id,
            date:quickDate.text,
            description:quickDescription.text,
            amountText:quickAmount.text,
            direction:entryDirection
        });
        return true;
    }

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
            visible: providerPane.details.ok && providerPane.details.sectionKind==="product"
            text: providerPane.details.visibleBalanceCents!==null
                ? (providerPane.accountSnapshot.mode==="demo"
                   ? "FICTIONAL SELECTED PRODUCT BALANCE // ":"MANUAL SELECTED PRODUCT ESTIMATE // ")
                   +ProviderPolicy.money(providerPane.details.visibleBalanceCents)
                : providerPane.details.visibleAccounts.length===0
                  ? "NO MANUAL ACCOUNT MATCHES THIS PRODUCT"
                  : "SELECTED PRODUCT HAS UNKNOWN BALANCE // KNOWN SUBTOTAL "
                    +ProviderPolicy.money(providerPane.details.visibleKnownBalanceSubtotalCents)
                    +" // "+providerPane.details.visibleUnknownBalanceCount+" UNKNOWN"
            font.pixelSize: 10
            font.bold: true
            color: providerPane.details.visibleBalanceCents===null
                ? Colors.orange:Colors.omnitrix
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
            text: "NOT CONNECTED // FEATURE INFORMATION ONLY // USE THE OFFICIAL SERVICE FOR REAL ACTIONS"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        FinanceBankingOfficialHandoff {
            width: parent.width
            visible: providerPane.details.ok
                && providerPane.details.sectionKind==="restricted"
            height: visible ? implicitHeight : 0
            providerId: providerPane.providerId
            sectionId: providerPane.details.ok ? providerPane.details.sectionId : ""
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
        Column {
            width: parent.width
            spacing: 5
            visible: providerPane.details.ok
                &&(providerPane.details.sectionKind==="accounts"
                    ||providerPane.details.sectionKind==="product")
                &&providerPane.details.visibleAccounts.length>0
            GohuText {
                width: parent.width
                text: "CASH ACCOUNTS // SESSION MONEY MOVEMENT"
                font.pixelSize: 10
                font.bold: true
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "MONEY IN "+ProviderPolicy.money(providerPane.details.visibleMovementInCents)
                    +" // MONEY OUT "+ProviderPolicy.money(providerPane.details.visibleMovementOutCents)
                    +" // NET "+ProviderPolicy.money(providerPane.details.visibleMovementNetCents)
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: providerPane.details.visibleTransactionCount
                    +" MANUAL/DEMO ENTRIES IN THIS SESSION // NOT VERIFIED INCOME, SPENDING OR TRANSFERS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
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
                    GohuText {
                        width: parent.width
                        text: "SESSION IN "+ProviderPolicy.money(modelData.creditsCents)
                            +" // OUT "+ProviderPolicy.money(modelData.debitsCents)
                            +" // "+modelData.transactionCount+" ENTRIES"
                        font.pixelSize: 9
                        color: Colors.cyan
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
        Column {
            width: parent.width
            spacing: 5
            visible: providerPane.details.ok
                &&(providerPane.details.sectionKind==="accounts"
                    ||providerPane.details.sectionKind==="product")
                &&providerPane.details.visibleAccounts.length>0
            GohuText {
                width: parent.width
                text: "RECENT SESSION ACTIVITY // UP TO 4 ENTRIES"
                font.pixelSize: 10
                font.bold: true
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: providerPane.details.visibleRecent.length===0
                text: "NO MANUAL OR FICTIONAL ACTIVITY RECORDED FOR THESE CASH ACCOUNTS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: providerPane.details.visibleRecent
                delegate: GohuText {
                    required property var modelData
                    width: providerContent.width
                    text: modelData.date+" // "+modelData.nickname
                        +" // "+ProviderPolicy.money(modelData.amountCents)
                        +" // "+modelData.description
                    font.pixelSize: 9
                    color: modelData.amountCents<0?Colors.orange:Colors.omnitrix
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
            GohuText {
                width: parent.width
                visible: providerPane.details.visibleRecentOmitted
                text: "MORE OR OLDER ENTRIES EXIST // OPEN ACTIVITY TO INSPECT RECENT SESSION RECORDS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
        Column {
            width: parent.width
            spacing: 6
            visible: providerPane.details.ok
                     &&providerPane.details.sectionKind==="activity"
            GohuText {
                width: parent.width
                text: providerPane.filteredActivity.ok
                    ? providerPane.filteredActivity.scope+" // UP TO 300 SESSION ENTRIES"
                    : "SESSION ACTIVITY UNAVAILABLE"
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                spacing: 4
                ActionButton {
                    width: (parent.width-8)/3
                    height: 28
                    label: "ALL"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    selected: providerPane.activityDirection==="all"
                    onLeftClicked: providerPane.activityDirection="all"
                }
                ActionButton {
                    width: (parent.width-8)/3
                    height: 28
                    label: "MONEY IN"
                    labelPixelSize: 9
                    accentColor: Colors.omnitrix
                    selected: providerPane.activityDirection==="in"
                    onLeftClicked: providerPane.activityDirection="in"
                }
                ActionButton {
                    width: (parent.width-8)/3
                    height: 28
                    label: "MONEY OUT"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    selected: providerPane.activityDirection==="out"
                    onLeftClicked: providerPane.activityDirection="out"
                }
            }
            ActionButton {
                width: parent.width
                height: 28
                label: providerPane.activityAccountIndex>0
                       &&providerPane.activityAccountIndex<=providerPane.providerAccounts.length
                       ? "FILTER ACCOUNT // "+providerPane.providerAccounts[providerPane.activityAccountIndex-1].nickname
                       : "FILTER ACCOUNT // ALL"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: providerPane.providerAccounts.length>0
                onLeftClicked: providerPane.activityAccountIndex=
                    (providerPane.activityAccountIndex+1)%(providerPane.providerAccounts.length+1)
            }
            GohuText {
                width: parent.width
                text: "SESSION DATE RANGE // INCLUSIVE // YYYY-MM-DD // BLANK MEANS NO LIMIT"
                font.pixelSize: 9
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                width: parent.width
                spacing: 5
                Rectangle {
                    width: (parent.width-5)/2
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: activityFromDate
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                        maximumLength: 10
                        onTextChanged: {
                            providerPane.activityPageIndex=0;
                            providerPane.clearSelectedEntry();
                        }
                    }
                }
                Rectangle {
                    width: (parent.width-5)/2
                    height: 29
                    color: Colors.black
                    border.color: Colors.cyan
                    clip: true
                    TextInput {
                        id: activityToDate
                        anchors.fill: parent
                        anchors.margins: 5
                        font.pixelSize: 11
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                        maximumLength: 10
                        onTextChanged: {
                            providerPane.activityPageIndex=0;
                            providerPane.clearSelectedEntry();
                        }
                    }
                }
            }
            Row {
                width: parent.width
                spacing: 5
                GohuText {
                    width: (parent.width-5)/2
                    text: "FROM DATE (OPTIONAL)"
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                }
                GohuText {
                    width: (parent.width-5)/2
                    text: "TO DATE (OPTIONAL)"
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                }
            }
            ActionButton {
                width: parent.width
                height: 28
                label: "CLEAR ACTIVITY DATE RANGE"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: {
                    activityFromDate.text="";
                    activityToDate.text="";
                }
            }
            GohuText {
                width: parent.width
                text: "SEARCH SESSION DESCRIPTION OR MANUAL ACCOUNT NICKNAME"
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
                    id: activitySearch
                    anchors.fill: parent
                    anchors.margins: 5
                    font.pixelSize: 11
                    color: Colors.white
                    selectByMouse: true
                    activeFocusOnPress: true
                    maximumLength: 64
                    onTextChanged: {
                        providerPane.activityPageIndex=0;
                        providerPane.clearSelectedEntry();
                    }
                }
            }
            GohuText {
                width: parent.width
                text: providerPane.filteredActivity.ok
                    ? "MATCHES "+providerPane.filteredActivity.totalMatches
                      +" / "+providerPane.filteredActivity.providerSessionCount
                      +" PROVIDER SESSION ENTRIES // PAGE "
                      +(providerPane.filteredActivity.pageIndex+1)
                      +" / "+providerPane.filteredActivity.pageCount
                      +" // SHOWING "+providerPane.filteredActivity.from
                      +"-"+providerPane.filteredActivity.to
                    : providerPane.filteredActivity.error
                      ? providerPane.filteredActivity.error
                      : "SESSION ACTIVITY UNAVAILABLE"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: providerPane.filteredActivity.ok
                text: "FILTERED SESSION MONEY IN "
                    +ProviderPolicy.money(providerPane.filteredActivity.matchedInCents)
                    +" // MONEY OUT "
                    +ProviderPolicy.money(providerPane.filteredActivity.matchedOutCents)
                    +" // NET "
                    +ProviderPolicy.money(providerPane.filteredActivity.matchedNetCents)
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: providerPane.filteredActivity.ok
                text: "THESE ARE USER-ENTERED MONEY MOVEMENTS // NOT VERIFIED INCOME OR SPENDING"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 29
                visible: providerPane.filteredActivity.ok
                available: providerPane.filteredActivity.ok
                    &&providerPane.filteredActivity.accountBreakdown.length>0
                label: providerPane.showActivityBreakdown
                    ? "HIDE FILTERED ACCOUNT BREAKDOWN"
                    : "SHOW FILTERED ACCOUNT BREAKDOWN"
                labelPixelSize: 9
                accentColor: Colors.magenta
                onLeftClicked: providerPane.showActivityBreakdown=
                    !providerPane.showActivityBreakdown
            }
            Column {
                width: parent.width
                spacing: 5
                visible: providerPane.showActivityBreakdown
                    &&providerPane.filteredActivity.ok
                    &&providerPane.filteredActivity.accountBreakdown.length>0
                GohuText {
                    width: parent.width
                    text: "MATCHED ACTIVITY BY MANUAL ACCOUNT // TOTALS INCLUDE ALL MATCHING PAGES"
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: providerPane.filteredActivity.ok
                        ? providerPane.filteredActivity.accountBreakdown:[]
                    delegate: Rectangle {
                        id: accountMovementCard
                        required property var modelData
                        width: providerContent.width
                        height: movementDetails.implicitHeight+12
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.cyan
                        Column {
                            id: movementDetails
                            x: 6
                            y: 6
                            width: accountMovementCard.width-12
                            spacing: 4
                            GohuText {
                                width: parent.width
                                text: modelData.accountNickname
                                    +" // "+modelData.matchedCount+" MATCHED ENTRIES"
                                font.pixelSize: 10
                                color: Colors.white
                                textFormat: Text.PlainText
                                wrapMode: Text.WordWrap
                            }
                            GohuText {
                                width: parent.width
                                text: "IN "+ProviderPolicy.money(modelData.matchedInCents)
                                    +" // OUT "+ProviderPolicy.money(modelData.matchedOutCents)
                                    +" // NET "+ProviderPolicy.money(modelData.matchedNetCents)
                                font.pixelSize: 9
                                color: Colors.cyan
                                textFormat: Text.PlainText
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: "MANUAL/DEMO CASH MOVEMENT ONLY // NOT VERIFIED BALANCES OR PROFIT"
                    font.pixelSize: 9
                    color: Colors.orange
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
        }
        Column {
            width: parent.width
            spacing: 6
            visible: providerPane.details.ok
                     &&providerPane.details.sectionKind==="activity"
                     &&providerPane.accountSnapshot.mode==="manual"
                     &&providerPane.providerAccounts.length>0
            GohuText {
                width: parent.width
                text: "QUICK MANUAL ENTRY // UPDATES ONLY THIS SESSION // DOES NOT MOVE MONEY"
                font.pixelSize: 10
                font.bold: true
                color: Colors.magenta
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 28
                label: providerPane.entryAccountIndex>=0
                       &&providerPane.entryAccountIndex<providerPane.providerAccounts.length
                       ? "MANUAL ACCOUNT // "+providerPane.providerAccounts[providerPane.entryAccountIndex].nickname
                       : "MANUAL ACCOUNT // SELECT"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: providerPane.entryAccountIndex=
                    (providerPane.entryAccountIndex+1)%providerPane.providerAccounts.length
            }
            Row {
                width: parent.width
                spacing: 4
                ActionButton {
                    width: (parent.width-4)/2
                    height: 28
                    label: "MONEY OUT"
                    labelPixelSize: 9
                    selected: providerPane.entryDirection==="out"
                    accentColor: Colors.orange
                    onLeftClicked: providerPane.entryDirection="out"
                }
                ActionButton {
                    width: (parent.width-4)/2
                    height: 28
                    label: "MONEY IN"
                    labelPixelSize: 9
                    selected: providerPane.entryDirection==="in"
                    accentColor: Colors.omnitrix
                    onLeftClicked: providerPane.entryDirection="in"
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
                    id: quickDate
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
                text: "DESCRIPTION // MANUAL ENTRY"
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
                    id: quickDescription
                    anchors.fill: parent
                    anchors.margins: 5
                    font.pixelSize: 11
                    color: Colors.white
                    maximumLength: 120
                    selectByMouse: true
                    activeFocusOnPress: true
                }
            }
            GohuText {
                width: parent.width
                text: "AMOUNT USD // POSITIVE NUMBER, E.G. 12.50"
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
                    id: quickAmount
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
                label: "ADD PROVIDER MANUAL ACTIVITY"
                labelPixelSize: 9
                accentColor: Colors.omnitrix
                onLeftClicked: providerPane.requestManualEntry()
            }
            GohuText {
                width: parent.width
                visible: !!providerPane.feedback
                text: providerPane.feedback
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
        Column {
            width: parent.width
            spacing: 6
            visible: providerPane.details.ok
                &&providerPane.details.sectionKind==="activity"
                &&providerPane.manualSession.mode==="manual"
                &&providerPane.correctionCandidate!==null
            GohuText {
                width: parent.width
                text: "CORRECT MANUAL ENTRY // SESSION ONLY // ACCOUNT ID IS LOCKED"
                font.pixelSize: 10
                font.bold: true
                color: Colors.magenta
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: providerPane.correctionCandidate
                    ? "SELECTED "+providerPane.correctionCandidate.entryId
                      +" // ORIGINAL "+providerPane.correctionCandidate.expectedDate
                      +" // "+ProviderPolicy.money(providerPane.correctionCandidate.expectedAmountCents)
                    : ""
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 28
                label: providerPane.correctionDirection==="out"
                       ? "CORRECTION DIRECTION // MONEY OUT":"CORRECTION DIRECTION // MONEY IN"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: {
                    providerPane.correctionDirection=
                        providerPane.correctionDirection==="out"?"in":"out";
                    providerPane.correctionDeleteArmed=false;
                }
            }
            GohuText {
                width: parent.width
                text: "CORRECT DATE // YYYY-MM-DD"
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
                    id: editDate
                    anchors.fill: parent
                    anchors.margins: 5
                    font.pixelSize: 11
                    color: Colors.white
                    selectByMouse: true
                    activeFocusOnPress: true
                }
            }
            GohuText {
                width: parent.width
                text: "CORRECT DESCRIPTION"
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
                    id: editDescription
                    anchors.fill: parent
                    anchors.margins: 5
                    font.pixelSize: 11
                    color: Colors.white
                    maximumLength: 120
                    selectByMouse: true
                    activeFocusOnPress: true
                }
            }
            GohuText {
                width: parent.width
                text: "CORRECT USD AMOUNT // POSITIVE NUMBER"
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
                    id: editAmount
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
                label: "SAVE MANUAL ENTRY CORRECTION"
                labelPixelSize: 9
                accentColor: Colors.omnitrix
                onLeftClicked: providerPane.requestCorrection()
            }
            ActionButton {
                width: parent.width
                height: 29
                label: providerPane.correctionDeleteArmed
                       ? "CONFIRM DELETE ORIGINAL MANUAL ENTRY"
                       : "DELETE SELECTED MANUAL ENTRY // TWO CLICKS"
                labelPixelSize: 9
                accentColor: providerPane.correctionDeleteArmed?Colors.red:Colors.orange
                onLeftClicked: providerPane.requestDeletion()
            }
            GohuText {
                width: parent.width
                text: providerPane.correctionDeleteArmed
                    ? "SECOND CLICK PERMANENTLY REMOVES THIS ENTRY FROM THE CURRENT UNSAVED SESSION"
                    : "DELETE CANNOT BE UNDONE; CORRECTION REPLACES ONLY THIS USER-ENTERED RECORD"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 27
                label: "CANCEL MANUAL CORRECTION"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: providerPane.clearSelectedEntry()
            }
        }
        GohuText {
            width: parent.width
            visible: providerPane.details.ok
                     &&providerPane.details.sectionKind==="activity"
                     &&providerPane.filteredActivity.ok
                     &&providerPane.filteredActivity.rows.length===0
            text: "NO SESSION ACTIVITY MATCHES THESE FILTERS"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: providerPane.filteredActivity.ok?providerPane.filteredActivity.rows:[]
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
                    ActionButton {
                        width: parent.width
                        height: 28
                        visible: providerPane.manualSession.mode==="manual"
                        label: "CORRECT / REMOVE THIS MANUAL ENTRY"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        onLeftClicked: providerPane.chooseManualEntry(modelData)
                    }
                }
            }
        }
        Row {
            width: parent.width
            spacing: 5
            visible: providerPane.details.ok
                     && providerPane.details.sectionKind==="activity"
                     && providerPane.filteredActivity.ok
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "PREVIOUS PAGE"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: providerPane.filteredActivity.pageIndex>0
                onLeftClicked: {
                    providerPane.activityPageIndex=
                        Math.max(0,providerPane.filteredActivity.pageIndex-1);
                    providerPane.returnToTopRequested();
                }
            }
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "NEXT PAGE"
                labelPixelSize: 9
                accentColor: Colors.magenta
                available: providerPane.filteredActivity.pageIndex+1
                           <providerPane.filteredActivity.pageCount
                onLeftClicked: {
                    providerPane.activityPageIndex=
                        providerPane.filteredActivity.pageIndex+1;
                    providerPane.returnToTopRequested();
                }
            }
        }
        GohuText {
            width: parent.width
            text: "NO VERIFIED BALANCES, PAYMENTS, CARDS, STOCKS OR LOANS // MANUAL BOOKKEEPING ONLY"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
