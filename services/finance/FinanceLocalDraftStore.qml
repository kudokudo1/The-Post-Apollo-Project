import QtQuick
import Quickshell
import Quickshell.Io

// Private local text drafts only. There is no Actual import, account mutation,
// or dependency on the real-budget write authorization file.
Scope {
    id: store
    property string sourceKey: ""
    property string month: ""
    property var drafts: []
    property int revision: 0
    property string state: "idle" // idle, pending, ready, failed
    property string message: "Saved drafts are stored locally."
    property string inputFrame: ""
    property string collected: ""
    property string activeAction: ""
    property string submittedSource: ""
    property string submittedMonth: ""
    property bool pendingReload: false
    signal draftSaved()
    signal draftDeleted()

    onSourceKeyChanged: refresh()
    onMonthChanged: refresh()

    function validContext() {
        return /^[a-f0-9]{64}$/.test(sourceKey)
            && /^\d{4}-(0[1-9]|1[0-2])$/.test(month);
    }

    function refresh() {
        // No drafts from an old budget may remain visible during source swaps.
        drafts = [];
        revision = 0;
        if (!validContext()) {
            state = "idle";
            return false;
        }
        if (worker.running || state === "pending") {
            pendingReload = true;
            return false;
        }
        return invoke({action:"list",sourceKey:sourceKey,month:month});
    }

    function invoke(command) {
        if (worker.running || state === "pending" || !validContext())
            return false;
        submittedSource = sourceKey;
        submittedMonth = month;
        activeAction = command.action;
        collected = "";
        inputFrame = JSON.stringify(command) + "\n";
        state = "pending";
        message = "Reading local drafts.";
        worker.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/local_drafts.mjs")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }

    function upsert(command) {
        if (state !== "ready" || !validContext() || !command
                || command.sourceKey !== sourceKey || command.month !== month)
            return false;
        return invoke({action:"upsert",sourceKey:sourceKey,month:month,
            id:command.id || null,expectedRevision:revision,draft:command});
    }

    function remove(id) {
        if (state !== "ready" || !validContext() || !id)
            return false;
        return invoke({action:"delete",sourceKey:sourceKey,month:month,
            id:id,expectedRevision:revision});
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (store.inputFrame) {
                worker.write(store.inputFrame);
                store.inputFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                // This result includes private draft descriptions and MUST
                // remain in process memory; never print its contents.
                const lines = String(text || "").split(/\r?\n/);
                for (let i=0;i<lines.length;i++) {
                    if (lines[i].startsWith("FINANCEW_DRAFT_RESULT "))
                        store.collected = lines[i].slice(22);
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                const sameContext = store.submittedSource === store.sourceKey
                    && store.submittedMonth === store.month;
                let accepted = false;
                if (exitCode === 0 && store.collected && sameContext) {
                    try {
                        const payload = JSON.parse(store.collected);
                        if (Number.isSafeInteger(payload.revision)
                                && Array.isArray(payload.drafts)
                                && payload.drafts.length <= 50
                                && payload.drafts.every(function(x) {
                                    return x && x.sourceKey === store.sourceKey
                                        && x.month === store.month
                                        && typeof x.id === "string";
                                })) {
                            store.revision = payload.revision;
                            store.drafts = payload.drafts;
                            store.state = "ready";
                            store.message = "LOCAL DRAFTS // SAVED PRIVATELY";
                            accepted = true;
                            if (store.activeAction === "upsert")
                                store.draftSaved();
                            if (store.activeAction === "delete")
                                store.draftDeleted();
                        }
                    } catch (error) { /* fixed error; no draft details */ }
                }
                if (!accepted && sameContext) {
                    store.state = "failed";
                    store.message = "LOCAL DRAFT STORE ERROR // NO CHANGE CONFIRMED";
                }
                store.activeAction = "";
                store.collected = "";
                if (store.pendingReload || !sameContext) {
                    store.pendingReload = false;
                    store.refresh();
                }
            });
        }
    }
}
