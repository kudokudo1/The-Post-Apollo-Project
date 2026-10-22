import QtQuick
import Quickshell
import Quickshell.Io

// D15 on-demand read-only historical scan. No startup or polling hooks,
// write permits, transaction mutators, or persistent financial caches.
Scope {
    id: history
    property string sourceKey: ""
    property string month: ""
    property string state: "idle" // idle, reading, ready, failed
    property string message: "HISTORY NOT SCANNED // MANUAL REVIEW REQUIRED"
    property var accounts: []
    property int recordsInspected: 0
    property string inflightSource: ""
    property string inflightMonth: ""
    property string captured: ""

    onSourceKeyChanged: invalidate()
    onMonthChanged: invalidate()

    function invalidate() {
        accounts = [];
        recordsInspected = 0;
        state = "idle";
        message = "HISTORY NOT SCANNED // MANUAL REVIEW REQUIRED";
        captured = "";
    }

    function scan() {
        if (worker.running || state === "reading"
                || !/^[a-f0-9]{64}$/.test(sourceKey)
                || !/^(?:19|20)\d{2}-(0[1-9]|1[0-2])$/.test(month))
            return false;
        inflightSource = sourceKey;
        inflightMonth = month;
        captured = "";
        accounts = [];
        recordsInspected = 0;
        state = "reading";
        message = "SCANNING ACCOUNT HISTORY // READ ONLY";
        worker.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/read_opening_history.mjs")],
            environment: ({
                FINANCEW_HISTORY_MONTH: month,
                ACTUAL_SERVER_URL: null,
                ACTUAL_SYNC_ID: null,
                ACTUAL_SYNC_ID_FILE: null,
                ACTUAL_PASSWORD_FILE: null
            })
        });
        return true;
    }

    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                const lines=String(text || "").split(/\r?\n/);
                for(let i=0;i<lines.length;i++)
                    if(lines[i].startsWith('{"schemaVersion":1,"kind":"financew-opening-history"'))
                        history.captured=lines[i];
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if (history.inflightSource !== history.sourceKey
                        || history.inflightMonth !== history.month) {
                    history.invalidate();
                    return;
                }
                try {
                    if(exitCode!==0 || !history.captured)
                        throw new Error("history-read-failed");
                    const value=JSON.parse(history.captured);
                    if(!value || value.schemaVersion!==1
                            || value.kind!=="financew-opening-history"
                            || value.readOnly!==true
                            || value.month!==history.month
                            || value.sourceKey!==history.sourceKey
                            || value.openingBalancesVerified!==false
                            || value.completeness!=="ledger-observation-only"
                            || !Array.isArray(value.accounts)
                            || value.accounts.length>30
                            || !Number.isSafeInteger(value.recordsInspected)
                            || !value.accounts.every(function(a) {
                                return a && typeof a.accountId==="string"
                                    && typeof a.accountName==="string"
                                    && (a.firstRecordedDate===null
                                        || /^\d{4}-\d{2}-\d{2}$/.test(a.firstRecordedDate))
                                    && (a.firstRecordedAmountCents===null
                                        || Number.isSafeInteger(a.firstRecordedAmountCents))
                                    && Number.isSafeInteger(a.transactionCount)
                                    && Number.isSafeInteger(a.startingBalanceCandidateCount)
                                    && (a.startingBalanceCandidateCents===null
                                        || Number.isSafeInteger(a.startingBalanceCandidateCents))
                                    && a.openingBalanceVerified===false;
                            }))
                        throw new Error("invalid-history-output");
                    history.accounts=value.accounts;
                    history.recordsInspected=value.recordsInspected;
                    history.state="ready";
                    history.message="HISTORY INSPECTED // STARTING BALANCES NOT VERIFIED";
                } catch(error) {
                    history.state="failed";
                    history.message="HISTORY SCAN UNAVAILABLE // CHECK ACTUAL";
                }
                history.captured="";
            });
        }
    }
}
