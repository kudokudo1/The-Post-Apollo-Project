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

    signal doctorsRefreshed()
    signal doctorSaved(var doctor)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];
        return [
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" "$@"',
            "hospital-doctor-service"
        ].concat(suffix);
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
        lastError = "";

        listProcess.exec(pxArgs([
            "hospital",
            "doctors",
            "--json"
        ]));
        return true;
    }

    function saveDoctor(idValue, nameValue, roleValue, statusValue) {
        const id = String(idValue || "").trim();
        const name = String(nameValue || id || "DOCTOR").trim();
        const role = String(roleValue || "DOCTOR").trim();
        const status = String(statusValue || "ACTIVE").toUpperCase();

        if (!id || saving || saveProcess.running)
            return false;

        if (["ACTIVE", "INACTIVE", "RELEASED"].indexOf(status) < 0) {
            lastError = "HOSPITAL DOCTOR // INVALID STATUS";
            return false;
        }

        saving = true;
        lastError = "";
        lastSavedDoctor = null;

        saveProcess.exec(pxArgs([
            "hospital",
            "doctor-put",
            id,
            "--name",
            name,
            "--role",
            role,
            "--status",
            status,
            "--json"
        ]));
        return true;
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
                try {
                    const result = JSON.parse(String(this.text || "[]"));

                    if (!Array.isArray(result))
                        throw new Error("PX Hospital doctors returned non-array data");

                    root.doctors = result.map(function(row) {
                        return root.normalizeDoctor(row);
                    }).filter(function(row) {
                        return !!row.id;
                    });
                    root.lastError = "";
                } catch (error) {
                    root.doctors = [];
                    root.lastError =
                        "HOSPITAL DOCTORS // " + String(error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            root.refreshing = false;
            root.loaded = true;
            root.lastRefreshedAt = new Date().toLocaleString();

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX HOSPITAL DOCTORS EXIT " + String(code);

            root.doctorsRefreshed();
        }
    }

    Process {
        id: saveProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    root.lastSavedDoctor =
                        root.normalizeDoctor(JSON.parse(body));
                } catch (error) {
                    root.lastError =
                        "HOSPITAL DOCTOR SAVE // " + String(error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = detail;
            }
        }

        onExited: function(code, exitStatus) {
            root.saving = false;

            if (Number(code) === 0
                    && !root.lastError
                    && root.lastSavedDoctor) {
                root.doctorSaved(root.lastSavedDoctor);
                root.refresh();
                return;
            }

            if (!root.lastError)
                root.lastError =
                    "PX HOSPITAL DOCTOR SAVE EXIT " + String(code);
        }
    }

    Component.onCompleted: refresh()
}
