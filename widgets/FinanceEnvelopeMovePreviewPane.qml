import QtQuick
import "../components"
import "../services/finance/FinanceEnvelopeMovePlan.js" as MoveRules

// FinanceW Simple M2a // staged, unmounted preview only.
// No write signal, Process, filesystem, Actual API, payment or account transfer.
Item {
    id: move
    objectName: "envelopeMovePreviewPane"
    property var snapshot: null
    property bool open: false
    property string fromCategoryId: ""
    property string toCategoryId: ""
    property string amountText: ""
    property var proposal: null
    property string errorText: ""

    readonly property bool sourceReady: !!snapshot
        && snapshot.readOnly===true
        && snapshot.source==="actual-budget"
        && snapshot.schemaVersion===1
        && Array.isArray(snapshot.categories)
    readonly property var choices: sourceReady
        ? snapshot.categories.filter(function(c) {
            return c && typeof c.id==="string" && !!c.id
                && typeof c.name==="string" && !!c.name.trim();
        }) : []
    readonly property var fromCategory: choices.find(function(c) {
        return c.id===fromCategoryId;
    }) || null
    readonly property var toCategory: choices.find(function(c) {
        return c.id===toCategoryId;
    }) || null

    width: parent ? parent.width : 0
    height: open ? paneBody.implicitHeight+18 : 0
    visible: open

    function invalidatePreview() {
        proposal=null;
        errorText="";
    }
    function clear() {
        open=false;
        fromCategoryId="";
        toCategoryId="";
        amountText="";
        invalidatePreview();
        return true;
    }
    function begin() {
        if(!sourceReady || choices.length<2)return false;
        clear();
        open=true;
        return true;
    }
    function chooseFrom(id) {
        if(!open || !sourceReady)return false;
        if(choices.filter(function(c) {return c.id===id;}).length!==1)
            return false;
        fromCategoryId=id;
        return true;
    }
    function chooseTo(id) {
        if(!open || !sourceReady)return false;
        if(choices.filter(function(c) {return c.id===id;}).length!==1)
            return false;
        toCategoryId=id;
        return true;
    }
    function cycleFrom() {
        if(!open || !choices.length)return false;
        const i=choices.findIndex(function(c){return c.id===fromCategoryId;});
        return chooseFrom(choices[(i+1)%choices.length].id);
    }
    function cycleTo() {
        if(!open || !choices.length)return false;
        const i=choices.findIndex(function(c){return c.id===toCategoryId;});
        return chooseTo(choices[(i+1)%choices.length].id);
    }
    function calculate() {
        if(!open || !sourceReady)return false;
        invalidatePreview();
        const result=MoveRules.previewEnvelopeMove(snapshot,fromCategoryId,
                                                    toCategoryId,amountText);
        if(!result.ok) {
            errorText=result.reason;
            return false;
        }
        proposal=result;
        return true;
    }

    // Never keep an approval or snapshot-bound preview after any input/source
    // changes. There is deliberately no approval or save action in M2a.
    onSnapshotChanged: clear()
    onFromCategoryIdChanged: invalidatePreview()
    onToCategoryIdChanged: invalidatePreview()
    onAmountTextChanged: invalidatePreview()

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
        width: Math.max(0,move.width-18)
        spacing: 7
        GohuText {
            width: parent.width
            text: "MOVE BETWEEN ENVELOPES // PREVIEW"
            font.pixelSize: 11
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: "BUDGET ALLOCATIONS ONLY // NOT A BANK TRANSFER"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            objectName: "moveFromPicker"
            width: parent.width
            height: 30
            label: "FROM // "+(move.fromCategory
                ? move.fromCategory.name : "SELECT ENVELOPE")+"  ›"
            labelPixelSize: 9
            accentColor: Colors.orange
            trackLabelGlowLocally: true
            available: move.sourceReady && move.choices.length>=2
            onLeftClicked: move.cycleFrom()
        }
        ActionButton {
            objectName: "moveToPicker"
            width: parent.width
            height: 30
            label: "TO // "+(move.toCategory
                ? move.toCategory.name : "SELECT ENVELOPE")+"  ›"
            labelPixelSize: 9
            accentColor: Colors.cyan
            trackLabelGlowLocally: true
            available: move.sourceReady && move.choices.length>=2
            onLeftClicked: move.cycleTo()
        }
        GohuText {
            width: parent.width
            text: "MOVE AMOUNT // USD"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
        }
        FinanceMoneyInput {
            width: parent.width
            value: move.amountText
            canEdit: move.sourceReady
            onValueEdited: function(value) {move.amountText=value;}
        }
        Row {
            width: parent.width
            spacing: 7
            ActionButton {
                objectName: "movePreviewAction"
                width: (parent.width-7)/2
                height: 30
                label: "PREVIEW MOVE"
                labelPixelSize: 9
                accentColor: Colors.cyan
                trackLabelGlowLocally: true
                available: move.open && move.sourceReady
                onLeftClicked: move.calculate()
            }
            ActionButton {
                objectName: "moveCancelAction"
                width: (parent.width-7)/2
                height: 30
                label: "CANCEL"
                labelPixelSize: 9
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                onLeftClicked: move.clear()
            }
        }
        GohuText {
            objectName: "moveErrorLabel"
            width: parent.width
            visible: !!move.errorText
            text: move.errorText
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Column {
            id: movePreviewSummary
            objectName: "movePreviewSummary"
            width: parent.width
            spacing: 5
            visible: !!move.proposal && move.proposal.ok
            GohuText {
                width: parent.width
                text: move.proposal
                    ? move.proposal.fromName+" // LEFT "
                        +(move.proposal.fromAvailableBeforeCents/100).toFixed(2)
                        +" → "+(move.proposal.fromAvailableAfterCents/100).toFixed(2)
                    : ""
                font.pixelSize: 10
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: move.proposal
                    ? move.proposal.toName+" // LEFT "
                        +(move.proposal.toAvailableBeforeCents/100).toFixed(2)
                        +" → "+(move.proposal.toAvailableAfterCents/100).toFixed(2)
                    : ""
                font.pixelSize: 10
                color: Colors.omnitrix
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: move.proposal
                    ? "UNASSIGNED // UNCHANGED "
                        +(move.proposal.toBudgetAfterCents/100).toFixed(2)
                    : ""
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
            }
            GohuText {
                width: parent.width
                visible: !!move.proposal
                    && move.proposal.destinationRemainsOverspent
                text: "DESTINATION REMAINS OVERSPENT // REVIEW BALANCE"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
            }
        }
        GohuText {
            width: parent.width
            text: "NOT SAVED // ATOMIC FINANCIAL WRITER NOT IMPLEMENTED"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
