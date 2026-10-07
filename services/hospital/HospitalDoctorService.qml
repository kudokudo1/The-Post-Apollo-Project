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
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-doctor-service"
        ].concat(suffix);
    }

    function compactPxError(value, context) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const lower = detail.toLowerCase();

        if (lower.indexOf("unknown command hospital") >= 0
                || lower.indexOf("unknown command agent") >= 0
                || lower.indexOf("post-apollo px control bus") >= 0)
            return "PX RUNTIME OUT OF DATE // UPDATE POST-APOLLO DEV EXPERIENCE";

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
                const body = String(this.text || "").trim();

                try {
                    const result = JSON.parse(body || "[]");

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
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL DOCTORS"
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
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL DOCTOR SAVE"
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
