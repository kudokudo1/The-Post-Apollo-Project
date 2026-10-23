import QtQuick
import "../components"

// FinanceW staged NEW transaction editor. UI-memory-only, intentionally has
// no Actual API, Process, persistence, or mutation methods.
Item {
    id: draft
    signal saveRequested(var payload)
    signal draftSaveRequested(var payload)
    property string localDraftId: ""
    property string draftStoreState: "idle"
    property string draftStoreMessage: ""
    property bool editing: false
    property string editingId: ""
    property string requestId: ""
    property var original: null
    property string saveState: "idle"
    property string saveMessage: ""
    readonly property bool savePending: saveState === "pending"
    readonly property bool localPending: draftStoreState === "pending"
    property string selectedMonth: ""
    property var accounts: []
    property string sourceKey: ""
    property bool open: false
    property bool reviewed: false
    property string dateText: ""
    property string payeeText: ""
    property string amountText: ""
    property string direction: "expense"
    property int accountIndex: 0

    readonly property string accountName:
        Array.isArray(accounts) && accountIndex >= 0
        && accountIndex < accounts.length
        ? String(accounts[accountIndex].name || "") : ""
    readonly property string accountId:
        Array.isArray(accounts) && accountIndex >= 0
        && accountIndex < accounts.length
        ? String(accounts[accountIndex].id || "") : ""
    readonly property string validationError: validate()
    readonly property int amountCents: parseCents(amountText)
    readonly property int signedAmountCents:
        direction === "expense" ? -amountCents : amountCents

    visible: open
    width: parent ? parent.width : 0
    height: open ? draftBody.implicitHeight + 18 : 0

    function parseCents(text) {
        const source = String(text || "");
        if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(source))
            return -1;
        const parts = source.split(".");
        const pennies = Number(parts[0]) * 100
                        + Number((parts[1] || "").padEnd(2, "0"));
        return Number.isSafeInteger(pennies) && pennies > 0 ? pennies : -1;
    }

    function validDate(text) {
        const input = String(text || "");
        if (!/^\d{4}-\d{2}-\d{2}$/.test(input)
                || input.slice(0, 7) !== selectedMonth)
            return false;
        const parts = input.split("-").map(Number);
        const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
        return date.getUTCFullYear() === parts[0]
               && date.getUTCMonth() + 1 === parts[1]
               && date.getUTCDate() === parts[2];
    }

    function validate() {
        if (!Array.isArray(accounts) || accounts.length === 0
                || !accountName || !accountId || !/^[a-f0-9]{64}$/.test(sourceKey))
            return "NO ACCOUNT AVAILABLE";
        if (!validDate(dateText))
            return "DATE MUST BE VALID AND IN SELECTED MONTH";
        if (!String(payeeText).trim()
                || String(payeeText).trim().length > 120)
            return "DESCRIPTION REQUIRED (MAX 120)";
        if (amountCents < 1)
            return "AMOUNT MUST BE POSITIVE, MAX 2 DECIMALS";
        if (direction !== "expense" && direction !== "income")
            return "INVALID DIRECTION";
        return "";
    }

    function newRequestId() {
        let result = "";
        for (let i = 0; i < 32; ++i)
            result += Math.floor(Math.random() * 16).toString(16);
        return result;
    }

    function beginEdit(transaction) {
        if (!transaction || transaction.editable !== true
                || !transaction.id || !transaction.accountId
                || !Number.isSafeInteger(transaction.amountCents)
                || transaction.amountCents === 0
                || !validDate(transaction.date))
            return false;
        const position = Array.isArray(accounts)
            ? accounts.findIndex(function(a) {return a.id === transaction.accountId;})
            : -1;
        if (position < 0)
            return false;
        clear();
        editing = true;
        editingId = transaction.id;
        original = {date:transaction.date,amountCents:transaction.amountCents};
        accountIndex = position;
        dateText = transaction.date;
        payeeText = transaction.description;
        amountText = (Math.abs(transaction.amountCents) / 100).toFixed(2);
        direction = transaction.amountCents < 0 ? "expense" : "income";
        requestId = newRequestId();
        reviewed = false;
        open = true;
        return true;
    }

    function requestDraftSave() {
        // Incomplete dates, descriptions, and amounts are allowed for drafts.
        // This never goes through the Actual transaction writer.
        if (editing || draftStoreState !== "ready"
                || localPending || savePending || !accountId
                || !/^[a-f0-9]{64}$/.test(sourceKey))
            return false;
        draftSaveRequested({id:localDraftId || null, sourceKey:sourceKey,
            month:selectedMonth,accountId:accountId,dateText:dateText,
            payeeText:payeeText,amountText:amountText,direction:direction});
        return true;
    }

    function beginStored(record) {
        if (!record || record.sourceKey !== sourceKey
                || record.month !== selectedMonth || !record.id)
            return false;
        const position = Array.isArray(accounts)
            ? accounts.findIndex(function(a) {return a.id === record.accountId;}) : -1;
        if (position < 0)
            return false;
        clear();
        localDraftId = record.id;
        accountIndex = position;
        dateText = record.dateText;
        payeeText = record.payeeText;
        amountText = record.amountText;
        direction = record.direction;
        requestId = newRequestId();
        open = true;
        return true;
    }

    function requestCommit() {
        if (!reviewed || validationError !== "" || !requestId
                || savePending || saveState === "uncertain")
            return false;
        const payload = {
            action: editing ? "update" : "create",
            requestId: requestId,
            sourceKey: sourceKey,
            accountId: accountId,
            month: selectedMonth,
            date: dateText,
            description: payeeText.trim(),
            amountCents: signedAmountCents
        };
        if (editing) {
            payload.transactionId = editingId;
            payload.original = original;
        }
        saveRequested(payload);
        return true;
    }

    function begin() {
        if (!Array.isArray(accounts) || accounts.length === 0)
            return false;
        clear();
        accountIndex = 0;
        requestId = newRequestId();
        dateText = selectedMonth + "-01";
        payeeText = "";
        amountText = "";
        direction = "expense";
        reviewed = false;
        open = true;
        return true;
    }

    function clear() {
        open = false;
        reviewed = false;
        editing = false;
        localDraftId = "";
        editingId = "";
        requestId = "";
        original = null;
        accountIndex = 0;
        dateText = "";
        payeeText = "";
        amountText = "";
        direction = "expense";
    }

    onSelectedMonthChanged: clear()
    onSourceKeyChanged: clear()
    onAccountsChanged: {
        if (open)
            clear(); // A refreshed snapshot invalidates in-progress context.
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 1
        border.color: Colors.omnitrix
    }

    Column {
        id: draftBody
        x: 9
        y: 9
        width: Math.max(0, draft.width - 18)
        spacing: 7

        GohuText {
            width: parent.width
            text: draft.editing ? "EDIT TRANSACTION // REVIEW"
                  : draft.localDraftId ? "SAVED LOCAL DRAFT // REVIEW"
                  : "NEW TRANSACTION // REVIEW"
            font.pixelSize: 11
            color: Colors.omnitrix
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: "DATE // MONTH / DAY / YEAR"
            font.pixelSize: 9
            color: Colors.cyan
        }

        FinanceDateInput {
            width: parent.width
            value: draft.dateText
            fallbackDate: draft.selectedMonth ? draft.selectedMonth+"-01" : ""
            canEdit: !draft.savePending
            onValueEdited: function(value) {
                draft.dateText=value;
                draft.reviewed=false;
            }
        }
        GohuText {
            width: parent.width
            text: "DESCRIPTION"
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
                text: draft.payeeText
                color: Colors.white
                font.pixelSize: 12
                maximumLength: 120
                readOnly: draft.editing
                selectByMouse: true
                onTextEdited: {
                    draft.payeeText = text;
                    draft.reviewed = false;
                }
            }
        }

        GohuText {
            width: parent.width
            text: "AMOUNT // USD"
            font.pixelSize: 9
            color: Colors.cyan
        }

        FinanceMoneyInput {
            width: parent.width
            value: draft.amountText
            canEdit: !draft.savePending
            onValueEdited: function(value) {
                draft.amountText=value;
                draft.reviewed=false;
            }
        }

        ActionButton {
            // Keep its label and sampled shadow aligned when content/state changes.
            trackLabelGlowLocally: true
            width: parent.width
            height: 28
            accentColor: Colors.omnitrix
            label: "ACCOUNT // " + draft.accountName
            labelPixelSize: 10
            available: draft.accounts && draft.accounts.length > 0
                       && !draft.editing && !draft.savePending
            onLeftClicked: {
                draft.accountIndex = (draft.accountIndex + 1) % draft.accounts.length;
                draft.reviewed = false;
            }
        }

        ActionButton {
            // Keep its label and sampled shadow aligned when content/state changes.
            trackLabelGlowLocally: true
            width: parent.width
            height: 28
            accentColor: Colors.cyan
            label: draft.direction === "expense" ? "EXPENSE" : "INCOME"
            labelPixelSize: 10
            available: !draft.savePending
            onLeftClicked: {
                draft.direction = draft.direction === "expense" ? "income" : "expense";
                draft.reviewed = false;
            }
        }

        GohuText {
            width: parent.width
            text: draft.reviewed
                  ? "PREVIEW // " + draft.dateText + "  "
                    + (draft.signedAmountCents < 0 ? "-$" : "$")
                    + (Math.abs(draft.signedAmountCents) / 100).toFixed(2)
                  : draft.validationError
                    ? draft.validationError : "READY TO PREVIEW"
            font.pixelSize: 10
            textFormat: Text.PlainText
            color: draft.validationError ? Colors.orange : Colors.omnitrix
            wrapMode: Text.WordWrap
        }

        GohuText {
            width: parent.width
            visible: draft.reviewed
            text: draft.accountName + " // " + draft.payeeText.trim()
            font.pixelSize: 10
            textFormat: Text.PlainText
            color: Colors.white
            wrapMode: Text.WordWrap
        }

        Row {
            width: parent.width
            spacing: 7
            ActionButton {
                // Keep its label and sampled shadow aligned when content/state changes.
                trackLabelGlowLocally: true
                width: (parent.width - 7) / 2
                height: 30
                accentColor: Colors.omnitrix
                label: draft.reviewed ? "CONFIRM SAVE" : "PREVIEW"
                available: !draft.validationError && !draft.savePending
                           && draft.saveState !== "uncertain"
                onLeftClicked: {
                    if (draft.reviewed)
                        draft.requestCommit();
                    else
                        draft.reviewed = true;
                }
            }
            ActionButton {
                // Keep its label and sampled shadow aligned when content/state changes.
                trackLabelGlowLocally: true
                width: (parent.width - 7) / 2
                height: 30
                accentColor: Colors.orange
                label: "CANCEL"
                available: !draft.savePending
                onLeftClicked: draft.clear()
            }
        }

        ActionButton {
            trackLabelGlowLocally: true
            width: parent.width
            height: 28
            accentColor: Colors.cyan
            label: draft.localDraftId ? "UPDATE DRAFT" : "SAVE DRAFT"
            labelPixelSize: 10
            available: !draft.editing && draft.draftStoreState === "ready"
                       && !draft.localPending && !draft.savePending
                       && draft.accounts && draft.accounts.length > 0
            onLeftClicked: draft.requestDraftSave()
        }

        GohuText {
            width: parent.width
            visible: draft.draftStoreState === "failed"
                     || draft.localPending
            text: draft.localPending ? "LOCAL DRAFT // STORING"
                  : draft.draftStoreMessage
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: draft.saveState === "pending"
                  ? "SAVING // DO NOT CLOSE OR RESTART SHELL"
                  : draft.saveState === "blocked" || draft.saveState === "uncertain"
                  ? draft.saveMessage
                  : draft.reviewed
                  ? "VERIFY DETAILS, THEN CONFIRM SAVE"
                  : "PREVIEW ONLY // NO CHANGES YET"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
    }
}
