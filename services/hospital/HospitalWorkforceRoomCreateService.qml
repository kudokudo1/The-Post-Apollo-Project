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
    signal created(var room)

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
        if (creating || bindProcess.running || nameProcess.running)
            return false;
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
        lastStatus = "CREATING UNSTAFFED ROOM // NO AGENT WILL LAUNCH";
        creating = true;
        bindProcess.exec(pxArgs([
            "hospital", "room-bind", id,
            "--repository", repository,
            "--patient-id", patientId,
            "--patient-label", patientLabel,
            "--json"
        ]));
        return true;
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
            root.lastStatus = nameSaved
                ? "ROOM CREATED // UNSTAFFED // NO SESSION OR WORKTREE"
                : "ROOM CREATED // NAME SAVE FAILED // USE EDIT NAME";
            root.lastError = nameSaved ? ""
                : "ROOM " + id + " EXISTS // " + String(nameProcess.errorText || "name not verified").slice(0,170);
            nameProcess.resultText = "";
            nameProcess.errorText = "";
            root.created(root.savedRoom);
            root.pending = ({});
        }
    }
}
