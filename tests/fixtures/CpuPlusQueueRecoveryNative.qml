import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as Presentation
import "widgets/cpuplus/CpuPlusQueueHistory.js" as History
import "widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery
import "memory/MemoryQueueSessionHost.js" as Host

// Disposable CI only. One canonical controller; no production unlock.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE") === "CI_DISPOSABLE_ONLY"
    property var host: Host.initial(Consumer)
    readonly property var recovery: Host.recoveryContext(host)
    readonly property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000001"
    property string oldOwner: ""
    property string resultId: ""
    property int phase: 0
    property int ticks: 0
    property int writes: 0
    property int reads: 0
    property bool dropping: false
    property bool exited: false
    property bool done: false
    function check(ok, label) {
        if (!ok) {
            console.error("QUEUE_R3_RECOVERY_FAIL // " + label + " // " + host.failure);
            done = true;
            child.running = false;
            Qt.quit();
        }
        return ok;
    }
    function launch(generation) {
        host = Host.start(host, Consumer, generation);
        exited = false;
        dropping = false;
        child.running = true;
    }
    function receive(line) {
        if (done || dropping) return;
        let packet;
        try { packet = JSON.parse(line); } catch (_) { check(false,"parse"); return; }
        if (phase === 2 && packet.kind === "ACTION") {
            // Observe the reply only in the harness, never deliver to Host.
            if (!check(packet.disposition === "REPORTED" && packet.result.request.id
                && !line.includes("inode"),"committed reply")) return;
            resultId = packet.result.request.id;
            dropping = true;
            child.running = false;
            return;
        }
        host = Host.feed(host,line+"\n",Consumer,Presentation.project,History.project,
            host.generation,Recovery.project,Recovery.row);
        check(host.phase !== "FAILED","canonical host accepts " + packet.kind);
    }
    function read(kind, value) {
        const request = Host.readRecovery(host,kind,value);
        if (!check(!!request.frame,"explicit recovery read")) return;
        host = request.state;
        ++reads;
        child.write(request.frame);
    }
    function submit(intent) {
        const sent = Host.confirm(host,intent,actionId,Consumer);
        if (!check(!!sent.frame && sent.state.session.pending && writes === 0,"single confirmed write")) return;
        host = sent.state;
        ++writes;
        child.write(sent.frame);
    }
    Process {
        id: child
        command: ["python3","-B",Quickshell.env("POST_APOLLO_QUEUE_PIPE_CHILD")]
        stdinEnabled: true
        stdout: SplitParser { onRead: data => smoke.receive(data) }
        stderr: SplitParser { onRead: data => console.log("QUEUE_R3_CHILD // " + data) }
        onExited: (exitCode, exitStatus) => {
            smoke.host = Host.stop(smoke.host,Consumer,"CHILD_EXIT",smoke.host.generation);
            smoke.exited = true;
            if (!smoke.done && !smoke.dropping) smoke.check(false,"unexpected child exit");
        }
    }
    Window {
        visible: smoke.armed
        width: 550
        height: 1000
        Column {
            width: parent.width
            CpuPlusQueuePane {
                id: pane
                width: parent.width
                observedDiskKiB: 25165816
                capacityTargetGiB: 16
                actionContext: Host.context(smoke.host)
                onIntentConfirmed: intent => smoke.submit(intent)
            }
            CpuPlusQueueRecoveryPane {
                id: recoveryPane
                width: parent.width
                atomicMode: true
                recoveryContext: smoke.recovery
                readAvailable: !!Host.readRecovery(smoke.host,"INVENTORY",16).frame
                onRecoveryReadRequested: (kind,value) => smoke.read(kind,value)
            }
        }
    }
    Timer {
        interval: 50
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 280) { smoke.check(false,"timeout " + smoke.phase); return; }
            if (smoke.phase === 0 && smoke.host.session.status) {
                if (!smoke.check(smoke.host.startupLocked && smoke.host.session.status.state === "IDLE REPORTED","initial locked")) return;
                smoke.oldOwner = smoke.host.session.ownerId;
                pane.expiryText = "2099-01-01 00:00";
                pane.prepareIntent("QUEUE");
                if (!smoke.check(!pane.preparation,"locked queue refused")) return;
                smoke.phase = 1;
                recoveryPane.requestRead("INVENTORY",16);
                recoveryPane.requestRead("INVENTORY",16);
                if (!smoke.check(smoke.reads === 1,"one inventory signal while pending")) return;
            } else if (smoke.phase === 1 && recoveryPane.view) {
                if (!smoke.check(recoveryPane.view.recent.length === 0 && recoveryPane.view.startupLocked
                    && smoke.host.startupLocked,"empty inventory no unlock")) return;
                // Deliberate test injection only, not a host API or acceptance.
                smoke.host = Object.assign({},smoke.host,{startupLocked:false});
                smoke.phase = 2;
                pane.prepareIntent("QUEUE");
                if (!smoke.check(!!pane.preparation,"fixture confirmation")) return;
                pane.confirmIntent();
                pane.confirmIntent();
            } else if (smoke.phase === 2 && smoke.exited) {
                if (!smoke.check(smoke.host.session.unresolved && smoke.host.startupLocked
                    && smoke.recovery.inventory === null && smoke.writes === 1,"lost reply remains unresolved")) return;
                smoke.phase = 3;
                smoke.launch(2);
            } else if (smoke.phase === 3 && smoke.host.session.status) {
                if (!smoke.check(smoke.host.session.ownerId !== smoke.oldOwner
                    && smoke.host.session.status.requestId === smoke.resultId
                    && smoke.host.session.unresolved && smoke.host.startupLocked,"new owner same saved request")) return;
                smoke.phase = 4;
                recoveryPane.requestRead("INVENTORY",16);
                if (!smoke.check(smoke.reads === 2,"new epoch inventory signal")) return;
            } else if (smoke.phase === 4 && recoveryPane.view) {
                const view = recoveryPane.view;
                if (!smoke.check(view.recent.length === 1 && view.recent[0].actionId === smoke.actionId
                    && view.recent[0].resultId === smoke.resultId && view.recent[0].state === "COMMITTED"
                    && view.pendingId === smoke.resultId && view.outcome === "UNVERIFIED"
                    && !view.canExecute && smoke.recovery.hostStatus.unresolved,"actual recovery pane local commit")) return;
                console.log("QUEUE_R3_RECOVERY_STEP // committed local intent rendered, startup locked");
                smoke.phase = 5;
                recoveryPane.lookupText = smoke.actionId;
                recoveryPane.requestRead("LOCAL_ACTION",recoveryPane.lookupText);
                recoveryPane.requestRead("LOCAL_ACTION",recoveryPane.lookupText);
                if (!smoke.check(smoke.reads === 3,"one exact lookup signal while pending")) return;
            } else if (smoke.phase === 5 && recoveryPane.localView) {
                const local = smoke.recovery.localAction;
                if (!smoke.check(recoveryPane.localView.record && !recoveryPane.localView.missing
                    && recoveryPane.localView.record.resultId === smoke.resultId
                    && recoveryPane.view === null,"actual exact lookup display")) return;
                if (!smoke.check(local.record.result_request_id === smoke.resultId
                    && local.record.state === "COMMITTED" && !local.canExecute
                    && smoke.host.startupLocked && smoke.host.session.unresolved && smoke.writes === 1,"exact action recovered without unlock")) return;
                pane.prepareIntent("CANCEL");
                if (!smoke.check(!pane.preparation,"no cancel before reconciliation")) return;
                smoke.phase = 6;
                recoveryPane.requestRead("LOCAL_ACTION","c23683a9-b2ab-4a2c-87ce-000000000099");
                if (!smoke.check(smoke.reads === 4,"missing-record lookup signal")) return;
            } else if (smoke.phase === 6 && recoveryPane.localView) {
                if (!smoke.check(recoveryPane.localView.missing && recoveryPane.localView.record === null
                    && smoke.host.startupLocked && smoke.host.session.unresolved,"missing record is not noncommit")) return;
                smoke.phase = 7;
                smoke.dropping = true;
                child.stdinEnabled = false;
            } else if (smoke.phase === 7 && smoke.exited) {
                recoveryPane.requestRead("INVENTORY",16);
                if (!smoke.check(smoke.reads === 4 && !recoveryPane.canRead && recoveryPane.view === null
                    && recoveryPane.localView === null,"EOF refuses reads and clears pane")) return;
                if (!smoke.check(smoke.recovery.inventory === null && smoke.recovery.localAction === null
                    && smoke.host.startupLocked && smoke.host.session.unresolved && smoke.writes === 1,"EOF clears recovery")) return;
                console.log("QUEUE_R3_RECOVERY_PASS // actual canonical host, QML pane, durable lost QUEUE, inventory, lookup, EOF");
                smoke.done = true;
                Qt.quit();
            }
        }
    }
    Component.onCompleted: {
        if (!armed) Qt.quit();
        else launch(1);
    }
}
