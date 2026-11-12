import QtQuick
import Quickshell
import Quickshell.Io

// New, unstaffed Room record only. Never starts a worker, creates a Bed,
// changes a branch, activates an Assignment or issues an AI turn.
// The random Room ID is minted by Surgery, never supplied as an existing ID.
Scope {
    id: root
    property bool creating: false
    property string lastError: ""
    property string lastStatus: ""
    property var pending: ({})
    property var savedRoom: null
    // v10 PX supports room-bind but not independent display names. Determine
    // compatibility *before* writing, without touching the Hospital DB.
    property string nameSupport: "CHECKING"
    property string lastRegisteredId: ""
    property string lastRequestedName: ""
    property bool lastNameSaved: false
    signal created(var room)
    signal idCollision(string roomId)

    function probeNameSupport() {
        if (creating || capabilityProcess.running)
            return false;
        nameSupport = "CHECKING";
        capabilityProcess.exec(pxArgs(["hospital", "room-name-set", "--help"]));
        return true;
    }
    Component.onCompleted: probeNameSupport()

    function pxArgs(args) {
        return [
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-workforce-room-create"
        ].concat(args);
    }

    function create(candidate) {
        const v = candidate || {};
        const id = String(v.id || "").trim();
        const repository = String(v.repository || "").trim();
        const name = String(v.name || "").trim();
        const patientId = String(v.patientId || "").trim();
        const patientLabel = String(v.patientLabel || "").trim();
        if (creating || bindProcess.running || nameProcess.running
                || lookupProcess.running)
            return false;
        if (nameSupport === "CHECKING") {
            lastError = "PX CAPABILITY CHECK RUNNING // ROOM NOT WRITTEN";
            return false;
        }
        if (!/^room-[a-z0-9-]{8,90}$/.test(id)
                || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)
                || !name || name.length > 96 || !patientId
                || !patientLabel || patientLabel.length > 96
                || /[\x00-\x1f\x7f]/.test(name + patientLabel)) {
            lastError = "ROOM CREATE REFUSED // INVALID NEW ROOM ID, NAME OR REPOSITORY";
            return false;
        }
        pending = {id: id, repository: repository, name: name,
            patientId: patientId, patientLabel: patientLabel};
        savedRoom = null;
        lastError = "";
        lastStatus = "CHECKING NEW ROOM ID // READ ONLY // NO WORKER";
        creating = true;
        // room-bind is an UPSERT in PX v10/v11. Never call it without first
        // checking the authoritative store for the exact generated ID.
        lookupProcess.exec(pxArgs(["hospital", "room", id, "--json"]));
        return true;
    }

    Process {
        id: capabilityProcess
        stdout: StdioCollector {}
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            root.nameSupport = Number(code) === 0
                ? "SUPPORTED" : "UNSUPPORTED";
        }
    }

    Process {
        id: lookupProcess
        property string resultText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: lookupProcess.resultText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: lookupProcess.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const id = String(root.pending.id || "");
            const error = String(lookupProcess.errorText || "");
            const exists = Number(code) === 0;
            const absent = Number(code) !== 0
                && error.indexOf("unknown Hospital room: " + id) >= 0;
            lookupProcess.resultText = "";
            lookupProcess.errorText = "";
            if (!root.creating || !id)
                return;
            if (exists || !absent) {
                root.lastError = exists
                    ? "ROOM ID COLLISION // EXISTING ROOM PRESERVED"
                    : "ROOM REGISTRY UNAVAILABLE // NO WRITE PERFORMED";
                root.lastStatus = exists
                    ? "FRESH ROOM ID REQUIRED // REVIEW AGAIN"
                    : "ROOM CREATE HELD // CHECK PX REGISTRY";
                root.creating = false;
                root.pending = ({});
                if (exists)
                    root.idCollision(id);
                return;
            }
            root.lastStatus = "CREATING UNSTAFFED ROOM // NO AGENT WILL LAUNCH";
            bindProcess.exec(root.pxArgs([
                "hospital", "room-bind", id,
                "--repository", root.pending.repository,
                "--patient-id", root.pending.patientId,
                "--patient-label", root.pending.patientLabel,
                "--json"
            ]));
        }
    }

    Process {
        id: bindProcess
        property string resultText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: bindProcess.resultText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: bindProcess.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            let result = null;
            try {
                if (Number(code) !== 0)
                    throw new Error(bindProcess.errorText || "PX EXIT " + code);
                result = JSON.parse(bindProcess.resultText);
                if (String(result.id || "") !== root.pending.id
                        || String(result.repository || "") !== root.pending.repository
                        || String(result.patientId || "") !== root.pending.patientId
                        || String(result.doctorId || "")
                        || String(result.providerId || "")
                        || String(result.assignmentId || "")
                        || String(result.branch || "")
                        || String(result.bedPath || ""))
                    throw new Error("PX ROOM IDENTITY OR UNSTAFFED CONTRACT MISMATCH");
            } catch (error) {
                root.lastError = "ROOM CREATE // " + String(error).slice(0,220);
                root.lastStatus = "ROOM CREATION NOT VERIFIED // REFRESH BEFORE RETRY";
                root.creating = false;
                root.pending = ({});
                bindProcess.resultText = "";
                bindProcess.errorText = "";
                return;
            }
            bindProcess.resultText = "";
            bindProcess.errorText = "";
            root.savedRoom = result;
            root.lastRegisteredId = root.pending.id;
            root.lastRequestedName = root.pending.name;
            if (root.nameSupport !== "SUPPORTED") {
                // The Room exists in PX v10, but v10 has no independent
                // display-name column. Never falsely claim the label saved
                // or reinterpret the Room name as its Team.
                root.creating = false;
                root.lastNameSaved = false;
                root.lastError = "";
                root.lastStatus = "ROOM REGISTERED BY ID // DISPLAY NAME PENDING PX V11";
                root.created(root.savedRoom);
                root.pending = ({});
                return;
            }
            root.lastStatus = "ROOM REGISTERED // APPLYING DISPLAY NAME";
            nameProcess.exec(root.pxArgs([
                "hospital", "room-name-set", root.pending.id,
                "--name", root.pending.name, "--json"
            ]));
        }
    }

    Process {
        id: nameProcess
        property string resultText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: nameProcess.resultText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: nameProcess.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const id = root.pending.id;
            let nameSaved = false;
            try {
                if (Number(code) === 0) {
                    const result = JSON.parse(nameProcess.resultText);
                    nameSaved = String(result.id || "") === id;
                }
            } catch (error) {
                nameSaved = false;
            }
            root.creating = false;
            root.lastNameSaved = nameSaved;
            root.lastStatus = nameSaved
                ? "ROOM REGISTERED + NAMED // NO SESSION OR WORKTREE"
                : "ROOM REGISTERED BY ID // DISPLAY NAME NOT SAVED";
            // This command may be unsupported on a mismatched PX runtime
            // after a successful bind. Never call it an ID collision.
            root.lastError = nameSaved ? ""
                : "PX NAME SAVE UNSUPPORTED OR FAILED // ROOM ID IS REGISTERED";
            nameProcess.resultText = "";
            nameProcess.errorText = "";
            root.created(root.savedRoom);
            root.pending = ({});
        }
    }
}
