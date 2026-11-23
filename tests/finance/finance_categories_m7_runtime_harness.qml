import QtQuick
import QtQuick.Window
import "../../widgets" as FinanceWidgets

// Headless QML runtime harness for the actual FinanceCategoriesPane.
// Uses fictional read-only data. There is deliberately NO write service.
Window {
    id: fixtureRoot
    objectName: "categoryRuntimeHarness"
    width: 510
    height: 920
    visible: true
    color: "#16051F"

    function original() {
        return {
            readOnly: true, source: "actual-budget",
            sourceKey: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            month: "2026-11",
            categoryGroups: [
                {id:"needs",name:"Needs"},
                {id:"wants",name:"Wants"},
                {id:"empty",name:"Empty"}
            ],
            categories: [
                {id:"rent",name:"Rent",group:"Needs",groupId:"needs",
                    budgetedCents:120000,availableCents:120000},
                {id:"coffee",name:"Coffee",group:"Wants",groupId:"wants",
                    budgetedCents:1500,availableCents:1000}
            ]
        };
    }
    property var fixture: original()

    function resetFixture() { fixture=original(); }
    function noBudgetFixture() { fixture=null; }
    function emptyCategoriesFixture() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.categories=[];
        fixture=copy;
    }
    function refreshFixture() {
        fixture=JSON.parse(JSON.stringify(fixture));
    }
    function switchMonth() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.month="2026-12";
        fixture=copy;
    }
    function changeGroupName() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.categoryGroups[0].name="New Needs";
        fixture=copy;
    }
    function changeCategoryName() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.categories[0].name="New Rent";
        fixture=copy;
    }
    function addIncomeGroup() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.categoryGroups.push({id:"income",name:"Income",is_income:true});
        fixture=copy;
    }
    function corruptGroupIdentity() {
        var copy=JSON.parse(JSON.stringify(fixture));
        copy.categoryGroups.push({id:"needs",name:"Duplicate Needs"});
        fixture=copy;
    }
    function openNeedsRename() {
        return actualCategoriesPane.beginRenameGroup(fixture.categoryGroups[0]);
    }
    function openRentCategoryRename() {
        return actualCategoriesPane.beginRename(fixture.categories[0]);
    }
    function openIncomeRename() {
        return actualCategoriesPane.beginRenameGroup(
            fixture.categoryGroups[fixture.categoryGroups.length-1]);
    }
    function openWantsRename() {
        return actualCategoriesPane.beginRenameGroup(fixture.categoryGroups[1]);
    }

    FinanceWidgets.FinanceCategoriesPane {
        id: actualCategoriesPane
        objectName: "actualCategoriesPane"
        width: fixtureRoot.width-24
        x: 12
        y: 8
        snapshot: fixtureRoot.fixture
    }
}
