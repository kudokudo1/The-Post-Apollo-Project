import QtQuick
import Quickshell
import Quickshell.Io

// Read only the GitHub login through the same 'gh' account used by GitW's
// GitHubAccountProfileService. Do not fetch email/profile PII or change auth.
// This is a suggestion, never proof of repository ownership or write access.
Scope {
    id: root
    property bool reading: false
    property bool loaded: false
    property string login: ""
    property string lastError: ""
    property string outputText: ""
    property string errorText: ""
    property bool stdoutDone: false
    property bool stderrDone: false
    property bool exitDone: false
    property int exitCode: -1
    signal refreshed()

    function refresh() {
        if (reading || readProcess.running)
            return false;
        reading = true;
        loaded = false;
        lastError = "";
        login = "";
        outputText = "";
        errorText = "";
        stdoutDone = false;
        stderrDone = false;
        exitDone = false;
        exitCode = -1;
        readProcess.exec(["bash", "-lc", "gh api user --jq .login"]);
        return true;
    }
    function maybeFinish() {
        if (!reading || !stdoutDone || !stderrDone || !exitDone)
            return;
        reading = false;
        const candidate = String(outputText || "").trim();
        if (exitCode === 0 && /^[A-Za-z0-9_.-]+$/.test(candidate)) {
            login = candidate;
            loaded = true;
        } else {
            lastError = "SIGNED-IN GITHUB LOGIN UNAVAILABLE // USE CURRENT PATIENT OR ENTER AN OWNER";
        }
        refreshed();
    }

    Process {
        id: readProcess
        stdout: StdioCollector {
            onStreamFinished: {
                root.outputText = String(this.text || "");
                root.stdoutDone = true;
                root.maybeFinish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                root.errorText = String(this.text || "");
                root.stderrDone = true;
                root.maybeFinish();
            }
        }
        onExited: function(code, status) {
            root.exitCode = Number(code);
            root.exitDone = true;
            root.maybeFinish();
        }
    }
}
