import QtQuick
import Quickshell
import Quickshell.Io

// Manual, memory-only read-only connection. No financial writes and no
// credential values passed into the Qt UI or process arguments.
Scope {
    id: budgetBridge
    property var snapshot: null
    property string state: "idle"
    property string message: "Press REFRESH to read your local budget."
    readonly property bool loading: state === "loading"

    function fail(reason) {
        snapshot = null;
        state = "failed";
        message = reason || "Could not read the local budget.";
    }

    function refresh() {
        if (loading || probe.running)
            return false;
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
                FINANCEW_MONTH: null
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
        if (!json)
            return;
        let payload;
        try {
            payload = JSON.parse(json);
            if (!payload || payload.schemaVersion !== 1
                || payload.source !== "actual-budget"
                || payload.readOnly !== true
                || !/^\d{4}-\d{2}$/.test(String(payload.month || ""))
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
        } catch {
            fail("Budget data format was not recognized.");
            return;
        }
        snapshot = payload;
        state = "ready";
        message = "Manual read complete.";
    }

    function acceptError(raw) {
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
            Qt.callLater(function() {
                if (budgetBridge.state === "loading")
                    budgetBridge.fail("Local budget read failed.");
            });
        }
    }
}
