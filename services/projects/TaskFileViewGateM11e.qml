import QtQuick
import Quickshell
import Quickshell.Io
import "TaskFileViewGatePolicyM11e.js" as GatePolicy

// UNMOUNTED M11e: executable ONLY by explicit standalone test config.
// The FileView is restricted by its QML path check to a manually created
// disposable m11e-fileview-test/fixture-only.json. QML cannot prove a path
// is not redirected by a symlink: native test requires operator supervision.
Scope {
    id: gate

    property string fixturePath: ""
    property string activePath: ""
    property bool attached: false
    property var gateState: GatePolicy.idle()
    readonly property string phase: gateState.phase
    readonly property string reason: gateState.reason
    readonly property int completedWrites: gateState.completed
    readonly property int confirmedCounter: gateState.document
        ? gateState.document.counter : -1
    readonly property bool testStageAvailable: GatePolicy.writable(gateState)
    readonly property bool liveWriterAuthorized: false
    readonly property bool sqliteWriterAuthorized: false
    readonly property bool remoteWriteAuthorized: false
    readonly property bool productionActivation: false

    signal observed()

    function attachTestFile() {
        if (attached || gateState.phase !== "UNARMED") return false;
        if (!/^\/.+\/m11e-fileview-test\/fixture-only\.json$/.test(fixturePath)) {
            gateState = GatePolicy.blocked(gateState,
                "EXPLICIT_TEST_FIXTURE_REQUIRED");
            observed();
            return false;
        }
        var result = GatePolicy.start(gateState);
        if (!result.accepted) return false;
        gateState = result.state;
        activePath = fixturePath;
        attached = true;
        observed();
        // Assigning FileView.path starts asynchronous load. No write.
        return true;
    }

    function stageSyntheticIncrement() {
        if (!attached || !fixtureFile.loaded) return false;
        var plan = GatePolicy.requestStage(gateState);
        if (!plan.accepted) {
            gateState = plan.state;
            observed();
            return false;
        }
        gateState = plan.state;
        // Only test fixture bytes and a single stage are ever written.
        // FileView saved() is not acceptance until reload() reads exact bytes.
        fixtureFile.setText(plan.raw);
        observed();
        return true;
    }

    function freezeTestAdmission() {
        var reply = GatePolicy.requestFreeze(gateState);
        gateState = reply.state;
        observed();
        return reply.accepted;
    }

    function reloadTestFile() {
        if (!attached) return false;
        var reply = GatePolicy.requestReload(gateState);
        if (!reply.accepted) return false;
        gateState = reply.state;
        fixtureFile.reload();
        observed();
        return true;
    }

    FileView {
        id: fixtureFile
        path: gate.attached ? gate.activePath : ""
        watchChanges: false
        atomicWrites: true
        blockWrites: false
        printErrors: false

        onLoaded: {
            if (!gate.attached) return;
            gate.gateState = GatePolicy.onLoaded(gate.gateState,
                fixtureFile.text());
            gate.observed();
        }
        onLoadFailed: function(error) {
            if (!gate.attached) return;
            gate.gateState = GatePolicy.onLoadFailed(gate.gateState);
            gate.observed();
        }
        onSaved: {
            if (!gate.attached) return;
            gate.gateState = GatePolicy.onSaved(gate.gateState);
            // saved() fires while FileView still holds its async writer.
            // Calling reload() synchronously can silently skip the read.
            // Dispatch on the next event-loop turn, fenced to this stage.
            if (gate.gateState.phase === "VERIFYING") {
                var savedToken = gate.gateState.activeToken;
                Qt.callLater(function() {
                    if (gate.attached && gate.gateState.phase === "VERIFYING"
                            && savedToken !== null
                            && gate.gateState.activeToken === savedToken) {
                        fixtureFile.reload();
                    }
                });
            }
            gate.observed();
        }
        onSaveFailed: function(error) {
            if (!gate.attached) return;
            gate.gateState = GatePolicy.onSaveFailed(gate.gateState);
            gate.observed();
        }
    }
}
