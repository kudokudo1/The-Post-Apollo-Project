import QtQuick
import QtQuick.Window
import "../../widgets" as FinanceWidgets

// Test-only integration of the REAL M3a preview + REAL D9 draft component.
// Fictional in-memory budget, no server, Quickshell or payment/writer process.
Window {
    id: root
    objectName: "m3cFixtureRoot"
    width: 520
    height: 1200
    visible: true
    color: "#160D24"
    property int previewCount: 0
    property int savedCount: 0
    property var savedPayload: null

    function original(){
        return {
            schemaVersion:1,source:"actual-budget",readOnly:true,
            sourceKey:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            month:"2026-11",toBudgetCents:12000,
            accounts:[{id:"checking",name:"Personal Checking",balanceCents:35000}],
            categoryGroups:[{id:"needs",name:"Needs"}],
            categories:[{id:"groceries",name:"Groceries",groupId:"needs",
                availableCents:7500,spentCents:-2500,budgetedCents:10000}]
        };
    }
    property var fixture: original()
    function refreshSource(){
        var snapshot=original();
        snapshot.categories[0].availableCents=7100;
        fixture=snapshot;
    }
    function switchMonth(){
        var snapshot=original();
        snapshot.month="2026-12";
        fixture=snapshot;
    }

    FinanceWidgets.FinanceTransactionDraftPane {
        id: draftPane
        objectName: "actualM3cTransactionDraft"
        width: root.width-24
        x: 12
        y: 12
        selectedMonth: root.fixture?root.fixture.month:""
        sourceKey: root.fixture?root.fixture.sourceKey:""
        accounts: root.fixture?root.fixture.accounts:[]
        saveState: "idle"
        draftStoreState: "ready"
        allowCategoryPreview: true
        onCategoryPreviewRequested: function(candidate) {
            if(previewPane.begin(candidate)){
                draftPane.categoryPreviewArmed=true;
                root.previewCount++;
            }
        }
        onSaveRequested: function(payload) {
            if(!draftPane.categoryPreviewArmed){
                root.savedCount++;
                root.savedPayload=payload;
            }
        }
    }

    FinanceWidgets.FinanceExpenseCategoryPreviewPane {
        id: previewPane
        objectName: "actualM3cCategoryPreview"
        x: 12
        y: draftPane.height+24
        width: root.width-24
        snapshot: root.fixture
    }
    Connections {
        target: draftPane
        function onDateTextChanged() { previewPane.clear(); }
        function onPayeeTextChanged() { previewPane.clear(); }
        function onAmountTextChanged() { previewPane.clear(); }
        function onDirectionChanged() { previewPane.clear(); }
        function onAccountIndexChanged() { previewPane.clear(); }
        function onEditingChanged() { previewPane.clear(); }
        function onOpenChanged() {
            if(!draftPane.open)previewPane.clear();
        }
        function onCategoryPreviewArmedChanged() {
            if(!draftPane.categoryPreviewArmed)previewPane.clear();
        }
    }
}
