import QtQuick
import Quickshell
import Quickshell.Io
import "ForestPreferencePolicy.js" as Preferences

// Local presentation preferences, not Forest Core session or model authority.
Scope {
    id: store
    property string status: "NOT_LOADED"
    readonly property bool busy: status === "LOADING" || status === "SAVING"
    property var committed: null
    property var submitted: null
    property string action: ""
    property string inputFrame: ""
    property string output: ""
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property bool refused: false
    signal loaded(var trees)

    function invoke(command) {
        if (busy || worker.running)
            return false;
        action = command.action;
        submitted = command;
        inputFrame = JSON.stringify(command) + "\n";
        output = "";
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        refused = false;
        status = action === "load" ? "LOADING" : "SAVING";
        worker.exec(["/usr/bin/python3", "-B",
            Quickshell.shellPath("scripts/forest/ui_model_preferences.py")]);
        return true;
    }
    function load() {
        return invoke({action:"load"});
    }
    function save(trees) {
        if (status !== "READY" || !committed)
            return false;
        const checked = Preferences.normalizeTrees(trees);
        if (!checked)
            return false;
        return invoke({action:"save",expectedRevision:committed.revision,trees:checked});
    }
    function finish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen)
            return;
        const doc = refused ? null : Preferences.parse(output);
        const saved = action === "save";
        // A save receipt must be about exactly the submitted preferences.
        const valid = doc && (!saved ||
            (Preferences.same(doc.trees, submitted.trees) &&
             doc.revision === submitted.expectedRevision + 1));
        if (!valid) {
            committed = null;
            status = "FAILED";
        } else {
            committed = doc;
            if (!saved)
                loaded(doc.trees);
            status = "READY";
        }
        submitted = null;
        inputFrame = "";
        output = "";
        action = "";
    }

    Process {
        id: worker
        running: false
        stdinEnabled: true
        onStarted: {
            if (store.busy && store.inputFrame) {
                worker.write(store.inputFrame);
                store.inputFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                if (!store.busy) return;
                if (store.stdoutSeen) store.refused = true;
                store.stdoutSeen = true;
                store.output = String(this.text || "");
                store.finish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (!store.busy) return;
                if (store.stderrSeen || String(this.text || "").trim().length)
                    store.refused = true;
                store.stderrSeen = true;
                store.finish();
            }
        }
        onExited: function(code, exitStatus) {
            if (!store.busy) return;
            if (store.exitSeen || code !== 0 || exitStatus !== 0)
                store.refused = true;
            store.exitSeen = true;
            store.finish();
        }
    }
}
