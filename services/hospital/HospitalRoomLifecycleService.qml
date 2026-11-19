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
    property bool nativeClientInstalled: false
    property string lastError: ""
    property string outcome: ""
    property var review: ({})
    property bool reviewReady: false
    property string pendingAction: ""
    property string pendingRoomId: ""
    property int pendingRevision: -1
    property string pendingDigest: ""

    // Historical shared UI binding name. This is ONLY native transport
    // readiness, NEVER human approval or verified ownership. The C5-H2
    // issuer obtains independent protected Room state and interactive
    // approval, and PX alone commits a one-use signed grant.
    // Do not rely on the legacy user-UID PX preview to request consent.
    readonly property bool permissionReady:
        active && nativeClientInstalled

    signal committed(var receipt)
    signal refused(string reason)

    onRoomIdChanged: {
        reviewReady = false;
        review = ({});
        outcome = "";
        lastError = "";
    }
    onActiveChanged: {
        if (!active) {
            reviewReady = false;
            nativeClientInstalled = false;
        } else {
            Qt.callLater(function() { root.probeNativeClient(); });
        }
    }

    readonly property string nativeClientPath:
        "/usr/libexec/post-apollo/hospital/hospital-room-request"

    function probeNativeClient() {
        if (!active || nativeProbe.running || operating)
            return false;
        nativeClientInstalled = false;
        try {
            nativeProbe.exec([nativeClientPath, "--check"]);
            return true;
        } catch (error) {
            nativeClientInstalled = false;
            lastError = "HOSPITAL BACKEND NOT READY // NATIVE CLIENT NOT INSTALLED";
            return false;
        }
    }

    // Fixed read-only native executable. It opens only PX's approved
    // protected writer socket with owner/peer UID and config checks.
    // No fallback to desktop-owned hospital.db or old px hospital CLI.
    readonly property string nativeReadPath:
        "/usr/libexec/post-apollo/hospital/hospital-room-read"

    function refresh() {
        const id = String(roomId || "").trim();
        if (!active || loading || operating || queryProcess.running
                || !/^[A-Za-z0-9._:/-]{1,160}$/.test(id))
            return false;
        reviewReady = false;
        review = ({});
        lastError = "";
        loading = true;
        if (!nativeClientInstalled && !nativeProbe.running)
            probeNativeClient();
        try {
            queryProcess.exec([nativeReadPath, "review", id]);
        } catch (error) {
            loading = false;
            reviewReady = false;
            lastError = "HOSPITAL BACKEND NOT READY // PROTECTED ROOM READER UNAVAILABLE";
            return false;
        }
        return true;
    }

    // Called only after two exact-Room UI gestures. The request contains
    // action + Room ID, never a desktop graph digest, grant or permission.
    // The installed issuer independently performs a protected source
    // PREPARE, rechecks operator + seat + Polkit + retention, then commits.
    // A missing/stale legacy PX review must not spoof or veto that authority.
    function execute(action, witness) {
        const room = String(roomId || "").trim();
        if (!active || !nativeClientInstalled || operating
                || executeProcess.running
                || (action !== "TRASH" && action !== "RESTORE")
                || !/^[A-Za-z0-9._:/-]{1,160}$/.test(room)) {
            lastError = "HOSPITAL NATIVE HOLD // REQUEST PATH NOT VERIFIED";
            refused(lastError);
            return false;
        }
        pendingAction = action;
        pendingRoomId = room;
        pendingDigest = "";
        pendingRevision = -1;
        operating = true;
        outcome = "NATIVE APPROVAL REQUESTED // " + action;
        lastError = "";
        try {
            executeProcess.exec([nativeClientPath, action, room]);
            return true;
        } catch (error) {
            operating = false;
            lastError = "HOSPITAL BACKEND NOT READY // NATIVE REQUEST UNAVAILABLE";
            refused(lastError);
            return false;
        }
    }

    // This status check cannot authorize a Room. The native executable
    // itself verifies its ROOT-owned inode and the ROOT-owned issuer socket;
    // production still requires the separate issuer/PX service installation.
    Process {
        id: nativeProbe
        property string outputText: ""
        stdout: StdioCollector {
            onStreamFinished: nativeProbe.outputText = String(this.text || "")
        }
        onExited: function(code, status) {
            const output = nativeProbe.outputText;
            nativeProbe.outputText = "";
            let installed = false;
            try {
                if (Number(code) === 0) {
                    const payload = JSON.parse(output || "{}");
                    installed = payload.schema === "postapollo.hospital.native-client.v1"
                        && payload.status === "INSTALLED";
                }
            } catch (error) {
                installed = false;
            }
            root.nativeClientInstalled = installed;
        }
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
                    throw new Error("HOSPITAL BACKEND NOT READY // PROTECTED ROOM REVIEW UNAVAILABLE");
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
                root.lastError = "HOSPITAL BACKEND NOT READY // "
                    + (String(e).includes("PROTECTED ROOM REVIEW")
                       ? "PROTECTED ROOM REVIEW UNAVAILABLE"
                       : "PROTECTED REVIEW FORMAT REFUSED");
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
                    throw new Error("PROTECTED ISSUER REFUSED OR NOT INSTALLED");
                payload = JSON.parse(result || "{}");
                if (payload.schema !== "postapollo.connections.hospital-native-issuer-response.v1"
                        || payload.status !== "COMMITTED"
                        || payload.action !== root.pendingAction
                        || payload.roomId !== root.pendingRoomId
                        || !Number.isSafeInteger(payload.revision)
                        || payload.revision <= 0
                        || payload.originalPreserved !== true
                        || payload.burnAllowed !== false)
                    throw new Error("PROTECTED COMMIT RECEIPT IDENTITY MISMATCH");
            } catch (e) {
                problem = "HOSPITAL NATIVE HOLD // " + String(e).slice(0,180);
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
                root.outcome = "PROTECTED PX // "
                    + (payload.action === "TRASH" ? "TRASHED" : "RESTORED")
                    + " // RECEIPT CONFIRMED";
                root.committed(payload);
            }
        }
    }
}
