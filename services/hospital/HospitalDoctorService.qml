import QtQuick
import Quickshell
import Quickshell.Io
import "HospitalDoctorDirectoryExitPolicy.js" as DoctorReadPolicy

Scope {
    id: root

    property var doctors: []
    property bool loaded: false
    property bool refreshing: false
    property bool saving: false
    property string lastError: ""
    property string lastRefreshedAt: ""
    property var lastSavedDoctor: null
    property bool listResponseAccepted: false

    // Source-only H1 cutover candidate. This executable must itself prove
    // installed root-owned identity, policy, protected socket and writer peer.
    // Never fall back to desktop PX if the protected reader is unavailable.
    readonly property string nativeReaderPath:
        "/usr/libexec/post-apollo/hospital/hospital-room-read"
    readonly property bool protectedDoctorWritesReady: false

    signal doctorsRefreshed()
    signal doctorSaved(var doctor)

    function compactPxError(value, context) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const rows = detail.split("\n").map(function(row) {
            return String(row || "").trim();
        }).filter(function(row) {
            return row.length > 0;
        });

        let message =
            rows.length > 0
            ? rows[rows.length - 1]
            : detail;

        if (message.length > 240)
            message = message.slice(0, 237) + "...";

        const prefix = String(context || "").trim();
        return prefix ? prefix + " // " + message : message;
    }

    function normalizeDoctor(record) {
        const row = record || {};

        return {
            id: String(row.id || "").trim(),
            name: String(row.name || row.id || "DOCTOR").trim(),
            role: String(row.role || "DOCTOR").trim(),
            status: String(row.status || "ACTIVE").toUpperCase(),
            createdAt: String(row.createdAt || "").trim(),
            updatedAt: String(row.updatedAt || "").trim()
        };
    }

    function doctorById(value) {
        const id = String(value || "").trim();

        for (let i = 0; i < doctors.length; ++i) {
            const row = doctors[i] || {};
            if (String(row.id || "") === id)
                return row;
        }

        return null;
    }

    function refresh() {
        if (refreshing || listProcess.running)
            return false;

        refreshing = true;
        loaded = false;
        listResponseAccepted = false;
        doctors = [];
        listProcess.pendingRead = DoctorReadPolicy.begin();
        lastRefreshedAt = "";
        lastError = "";

        // Installed native reader validates executable/source identity,
        // root-owned policy, protected writer identity and exact metadata.
        // No desktop SQLite or alternate PX command may be used here.
        listProcess.exec([nativeReaderPath, "doctor-directory"]);
        return true;
    }

    function saveDoctor(idValue, nameValue, roleValue, statusValue) {
        // Do not reuse legacy desktop Doctor mutations after native read
        // cutover. A separately authorized protected write contract must
        // be implemented and accepted before Doctor changes can be saved.
        saving = false;
        lastSavedDoctor = null;
        lastError = "HOSPITAL DOCTOR WRITE // PROTECTED ROUTE NOT ENABLED";
        return false;
    }

    function releaseDoctor(idValue) {
        const doctor = doctorById(idValue) || {};
        return saveDoctor(
            idValue,
            doctor.name || idValue,
            doctor.role || "DOCTOR",
            "RELEASED"
        );
    }

    // Only this callback publishes the directory. The policy refuses to
    // complete before stdout, stderr, AND exit are all observed; it also
    // refuses all malformed/nonzero/crashed outcomes. Until then only the
    // internal Process.pendingRead may hold staged metadata.
    function advanceDoctorRead(next) {
        if (!refreshing || !listProcess.pendingRead || !next)
            return;
        listProcess.pendingRead = next;
        if (!next.complete)
            return;

        // Once all three callbacks have arrived, no output from this
        // process instance may be promoted by a late/duplicate callback.
        listProcess.pendingRead = null;
        refreshing = false;
        if (next.accepted) {
            listResponseAccepted = true;
            loaded = true;
            lastError = "";
            lastRefreshedAt = new Date().toLocaleString();
            doctors = next.records;
        } else {
            listResponseAccepted = false;
            loaded = false;
            doctors = [];
            lastRefreshedAt = "";
            lastError = next.error ||
                "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER";
        }
        doctorsRefreshed();
    }

    Process {
        id: listProcess
        property var pendingRead: null

        stdout: StdioCollector {
            onStreamFinished: {
                if (!root.refreshing || !listProcess.pendingRead)
                    return;
                root.advanceDoctorRead(DoctorReadPolicy.captureStdout(
                    listProcess.pendingRead, this.text
                ));
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                if (!root.refreshing || !listProcess.pendingRead)
                    return;
                root.advanceDoctorRead(DoctorReadPolicy.captureStderr(
                    listProcess.pendingRead, this.text
                ));
            }
        }

        onExited: function(code, exitStatus) {
            if (!root.refreshing || !listProcess.pendingRead)
                return;
            root.advanceDoctorRead(DoctorReadPolicy.captureExit(
                listProcess.pendingRead, code, exitStatus
            ));
        }
    }

    Component.onCompleted: refresh()
}
