import QtQuick
import "../components"
import "../services/finance/FinanceAllocationPreview.js" as AllocationRules
import "../services/finance/FinanceSpreadsheetPolicy.js" as StepRules

// Compact budget table. SET is editable; SPENT and LEFT come from Actual.
// One explicit SAVE ROW uses the existing D12 allocation writer unchanged.
Item {
    id: grid
    property var snapshot: null
    property string writeState: "idle"
    property string writeMessage: ""
    property string selectedCategoryId: ""
    property string draftText: ""
    property bool submitted: false
    signal saveRequested(var payload)
    readonly property bool lockedForRecovery: writeState==="pending"
        || writeState==="uncertain"
    readonly property var selectedCategory: {
        if(!snapshot || !Array.isArray(snapshot.categories))return null;
        const found=snapshot.categories.filter(function(c){
            return c && c.id===selectedCategoryId;
        });
        return found.length===1 ? found[0] : null;
    }
    readonly property var proposal: selectedCategory
        ? AllocationRules.previewAllocation(snapshot,selectedCategoryId,draftText)
        : null
    readonly property bool canSave: !!proposal && proposal.ok
        && proposal.allocationChangeCents!==0
        && !proposal.exceedsUnallocatedFunds && !proposal.categoryRemainsOverspent
        && !lockedForRecovery && !submitted
        && snapshot && proposal.sourceKey===snapshot.sourceKey
        && proposal.month===snapshot.month
        && selectedCategory && proposal.originalBudgetedCents===selectedCategory.budgetedCents
        && proposal.originalAvailableCents===selectedCategory.availableCents
        && proposal.toBudgetBeforeCents===snapshot.toBudgetCents

    width: parent ? parent.width : 0
    height: tableBody.implicitHeight
    function reset(){
        selectedCategoryId="";
        draftText="";
        submitted=false;
    }
    onSnapshotChanged: reset()
    function choose(row,text) {
        if(lockedForRecovery || submitted || !row || !snapshot
                || !Array.isArray(snapshot.categories))return false;
        const found=snapshot.categories.filter(function(c){return c && c.id===row.id;});
        if(found.length!==1)return false;
        selectedCategoryId=row.id;
        draftText=text===undefined
            ? (row.budgetedCents/100).toFixed(2) : text;
        return true;
    }
    function step(row,delta) {
        if(!row || lockedForRecovery || submitted)return false;
        const source=selectedCategoryId===row.id ? draftText
            : (row.budgetedCents/100).toFixed(2);
        const next=StepRules.stepAmount(source,delta,true);
        if(next===null)return false;
        return choose(row,next);
    }
    function saveSelected() {
        if(!canSave || !selectedCategory)return false;
        submitted=true;
        let id="";
        for(let i=0;i<32;i++)id+=Math.floor(Math.random()*16).toString(16);
        saveRequested({
            action:"set-amount",requestId:id,
            sourceKey:proposal.sourceKey,month:proposal.month,
            categoryId:proposal.categoryId,
            expectedBudgetedCents:proposal.originalBudgetedCents,
            expectedAvailableCents:proposal.originalAvailableCents,
            expectedToBudgetCents:proposal.toBudgetBeforeCents,
            targetBudgetedCents:proposal.targetBudgetedCents
        });
        return true;
    }
    Column {
        id: tableBody
        width: grid.width
        spacing: 5
        Row {
            width: parent.width
            spacing: 6
            GohuText {
                width: parent.width-84
                text: "BUDGET"
                font.pixelSize: 11
                color: Colors.cyan
            }
            ActionButton {
                width: 78
                height: 27
                label: grid.submitted ? "SENT" : "SAVE ROW"
                labelPixelSize: 9
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                available: grid.canSave
                onLeftClicked: grid.saveSelected()
            }
        }
        GohuText {
            width: parent.width
            text: grid.selectedCategory
                ? grid.selectedCategory.name+" // "+(grid.proposal && grid.proposal.ok
                    ? (grid.proposal.allocationChangeCents>0?"+":"")
                      +(grid.proposal.allocationChangeCents/100).toFixed(2) : "EDITING")
                : "EDIT A SET AMOUNT OR USE − / +"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            visible: grid.proposal && grid.proposal.ok
                && (grid.proposal.exceedsUnallocatedFunds
                    || grid.proposal.categoryRemainsOverspent)
            text: "NOT ENOUGH UNALLOCATED FUNDS / CATEGORY OVERSPENT"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: grid.writeState==="blocked" || grid.lockedForRecovery
            text: grid.writeState==="blocked" && grid.writeMessage.indexOf("WRITES LOCKED")>=0
                ? "SAVING LOCKED"
                : grid.writeState==="pending" ? "SAVING..."
                : "CHECK ACTUAL BEFORE ANOTHER SAVE"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            GohuText {
                width: parent.width*0.48
                text: "SET (EDIT)"
                font.pixelSize: 9
                color: Colors.cyan
            }
            GohuText {
                width: parent.width*0.26
                text: "SPENT"
                font.pixelSize: 9
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
            }
            GohuText {
                width: parent.width*0.26
                text: "LEFT"
                font.pixelSize: 9
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
            }
        }
        Repeater {
            model: grid.snapshot && Array.isArray(grid.snapshot.categories)
                ? grid.snapshot.categories : []
            delegate: Rectangle {
                id: categoryRow
                required property var modelData
                width: tableBody.width
                height: 62
                color: Colors.black
                border.width: 1
                border.color: grid.selectedCategoryId===modelData.id
                    ? Colors.magenta
                    : modelData.availableCents<0 ? Colors.orange : Colors.cyan
                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.leftMargin: 5
                    anchors.topMargin: 3
                    width: parent.width-10
                    text: modelData.name
                    textFormat: Text.PlainText
                    font.pixelSize: 10
                    color: Colors.white
                    elide: Text.ElideRight
                }
                Row {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 4
                    anchors.rightMargin: 4
                    anchors.bottomMargin: 4
                    height: 27
                    spacing: 0
                    Item {
                        width: parent.width*0.48
                        height: parent.height
                        Row {
                            anchors.fill: parent
                            spacing: 2
                            ActionButton {
                                width: 19
                                height: parent.height
                                label: "−"
                                labelPixelSize: 14
                                accentColor: Colors.cyan
                                available: !grid.lockedForRecovery && !grid.submitted
                                onLeftClicked: grid.step(categoryRow.modelData,-100)
                            }
                            FinanceMoneyInput {
                                width: Math.max(26,parent.width-44)
                                height: parent.height
                                value: grid.selectedCategoryId===categoryRow.modelData.id
                                    ? grid.draftText
                                    : (categoryRow.modelData.budgetedCents/100).toFixed(2)
                                canEdit: !grid.lockedForRecovery && !grid.submitted
                                onValueEdited: function(value) {
                                    grid.choose(categoryRow.modelData,value);
                                }
                            }
                            ActionButton {
                                width: 19
                                height: parent.height
                                label: "+"
                                labelPixelSize: 14
                                accentColor: Colors.cyan
                                available: !grid.lockedForRecovery && !grid.submitted
                                onLeftClicked: grid.step(categoryRow.modelData,100)
                            }
                        }
                    }
                    GohuText {
                        width: parent.width*0.26
                        height: parent.height
                        text: (categoryRow.modelData.spentCents/100).toFixed(2)
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: Colors.white
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width*0.26
                        height: parent.height
                        text: (categoryRow.modelData.availableCents/100).toFixed(2)
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: categoryRow.modelData.availableCents<0
                            ? Colors.orange : Colors.omnitrix
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
