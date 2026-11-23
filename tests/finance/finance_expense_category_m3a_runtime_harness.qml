import QtQuick
import QtQuick.Window
import "../../widgets" as FinanceWidgets

// Simple M3a test-only source: an isolated QML pane with fictional input.
Window {
    id: root
    objectName: "expenseCategoryM3aHarness"
    width: 520
    height: 770
    visible: true
    color: "#190E2B"

    function original(){
        return {
            schemaVersion:1,source:"actual-budget",readOnly:true,
            sourceKey:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            month:"2026-11",toBudgetCents:12000,
            accounts:[{id:"checking",name:"Personal Checking",balanceCents:35000}],
            categoryGroups:[{id:"needs",name:"Needs"},{id:"wants",name:"Wants"}],
            categories:[
                {id:"groceries",name:"Groceries",groupId:"needs",
                 availableCents:7500,spentCents:-2500,budgetedCents:10000},
                {id:"coffee",name:"Coffee",groupId:"wants",
                 availableCents:500,spentCents:-500,budgetedCents:1000}
            ]
        };
    }
    function originalDraft() {
        return {
            action:"create",direction:"expense",editing:false,
            sourceKey:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            month:"2026-11",accountId:"checking",date:"2026-11-23",
            description:"Fictional Supermarket",amountCents:-1250
        };
    }
    property var fixture: original()
    function openFixture(){return previewPane.begin(originalDraft());}
    function beginIncome(){
        var draft=originalDraft();draft.direction="income";
        return previewPane.begin(draft);
    }
    function selectGroceries(){return previewPane.selectCategory("groceries");}
    function selectCoffee(){return previewPane.selectCategory("coffee");}
    function propose(){return previewPane.calculate();}
    function resetSource(){fixture=original();}
    function switchMonth(){
        var s=original();s.month="2026-12";fixture=s;
    }
    function duplicateCategory(){
        var s=original();s.categories.push({...s.categories[0]});fixture=s;
    }
    function breakSource(){
        var s=original();s.sourceKey="invalid";fixture=s;
    }
    function noSource(){fixture=null;}

    FinanceWidgets.FinanceExpenseCategoryPreviewPane {
        id: previewPane
        objectName: "actualExpenseCategoryPreview"
        width: root.width-24
        x: 12
        y: 12
        snapshot: root.fixture
    }
}
