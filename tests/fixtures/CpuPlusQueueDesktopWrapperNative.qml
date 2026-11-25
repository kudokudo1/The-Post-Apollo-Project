import QtQuick
import Quickshell
import "services/memory" as Memory

ShellRoot {
    id: smoke
    readonly property string trial: Quickshell.env("POST_APOLLO_WRAPPER_TRIAL") || ""
    readonly property string rootPath: Quickshell.env("POST_APOLLO_WRAPPER_ROOT") || ""
    readonly property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000062"
    property int step: 0
    property int ticks: 0
    property bool done: false
    Memory.MemoryQueueDesktopSession {
        id: session
        pythonPath: "/usr/bin/python3"
        ownerPath: smoke.rootPath+"/child.py"
        helperPath: smoke.rootPath+"/helper.py"
        checkpointDirectory: smoke.rootPath+"/checkpoint"
    }
    function check(ok,label) {
        if (!ok) {
            console.error("R6H_FAIL // "+trial+" // "+label+" // "+session.phase+" // "+session.failure);
            done=true;Qt.quit();
        }
        return ok;
    }
    Timer {
        interval: 25
        repeat: true
        running: !smoke.done
        onTriggered: {
            if (++smoke.ticks>1200 || session.phase==="FAILED"){smoke.check(false,"deadline or failure");return;}
            if (!smoke.check(session.startupLocked && !session.canExecute,"always locked"))return;
            if (smoke.step===0 && session.phase==="IDLE") {
                if (!smoke.check(!session.advance({}) && session.open() && !session.open(),"explicit single launch"))return;
                smoke.step=1;
            } else if (smoke.step===1 && session.phase==="ACTIVE"
                && session.recoveryContext.hostStatus.phase==="CONNECTED") {
                // HELLO can precede STATUS; only a successful canonical
                // transition moves the fixture to the next stage.
                if (smoke.trial==="LIVE") {
                    if (session.beginReview(smoke.actionId)) smoke.step=2;
                } else if (session.readDisposition(smoke.actionId)) smoke.step=5;
            } else if (smoke.step===2 && session.dispositionContext.canDismiss) {
                const v=session.dispositionContext;
                const selection={reviewId:v.review.review_id,digest:v.review.review_digest,sequence:v.reviewSequence};
                if (!smoke.check(!session.dismiss(Object.assign({},selection,{sequence:selection.sequence+1}))
                    && session.dismiss(selection) && !session.dismiss(selection),"one exact durable dismissal"))return;
                smoke.step=3;
            } else if (smoke.step===3 && session.dispositionContext.receipt) {
                if (!smoke.check(!session.readDisposition(smoke.actionId),"fresh durable LOAD required"))return;
                if (session.close()) smoke.step=4;
            } else if (smoke.step===4 && session.phase==="IDLE") {
                if (!smoke.check(session.open(),"explicit recovery reconnect"))return;
                smoke.step=6;
            } else if (smoke.step===6 && session.phase==="ACTIVE") {
                if (session.readDisposition(smoke.actionId)) smoke.step=5;
            } else if (smoke.step===5 && session.retentionSelection) {
                const s=session.retentionSelection;
                if (!smoke.check(smoke.trial!=="MISSING"
                    && !session.advance(Object.assign({},s,{storageGeneration:s.storageGeneration+1}))
                    && session.advance(s) && !session.advance(s),"one exact retention advance"))return;
                smoke.step=7;
            } else if (smoke.step===5 && smoke.trial==="MISSING"
                && session.dispositionContext.phase==="DISMISS_UNKNOWN" && !session.retentionSelection) {
                if (!smoke.check(!session.advance({}) && session.close(),"missing receipt remains locked"))return;
                smoke.step=8;
            } else if (smoke.step===7 && session.phase==="IDLE") {
                if (!smoke.check(session.storageGeneration===1 && !session.retentionSelection
                    && !session.recoveryContext.hostStatus.unresolved,"fresh locked generation, no auto-launch"))return;
                console.log("R6H_NATIVE_PASS // "+smoke.trial);smoke.done=true;Qt.quit();
            } else if (smoke.step===8 && session.phase==="IDLE") {
                console.log("R6H_NATIVE_PASS // "+smoke.trial);smoke.done=true;Qt.quit();
            }
        }
    }
    Component.onCompleted: {
        if (Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")!=="CI_DISPOSABLE_ONLY"
            || !["LIVE","RECOVERED","MISSING"].includes(trial) || !rootPath.startsWith("/tmp/")) {
            done=true;Qt.quit();
        }
    }
}
