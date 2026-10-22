import QtQuick
import "../components"

// FinanceW staged NEW transaction editor. UI-memory-only, intentionally has
// no Actual API, Process, persistence, or mutation methods.
Item {
    id: draft
    property string selectedMonth: ""
    property var accounts: []
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
    readonly property string validationError: validate()
    readonly property int amountCents: parseCents(amountText)
    readonly property int signedAmountCents:
        direction === "expense" ? -amountCents : amountCents

    visible: open
    width: parent ? parent.width : 0
    height: open ? draftBody.implicitHeight + 18 : 0

    function parseCents(text) {
        const source = String(text || "");
        if (!/^\\d{1,9}(?:\\.\\d{1,2})?$/.test(source))
            return -1;
        const parts = source.split(".");
        const pennies = Number(parts[0]) * 100
                        + Number((parts[1] || "").padEnd(2, "0"));
        return Number.isSafeInteger(pennies) && pennies > 0 ? pennies : -1;
    }

    function validDate(text) {
        const input = String(text || "");
        if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(input)
                || input.slice(0, 7) !== selectedMonth)
            return false;
        const parts = input.split("-").map(Number);
        const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
        return date.getUTCFullYear() === parts[0]
               && date.getUTCMonth() + 1 === parts[1]
               && date.getUTCDate() === parts[2];
    }

    function validate() {
        if (!Array.isArray(accounts) || accounts.length === 0 || !accountName)
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

    function begin() {
        if (!Array.isArray(accounts) || accounts.length === 0)
            return false;
        accountIndex = 0;
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
        accountIndex = 0;
        dateText = "";
        payeeText = "";
        amountText = "";
        direction = "expense";
    }

    onSelectedMonthChanged: clear()
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
            text: "NEW TRANSACTION // DRAFT ONLY"
            font.pixelSize: 11
            color: Colors.omnitrix
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: "DATE // YYYY-MM-DD"
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
                text: draft.dateText
                color: Colors.white
                font.pixelSize: 12
                selectByMouse: true
                onTextEdited: {
                    draft.dateText = text;
                    draft.reviewed = false;
                }
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

        Rectangle {
            width: parent.width
            height: 28
            color: Colors.dark
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 6
                text: draft.amountText
                color: Colors.white
                font.pixelSize: 12
                selectByMouse: true
                onTextEdited: {
                    draft.amountText = text;
                    draft.reviewed = false;
                }
            }
        }

        ActionButton {
            width: parent.width
            height: 28
            accentColor: Colors.omnitrix
            label: "ACCOUNT // " + draft.accountName
            labelPixelSize: 10
            available: draft.accounts && draft.accounts.length > 0
            onLeftClicked: {
                draft.accountIndex = (draft.accountIndex + 1) % draft.accounts.length;
                draft.reviewed = false;
            }
        }

        ActionButton {
            width: parent.width
            height: 28
            accentColor: Colors.cyan
            label: draft.direction === "expense" ? "EXPENSE" : "INCOME"
            labelPixelSize: 10
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
                width: (parent.width - 7) / 2
                height: 30
                accentColor: Colors.omnitrix
                label: "PREVIEW"
                available: !draft.validationError
                onLeftClicked: draft.reviewed = true
            }
            ActionButton {
                width: (parent.width - 7) / 2
                height: 30
                accentColor: Colors.orange
                label: "CANCEL"
                onLeftClicked: draft.clear()
            }
        }

        GohuText {
            width: parent.width
            text: "NOT SENT // NO SAVE OR EDIT PERMISSION"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
    }
}
