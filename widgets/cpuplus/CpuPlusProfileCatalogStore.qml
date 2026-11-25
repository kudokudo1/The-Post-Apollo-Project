import QtQuick
import Quickshell
import Quickshell.Io
import "CpuPlusProfileCatalog.js" as Catalog

// Event-driven, unprivileged catalog owner. One child per explicit request.
// Lives in the parent memory pane, not the demand-loaded PROF page.
Scope {
    id: root
    objectName: "cpuplusProfileCatalogStore"
    property var document: null
    property bool busy: false
    property bool faulted: false
    property string status: "NOT LOADED"
    property var submitted: null
    property var baseline: null
    property string frame: ""
    property string output: ""
    property bool stdoutSeen: false
    property bool exitSeen: false
    property bool exitOk: false
    readonly property bool ready: !busy && !faulted && document!==null
    function list() {return invoke({action:"list",schema:"post-apollo-cpuplus-profiles-v2"},null);}
    function saveNew(name,targets) {
        if(!ready)return false;
        const request=Catalog.create(document,name,targets);
        return request!==null&&invoke(request,document);
    }
    function changeExisting(request) {
        if(!ready || !request || !["edit","rename","delete"].includes(request.action)
            || Catalog.expectedDocument(document,request)===null)return false;
        return invoke(request,document);
    }
    function invoke(request,base) {
        if(busy||faulted||worker.running)return false;
        baseline=base; submitted=request;
        frame=JSON.stringify(request)+"\n"; output="";
        stdoutSeen=false; exitSeen=false; exitOk=false;
        document=null; busy=true;
        status=request.action==="list"?"LOADING":"SAVING";
        deadline.restart();
        worker.exec(["/usr/bin/timeout","--kill-after=2s","10s","/usr/bin/python3","-I","-B",
            Quickshell.shellPath("scripts/cpuplus_profile_catalog.py")]);
        return true;
    }
    function finish() {
        if(!busy||!stdoutSeen||!exitSeen)return;
        deadline.stop();
        const next=exitOk?Catalog.accepted(output,submitted,baseline):null;
        document=next;
        status=next===null?"NOT CONFIRMED // LOAD LIST BEFORE RETRY"
            : submitted.action==="list"?"READY":submitted.action.toUpperCase()+" CONFIRMED // LOCAL CATALOG ONLY";
        submitted=null; baseline=null; frame=""; output=""; busy=false;
    }
    Timer {
        id: deadline
        interval: 15000
        repeat: false
        onTriggered: {
            if(!root.busy)return;
            root.faulted=true; root.document=null; root.busy=false;
            root.submitted=null; root.baseline=null; root.frame=""; root.output="";
            root.status="OUTCOME UNKNOWN // REOPEN MEMORY AND LOAD LIST";
            worker.running=false;
        }
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: if(root.busy&&root.frame){worker.write(root.frame);root.frame="";}
        stdout: StdioCollector {
            onStreamFinished: {
                if(!root.busy)return;
                root.output=this.text; root.stdoutSeen=true; root.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,exitStatus) {
            if(!root.busy)return;
            root.exitOk=code===0&&exitStatus===0; root.exitSeen=true;root.finish();
        }
    }
}
