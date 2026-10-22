import QtQuick
import "../components"
import "../services/finance/FinanceAllocationPreview.js" as PreviewRules

// D11 proposal calculator only. No Process, persistence, financial write,
// Actual API methods, or mutation authority exists in this pane.
Item {
    id: allocation
    property var snapshot: null
    property bool open: false
    property string categoryId: ""
    property string targetText: ""
    property var proposal: null
    property string errorText: ""
    readonly property bool sourceReady: !!snapshot
        && snapshot.sourceKey && snapshot.readOnly === true
    readonly property var category:
        snapshot && Array.isArray(snapshot.categories)
        ? snapshot.categories.find(function(c) {return c.id === categoryId;}) : null

    visible: open
    width: parent ? parent.width : 0
    height: open ? paneBody.implicitHeight + 18 : 0

    function clear() {
        open = false;
        categoryId = "";
        targetText = "";
        proposal = null;
        errorText = "";
    }

    function begin(categoryRow) {
        if (!sourceReady || !categoryRow || !categoryRow.id
                || !Number.isSafeInteger(categoryRow.budgetedCents))
            return false;
        const matches = snapshot.categories.filter(function(c) {
            return c && c.id === categoryRow.id;
        });
        if (matches.length !== 1)
            return false;
        clear();
        categoryId = categoryRow.id;
        targetText = (Math.max(0, categoryRow.budgetedCents) / 100).toFixed(2);
        open = true;
        return true;
    }

    function calculate() {
        proposal = null;
        const result = PreviewRules.previewAllocation(snapshot, categoryId, targetText);
        if (!result.ok) {
            errorText = result.reason;
            return false;
        }
        errorText = "";
        proposal = result;
        return true;
    }

    onSnapshotChanged: clear()
    onTargetTextChanged: {
        proposal = null;
        errorText = "";
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
    }
    Column {
        id: paneBody
        x: 9
        y: 9
        width: Math.max(0, allocation.width - 18)
        spacing: 8
        GohuText {
            width: parent.width
            text: "CATEGORY ALLOCATION // PREVIEW"
            font.pixelSize: 11
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: allocation.category ? allocation.category.name : "CATEGORY UNAVAILABLE"
            font.pixelSize: 10
            color: Colors.white
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "PROPOSED ALLOCATION // USD"
            font.pixelSize: 9
            color: Colors.cyan
        }
        Rectangle {
            width: parent.width
            height: 28
            color: Colors.dark
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 6
                text: allocation.targetText
                color: Colors.white
                font.pixelSize: 12
                selectByMouse: true
                onTextEdited: allocation.targetText = text
            }
        }
        GohuText {
            width: parent.width
            text: allocation.category
                  ? "CURRENT SET // "
                    + (allocation.category.budgetedCents / 100).toFixed(2)
                    + " USD" : "NO CATEGORY"
            font.pixelSize: 10
            textFormat: Text.PlainText
            color: Colors.white
        }
        Row {
            width: parent.width
            spacing: 7
            ActionButton {
                trackLabelGlowLocally: true
                width: (parent.width - 7) / 2
                height: 30
                label: "PREVIEW"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: allocation.open && allocation.sourceReady
                onLeftClicked: allocation.calculate()
            }
            ActionButton {
                trackLabelGlowLocally: true
                width: (parent.width - 7) / 2
                height: 30
                label: "CANCEL"
                labelPixelSize: 10
                accentColor: Colors.orange
                onLeftClicked: allocation.clear()
            }
        }
        GohuText {
            width: parent.width
            visible: !!allocation.errorText
            text: allocation.errorText
            textFormat: Text.PlainText
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Column {
            width: parent.width
            spacing: 5
            visible: !!allocation.proposal && allocation.proposal.ok
            GohuText {
                width: parent.width
                text: allocation.proposal
                    ? "SET // " + (allocation.proposal.originalBudgetedCents / 100).toFixed(2)
                      + " → " + (allocation.proposal.targetBudgetedCents / 100).toFixed(2)
                    : ""
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: Colors.white
            }
            GohuText {
                width: parent.width
                text: allocation.proposal
                    ? "CATEGORY LEFT // " + (allocation.proposal.originalAvailableCents / 100).toFixed(2)
                      + " → " + (allocation.proposal.categoryAvailableAfterCents / 100).toFixed(2)
                    : ""
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: allocation.proposal && allocation.proposal.categoryRemainsOverspent
                       ? Colors.magenta : Colors.omnitrix
            }
            GohuText {
                width: parent.width
                text: allocation.proposal
                    ? "TO BUDGET // " + (allocation.proposal.toBudgetBeforeCents / 100).toFixed(2)
                      + " → " + (allocation.proposal.toBudgetAfterCents / 100).toFixed(2)
                    : ""
                textFormat: Text.PlainText
                font.pixelSize: 10
                color: allocation.proposal && allocation.proposal.exceedsUnallocatedFunds
                       ? Colors.orange : Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: allocation.proposal && allocation.proposal.exceedsUnallocatedFunds
                text: "WARNING // PROPOSAL EXCEEDS TO-BUDGET FUNDS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
        GohuText {
            width: parent.width
            text: "SIMULATION ONLY // NO ACTUAL CHANGES"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
