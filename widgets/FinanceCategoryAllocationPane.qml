import QtQuick
import "../components"
import "../services/finance/FinanceAllocationPreview.js" as PreviewRules

// D12d: preview and explicit confirmation only. The separate guarded writer
// owns every mutation and permission check; no Actual API exists in this pane.
Item {
    id: allocation
    property var snapshot: null
    property bool open: false
    property string categoryId: ""
    property string targetText: ""
    property var proposal: null
    property string errorText: ""
    property string writeState: "idle"
    property string writeMessage: ""
    property bool approvalArmed: false
    property bool submitted: false
    property string requestId: ""
    signal saveRequested(var payload)
    readonly property bool writePending: writeState === "pending"
    readonly property bool writeUncertain: writeState === "uncertain"
    readonly property bool proposalEligible: !!proposal && proposal.ok
        && proposal.allocationChangeCents !== 0
        && !proposal.exceedsUnallocatedFunds
        && !proposal.categoryRemainsOverspent
        && category && proposal.categoryId === category.id
        && snapshot && proposal.sourceKey === snapshot.sourceKey
        && proposal.month === snapshot.month
        && proposal.originalBudgetedCents === category.budgetedCents
        && proposal.originalAvailableCents === category.availableCents
        && proposal.toBudgetBeforeCents === snapshot.toBudgetCents
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
        approvalArmed = false;
        submitted = false;
        requestId = "";
    }

    function newRequestId() {
        let result = "";
        for (let i=0;i<32;++i)
            result += Math.floor(Math.random() * 16).toString(16);
        return result;
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
        approvalArmed = false;
        submitted = false;
        requestId = newRequestId();
        return true;
    }

    function requestSave() {
        if (!open || !proposalEligible || !approvalArmed
                || submitted || writePending || writeUncertain || !requestId)
            return false;
        // Values are bound to the exact source/month/category from preview.
        // The writer independently rereads Actual and rejects stale data.
        submitted = true;
        saveRequested({
            action:"set-amount",requestId:requestId,
            sourceKey:proposal.sourceKey,month:proposal.month,
            categoryId:proposal.categoryId,
            expectedBudgetedCents:proposal.originalBudgetedCents,
            expectedAvailableCents:proposal.originalAvailableCents,
            expectedToBudgetCents:proposal.toBudgetBeforeCents,
            targetBudgetedCents:proposal.targetBudgetedCents
        });
        return true;
    }

    onSnapshotChanged: clear()
    onTargetTextChanged: {
        proposal = null;
        approvalArmed = false;
        submitted = false;
        requestId = "";
        errorText = "";
    }
    onWriteStateChanged: {
        if (writeState === "uncertain" || writeState === "committed")
            approvalArmed = false;
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
        FinanceMoneyInput {
            width: parent.width
            value: allocation.targetText
            canEdit: !allocation.writePending && !allocation.writeUncertain
            onValueEdited: function(value) {allocation.targetText=value;}
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
                    && !allocation.writePending && !allocation.writeUncertain
                onLeftClicked: allocation.calculate()
            }
            ActionButton {
                trackLabelGlowLocally: true
                width: (parent.width - 7) / 2
                height: 30
                label: "CANCEL"
                labelPixelSize: 10
                accentColor: Colors.orange
                available: !allocation.writePending
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
        ActionButton {
            trackLabelGlowLocally: true
            width: parent.width
            height: 30
            label: allocation.submitted ? "REQUEST SUBMITTED"
                 : allocation.approvalArmed ? "CONFIRM SAVE" : "ARM SAVE"
            labelPixelSize: 10
            accentColor: allocation.approvalArmed ? Colors.magenta : Colors.orange
            available: allocation.proposalEligible && !allocation.submitted
                && !allocation.writePending && !allocation.writeUncertain
            onLeftClicked: {
                if (allocation.approvalArmed)
                    allocation.requestSave();
                else
                    allocation.approvalArmed = true;
            }
        }
        GohuText {
            width: parent.width
            visible: !!allocation.proposal && !allocation.proposalEligible
            text: "NOT ELIGIBLE TO SAVE // ADJUST PROPOSAL"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: allocation.writePending
                || allocation.writeState === "blocked"
                || allocation.writeUncertain
            text: allocation.writeMessage
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: allocation.approvalArmed
                  ? "NEXT STEP CHANGES ACTUAL IF SEPARATELY AUTHORIZED"
                  : "PREVIEW IS SAFE // SAVING REQUIRES OPERATOR ACTIVATION"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
