pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Owns Zellij pane-scroll configuration only. Does not control Kitty, Sway,
// the scrollbar widget, active Zellij processes or terminal input events.
Scope {
    id: settings
    property bool active: false
    property bool busy: false
    property bool inspecting: false
    property bool returned: false
    property bool confirmRequired: false
    property string hostStatus: "unchecked"
    property string hostError: ""
    property string feedback: "INSPECT ZELLIJ CONFIGURATION TO BEGIN"
    property string configPath: ""
    property string observedRevision: ""
    property string stagedMouse: "true"
    property string stagedResize: "true"
    property string stagedSync: "true"
    property int stagedBuffer: 10000
    property string installedMouse: ""
    property string installedResize: ""
    property string installedSync: ""
    property int installedBuffer: 0
    property bool stageEdited: false

    readonly property bool canPrepare:
        !busy && !confirmRequired
        && (hostStatus === "managed" || hostStatus === "available")
        && /^[a-f0-9]{64}$/.test(observedRevision)
        && (hostStatus !== "managed"
            || stagedMouse !== installedMouse
            || stagedResize !== installedResize
            || stagedSync !== installedSync
            || stagedBuffer !== installedBuffer)

    function open() {
        if (active)
            return true;
        active = true;
        refresh();
        return true;
    }
    function close() {
        if (busy)
            return false;
        active = false;
        confirmRequired = false;
        return true;
    }
    function refresh() {
        if (busy)
            return false;
        busy = true;
        inspecting = true;
        returned = false;
        confirmRequired = false;
        hostError = "";
        feedback = "READING ZELLIJ CONFIG // NO WRITES";
        worker.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/ZellijScrollConfig.py"),
            "status"
        ]);
        return true;
    }
    function stage(key, value) {
        if (busy)
            return false;
        if (key === "mouse" || key === "resize" || key === "sync") {
            if (value !== "true" && value !== "false")
                return false;
            if (key === "mouse")
                stagedMouse = value;
            else if (key === "resize")
                stagedResize = value;
            else
                stagedSync = value;
        } else if (key === "buffer") {
            if ([1000,5000,10000,20000,50000,100000].indexOf(value) < 0)
                return false;
            stagedBuffer = value;
        } else {
            return false;
        }
        confirmRequired = false;
        stageEdited = true;
        feedback = "STAGED ONLY // ZELLIJ CONFIG UNCHANGED";
        return true;
    }
    function prepare() {
        if (!canPrepare)
            return false;
        confirmRequired = true;
        feedback = hostStatus === "available"
            ? "CONFIRM FIRST MANAGED ZELLIJ BLOCK + ORIGINAL BACKUP"
            : "CONFIRM EDIT TO OWNED ZELLIJ SCROLL BLOCK";
        return true;
    }
    function cancel() {
        if (busy)
            return false;
        confirmRequired = false;
        feedback = "ZELLIJ CHANGE CANCELLED";
        return true;
    }
    function confirm() {
        if (!confirmRequired || busy || observedRevision.length !== 64)
            return false;
        confirmRequired = false;
        busy = true;
        inspecting = false;
        returned = false;
        hostError = "";
        feedback = "SAVING ONLY AUTHORIZED ZELLIJ SCROLL OPTIONS";
        worker.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/ZellijScrollConfig.py"),
            "apply", observedRevision, stagedMouse,
            stagedResize, stagedSync, String(stagedBuffer)
        ]);
        return true;
    }
    function acceptReply(raw) {
        returned = true;
        let reply;
        try { reply = JSON.parse(String(raw)); }
        catch (_) {
            hostStatus = "unavailable";
            hostError = "INVALID_HELPER_REPLY";
            return;
        }
        if (!reply || typeof reply.status !== "string") {
            hostStatus = "unavailable";
            hostError = "INVALID_HELPER_REPLY";
            return;
        }
        if (reply.status === "unavailable") {
            hostStatus = "unavailable";
            hostError = String(reply.code || "ZELLIJ_CONFIG_UNAVAILABLE");
            feedback = "REFUSED // " + hostError;
            return;
        }
        if (inspecting) {
            if (reply.status !== "managed" && reply.status !== "available") {
                hostStatus = "unavailable";
                hostError = "UNEXPECTED_STATUS";
                return;
            }
            hostStatus = reply.status;
            configPath = String(reply.config || "");
            observedRevision = String(reply.revision || "");
            if (reply.status === "managed") {
                installedMouse = String(reply.mouse || "");
                installedResize = String(reply.resize || "");
                installedSync = String(reply.sync || "");
                installedBuffer = Number(reply.buffer || 0);
                if (!stageEdited) {
                    stagedMouse = installedMouse;
                    stagedResize = installedResize;
                    stagedSync = installedSync;
                    stagedBuffer = installedBuffer;
                }
            } else {
                installedMouse = "";
                installedResize = "";
                installedSync = "";
                installedBuffer = 0;
            }
            feedback = reply.status === "managed"
                ? "MANAGED SETTINGS READ // NOT VERIFIED IN RUNNING ZELLIJ"
                : "NO EXISTING SCROLL OVERRIDES // ENROLLMENT AVAILABLE";
            return;
        }
        if (reply.status !== "saved" || !/^[a-f0-9]{64}$/.test(reply.revision || "")) {
            hostStatus = "unavailable";
            hostError = "UNVERIFIED_SAVE_REPLY";
            return;
        }
        observedRevision = reply.revision;
        hostStatus = "managed";
        installedMouse = stagedMouse;
        installedResize = stagedResize;
        installedSync = stagedSync;
        installedBuffer = stagedBuffer;
        stageEdited = false;
        feedback = "ZELLIJ CONFIG SAVED // LIVE SESSION NOT VERIFIED";
    }
    Process {
        id: worker
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.acceptReply(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.busy = false;
            if (code !== 0 || !settings.returned) {
                settings.hostStatus = "unavailable";
                settings.hostError = settings.hostError || "ZELLIJ_HELPER_FAILED";
                settings.feedback = "ZELLIJ CHANGE NOT VERIFIED // REFRESH";
            }
            settings.inspecting = false;
        }
    }
}
