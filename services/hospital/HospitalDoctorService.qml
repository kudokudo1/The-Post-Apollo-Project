import QtQuick
import Quickshell
import Quickshell.Io

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

    Process {
        id: listProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                // Empty stdout is NOT an empty roster: the native client
                // must explicitly emit [] or a validated metadata array.
                if (!body)
                    return;

                try {
                    const result = JSON.parse(body);
                    if (!Array.isArray(result) || result.length > 250)
                        throw new Error("INVALID PROTECTED DOCTOR DIRECTORY");

                    const identities = {};
                    const doctors = result.map(function(row) {
                        const normalized = root.normalizeDoctor(row);
                        if (!normalized.id
                                || Object.prototype.hasOwnProperty.call(
                                    identities, normalized.id))
                            throw new Error("INVALID PROTECTED DOCTOR ID");
                        identities[normalized.id] = true;
                        return normalized;
                    });

                    root.doctors = doctors;
                    root.listResponseAccepted = true;
                    root.lastError = "";
                } catch (error) {
                    root.doctors = [];
                    root.listResponseAccepted = false;
                    root.lastError = root.compactPxError(
                        error,
                        "HOSPITAL PROTECTED DOCTORS"
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = root.compactPxError(
                        detail,
                        "HOSPITAL DOCTOR"
                    );
            }
        }

        onExited: function(code, exitStatus) {
            root.refreshing = false;
            const accepted = Number(code) === 0
                && root.listResponseAccepted && !root.lastError;
            root.loaded = accepted;
            if (accepted) {
                root.lastRefreshedAt = new Date().toLocaleString();
            } else {
                root.doctors = [];
                root.lastRefreshedAt = "";
                root.listResponseAccepted = false;
                if (!root.lastError)
                    root.lastError =
                        "HOSPITAL BACKEND NOT READY // PROTECTED DOCTOR READER";
            }

            root.doctorsRefreshed();
        }
    }

    Component.onCompleted: refresh()
}
