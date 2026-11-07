import QtQuick
import Quickshell
import Quickshell.Io

// Operator-facing Doctor labels only. Never edits Doctor ID, Patient, Team,
// Git branch, Doctor, Provider, Assignment, or live provider session.
Scope {
    id: root

    property bool saving: false
    property string lastError: ""
    property string lastStatus: ""
    property string pendingDoctorId: ""
    property var lastSavedDoctor: null

    signal nameSaved(var doctor)

    function clearStatus() {
        if (!saving) {
            lastError = "";
            lastStatus = "";
        }
    }

    function saveName(doctorIdValue, displayNameValue) {
        const id = String(doctorIdValue || "").trim();
        const name = String(displayNameValue || "").trim();
        if (!id || saving || saveProcess.running)
            return false;
        if (name.length > 96 || /[\x00-\x1f\x7f]/.test(name)) {
            lastError = "DOCTOR NAME // INVALID CHARACTERS OR LENGTH";
            return false;
        }

        pendingDoctorId = id;
        saving = true;
        lastError = "";
        lastStatus = "DOCTOR NAME // SAVING";
        lastSavedDoctor = null;
        saveProcess.exec([
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-doctor-name",
            "hospital", "doctor-name-set", id,
            "--name", name, "--json"
        ]);
        return true;
    }

    Process {
        id: saveProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;
                try {
                    const result = JSON.parse(body);
                    if (String(result.id || "") !== root.pendingDoctorId)
                        throw new Error("DOCTOR NAME // IDENTITY MISMATCH");
                    root.lastSavedDoctor = result;
                } catch (error) {
                    root.lastError = "DOCTOR NAME // INVALID PX REPLY // "
                        + String(error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail) {
                    const rows = detail.split("\n").filter(function(row) {
                        return !!String(row || "").trim();
                    });
                    root.lastError = "DOCTOR NAME // PX ERROR // "
                        + (rows.length ? rows[rows.length - 1] : detail).slice(0, 220);
                }
            }
        }

        onExited: function(code, exitStatus) {
            root.saving = false;
            if (Number(code) === 0 && !root.lastError && root.lastSavedDoctor) {
                root.lastStatus = "DOCTOR NAME // SAVED";
                root.nameSaved(root.lastSavedDoctor);
                return;
            }
            if (!root.lastError)
                root.lastError = "DOCTOR NAME // PX EXIT " + String(code)
                    + " // CHECK PX V11";
            root.lastStatus = "DOCTOR NAME // STOPPED";
        }
    }
}
