import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as QueueView

// Disposable real Quickshell Process transport and actual DOC 2 pane.
// This host is a fixture only, not a production singleton.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE") === "CI_DISPOSABLE_ONLY"
    property var session: Consumer.initial()
    property var context: null
    property var detail: null
    property string firstId: ""
    property string firstOwner: ""
    property string replacementId: ""
    property int phase: 0
    property int sends: 0
    property int ticks: 0
    property bool dropping: false
    property bool exited: false
    property bool done: false
    property bool hello: false
    property var lastReply: null
    function check(ok, message) {
        if (!ok) {
            console.error("QUEUE_R3_NATIVE_FAIL // " + message);
            done = true;
            child.running = false;
            Qt.quit();
        }
        return ok;
    }
    function setSession(next, projection) {
        session = next;
        context = next.status ? {state:next,projection:projection} : null;
    }
    function receive(line) {
        if (done || dropping) return;
        if (!check(line.length < 16384, "bounded output")) return;
        let packet;
        try { packet = JSON.parse(line); } catch (_) { check(false,"JSON parse"); return; }
        if (!check(packet.version === 1 && packet.can_execute === false,"packet authority")) return;
        if (packet.kind === "HELLO") {
            if (!check(!hello && /^[0-9a-f-]{36}$/.test(packet.owner_id),"HELLO epoch")) return;
            hello = true;
            setSession(Consumer.connect(session,packet.owner_id),null);
            return;
        }
        if (!check(hello && packet.owner_id === session.ownerId,"owner binding")) return;
        if (packet.kind === "INVALIDATE") {
            setSession(Consumer.timeout(session),null);
        } else if (packet.kind === "STATUS") {
            const next = Consumer.acceptStatus(session,packet,QueueView.project);
            if (!check(next.status && !next.status.canExecute
                && next.status.outcome === "UNVERIFIED","actual projector accepts status")) return;
            setSession(next,packet.projection);
        } else if (packet.kind === "ACTION") {
            if (!check(packet.result && packet.result.adjustment_outcome === "UNVERIFIED"
                && packet.result.can_execute === false && !line.includes("inode")
                && !line.includes("device"),"reduced action result")) return;
            lastReply = packet;
            if (phase === 2) {
                // Deliberately lose a reply after the fixture's durable replace.
                // Discard it rather than advancing the consumer; stop child.
                replacementId = packet.result.request.id;
                dropping = true;
                child.running = false;
                return;
            }
            setSession(Consumer.acceptAction(session,packet),null);
            if (!check(!session.pending && !session.unresolved && !session.status,
                "correlated reply invalidates pending")) return;
        } else if (packet.kind === "DETAIL") {
            if (!check(packet.detail.adjustment_outcome === "UNVERIFIED"
                && !line.includes("inode") && !line.includes("device")
                && !line.includes('"receipt"'),"reduced history")) return;
            detail = packet.detail;
        } else {
            check(false,"unexpected packet " + packet.kind);
        }
    }
    function submit(intent) {
        // Fixture host reproduces the explicit host-side confirmation boundary.
        if (!check(context && session.status && !session.pending && !session.unresolved,
            "host session usable")) return;
        const prepared = Consumer.prepare(session,intent.kind,intent.targetGiB,intent.expiresAt);
        if (!check(prepared.prepared && ["ownerId","statusSequence","actionSequence","kind",
            "expectedId","targetGiB","expiresAt"].every(k=>prepared.prepared[k] === intent[k]),
            "host revalidates frozen intent")) return;
        // Unique deterministic UUIDs for this test only, not production generation.
        const id = "c23683a9-b2ab-4a2c-87ce-" + String(++sends).padStart(12,"0");
        const submitted = Consumer.submit(prepared,id);
        if (!check(submitted.message && submitted.state.pending,"pending before write")) return;
        setSession(submitted.state,null);
        child.write(JSON.stringify({version:1,kind:"ACTION",message:submitted.message}) + "\n");
    }
    function confirm(kind) {
        pane.prepareIntent(kind);
        if (!check(pane.preparation && pane.preparation.kind === kind,"prepare " + kind)) return;
        pane.confirmIntent();
        pane.confirmIntent(); // second activation cannot emit a second action
    }
    Process {
        id: child
        command: ["python3","-B",Quickshell.env("POST_APOLLO_QUEUE_PIPE_CHILD")]
        stdinEnabled: true
        stdout: SplitParser { onRead: data => smoke.receive(data) }
        stderr: SplitParser { onRead: data => console.log("QUEUE_R3_CHILD // " + data) }
        onExited: (exitCode, exitStatus) => {
            smoke.exited = true;
            smoke.hello = false;
            smoke.setSession(Consumer.disconnect(smoke.session),null);
            if (!smoke.done && !smoke.dropping && smoke.phase !== 5)
                smoke.check(false,"unexpected child exit " + exitCode);
        }
    }
    Window {
        visible: smoke.armed
        width: 500
        height: 900
        CpuPlusQueuePane {
            id: pane
            width: parent.width
            observedDiskKiB: 25165816
            capacityTargetGiB: 16
            actionContext: smoke.context
            onIntentConfirmed: intent => smoke.submit(intent)
        }
    }
    Timer {
        interval: 50
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 240) { smoke.check(false,"timeout phase " + smoke.phase); return; }
            if (smoke.phase === 0 && smoke.session.status) {
                if (!smoke.check(smoke.session.status.state === "IDLE REPORTED","initial idle")) return;
                smoke.firstOwner = smoke.session.ownerId;
                pane.expiryText = "2099-01-01 00:00";
                smoke.phase = 1;
                smoke.confirm("QUEUE");
            } else if (smoke.phase === 1 && smoke.session.status && smoke.session.status.requestId) {
                if (!smoke.check(smoke.sends === 1 && smoke.session.status.state === "UNKNOWN"
                    && smoke.session.status.code === "OBSERVATION_UNAVAILABLE","queued without fake readiness")) return;
                smoke.firstId = smoke.session.status.requestId;
                pane.expiryText = "2099-01-02 00:00";
                smoke.phase = 2;
                smoke.confirm("REPLACE");
            } else if (smoke.phase === 2 && smoke.exited) {
                if (!smoke.check(smoke.session.unresolved && !smoke.context && smoke.sends === 2
                    && smoke.replacementId !== smoke.firstId,"lost replace reply locks out UI")) return;
                pane.prepareIntent("CANCEL");
                if (!smoke.check(!pane.preparation,"disconnected refusal")) return;
                // Explicit fixture reconnect after exit; no automatic resend.
                smoke.phase = 3;
                smoke.dropping = false;
                smoke.exited = false;
                child.running = true;
            } else if (smoke.phase === 3 && smoke.session.status) {
                if (!smoke.check(smoke.session.ownerId !== smoke.firstOwner
                    && smoke.session.status.requestId === smoke.replacementId
                    && smoke.session.unresolved && smoke.sends === 2,"durable replacement / new epoch")) return;
                pane.prepareIntent("CANCEL");
                if (!smoke.check(!pane.preparation,"unresolved refusal")) return;
                smoke.phase = 4;
                child.write(JSON.stringify({version:1,kind:"HISTORY",owner_id:smoke.session.ownerId,
                    request_id:smoke.firstId}) + "\n");
            } else if (smoke.phase === 4 && smoke.detail) {
                if (!smoke.check(smoke.detail.request.id === smoke.firstId
                    && smoke.detail.request.state === "REPLACED"
                    && smoke.detail.request.replaced_by === smoke.replacementId,"historical reconciliation")) return;
                smoke.setSession(Consumer.acknowledgeReconciliation(smoke.session),smoke.context.projection);
                smoke.phase = 5;
                smoke.confirm("CANCEL");
            } else if (smoke.phase === 5 && smoke.session.status && smoke.session.status.state === "IDLE REPORTED") {
                if (!smoke.check(smoke.sends === 3 && smoke.lastReply.result.request.state === "CANCELLED"
                    && !smoke.session.unresolved,"cancel and idle")) return;
                smoke.phase = 6;
                smoke.dropping = true;
                child.stdinEnabled = false;
            } else if (smoke.phase === 6 && smoke.exited) {
                if (!smoke.check(!smoke.context && !smoke.session.status && smoke.sends === 3,
                    "EOF invalidates host")) return;
                console.log("QUEUE_R3_NATIVE_PASS // actual QML confirmation, pipe, durable replacement, history, cancel, EOF");
                smoke.done = true;
                Qt.quit();
            }
        }
    }
    Component.onCompleted: {
        if (!armed) Qt.quit();
        else child.running = true;
    }
}
