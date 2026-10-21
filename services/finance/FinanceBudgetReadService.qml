import QtQuick
import Quickshell
import Quickshell.Io

// Read-only Actual connection: refresh on FinanceW open or month change.
// One probe runs at a time, with latest-month-wins queued refreshes.
// Nothing starts at shell boot; credentials never enter the Qt UI or argv.
Scope {
    id: budgetBridge
    property var snapshot: null
    property string state: "idle"
    property string message: "Press REFRESH to read your local budget."
    readonly property bool loading: state === "loading"
    // Only Process may read the local budget; refreshes are serialized.
    property string selectedMonth: Qt.formatDate(new Date(), "yyyy-MM")
    property string inFlightMonth: ""
    property bool pendingRefresh: false

    function shiftMonth(direction) {
        if (direction !== 1 && direction !== -1)
            return false;
        const parts = selectedMonth.split("-");
        if (parts.length !== 2)
            return false;
        const monthIndex = Number(parts[0]) * 12 + Number(parts[1]) - 1
                           + direction;
        const nextYear = Math.floor(monthIndex / 12);
        const nextMonth = monthIndex - nextYear * 12 + 1;
        if (nextYear < 1900 || nextYear > 2099
                || nextMonth < 1 || nextMonth > 12)
            return false;
        selectedMonth = String(nextYear) + "-"
                        + String(nextMonth).padStart(2, "0");
        // Never show another month's values while navigating.
        snapshot = null;
        state = "idle";
        message = "Reading selected month.";
        refresh();
        return true;
    }

    function fail(reason) {
        snapshot = null;
        state = "failed";
        message = reason || "Could not read the local budget.";
    }

    function refresh() {
        // During a slow download, keep the latest selection and fetch it
        // once the current read exits. Repeated opens don't spawn duplicates.
        if (probe.running) {
            pendingRefresh = selectedMonth !== inFlightMonth;
            snapshot = null;
            state = "loading";
            message = pendingRefresh ? "Waiting to read selected month."
                                     : "Reading the local budget.";
            return false;
        }
        pendingRefresh = false;
        inFlightMonth = selectedMonth;
        snapshot = null;
        state = "loading";
        message = "Reading the local budget.";
        probe.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/read_budget.mjs")],
            environment: ({
                ACTUAL_SYNC_ID: null,
                ACTUAL_SYNC_ID_FILE: null,
                ACTUAL_PASSWORD_FILE: null,
                ACTUAL_SERVER_URL: "http://127.0.0.1:5007",
                FINANCEW_MONTH: selectedMonth
            })
        });
        return true;
    }

    function acceptOutput(raw) {
        const lines = String(raw || "").split(/\r?\n/);
        let json = "";
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].indexOf('{"schemaVersion":') === 0) {
                json = lines[i];
                break;
            }
        }
        if (!json || inFlightMonth !== selectedMonth)
            return; // A superseded month may never overwrite the selected one.
        let payload;
        try {
            payload = JSON.parse(json);
            if (!payload || payload.schemaVersion !== 1
                || payload.source !== "actual-budget"
                || payload.readOnly !== true
                || !/^\d{4}-\d{2}$/.test(String(payload.month || ""))
                || payload.month !== selectedMonth
                || !Number.isSafeInteger(payload.toBudgetCents)
                || !Array.isArray(payload.accounts)
                || !Array.isArray(payload.categories)
                || !payload.accounts.every(function(a) {
                    return a && typeof a.name === "string"
                        && Number.isSafeInteger(a.balanceCents);
                })
                || !payload.categories.every(function(c) {
                    return c && typeof c.name === "string"
                        && Number.isSafeInteger(c.availableCents)
                        && Number.isSafeInteger(c.budgetedCents)
                        && Number.isSafeInteger(c.spentCents);
                }))
                throw new Error("Invalid snapshot");
        } catch (error) {
            fail("Budget data format was not recognized.");
            return;
        }
        snapshot = payload;
        state = "ready";
        message = "Budget read complete.";
    }

    function acceptError(raw) {
        if (inFlightMonth !== selectedMonth)
            return; // Suppress errors from superseded month reads.
        const detail = String(raw || "");
        if (detail.indexOf("FINANCEW_READ_ONLY_ERROR") < 0)
            return;
        if (detail.indexOf("missing-or-invalid-sync-id") >= 0)
            fail("Sync ID not configured. See FinanceW setup.");
        else
            fail("Local budget read failed. Check server and credentials.");
    }

    Process {
        id: probe
        stdout: StdioCollector {
            onStreamFinished: budgetBridge.acceptOutput(text)
        }
        stderr: StdioCollector {
            onStreamFinished: budgetBridge.acceptError(text)
        }
        onExited: function(exitCode, exitStatus) {
            // Defer until the process/collectors finish delivering output.
            Qt.callLater(function() {
                if (budgetBridge.pendingRefresh) {
                    budgetBridge.pendingRefresh = false;
                    budgetBridge.state = "idle";
                    budgetBridge.refresh();
                } else if (budgetBridge.state === "loading") {
                    budgetBridge.fail("Local budget read failed.");
                }
            });
        }
    }
}
