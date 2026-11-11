pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "UniversalAutoscrollPolicy.js" as Auto

// CPU++ middle-button owner. One mode per physical pointer.
// Windows-style autoscroll is engine-only until a consented, compositor-level
// global pointer capture and virtual axis path passes independent verification.
Scope {
    id: settings

    property bool modePage: false
    property string stagedMode: "off" // off, lock, auto
    property string hostStatus: "unchecked"
    property string hostError: ""
    property string feedback: "INSPECT SWAY BEFORE SELECTING SCROLL MODE"
    property var devices: []
    property string selectedId: ""
    property string activeId: ""
    property bool hasSnapshot: false
    property bool busy: false
    property bool inspectRunning: false
    property bool returned: false
    property string pendingAction: ""
    property string executing: ""
    property var expected: null
    property var autoscrollEngine: Auto.initial()
    readonly property bool autoscrollRuntimeAvailable: false
    readonly property bool canPrepare:
        !busy && pendingAction === "" && hostStatus === "ready"
        && (stagedMode === "lock" && chosenDevice !== null
            && activeId === ""
            || stagedMode === "off" && activeId !== ""
            && hasSnapshot)
    readonly property var chosenDevice: findDevice(selectedId)

    function findDevice(identifier) {
        for (let i=0;i<devices.length;i++)
            if (devices[i].identifier === identifier) return devices[i];
        return null;
    }
    function openModePage() {
        if (busy) return false;
        modePage = true;
        inspect();
        return true;
    }
    function closeModePage() {
        if (busy) return false;
        modePage = false;
        pendingAction = "";
        return true;
    }
    function chooseDevice(id) {
        if (busy || !findDevice(id)) return false;
        selectedId = id;
        pendingAction = "";
        feedback = "DEVICE STAGED // " + id;
        return true;
    }
    function chooseMode(value) {
        if (busy || ["off","lock","auto"].indexOf(value) < 0)
            return false;
        stagedMode = value;
        pendingAction = "";
        feedback = value === "auto"
            ? "AUTOSCROLL ENGINE READY // GLOBAL POINTER CAPTURE NOT VERIFIED"
            : value === "lock"
              ? "NATIVE SCROLL LOCK STAGED // PREPARE TO CONFIRM"
              : "NORMAL MIDDLE-CLICK STAGED // RESTORES PREVIOUS SWAY MODE";
        return true;
    }
    function inspect() {
        if (busy) return false;
        busy = true;
        inspectRunning = true;
        returned = false;
        hostError = "";
        pendingAction = "";
        feedback = "READING SWAY POINTER CONFIGURATION";
        worker.exec(["python3", "-B", "-I",
                    Quickshell.shellPath("services/input/SwayScrollLock.py"),
                    "inspect"]);
        return true;
    }
    function prepare() {
        if (!canPrepare) return false;
        pendingAction = stagedMode === "lock" ? "enable" : "restore";
        expected = chosenDevice === null ? null : ({
            identifier: chosenDevice.identifier,
            scroll_method: chosenDevice.scroll_method,
            scroll_button_lock: chosenDevice.scroll_button_lock,
            scroll_button: chosenDevice.scroll_button
        });
        feedback = pendingAction === "enable"
            ? "CONFIRM NATIVE MIDDLE-CLICK LOCK // ORIGINAL SAVED FOR RECOVERY"
            : "CONFIRM RESTORE OF PREVIOUS INPUT CONFIGURATION";
        return true;
    }
    function cancel() {
        if (busy) return false;
        pendingAction = "";
        feedback = "MODE CHANGE CANCELLED";
        return true;
    }
    function confirm() {
        if (busy || pendingAction !== "enable"
                && pendingAction !== "restore") return false;
        if (pendingAction === "enable"
                && (!expected || !findDevice(expected.identifier)
                    || selectedId !== expected.identifier))
            return false;
        executing = pendingAction;
        pendingAction = "";
        busy = true;
        inspectRunning = false;
        returned = false;
        hostError = "";
        let args = ["python3", "-B", "-I",
                    Quickshell.shellPath("services/input/SwayScrollLock.py")];
        if (executing === "enable") {
            args.push("enable", expected.identifier, expected.scroll_method,
                      expected.scroll_button_lock,
                      String(expected.scroll_button));
        } else {
            args.push("restore");
        }
        feedback = "APPLYING AND VERIFYING PER-DEVICE SWAY INPUT MODE";
        worker.exec(args);
        return true;
    }
    function accept(raw) {
        returned = true;
        let reply;
        try { reply = JSON.parse(String(raw)); }
        catch (_) {
            hostStatus = "unavailable";
            hostError = "INVALID_REPLY";
            return;
        }
        if (!reply || reply.status === "unavailable") {
            hostStatus = "unavailable";
            hostError = String(reply && reply.code || "SWAY_UNAVAILABLE");
            feedback = "MODE NOT VERIFIED // " + hostError;
            return;
        }
        if (inspectRunning) {
            if (reply.status !== "ok" || !Array.isArray(reply.devices)) {
                hostStatus = "unavailable";
                hostError = "INVALID_DEVICE_LIST";
                return;
            }
            const valid = reply.devices.filter(x => x
                && typeof x.identifier === "string"
                && ["none","two_finger","edge","on_button_down"]
                    .indexOf(x.scroll_method) >= 0
                && ["enabled","disabled"].indexOf(x.scroll_button_lock) >= 0
                && Number.isInteger(x.scroll_button));
            devices = valid;
            hasSnapshot = reply.snapshot === true;
            activeId = String(reply.active_identifier || "");
            if (!findDevice(selectedId))
                selectedId = valid.length ? valid[0].identifier : "";
            hostStatus = "ready";
            feedback = activeId
                ? "SCROLL LOCK SNAPSHOT PRESENT // USE OFF TO RESTORE"
                : "SWAY READABLE // SELECT DEVICE AND MODE";
            return;
        }
        if (executing === "enable" && reply.status === "enabled") {
            activeId = String(reply.identifier || "");
            hasSnapshot = true;
            hostStatus = "ready";
            feedback = "SWAY SCROLL LOCK VERIFIED // CLICK TWICE TO EXIT";
        } else if (executing === "restore" && reply.status === "restored") {
            activeId = "";
            hasSnapshot = false;
            hostStatus = "ready";
            stagedMode = "off";
            feedback = "ORIGINAL SWAY POINTER SETTINGS RESTORED";
        } else {
            hostStatus = "unavailable";
            hostError = "UNEXPECTED_RESULT";
        }
    }
    Process {
        id: worker
        running: false
        stdout: StdioCollector {
            onStreamFinished: settings.accept(this.text)
        }
        onExited: function(code, exitStatus) {
            settings.busy = false;
            if (code !== 0 || !settings.returned) {
                settings.hostStatus = "unavailable";
                settings.hostError = settings.hostError || "SWAY_MODE_COMMAND_FAILED";
                settings.feedback = "MODE NOT VERIFIED // INSPECT BEFORE RETRY";
            }
            settings.inspectRunning = false;
            settings.executing = "";
        }
    }
}
