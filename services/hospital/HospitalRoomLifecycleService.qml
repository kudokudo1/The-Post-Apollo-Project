import QtQuick
import Quickshell
import Quickshell.Io

// Source-owned PX Room lifecycle transport, separate from GIO and Trash++
// managed copies. UI state is never source authority. Production must remain
// locked until an independently verified operator grant is available.
Scope {
    id: root

    property string roomId: ""
    property bool active: false
    property bool loading: false
    property bool operating: false
    property string lastError: ""
    property string outcome: ""
    property var review: ({})
    property bool reviewReady: false
    property string pendingAction: ""
    property string pendingRoomId: ""
    property int pendingRevision: -1
    property string pendingDigest: ""

    readonly property bool permissionReady:
        reviewReady && review.operatorAuthenticated === true
        && review.requiresOwnerReview === false

    signal committed(var receipt)
    signal refused(string reason)

    onRoomIdChanged: {
        reviewReady = false;
        review = ({});
        outcome = "";
        lastError = "";
    }
    onActiveChanged: {
        if (!active)
            reviewReady = false;
    }

    function commandArgs(args) {
        return [
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-room-lifecycle", "hospital"
        ].concat(args);
    }

    function refresh() {
        const id = String(roomId || "").trim();
        if (!active || loading || operating || queryProcess.running
                || !/^[A-Za-z0-9._:/-]{1,160}$/.test(id))
            return false;
        reviewReady = false;
        review = ({});
        lastError = "";
        loading = true;
        queryProcess.exec(commandArgs([
            "room-lifecycle-review", id, "--json"
        ]));
        return true;
    }

    // Called only after a deliberate operator UI confirmation. The backend
    // rechecks exact Room ID, digest and revision under BEGIN IMMEDIATE.
    // No unsigned UI state can substitute for independent authority.
    function execute(action, witness) {
        const evidence = witness || {};
        const current = review || {};
        const room = String(roomId || "").trim();
        const digest = String(evidence.digest || "");
        const revision = evidence.revision;
        const expectedState = action === "TRASH" ? "ACTIVE" : "TRASHED";
        const permitted = action === "TRASH"
            ? current.canTrash === true : current.canRestore === true;
        if (!active || !permissionReady || !reviewReady || loading
                || operating || executeProcess.running
                || (action !== "TRASH" && action !== "RESTORE")
                || !permitted || current.state !== expectedState
                || current.roomId !== room
                || current.digest !== digest
                || current.revision !== revision
                || !/^[0-9a-f]{64}$/.test(digest)
                || !Number.isSafeInteger(revision) || revision < 0) {
            lastError = "LIFECYCLE REFUSED // AUTHORITY OR REVIEW NOT VERIFIED";
            refused(lastError);
            return false;
        }
        pendingAction = action;
        pendingRoomId = room;
        pendingDigest = digest;
        pendingRevision = revision;
        operating = true;
        outcome = "PX // " + action + " SUBMITTED";
        lastError = "";
        executeProcess.exec(commandArgs([
            action === "TRASH"
                ? "room-lifecycle-trash" : "room-lifecycle-restore",
            room,
            "--expected-revision", String(revision),
            "--expected-digest", digest,
            "--confirm-room-id", room,
            "--json"
        ]));
        return true;
    }

    Process {
        id: queryProcess
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: queryProcess.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: queryProcess.errorText = String(this.text || "")
        }
        onExited: function(code, status) {
            const output = queryProcess.outputText;
            const error = queryProcess.errorText;
            queryProcess.outputText = "";
            queryProcess.errorText = "";
            root.loading = false;
            try {
                if (Number(code) !== 0)
                    throw new Error(String(error || output || "PX NOT AVAILABLE").slice(0,240));
                const payload = JSON.parse(output || "{}");
                if (String(payload.roomId || "") !== String(root.roomId || "")
                        || !/^[0-9a-f]{64}$/.test(String(payload.digest || ""))
                        || !Number.isSafeInteger(payload.revision)
                        || (payload.state !== "ACTIVE" && payload.state !== "TRASHED")
                        || !Array.isArray(payload.blockers))
                    throw new Error("PX EXACT ROOM REVIEW MISMATCH");
                root.review = payload;
                root.reviewReady = true;
                root.lastError = "";
            } catch (e) {
                root.review = ({});
                root.reviewReady = false;
                root.lastError = "PX REVIEW // " + String(e).slice(0,230);
            }
        }
    }

    Process {
        id: executeProcess
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: executeProcess.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: executeProcess.errorText = String(this.text || "")
        }
        onExited: function(code, status) {
            const result = executeProcess.outputText;
            const err = executeProcess.errorText;
            executeProcess.outputText = "";
            executeProcess.errorText = "";
            root.operating = false;
            let payload = null;
            let problem = "";
            try {
                if (Number(code) !== 0)
                    throw new Error(String(err || result || "PX REFUSED").slice(0,230));
                payload = JSON.parse(result || "{}");
                if (payload.roomId !== root.pendingRoomId
                        || payload.state !== (root.pendingAction === "TRASH"
                            ? "TRASHED" : "ACTIVE")
                        || payload.revision !== root.pendingRevision + 1
                        || payload.originalPreserved !== true
                        || payload.burnAllowed !== false)
                    throw new Error("PX RECEIPT IDENTITY OR STATE MISMATCH");
            } catch (e) {
                problem = "PX LIFECYCLE // " + String(e).slice(0,240);
            }
            root.pendingAction = "";
            root.pendingRoomId = "";
            root.pendingRevision = -1;
            root.pendingDigest = "";
            root.reviewReady = false;
            root.review = ({});
            if (problem) {
                root.lastError = problem;
                root.outcome = "REFUSED / UNKNOWN // REFRESH ROOM";
                root.refused(problem);
            } else {
                root.lastError = "";
                root.outcome = "PX " + payload.state + " // RECEIPT RECORDED";
                root.committed(payload);
            }
        }
    }
}
