import QtQuick
import Quickshell
import Quickshell.Io
import "services/memory" as Memory
import "services/notifications" as Hub
import "services/memory/MemoryQueueSessionHost.js" as Host
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer

ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")==="CI_DISPOSABLE_ONLY"
    readonly property string trial: Quickshell.env("POST_APOLLO_QUEUE_HUB_TRIAL") || ""
    property int phase: 0
    property int ticks: 0
    property int offers: 0
    property int writes: 0
    property bool done: false
    property string requestId: ""
    property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000041"
    property string cancelId: "c23683a9-b2ab-4a2c-87ce-000000000042"
    property string forgedId: "c23683a9-b2ab-4a2c-87ce-000000000043"
    readonly property var hub: Hub.NotificationsService
    Memory.MemoryQueueHubBinding { id: binding }
    function check(ok,label) {
        if (!ok) {
            console.error("QUEUE_HUB_NATIVE_FAIL // "+label+" // "+binding.lastOutcome);
            done=true; child.running=false; Qt.quit();
        }
        return ok;
    }
    function send(kind,id) {
        const current=binding.hostState;
        const intent=Consumer.prepare(current.session,kind,kind==="QUEUE"?16:null,
            kind==="QUEUE"?Math.floor(Date.now()/1000)+180:null).prepared;
        const next=Host.confirm(current,intent,id,Consumer);
        if (!check(!!next.frame && binding.publishState(next.state),"explicit action transition"))return;
        ++writes;
        child.write(next.frame);
    }
    function receive(line) {
        if (done) return;
        let p;
        try { p=JSON.parse(line); } catch (_) { check(false,"invalid child packet");return; }
        const g=binding.hostState.generation;
        if (!check(binding.receive(line,g),"canonical native receive "+p.kind))return;
        if (p.kind==="NOTIFICATION") {
            ++offers;
            const expected=trial==="BLOCK"?"BLOCKED":"HISTORY_OBSERVED";
            if (!check(binding.lastOutcome===expected,"actual Hub result "+p.notice.kind))return;
            const historyIndex=hub.indexOfNotification(hub.notifications,p.notice.event_id);
            const activeIndex=hub.indexOfNotification(hub.activeNotifications,p.notice.event_id);
            if (!check((historyIndex>=0)===(trial!=="BLOCK")
                && (activeIndex>=0)===(trial==="NORMAL"),"actual Hub history and suppression"))return;
            if (historyIndex>=0 && !check(hub.notifications.get(historyIndex).sourceId==="cpu-plus-memory-queue",
                "actual singleton source identity"))return;
            const count=hub.notifications.count;
            if (!check(!binding.receive(line,g+1),"stale generation ignored"))return;
            if (!check(binding.receive(line,g) && binding.lastOutcome==="NOT_OFFERED"
                && hub.notifications.count===count,"duplicate not offered"))return;
            if (phase===2 && p.notice.kind==="ATTENTION") {
                requestId=p.notice.request_id;
                phase=3;
            } else if (phase===4 && p.notice.kind==="CANCELLED") {
                if (!check(p.notice.request_id===requestId,"terminal correlation"))return;
                phase=5;
            } else check(false,"unexpected native notification phase");
        }
    }
    Process {
        id: child
        command: ["/usr/bin/python3","-B",Quickshell.env("POST_APOLLO_QUEUE_PIPE_CHILD")]
        stdinEnabled: true
        stdout: SplitParser { onRead: data=>smoke.receive(data) }
        stderr: SplitParser { onRead: data=>console.log("QUEUE_HUB_CHILD // "+data) }
        onExited: (code,status)=>{
            if (!smoke.done && smoke.phase===6 && code===0 && status===0) {
                if (!smoke.check(smoke.offers===2 && smoke.writes===2,"exact native offer count"))return;
                console.log("QUEUE_HUB_NATIVE_PASS // "+smoke.trial);
                smoke.done=true; Qt.quit();
            } else if (!smoke.done) smoke.check(false,"unexpected owner exit");
        }
    }
    Timer {
        interval:50
        repeat:true
        running:smoke.armed && !smoke.done
        onTriggered:{
            if (++smoke.ticks>300){smoke.check(false,"timeout phase "+smoke.phase);return;}
            if (smoke.phase===0 && smoke.hub.historyReady && smoke.hub.policyReady
                && ["ready","new","saved","saving"].includes(smoke.hub.historyStatus)
                && ["ready","new","saved","saving"].includes(smoke.hub.policyStatus)) {
                if (!smoke.check(smoke.hub.notifications.count===0 && smoke.hub.activeNotifications.count===0,
                    "private empty Hub"))return;
                if (smoke.trial==="BLOCK") {
                    if (!smoke.check(smoke.hub.setBlocked("cpu-plus-memory-queue","cpu-plus-memory-queue","CPU++",true),"set isolated BLOCK"))return;
                } else if (smoke.trial==="DND") {
                    if (!smoke.check(smoke.hub.setDnd("cpu-plus-memory-queue","cpu-plus-memory-queue","CPU++",true),"set isolated DND"))return;
                }
                if (!smoke.check(binding.publishState(Host.start(binding.hostState,Consumer,1,"LEGACY",false,false,true)),
                    "start explicit notify-only host"))return;
                smoke.phase=1;child.running=true;
            } else if (smoke.phase===1 && binding.hostState.session.status?.state==="IDLE REPORTED") {
                const s=binding.hostState, now=Date.now();
                const forged={version:1,kind:"NOTIFICATION",owner_id:s.session.ownerId,can_execute:false,
                    status_sequence:s.sequence,notice:{version:1,event_id:"apollo-cpu-memory-"+smoke.forgedId+"-cancelled",
                    request_id:smoke.forgedId,kind:"CANCELLED",code:"CANCELLED",observed_at:Math.floor(now/1000),
                    target_gib:16,original_actual_kib:25165816,delivery_state:"ATTEMPT_RESERVED",can_execute:false,
                    checked_at_ms:now,valid_before_wall_ms:now+5000}};
                if (!smoke.check(binding.receive(JSON.stringify(forged),1)
                    && binding.lastOutcome==="TERMINAL_UNCORRELATED" && smoke.hub.notifications.count===0,
                    "uncorrelated terminal not offered"))return;
                // Fixture-only reviewed startup injection; no production unlock.
                binding.publishState(Object.assign({},binding.hostState,{startupLocked:false}));
                smoke.phase=2;smoke.send("QUEUE",smoke.actionId);
            } else if (smoke.phase===3) {
                smoke.phase=4;smoke.send("CANCEL",smoke.cancelId);
            } else if (smoke.phase===5) {
                smoke.phase=6;child.stdinEnabled=false;
            }
        }
    }
    Component.onCompleted:{
        if (!armed || !["NORMAL","BLOCK","DND"].includes(trial))Qt.quit();
    }
}
