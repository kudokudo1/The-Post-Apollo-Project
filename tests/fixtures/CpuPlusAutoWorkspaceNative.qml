import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as Presentation
import "widgets/cpuplus/CpuPlusQueueHistory.js" as History
import "widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery
import "services/memory/MemoryQueueSessionHost.js" as Host

// Disposable workspace composition, independent of DOC 4 watchdog fixture.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")==="CI_DISPOSABLE_ONLY"
    property var host: Host.initial(Consumer)
    property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000001"
    property string resultId: ""
    property string oldOwner: ""
    property int phase: 0
    property int ticks: 0
    property int reads: 0
    property int writes: 0
    property bool dropping: false
    property bool exited: false
    property bool done: false
    property bool mounted: true
    function check(ok,label) {
        if (!ok) {
            console.error("QUEUE_WORKSPACE_FAIL // "+label+" // "+host.failure);
            done=true; child.running=false; Qt.quit();
        }
        return ok;
    }
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const c of item.children||[]) {
            const v=find(c,name); if(v)return v;
        }
        return null;
    }
    function launch(generation) {
        host=Host.start(host,Consumer,generation);
        exited=false; dropping=false; child.stdinEnabled=true; child.running=true;
    }
    function receive(line) {
        if(done||dropping)return;
        let p;
        try {p=JSON.parse(line);} catch(_) {check(false,"invalid fixture packet");return;}
        if(phase===3&&p.kind==="ACTION") {
            if(!check(p.disposition==="REPORTED"&&p.result.request.id,"durable commit before lost reply"))return;
            resultId=p.result.request.id;
            dropping=true; child.running=false;
            return;
        }
        host=Host.feed(host,line+"\n",Consumer,Presentation.project,History.project,
            host.generation,Recovery.project,Recovery.row);
        check(host.phase!=="FAILED","canonical feed "+p.kind);
    }
    function send(req,mutation) {
        if(!check(!!req.frame,"explicit accepted frame"))return;
        host=req.state;
        if(mutation)++writes; else ++reads;
        child.write(req.frame);
    }
    Process {
        id: child
        command: ["python3","-B",Quickshell.env("POST_APOLLO_QUEUE_PIPE_CHILD")]
        stdinEnabled: true
        stdout: SplitParser { onRead: data=>smoke.receive(data) }
        stderr: SplitParser { onRead: data=>console.log("QUEUE_WORKSPACE_CHILD // "+data) }
        onExited: (code,status)=>{
            smoke.host=Host.stop(smoke.host,Consumer,"CHILD_EXIT",smoke.host.generation);
            smoke.exited=true;
            if(!smoke.done&&!smoke.dropping)smoke.check(false,"unexpected exit");
        }
    }
    Window {
        width: 320
        height: 620
        visible: smoke.armed
        Item {
            anchors.fill: parent
            Column {
                id: top
                anchors.top: parent.top
                width: parent.width
            }
            Column {
                id: bottom
                anchors.bottom: parent.bottom
                width: parent.width
            }
            Flickable {
                id: middle
                anchors.top: top.bottom
                anchors.bottom: bottom.top
                width: parent.width
                clip: true
                contentWidth: width
                contentHeight: workspace.item?workspace.item.implicitHeight:0
                Loader {
                    id: workspace
                    width: middle.width
                    active: smoke.mounted
                    sourceComponent: CpuPlusAutoWorkspace {
                        headerTarget: top
                        footerTarget: bottom
                        observedDiskKiB: 25165816
                        capacityTargetGiB: 16
                        hostState: smoke.host
                        onSectionChangedByUser: middle.contentY=0
                        onIntentConfirmed: intent=>smoke.send(Host.confirm(smoke.host,intent,smoke.actionId,Consumer),true)
                        onHistoryReadRequested: id=>smoke.send(Host.readHistory(smoke.host,id),false)
                        onRecoveryReadRequested: (kind,value)=>smoke.send(Host.readRecovery(smoke.host,kind,value),false)
                    }
                }
            }
        }
    }
    Timer {
        interval: 50
        repeat: true
        running: smoke.armed&&!smoke.done
        onTriggered: {
            if(++smoke.ticks>280){smoke.check(false,"timeout "+smoke.phase);return;}
            const w=workspace.item;
            const requests=smoke.find(w,"cpuplusQueuePane");
            const history=smoke.find(w,"cpuplusQueueHistoryPane");
            const recovery=smoke.find(w,"cpuplusQueueRecoveryPane");
            if(w) {
                const nav=smoke.find(bottom,"cpuplusAutoNavigation");
                if(!nav)return;
                if(!smoke.check(middle.height>0&&nav.visible,"fixed rails and positive viewport"))return;
            }
            if(smoke.phase===0&&requests&&smoke.host.session.status) {
                if(!smoke.check(smoke.host.startupLocked&&smoke.host.session.status.state==="IDLE REPORTED","startup locked"))return;
                smoke.oldOwner=smoke.host.session.ownerId;
                requests.expiryText="2099-01-01 00:00";
                requests.prepareIntent("QUEUE");
                if(!smoke.check(!requests.preparation,"no startup mutation"))return;
                w.selectSection("RECOVERY"); smoke.phase=1;
            } else if(smoke.phase===1&&recovery) {
                recovery.requestRead("INVENTORY",16);
                recovery.requestRead("INVENTORY",16);
                if(!smoke.check(smoke.reads===1&&smoke.host.recoveryRead,"single inventory read"))return;
                smoke.phase=2;
            } else if(smoke.phase===2&&recovery&&recovery.view) {
                if(!smoke.check(recovery.view.recent.length===0&&smoke.host.startupLocked,"empty inventory never unlocks"))return;
                // Fixture-only injection matching the merged DOC 4 native trial.
                smoke.host=Object.assign({},smoke.host,{startupLocked:false});
                w.selectSection("REQUESTS"); smoke.phase=20;
            } else if(smoke.phase===20&&requests) {
                requests.expiryText="2099-01-01 00:00";
                requests.prepareIntent("QUEUE");
                if(!smoke.check(!!requests.preparation,"fixture-only prepare"))return;
                smoke.phase=3;
                requests.confirmIntent(); requests.confirmIntent();
                if(!smoke.check(smoke.writes===1&&smoke.host.session.pending,"one durable request"))return;
                smoke.mounted=false;
            } else if(smoke.phase===3&&smoke.exited) {
                if(!smoke.check(!workspace.item&&smoke.host.session.unresolved&&smoke.host.startupLocked&&smoke.writes===1,
                    "lost reply retained outside destroyed workspace"))return;
                smoke.launch(2); smoke.phase=4;
            } else if(smoke.phase===4&&smoke.host.session.status) {
                if(!smoke.check(smoke.host.session.ownerId!==smoke.oldOwner&&smoke.host.session.status.requestId===smoke.resultId
                    &&smoke.host.session.unresolved&&smoke.host.startupLocked,"new owner retains unresolved request"))return;
                smoke.mounted=true; smoke.phase=5;
            } else if(smoke.phase===5&&requests) {
                requests.prepareIntent("CANCEL");
                if(!smoke.check(!requests.preparation,"cancel locked after reopen"))return;
                w.selectSection("HISTORY"); smoke.phase=6;
            } else if(smoke.phase===6&&history) {
                history.lookupText=smoke.resultId; history.requestRead(); history.requestRead();
                if(!smoke.check(smoke.reads===2&&smoke.host.historyRead,"one exact history read"))return;
                smoke.phase=7;
            } else if(smoke.phase===7&&history&&history.detail) {
                if(!smoke.check(history.detail.requestId===smoke.resultId&&history.detail.state==="QUEUED"
                    &&history.detail.outcome==="UNVERIFIED"&&!history.detail.canExecute,"exact history rendered"))return;
                w.selectSection("RECOVERY"); smoke.phase=8;
            } else if(smoke.phase===8&&recovery) {
                recovery.requestRead("INVENTORY",16);
                if(!smoke.check(smoke.reads===3&&smoke.host.recoveryRead,"recovery read after history"))return;
                smoke.phase=9;
            } else if(smoke.phase===9&&recovery&&recovery.view) {
                if(!smoke.check(recovery.view.recent.length===1&&recovery.view.recent[0].actionId===smoke.actionId
                    &&recovery.view.recent[0].resultId===smoke.resultId&&recovery.view.recent[0].state==="COMMITTED"
                    &&smoke.host.startupLocked,"committed inventory rendered"))return;
                recovery.requestRead("LOCAL_ACTION",smoke.actionId); smoke.phase=10;
            } else if(smoke.phase===10&&recovery&&recovery.localView) {
                if(!smoke.check(recovery.localView.record&&recovery.localView.record.resultId===smoke.resultId
                    &&smoke.reads===4&&smoke.writes===1,"exact local action rendered"))return;
                smoke.phase=11; smoke.dropping=true; child.stdinEnabled=false;
            } else if(smoke.phase===11&&recovery&&smoke.exited) {
                recovery.requestRead("INVENTORY",16);
                if(!smoke.check(!recovery.canRead&&!recovery.localView&&!recovery.view&&smoke.reads===4
                    &&smoke.writes===1&&smoke.host.startupLocked&&smoke.host.session.unresolved,"EOF clears view, no retry"))return;
                console.log("QUEUE_WORKSPACE_PASS // actual pipe, destroyed/reopened workspace, history, recovery, EOF");
                smoke.done=true; Qt.quit();
            }
        }
    }
    Component.onCompleted: {if(!armed)Qt.quit();else launch(1);}
}
