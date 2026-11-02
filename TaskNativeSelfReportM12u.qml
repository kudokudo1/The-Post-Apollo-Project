//@ pragma DataDir $BASE/post-apollo-m12u-fixture
//@ pragma StateDir $BASE/post-apollo-m12u-state
import QtQuick
import Quickshell
import qs.services.hub

// M12u: unmounted standalone auto-smoke of the *actual* To-Do singleton.
// The operator must explicitly launch the dedicated runner, which provides
// a newly created private XDG root and POST_APOLLO_M12U_DISPOSABLE=1.
// One synthetic legacy mutation. No second FileView, generic writer,
// production ticket enablement, startup changes to the live shell or retry.
Scope {
    id: smoke
    readonly property string expectedSuffix: "/post-apollo-m12u-fixture"
    readonly property bool isolatedPath:
        Quickshell.dataDir.endsWith(expectedSuffix)
        && ApolloHubTodoStore.storagePath
           === Quickshell.dataDir + "/apollo-hub-todo-v1.json"
    readonly property bool safe:
        isolatedPath
        && Quickshell.env("POST_APOLLO_M12U_DISPOSABLE") === "1"
        && !ApolloHubTodoStore.guardedWriterEnabled
        && !ApolloHubTodoStore.ticketProducerEnabled
        && !ApolloHubTodoStore.independentlyAuthenticatedTicketReceipt
    readonly property string fixtureTitle: "M12U_SYNTHETIC_TASK"
    property string phase: "WAIT_INITIAL"
    property string resultLine: "PENDING"
    property bool finished: false

    function stage(name) {
        console.warn("M12U_STAGE|" + name + "|PASS");
    }

    function endTest(ok, reason) {
        if (finished) return;
        finished = true;
        resultLine = (ok ? "PASS" : "FAIL") + " // " + reason;
        console.warn("M12U_RESULT|" + (ok ? "PASS" : "FAIL")
                     + "|" + reason);
        deadline.stop();
    }

    function validOneTask() {
        var s = ApolloHubTodoStore.snapshot;
        return s && s.total === 1 && s.remaining === 1
               && s.items && s.items.length === 1
               && s.items[0].title === fixtureTitle
               && s.items[0].done === false;
    }

    // Queue observations after the FileView event which changed the store
    // state unwinds. Calling addTask() synchronously from the initial
    // onLoadFailed transition, or reloadFromDisk() synchronously from
    // onSaved, is a test-harness reentrancy risk, not a requirement of the
    // live writer. Qt.callLater coalesces calls to the same named function.
    function scheduleAdvance() {
        if (!finished) Qt.callLater(smoke.advance);
    }

    function advance() {
        if (finished) return;
        if (!isolatedPath) {
            endTest(false, "FIXTURE_PATH_MISMATCH");
            return;
        }
        if (Quickshell.env("POST_APOLLO_M12U_DISPOSABLE") !== "1") {
            endTest(false, "DISPOSABLE_ENV_MISSING");
            return;
        }
        if (!safe) {
            endTest(false, "PRODUCTION_GATES_UNSAFE");
            return;
        }
        var state = ApolloHubTodoStore.storageState;
        if (state === "error" || state === "unsupported") {
            endTest(false, "STORE_REPORTED_ERROR");
            return;
        }
        if (phase === "WAIT_INITIAL") {
            if (state === "loading") return;
            if (state !== "empty"
                    || ApolloHubTodoStore.snapshot.total !== 0) {
                endTest(false, "INITIAL_FIXTURE_NOT_EMPTY");
                return;
            }
            stage("INITIAL_EMPTY");
            // The current producer is hard-disabled. Its refusal must not
            // itself cause a write or transition the store to SAVING.
            phase = "CHECKING_TICKET";
            var ticket = ApolloHubTodoStore.submit(
                "HUB", "addTask",
                {args:{title:"M12U_DISABLED_TICKET_CHECK"}});
            if (!ticket || ticket.admitted !== false
                    || ticket.reason !== "M12Q_DISABLED_NO_WRITER"
                    || ApolloHubTodoStore.storageState !== "empty"
                    || ApolloHubTodoStore.snapshot.total !== 0) {
                endTest(false, "TICKET_GATE_DID_NOT_REFUSE");
                return;
            }
            stage("TICKET_DISABLED");
            // This is the sole explicit test write. All checks above must
            // pass before invoking the original legacy mutation route.
            phase = "WAIT_SAVE";
            if (!ApolloHubTodoStore.addTask("M12U_SYNTHETIC_TASK")) {
                endTest(false, "LEGACY_STAGE_REFUSED");
                return;
            }
            return;
        }
        if (phase === "WAIT_SAVE") {
            if (state === "saving") return;
            if (state !== "ready" || !validOneTask()) {
                endTest(false, "SAVE_CALLBACK_INVALID");
                return;
            }
            stage("NATIVE_SAVE");
            phase = "WAIT_RELOAD";
            if (!ApolloHubTodoStore.reloadFromDisk()) {
                endTest(false, "NATIVE_RELOAD_REFUSED");
                return;
            }
            return;
        }
        if (phase === "WAIT_RELOAD") {
            if (state === "loading") return;
            if (state !== "ready" || !validOneTask()) {
                endTest(false, "RELOAD_CALLBACK_INVALID");
                return;
            }
            stage("NATIVE_RELOAD");
            endTest(true, "NATIVE_SEQUENCE");
        }
    }

    Component.onCompleted: {
        // Delayed, so FileView's initial ready/empty state can arrive first.
        // Launch is the operator's single deliberate disposable test action.
        console.warn("M12U_BOOT|CONFIG_LOADED|PASS");
        smoke.scheduleAdvance();
    }

    Connections {
        target: ApolloHubTodoStore
        function onStorageStateChanged() {
            // Fixed-vocabulary state trace from the real singleton only.
            // No task title, document bytes or filesystem paths in logs.
            var state=String(ApolloHubTodoStore.storageState).toUpperCase();
            if (["LOADING","EMPTY","SAVING","READY","ERROR","UNSUPPORTED"].indexOf(state) >= 0)
                console.warn("M12U_STATE|" + state + "|OBSERVED");
            smoke.scheduleAdvance();
        }
    }

    Timer {
        id: deadline
        interval: 20000
        repeat: false
        running: true
        onTriggered: smoke.endTest(false, "NATIVE_CALLBACK_TIMEOUT")
    }

    PanelWindow {
        visible: true
        implicitWidth: 540
        implicitHeight: 230
        focusable: false
        exclusiveZone: 0
        anchors { left: true; top: true }
        color: "#1B0623"
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 2
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                Text {
                    text: "TASKS // M12u AUTOMATIC NATIVE SMOKE"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "SYNTHETIC DATA ONLY // NO PRODUCTION WRITE"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {
                    width: parent.width
                    text: "GUARD // " + (smoke.safe ? "ISOLATED" : "REFUSED")
                    color: smoke.safe ? "#9ece6a" : "#F2BE4E"
                    font.pixelSize: 13
                }
                Text {
                    width: parent.width
                    text: "PHASE // " + smoke.phase
                    color: "#DCF3FA"
                    font.pixelSize: 13
                }
                Text {
                    width: parent.width
                    text: "RESULT // " + smoke.resultLine
                    color: smoke.finished && smoke.resultLine.indexOf("PASS")===0
                           ? "#9ece6a" : "#F2BE4E"
                    font.pixelSize: 13
                }
                Text {
                    width: parent.width
                    text: "Runner independently checks JSON after this process exits."
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
            }
        }
    }
}
