import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as Presentation
import "widgets/cpuplus/CpuPlusQueueHistory.js" as History
import "widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery
import "watchdog/MemoryQueueSessionHost.js" as Host
import "watchdog" as Memory

// Disposable CI only. One canonical controller; no production unlock.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE") === "CI_DISPOSABLE_ONLY"
    readonly property bool timeoutTrial: Quickshell.env("POST_APOLLO_QUEUE_WATCHDOG_TRIAL") === "1"
    readonly property string stagedTrial: (Quickshell.env("POST_APOLLO_QUEUE_STAGED_TRIAL") || "")
    readonly property string ackTrial: (Quickshell.env("POST_APOLLO_QUEUE_ACK_TRIAL") || "")
    readonly property var reviewView: Host.reviewContext(host)
    property int reviewWrites: 0
    property int ackWrites: 0
    property int receiptReads: 0
    property string reviewId: ""
    property var reviewedEvidence: null
    property var savedReceipt: null
    property int commits: 0
    property int watchdogTrips: 0
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
        host = Host.start(host, Consumer, generation, stagedTrial ? "STAGED" : "LEGACY", !!ackTrial);
        exited = false;
        dropping = false;
        child.stdinEnabled = true;
        child.running = true;
    }
    function receive(line) {
        if (done || dropping) return;
        let packet;
        try { packet = JSON.parse(line); } catch (_) { check(false,"parse"); return; }
        if (phase === 2 && packet.kind === "ACTION" && stagedTrial !== "ROUNDTRIP") {
            if (!check(!timeoutTrial,"delayed child replied before watchdog")) return;
            // Observe the reply only in the harness, never deliver to Host.
            if (!check(packet.disposition === "REPORTED" && packet.result.request.id
                && !line.includes("inode"),"committed reply")) return;
            resultId = packet.result.request.id;
            dropping = true;
            child.running = false;
            return;
        }
        if (phase === 10 && ackTrial === "LOST" && packet.kind === "RECOVERY_ACK") {
            // The harness witnesses the durable receipt but deliberately
            // never gives this response to the canonical host.
            if (!check(packet.receipt.review.review_id === reviewId
                && packet.receipt.disposition === "REVIEW_ACKNOWLEDGED_ONLY"
                && packet.receipt.startup_unlock === false,"lost ack persisted")) return;
            savedReceipt = packet.receipt;
            dropping = true;
            child.running = false;
            return;
        }
        host = Host.feed(host,line+"\n",Consumer,Presentation.project,History.project,
            host.generation,Recovery.project,Recovery.row);
        if (!check(host.phase !== "FAILED","canonical host accepts " + packet.kind)) return;
        if (packet.kind === "PREPARED_ACTION") {
            if (!check(!!stagedTrial && host.stage.phase === "RECEIPT_READY"
                && host.session.pending && commits === 0,"validated live receipt")) return;
            if (stagedTrial === "EOF") {
                dropping = true;
                child.stdinEnabled = false;
                return;
            }
            const next = Host.takeCommit(host,host.generation);
            if (!check(!!next.frame,"one commit frame")) return;
            host = next.state;
            ++commits;
            if (!check(!Host.takeCommit(host,host.generation).frame,"commit consumed before write")) return;
            child.write(next.frame);
        }
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
    Memory.MemoryQueueSessionWatchdog {
        id: watchdog
        hostState: smoke.host
        timeouts: ({HELLO:5000,PUBLICATION:5000,ACTION:1200,HISTORY:3000,RECOVERY:3000,PARTIAL_FRAME:2000})
        onPolicyRejected: generation => smoke.check(false,"watchdog policy rejected")
        onDeadlineExpired: (generation,category,ticket) => {
            if (!smoke.check(smoke.timeoutTrial && smoke.phase===2 && category==="ACTION"
                && generation===smoke.host.generation && smoke.watchdogTrips===0,"exact action watchdog")) return;
            ++smoke.watchdogTrips;
            smoke.host=Host.stop(smoke.host,Consumer,"ACTION_TIMEOUT",generation);
            if (!smoke.check(smoke.host.session.unresolved && smoke.host.startupLocked
                && watchdog.activeCount===0,"timeout invalidates before child stop")) return;
            smoke.dropping=true;
            child.running=false;
            console.log("QUEUE_R3_WATCHDOG_STEP // exact action timeout, owner invalidated before stop");
        }
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
                if (!smoke.check(watchdog.activeCount===0,"idle no active deadlines")) return;
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
            } else if (smoke.phase === 2 && smoke.stagedTrial === "ROUNDTRIP" && smoke.host.session.status) {
                if (!smoke.check(!!smoke.host.session.status.requestId && !smoke.host.session.pending
                    && smoke.commits === 1 && smoke.writes === 1,"staged roundtrip committed once")) return;
                smoke.dropping = true;
                smoke.phase = 8;
                child.stdinEnabled = false;
            } else if (smoke.phase === 8 && smoke.exited) {
                console.log("QUEUE_R3_STAGED_PASS // actual roundtrip");
                console.log("QUEUE_R3_RECOVERY_PASS // staged roundtrip");
                smoke.done = true;
                Qt.quit();
            } else if (smoke.phase === 2 && smoke.exited) {
                if (!smoke.check(smoke.host.session.unresolved && smoke.host.startupLocked
                    && smoke.recovery.inventory === null && smoke.writes === 1,"lost reply remains unresolved")) return;
                smoke.phase = 3;
                smoke.launch(2);
            } else if (smoke.phase === 3 && smoke.host.session.status) {
                if (!smoke.check(smoke.host.session.ownerId !== smoke.oldOwner
                    && (smoke.stagedTrial === "EOF"
                        ? smoke.host.session.status.requestId === null
                        : !!smoke.host.session.status.requestId
                            && (smoke.timeoutTrial || smoke.host.session.status.requestId === smoke.resultId))
                    && smoke.host.session.unresolved && smoke.host.startupLocked,"new owner same saved request")) return;
                if(smoke.timeoutTrial)smoke.resultId=smoke.host.session.status.requestId;
                if(!smoke.check(watchdog.activeCount===0,"reconnected idle deadlines"))return;
                smoke.phase = 4;
                recoveryPane.requestRead("INVENTORY",16);
                if (!smoke.check(smoke.reads === 2,"new epoch inventory signal")) return;
            } else if (smoke.phase === 4 && recoveryPane.view) {
                const view = recoveryPane.view;
                if (!smoke.check(view.recent.length === 1 && view.recent[0].actionId === smoke.actionId
                    && view.recent[0].resultId === (smoke.stagedTrial === "EOF" ? null : smoke.resultId)
                    && view.recent[0].state === (smoke.stagedTrial === "EOF" ? "PREPARED" : "COMMITTED")
                    && view.pendingId === (smoke.stagedTrial === "EOF" ? null : smoke.resultId) && view.outcome === "UNVERIFIED"
                    && !view.canExecute && smoke.recovery.hostStatus.unresolved,"actual recovery pane local commit")) return;
                console.log("QUEUE_R3_RECOVERY_STEP // "+view.recent[0].state+" local intent rendered, startup locked");
                smoke.phase = 5;
                recoveryPane.lookupText = smoke.actionId;
                recoveryPane.requestRead("LOCAL_ACTION",recoveryPane.lookupText);
                recoveryPane.requestRead("LOCAL_ACTION",recoveryPane.lookupText);
                if (!smoke.check(smoke.reads === 3,"one exact lookup signal while pending")) return;
            } else if (smoke.phase === 5 && recoveryPane.localView) {
                const local = smoke.recovery.localAction;
                if (!smoke.check(recoveryPane.localView.record && !recoveryPane.localView.missing
                    && recoveryPane.localView.record.resultId === (smoke.stagedTrial === "EOF" ? null : smoke.resultId)
                    && recoveryPane.view === null,"actual exact lookup display")) return;
                if (!smoke.check(local.record.result_request_id === (smoke.stagedTrial === "EOF" ? null : smoke.resultId)
                    && local.record.state === (smoke.stagedTrial === "EOF" ? "PREPARED" : "COMMITTED") && !local.canExecute
                    && smoke.host.startupLocked && smoke.host.session.unresolved && smoke.writes === 1,"exact action recovered without unlock")) return;
                pane.prepareIntent("CANCEL");
                if (!smoke.check(!pane.preparation,"no cancel before reconciliation")) return;
                smoke.phase = 6;
                recoveryPane.requestRead("LOCAL_ACTION","c23683a9-b2ab-4a2c-87ce-000000000099");
                if (!smoke.check(smoke.reads === 4,"missing-record lookup signal")) return;
            } else if (smoke.phase === 6 && recoveryPane.localView) {
                if (!smoke.check(recoveryPane.localView.missing && recoveryPane.localView.record === null
                    && smoke.host.startupLocked && smoke.host.session.unresolved,"missing record is not noncommit")) return;
                if (smoke.ackTrial) {
                    if (!smoke.check(smoke.stagedTrial === "EOF" && smoke.commits === 0
                        && smoke.host.startupLocked && smoke.host.session.unresolved,"review requires unresolved preparation")) return;
                    const request = Host.beginReview(smoke.host,smoke.actionId);
                    if (!smoke.check(!!request.frame && smoke.reviewWrites === 0,"explicit review request")) return;
                    smoke.phase = 9;
                    smoke.host = request.state;
                    ++smoke.reviewWrites;
                    child.write(request.frame);
                } else {
                    smoke.phase = 7;
                    smoke.dropping = true;
                    child.stdinEnabled = false;
                }
            } else if (smoke.phase === 9 && smoke.reviewView.phase === "REVIEW_READY") {
                const v = smoke.reviewView;
                if (!smoke.check(v.canAcknowledge && v.review.snapshot.record.state === "PREPARED"
                    && v.review.snapshot.record.message.action_id === smoke.actionId
                    && v.review.snapshot.pending_request_id === null
                    && v.startupLocked && !v.canExecute && smoke.ackWrites === 0
                    && smoke.host.session.unresolved && watchdog.activeCount === 1,
                    "exact review visible before acknowledgment")) return;
                smoke.reviewId = v.review.review_id;
                smoke.reviewedEvidence = v.review;
                const selection = {reviewId:v.review.review_id,digest:v.review.review_digest,sequence:v.reviewSequence};
                if (!smoke.check(!Host.acknowledgeReview(smoke.host,
                    Object.assign({},selection,{digest:"0".repeat(64)}),smoke.host.generation).frame,
                    "wrong selection refused")) return;
                smoke.phase = 10;
                if (smoke.ackTrial === "EOF") {
                    smoke.dropping = true;
                    child.stdinEnabled = false;
                } else {
                    // Fixture simulates explicit operator confirmation.
                    const next = Host.acknowledgeReview(smoke.host,selection,smoke.host.generation);
                    if (!smoke.check(!!next.frame,"explicit ack frame")) return;
                    smoke.host = next.state;
                    ++smoke.ackWrites;
                    if (!smoke.check(!Host.acknowledgeReview(smoke.host,selection,smoke.host.generation).frame,
                        "duplicate ack refused before write")) return;
                    child.write(next.frame);
                }
            } else if (smoke.phase === 10 && smoke.ackTrial === "ACK" && smoke.reviewView.receipt && !smoke.dropping) {
                const receipt = smoke.reviewView.receipt;
                if (!smoke.check(receipt.disposition === "REVIEW_ACKNOWLEDGED_ONLY"
                    && receipt.review.review_id === smoke.reviewId && !receipt.startup_unlock
                    && !receipt.can_execute && smoke.host.startupLocked && smoke.host.session.unresolved,
                    "explicit acknowledgment saved without unlock")) return;
                smoke.savedReceipt = receipt;
                smoke.dropping = true;
                child.stdinEnabled = false;
            } else if (smoke.phase === 10 && smoke.exited) {
                if (!smoke.check(smoke.host.startupLocked && smoke.host.session.unresolved
                    && smoke.reviewView.unknownReviewId === (smoke.ackTrial === "LOST" ? smoke.reviewId : null)
                    && smoke.reviewView.review === null && smoke.reviewView.receipt === null
                    && smoke.ackWrites === (smoke.ackTrial === "EOF" ? 0 : 1),
                    "terminal review continuation retired")) return;
                smoke.phase = 11;
                smoke.launch(3);
            } else if (smoke.phase === 11 && smoke.host.session.status) {
                if (!smoke.check(smoke.host.startupLocked && smoke.host.session.unresolved
                    && smoke.host.session.status.requestId === null
                    && !smoke.reviewView.canAcknowledge && !Host.takeCommit(smoke.host,smoke.host.generation).frame,
                    "restart cannot acknowledge or commit recovered review")) return;
                const request = Host.readReviewReceipt(smoke.host,smoke.reviewId);
                if (!smoke.check(!!request.frame && smoke.receiptReads === 0,"explicit historical receipt lookup")) return;
                smoke.phase = 12;
                smoke.host = request.state;
                ++smoke.receiptReads;
                child.write(request.frame);
            } else if (smoke.phase === 12 && !smoke.host.reviewFlow) {
                const receipt = smoke.reviewView.receipt;
                if (!smoke.check(smoke.host.startupLocked && smoke.host.session.unresolved
                    && smoke.reviewView.unknownReviewId === null && !smoke.reviewView.canAcknowledge
                    && (smoke.ackTrial === "EOF" ? receipt === null
                        : !!receipt && Host.equal(receipt,smoke.savedReceipt)
                            && Host.equal(receipt.review,smoke.reviewedEvidence)),
                    "exact historical acknowledgment or missing receipt")) return;
                smoke.phase = 13;
                recoveryPane.requestRead("LOCAL_ACTION",smoke.actionId);
                if (!smoke.check(smoke.reads === 5,"final exact preparation lookup")) return;
            } else if (smoke.phase === 13 && recoveryPane.localView) {
                if (!smoke.check(recoveryPane.localView.record.state === "PREPARED"
                    && recoveryPane.localView.record.resultId === null && smoke.host.startupLocked
                    && smoke.host.session.unresolved && smoke.commits === 0
                    && smoke.writes === 1 && smoke.reviewWrites === 1 && smoke.receiptReads === 1,
                    "persistent preparation unchanged")) return;
                smoke.phase = 14;
                smoke.dropping = true;
                child.stdinEnabled = false;
            } else if (smoke.phase === 14 && smoke.exited) {
                if (!smoke.check(watchdog.activeCount === 0 && smoke.host.startupLocked
                    && smoke.host.session.unresolved && smoke.reviewView.receipt === null,
                    "final disconnect clears live review view")) return;
                console.log("QUEUE_R3_ACK_PASS // "+smoke.ackTrial);
                console.log("QUEUE_R3_STAGED_PASS // EOF");
                console.log("QUEUE_R3_RECOVERY_PASS // native explicit acknowledgment trial");
                smoke.done = true;
                Qt.quit();
            } else if (smoke.phase === 7 && smoke.exited) {
                recoveryPane.requestRead("INVENTORY",16);
                if (!smoke.check(smoke.reads === 4 && !recoveryPane.canRead && recoveryPane.view === null
                    && recoveryPane.localView === null,"EOF refuses reads and clears pane")) return;
                if (!smoke.check(smoke.recovery.inventory === null && smoke.recovery.localAction === null
                    && smoke.host.startupLocked && smoke.host.session.unresolved && smoke.writes === 1,"EOF clears recovery")) return;
                if(!smoke.check(smoke.watchdogTrips===(smoke.timeoutTrial?1:0)
                    && watchdog.activeCount===0,"exact deadline count and no idle timers"))return;
                if(smoke.stagedTrial) {
                    if (!smoke.check(smoke.commits === (smoke.stagedTrial === "EOF" ? 0 : 1),"staged commit count")) return;
                    console.log("QUEUE_R3_STAGED_PASS // "+smoke.stagedTrial);
                }
                if(smoke.timeoutTrial)console.log("QUEUE_R3_WATCHDOG_PASS // delayed committed reply recovered, no replay");
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
