import QtQuick
import Quickshell
import Quickshell.Io
import "DiagnosticWorkflowDefaults.js" as Defaults
import "DiagnosticWorkflowCatalog.js" as Catalog
import "DiagnosticCalibration.js" as Calibration
import "DiagnosticWorkflowReceipt.js" as Receipt

// Single catalog transport. Owner mounts once, loads explicitly on demand.
// A successful storage receipt is required before publishing edits.
Scope {
    id: store
    property var document: null
    property var expected: null
    readonly property var rows: document ? document.rows : []
    readonly property var favorites: rows.filter(row=>row.favorite)
    property string status: "NOT LOADED"
    property bool busy: false
    property bool faulted: false
    readonly property bool ready: status==="READY" && !busy && !faulted
    property var submitted: null
    property string frame: ""
    property string output: ""
    property bool stdoutSeen: false
    property bool exitSeen: false
    property bool exitOk: false
    signal completed(string outcome)
    function calibration() {
        return {workshopDraftFromPlan:plan=>Calibration.workshopDraftFromPlan(plan),
                workshopPlanFromDraft:draft=>Calibration.workshopPlanFromDraft(draft)};
    }
    function validated(doc) {
        return Catalog.validatedCatalog(doc,Defaults.initialWorkflowFavorites(),calibration());
    }
    function seed() {
        return Catalog.newCatalog(Defaults.initialWorkflowFavorites(),calibration());
    }
    function load() { return invoke({action:"load"}); }
    function edit(change) {
        if(!ready)return false;
        const next=Catalog.editCatalog(document,change,Defaults.initialWorkflowFavorites(),calibration());
        if(!next)return false;
        return invoke({action:"save",expected:expected,document:next});
    }
    function invoke(request) {
        if(busy||faulted||worker.running)return false;
        const frozen=JSON.stringify(request);
        if(frozen.length>132096)return false;
        submitted=JSON.parse(frozen);
        frame=frozen+"\n";
        output="";
        stdoutSeen=false;
        exitSeen=false;
        exitOk=false;
        busy=true;
        status=request.action==="save"?"SAVING":"LOADING";
        deadline.restart();
        // Ignore PYTHON environment and user site. The trusted script directory
        // is required for the helper's sibling imports (unlike -I).
        worker.exec(["/usr/bin/timeout","--kill-after=2s","10s","/usr/bin/python3",
            "-E","-s","-B",Quickshell.shellPath("scripts/cpuplus_diagnostic_workflow_catalog.py")]);
        return true;
    }
    function finish() {
        if(!busy||!stdoutSeen||!exitSeen)return;
        deadline.stop();
        let result=null;
        if(exitOk&&output.length<=66560){
            try {
                result=Receipt.qualifyReceipt(JSON.parse(output),submitted,
                    doc=>store.validated(doc),()=>store.seed());
            }catch(error){}
        }
        document=result?result.document:null;
        expected=result?result.expected:null;
        status=result?result.status:"FAILED";
        submitted=null;
        output="";
        frame="";
        busy=false;
        completed(status);
    }
    Timer {
        id: deadline
        interval: 15000
        repeat: false
        onTriggered: {
            if(!store.busy)return;
            store.faulted=true;
            store.document=null;
            store.expected=null;
            store.submitted=null;
            store.output="";
            store.frame="";
            store.status="UNAVAILABLE // RESTART REQUIRED";
            store.busy=false;
            worker.running=false;
            store.completed(store.status);
        }
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if(store.busy&&store.frame){
                worker.write(store.frame);
                store.frame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                if(!store.busy)return;
                store.output=this.text;
                store.stdoutSeen=true;
                store.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,exitStatus) {
            if(!store.busy)return;
            store.exitOk=code===0&&exitStatus===0;
            store.exitSeen=true;
            store.finish();
        }
    }
}
