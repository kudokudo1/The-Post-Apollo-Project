import QtQuick
import "../notifications" as Hub
import "MemoryQueueSessionHost.js" as Host
import "MemoryQueueNotificationAdapter.js" as Adapter
import "../../widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "../../widgets/cpuplus/CpuPlusQueuePresentation.js" as Presentation
import "../../widgets/cpuplus/CpuPlusQueueHistory.js" as History
import "../../widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery

// Unmounted desktop binding. Uses the existing Hub singleton, not a second
// service or poller. The trusted process wrapper supplies complete bounded
// lines and publishes explicit Host transitions before transmitting frames.
// SplitParser upstream allocation is a separate launcher obligation.
QtObject {
    id: root
    property var hostState: Host.initial(Consumer)
    property bool busy: false
    property string lastOutcome: "NONE"
    property var terminal: null
    function publishState(next) {
        if (busy || !next || !next.session || !Number.isSafeInteger(next.generation))
            return false;
        busy=true;
        try {
            terminal=null;
            lastOutcome="NONE";
            hostState=next;
            return true;
        } finally { busy=false; }
    }
    function receive(line,generation) {
        if (busy || generation!==hostState.generation)
            return false;
        busy=true;
        try {
            const prior=hostState;
            let packet=null;
            if (typeof line==="string" && line.length>0 && line.length<16384
                && !/[\r\n]/.test(line)) {
                try { packet=JSON.parse(line); } catch (_) {}
            }
            if (!packet) {
                terminal=null;
                hostState=Host.stop(prior,Consumer,"INVALID_HUB_LINE",generation);
                lastOutcome="INVALID_LINE";
                return false;
            }
            // Collect, do not deliver inside Host.feed. Publish the returned
            // state before any Hub model signal can reenter the wrapper.
            let notice=null;
            const next=Host.feed(prior,line+"\n",Consumer,Presentation.project,History.project,
                generation,Recovery.project,Recovery.row,n=>{notice=n;});
            if (next.phase==="FAILED") {
                terminal=null;
                hostState=next;
                lastOutcome="HOST_FAILED";
                return false;
            }
            if (packet.kind==="ACTION") {
                terminal=null;
                const pending=prior.session.pending;
                const r=packet.result?.request;
                const expected=pending?.kind==="CANCEL"?"CANCELLED":pending?.kind==="EXPIRE"?"EXPIRED":null;
                if (pending && expected && next.sequence===packet.sequence && !next.session.pending
                    && next.session.feedback==="REPORTED // FRESH STATUS REQUIRED"
                    && packet.action_id===pending.action_id && packet.action_sequence===pending.action_sequence
                    && packet.disposition==="REPORTED" && packet.result?.notification_error===null
                    && Host.exact(r,["id","state","target_gib","expires_at"])
                    && r.id===pending.expected_request_id && r.state===expected
                    && Number.isSafeInteger(r.target_gib) && r.target_gib>=4 && r.target_gib<=64
                    && r.target_gib%4===0 && Host.positive(r.expires_at)) {
                    terminal={generation,requestId:r.id,kind:r.state,targetGiB:r.target_gib,statusSequence:null};
                }
            } else if (packet.kind==="STATUS" && terminal) {
                if (terminal.statusSequence!==null || next.projection?.status.state!=="IDLE"
                    || next.projection?.status.request_id!==null)
                    terminal=null;
                else terminal=Object.assign({},terminal,{statusSequence:next.sequence});
            } else if (packet.kind!=="INVALIDATE" && packet.kind!=="NOTIFICATION") {
                terminal=null;
            }
            hostState=next;
            if (packet.kind==="NOTIFICATION") {
                lastOutcome="NOT_OFFERED";
                const evidence=terminal;
                terminal=null;
                if (!notice) return true;
                if (["CANCELLED","EXPIRED"].includes(notice.kind)
                    && (!evidence || evidence.generation!==generation
                        || evidence.statusSequence!==packet.status_sequence
                        || evidence.requestId!==notice.request_id || evidence.kind!==notice.kind
                        || evidence.targetGiB!==notice.target_gib)) {
                    lastOutcome="TERMINAL_UNCORRELATED";
                    return true;
                }
                // No packet retention or retry. A reserved offer is not a
                // popup, persistence or operator-read receipt.
                try { lastOutcome=Adapter.offer(Hub.NotificationsService,notice,Date.now()); }
                catch (_) { lastOutcome="OFFER_OUTCOME_UNKNOWN"; }
            }
            return true;
        } finally { busy=false; }
    }
}
