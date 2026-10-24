import QtQuick
import Quickshell
import Quickshell.Io

// Explicit user actions ONLY. Commands use fixed argv; never shell-join paths.
// Successful UI operations still do not authorize a PX provider turn.
Scope {
    id: service

    property bool busy: false
    property string activeAction: ""
    property string lastError: ""
    property var registeredBeds: []
    property var staleBeds: []
    property string output: ""
    property string errorOutput: ""
    property int exitCode: -1
    property bool sawExit: false
    property bool sawOutput: false
    property bool sawError: false

    signal registryLoaded(var beds, var stale)
    signal bedRegistered(var bed)
    signal bedCreated(var bed)
    signal operationFailed(string action, string code)

    readonly property string helperPath:
        Quickshell.shellPath("scripts/hospital-bed-operations.py")

    function begin(action, args) {
        if (busy || opProcess.running)
            return false;
        const values = Array.isArray(args) ? args : [];
        activeAction = String(action);
        busy = true;
        lastError = "";
        output = "";
        errorOutput = "";
        exitCode = -1;
        sawExit = false;
        sawOutput = false;
        sawError = false;
        opProcess.exec(["python3", helperPath, action].concat(values));
        return true;
    }

    function loadKnown(repository) {
        const repo = String(repository || "").trim();
        return begin("list", repo ? ["--repository", repo] : []);
    }

    function registerExisting(path, repository, branch) {
        const directory = String(path || "").trim();
        const repo = String(repository || "").trim();
        const expected = String(branch || "").trim();
        if (!directory || !repo || !expected) {
            lastError = "BED REGISTER // PATH, PATIENT AND BRANCH REQUIRED";
            return false;
        }
        return begin("register", [
            "--path", directory, "--repository", repo, "--branch=" + expected
        ]);
    }

    function createNew(seedPath, repository, branch) {
        const seed = String(seedPath || "").trim();
        const repo = String(repository || "").trim();
        const expected = String(branch || "").trim();
        if (!seed || !repo || !expected) {
            lastError = "BED CREATE // MATCHING PATIENT SEED REQUIRED";
            return false;
        }
        return begin("create", [
            "--seed-path", seed, "--repository", repo, "--branch=" + expected
        ]);
    }

    function maybeFinish() {
        if (!busy || !sawExit || !sawOutput || !sawError)
            return;
        const action = activeAction;
        busy = false;
        activeAction = "";
        let result = null;
        try {
            result = JSON.parse(String(output || "").trim());
        } catch (error) {
            result = null;
        }
        if (exitCode !== 0 || !result || result.ok !== true) {
            lastError = String(result && result.code
                ? result.code
                : ("BED_OPERATION_EXIT_" + exitCode)).trim();
            operationFailed(action, lastError);
            return;
        }

        if (action === "list") {
            registeredBeds = Array.isArray(result.beds) ? result.beds : [];
            staleBeds = Array.isArray(result.stale) ? result.stale : [];
            registryLoaded(registeredBeds, staleBeds);
            return;
        }
        const bed = result.bed || null;
        if (!bed || !bed.path || !bed.repository || !bed.branch) {
            lastError = "BED_OPERATION_RESPONSE_INVALID";
            operationFailed(action, lastError);
            return;
        }
        const existing = registeredBeds.filter(function(row) {
            return String((row || {}).path || "") !== String(bed.path);
        });
        existing.push(bed);
        registeredBeds = existing;
        if (action === "register")
            bedRegistered(bed);
        if (action === "create")
            bedCreated(bed);
        registryLoaded(registeredBeds, staleBeds);
    }

    Process {
        id: opProcess

        stdout: StdioCollector {
            onStreamFinished: {
                service.output = String(this.text || "");
                service.sawOutput = true;
                service.maybeFinish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                service.errorOutput = String(this.text || "");
                service.sawError = true;
                service.maybeFinish();
            }
        }
        onExited: function(code, exitStatus) {
            service.exitCode = Number(code);
            service.sawExit = true;
            service.maybeFinish();
        }
    }
}
