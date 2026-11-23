import QtQuick
import "../components"
import "../services/finance/FinanceExpenseCategoryPreview.js" as ExpenseRules

// M3a // isolated categorization PREVIEW ONLY. No save/request signal.
// Not mounted in FinanceW until a category-aware transaction writer is
// independently reviewed and the UX clearly distinguishes preview/save.
Item {
    id: expense
    objectName: "expenseCategoryPreviewPane"
    property var snapshot: null
    property var candidate: null
    property bool open: false
    property string selectedCategoryId: ""
    property var proposal: null
    property string errorText: ""

    readonly property bool sourceReady: !!snapshot
        && snapshot.schemaVersion===1
        && snapshot.readOnly===true
        && snapshot.source==="actual-budget"
        && typeof snapshot.sourceKey==="string"
        && /^[a-f0-9]{64}$/.test(snapshot.sourceKey)
        && /^(19|20)\d{2}-(0[1-9]|1[0-2])$/.test(snapshot.month||"")
        && Array.isArray(snapshot.categories)
        && Array.isArray(snapshot.categoryGroups)
        && Array.isArray(snapshot.accounts)
    readonly property var choices: sourceReady
        ? snapshot.categories.filter(function(c) {
            return c && typeof c.id==="string" && !!c.id
                && typeof c.name==="string" && !!c.name.trim();
        }) : []
    readonly property var selectedCategory: {
        if(!sourceReady)return null;
        const matches=choices.filter(function(c){return c.id===selectedCategoryId;});
        return matches.length===1 ? matches[0] : null;
    }
    width: parent ? parent.width : 0
    height: open ? content.implicitHeight+18 : 0
    visible: open

    function invalidate() {
        proposal=null;
        errorText="";
    }
    function clear() {
        open=false;
        candidate=null;
        selectedCategoryId="";
        invalidate();
        return true;
    }
    function begin(draft) {
        if(!sourceReady || !draft || choices.length===0)return false;
        clear();
        // Own a detached candidate. An in-progress input change will require
        // explicit new preview rather than silently reusing a stale plan.
        candidate={
            action:draft.action,direction:draft.direction,editing:draft.editing,
            sourceKey:draft.sourceKey,month:draft.month,
            accountId:draft.accountId,date:draft.date,
            description:draft.description,amountCents:draft.amountCents
        };
        open=true;
        return true;
    }
    function selectCategory(id) {
        if(!open || !sourceReady)return false;
        const matches=choices.filter(function(c){return c.id===id;});
        if(matches.length!==1)return false;
        selectedCategoryId=id;
        return true;
    }
    function nextCategory() {
        if(!open || !choices.length)return false;
        const at=choices.findIndex(function(c){return c.id===selectedCategoryId;});
        const next=choices[(at+1)%choices.length];
        return selectCategory(next.id);
    }
    function calculate() {
        if(!open || !sourceReady)return false;
        invalidate();
        const result=ExpenseRules.previewExpenseCategory(snapshot,candidate,
                                                          selectedCategoryId);
        if(!result.ok){
            errorText=result.reason;
            return false;
        }
        proposal=result;
        return true;
    }

    onSnapshotChanged: clear()
    onCandidateChanged: invalidate()
    onSelectedCategoryIdChanged: invalidate()

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
    }
    Column {
        id: content
        x: 9
        y: 9
        width: Math.max(0,expense.width-18)
        spacing: 7
        GohuText {
            width: parent.width
            text: "NEW EXPENSE // CATEGORY PREVIEW"
            font.pixelSize: 11
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "NOT CONNECTED TO TRANSACTION SAVE"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: expense.candidate
                ? expense.candidate.description+" // "
                  +expense.candidate.date+" // "
                  +(expense.candidate.amountCents/100).toFixed(2)
                : "NO DRAFT SELECTED"
            font.pixelSize: 10
            color: Colors.white
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            objectName: "expenseCategoryPicker"
            width: parent.width
            height: 30
            label: "CATEGORY // "+(expense.selectedCategory
                ? expense.selectedCategory.name : "SELECT ENVELOPE")+"  ›"
            labelPixelSize: 9
            accentColor: Colors.cyan
            trackLabelGlowLocally: true
            available: expense.open && expense.sourceReady && expense.choices.length>0
            onLeftClicked: expense.nextCategory()
        }
        Row {
            width: parent.width
            spacing: 7
            ActionButton {
                objectName: "expenseCategoryPreviewAction"
                width: (parent.width-7)/2
                height: 30
                label: "PREVIEW"
                labelPixelSize: 10
                accentColor: Colors.cyan
                trackLabelGlowLocally: true
                available: expense.open && expense.sourceReady
                onLeftClicked: expense.calculate()
            }
            ActionButton {
                objectName: "expenseCategoryCancelAction"
                width: (parent.width-7)/2
                height: 30
                label: "CANCEL"
                labelPixelSize: 10
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                onLeftClicked: expense.clear()
            }
        }
        GohuText {
            objectName: "expenseCategoryErrorText"
            width: parent.width
            visible: !!expense.errorText
            text: expense.errorText
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Column {
            objectName: "expenseCategorySummary"
            width: parent.width
            visible: !!expense.proposal && expense.proposal.ok
            spacing: 5
            GohuText {
                width: parent.width
                text: expense.proposal
                    ? expense.proposal.groupName+" / "+expense.proposal.categoryName
                    : ""
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: expense.proposal
                    ? "ESTIMATED LEFT // "
                      +(expense.proposal.availableBeforeCents/100).toFixed(2)
                      +" → "
                      +(expense.proposal.estimatedAvailableAfterCents/100).toFixed(2)
                    : ""
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: !!expense.proposal && expense.proposal.estimatedOverspent
                text: "ESTIMATE WOULD OVERSPEND THIS ENVELOPE"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
            }
        }
        GohuText {
            width: parent.width
            text: "ESTIMATE ONLY // ACTUAL RECALCULATES // NOT SAVED"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
