pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Kitty owns its own wheel vs high-precision Wayland scrollback configuration.
// No Kitty, Sway, or Zellij command is executed when this singleton loads.
Scope {
    id: settings
    property bool terminalMode: false
    property bool busy: false
    property bool returned: false
    property bool examining: false
    property string hostStatus: "unchecked"
    property string hostError: ""
    property string feedback: "INSPECT KITTY CONFIGURATION TO BEGIN"
    property string configPath: ""
    property string fragmentPath: ""
    property real stagedWheel: 5.0
    property real stagedTouch: 1.0
    property real installedWheel: -1
    property real installedTouch: -1
    property bool stageEdited: false
    property string confirmAction: ""
    property string activeAction: ""

    readonly property bool canInstall:
        !busy && (hostStatus === "needs_include"
                   || hostStatus === "needs_fragment"
                   || hostStatus === "installed")
    readonly property bool hasChanges:
        installedWheel < 0 || installedTouch < 0
        || Math.abs(installedWheel - stagedWheel) > 0.001
        || Math.abs(installedTouch - stagedTouch) > 0.001

    function chooseMode(kitty) {
        if (busy)
            return false;
        const mode = kitty === true;
        if (terminalMode === mode)
            return true;
        terminalMode = mode;
        confirmAction = "";
        if (terminalMode)
            refresh();
        return true;
    }
    function refresh() {
        if (busy)
            return false;
        busy = true;
        examining = true;
        returned = false;
        confirmAction = "";
        hostError = "";
        feedback = "READING KITTY CONFIG WITHOUT WRITES";
        worker.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/KittyScrollConfig.py"),
            "status"
        ]);
        return true;
    }
    function stage(kind, amount) {
        if (busy || typeof amount !== "number" || !Number.isFinite(amount))
            return false;
        if (kind === "wheel" && (amount < 0.5 || amount > 16))
            return false;
        if (kind === "touch" && (amount < 0.25 || amount > 8))
            return false;
        if (kind === "wheel")
            stagedWheel = amount;
        else if (kind === "touch")
            stagedTouch = amount;
        else
            return false;
        stageEdited = true;
        confirmAction = "";
        feedback = "STAGED ONLY // NO KITTY CONFIG CHANGES";
        return true;
    }
    function prepare() {
        if (!canInstall || !hasChanges || confirmAction !== "")
            return false;
        confirmAction = hostStatus === "needs_include" ? "enroll" : "apply";
        feedback = confirmAction === "enroll"
            ? "CONFIRM ONE-TIME KITTY CONFIG INCLUDE AND SCROLL SETTINGS"
            : "CONFIRM MANAGED KITTY SCROLL CONFIG UPDATE";
        return true;
    }
    function cancel() {
        if (busy)
            return false;
        confirmAction = "";
        feedback = "KITTY CHANGE CANCELLED";
        return true;
    }
    function confirm() {
        if (busy || confirmAction !== "enroll" && confirmAction !== "apply")
            return false;
        if (!canInstall || !hasChanges)
            return false;
        activeAction = confirmAction;
        confirmAction = "";
        busy = true;
        examining = false;
        returned = false;
        hostError = "";
        feedback = "WRITING ONLY THE APPROVED KITTY SETTINGS";
        worker.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/input/KittyScrollConfig.py"),
            activeAction, stagedWheel.toFixed(2), stagedTouch.toFixed(2)
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
            hostError = String(reply.code || "KITTY_CONFIG_UNAVAILABLE");
            feedback = "KITTY CONFIG UNCHANGED // " + hostError;
            return;
        }
        if (examining) {
            if (["installed", "needs_include", "needs_fragment",
                 "needs_config"].indexOf(reply.status) < 0) {
                hostStatus = "unavailable";
                hostError = "UNEXPECTED_STATUS";
                return;
            }
            hostStatus = reply.status;
            configPath = String(reply.config || "");
            fragmentPath = String(reply.fragment || "");
            if (reply.status === "installed"
                    && Number.isFinite(reply.wheel)
                    && Number.isFinite(reply.touch)) {
                installedWheel = Number(reply.wheel);
                installedTouch = Number(reply.touch);
                if (!stageEdited) {
                    stagedWheel = installedWheel;
                    stagedTouch = installedTouch;
                }
            } else {
                installedWheel = -1;
                installedTouch = -1;
            }
            feedback = reply.status === "installed"
                ? "KITTY MANAGED SETTINGS FOUND // NOT RUNTIME VERIFIED"
                : reply.status === "needs_include"
                  ? "KITTY INCLUDE MISSING // ENROLL REQUIRES CONFIRMATION"
                  : reply.status === "needs_fragment"
                    ? "INCLUDE FOUND // CHOOSE AND CONFIRM FACTORS"
                    : "KITTY.CONF MISSING // CREATE IT IN KITTY FIRST";
            return;
        }
        if (reply.status !== "saved" && reply.status !== "enrolled"
                && reply.status !== "already_enrolled") {
            hostStatus = "unavailable";
            hostError = "UNEXPECTED_WRITE_REPLY";
            return;
        }
        hostStatus = "installed";
        installedWheel = stagedWheel;
        installedTouch = stagedTouch;
        stageEdited = false;
        feedback = "KITTY CONFIG SAVED // RELOAD OR AUTO-RELOAD TO TEST";
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
                settings.hostError = settings.hostError || "KITTY_HELPER_FAILED";
                settings.feedback = "NO VERIFIED CHANGE // INSPECT BEFORE RETRY";
            }
            settings.activeAction = "";
            settings.examining = false;
        }
    }
}
