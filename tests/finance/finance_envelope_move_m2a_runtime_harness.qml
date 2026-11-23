import QtQuick
import QtQuick.Window
import "../../widgets" as FinanceWidgets

// Disposable fictional fixture. No Quickshell, API, writer or permits.
Window {
    id: fixtureRoot
    objectName: "moveFixtureRoot"
    width: 510
    height: 810
    visible: true
    color: "#1A1128"

    function original() {
        return {
            schemaVersion:1,source:"actual-budget",readOnly:true,
            sourceKey:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            month:"2026-11",toBudgetCents:4000,
            categories:[
                {id:"groceries",name:"Groceries",groupId:"needs",
                 budgetedCents:20000,availableCents:14000},
                {id:"fuel",name:"Fuel",groupId:"needs",
                 budgetedCents:5000,availableCents:2500},
                {id:"utilities",name:"Utilities",groupId:"needs",
                 budgetedCents:3000,availableCents:-1000}
            ]
        };
    }
    property var fixture: original()
    function resetFixture(){fixture=original();}
    function newMonth(){
        var clone=JSON.parse(JSON.stringify(fixture));
        clone.month="2026-12";
        fixture=clone;
    }
    function updateBalances(){
        var clone=JSON.parse(JSON.stringify(fixture));
        clone.categories[0].availableCents=13000;
        fixture=clone;
    }
    function dropSource(){fixture=null;}

    FinanceWidgets.FinanceEnvelopeMovePreviewPane {
        id: movePane
        objectName: "realEnvelopeMovePane"
        width: fixtureRoot.width-24
        x: 12
        y: 12
        snapshot: fixtureRoot.fixture
    }
}
