import QtQuick
import Quickshell
import Quickshell.Io

// Explicit, bounded model-only proposal. The Python client receives ONLY
// the operator's submitted brief via stdin, never project/Room files.
// This service cannot save records, start a Provider, or grant authority.
Scope {
    id: root
    property bool busy: false
    property bool completed: false
    property string lastError: ""
    property string pendingBrief: ""
    property string pendingKey: ""
    property string stdoutText: ""
    property bool stdoutDone: false
    property bool exitDone: false
    property int exitCode: -1
    property int sequence: 0
    property var proposal: ({})
    signal finished(var result)

    function reset() {
        sequence += 1;
        completed = false;
        lastError = "";
        proposal = ({});
        // Do not stop a request already in flight. Its result is ignored
        // unless it still matches the active request and operator brief.
        pendingKey = "";
    }

    function generate(brief) {
        const text = String(brief || "");
        root.reset();
        if (!text.trim() || text.length > 4000 || modelProcess.running
                || root.busy) {
            root.lastError = modelProcess.running || root.busy
                ? "AN AI REQUEST IS STILL RUNNING // TRY AGAIN AFTER IT FINISHES"
                : "ENTER A BRIEF OF AT MOST 4000 CHARACTERS";
            return false;
        }
        root.pendingBrief = text;
        root.pendingKey = "req" + Date.now().toString(36)
            + Math.floor(Math.random() * 0x7fffffff).toString(36);
        root.stdoutText = "";
        root.stdoutDone = false;
        root.exitDone = false;
        root.exitCode = -1;
        root.busy = true;
        // The API key is read only by the Python child from its existing
        // environment. It is never sent to QML or included in command args.
        modelProcess.exec(["python3",
            Quickshell.shellDir + "/services/hospital/hospital_ai_proposal_client.py"]);
        return true;
    }

    function maybeFinish() {
        if (!root.busy || !root.stdoutDone || !root.exitDone)
            return;
        root.busy = false;
        const activeKey = root.pendingKey;
        root.pendingKey = "";
        if (!activeKey)
            return;
        let data = {};
        try {
            if (root.stdoutText.length > 24000)
                throw new Error("oversized model reply");
            data = JSON.parse(root.stdoutText || "{}");
        } catch (error) {
            root.lastError = "MODEL RESPONSE INVALID // USE LOCAL STARTER DRAFT";
            root.finished({ready:false,error:root.lastError});
            return;
        }
        if (String(data.requestKey || "") !== activeKey || root.exitCode !== 0
                || data.ready !== true) {
            root.lastError = String(data.error ||
                "MODEL REFUSED OR UNAVAILABLE // USE LOCAL STARTER DRAFT").slice(0,180);
            root.finished({ready:false,error:root.lastError});
            return;
        }
        // The Python client has already validated the schema/READ boundary;
        // the parent validates identity and permissions again before display.
        if (data.permissions !== "READ"
                || ["INT", "NRS", "DOC"].indexOf(String(data.role)) < 0
                || !data.goal || !data.roomName || !data.workerName || !data.title
                || !data.constraints || !data.definitionDone || !data.checklist
                || data.writesHospital !== false || data.launchesProvider !== false) {
            root.lastError = "MODEL PROPOSAL CONTRACT REFUSED";
            root.finished({ready:false,error:root.lastError});
            return;
        }
        root.completed = true;
        root.proposal = data;
        root.finished(data);
    }

    Process {
        id: modelProcess
        stdinEnabled: true
        onStarted: {
            if (root.pendingKey) {
                modelProcess.write(JSON.stringify({
                    brief: root.pendingBrief,
                    requestKey: root.pendingKey
                }) + "\n");
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = String(this.text || "");
                root.stdoutDone = true;
                root.maybeFinish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                // Never display raw stderr: an HTTP stack or diagnostic
                // could contain unrelated environment or provider metadata.
            }
        }
        onExited: function(code, status) {
            root.exitCode = Number(code);
            root.exitDone = true;
            root.maybeFinish();
        }
    }
}
