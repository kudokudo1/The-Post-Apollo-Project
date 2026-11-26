import QtQuick
import QtQuick.Window
import Quickshell
import "widgets"
import "services/github"

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property int controlIndex: -1
    property string targetPath: ".github/workflows/native-fedora-xvfb-publish.yml"

    function inventory() {
        const rows = [];
        for (let i=0; i<240; i++)
            rows.push({id:i+1,name:"Clock "+i,path:".github/workflows/clock-"+i+".yml",state:"active"});
        rows.push({id:241,name:"Publish qualified native Fedora Xvfb image",path:targetPath,state:"active"});
        return rows;
    }
    QtObject {
        id: remote
        property string repoSlug: "fixture/repository"
        property var workflows: root.inventory()
        property bool available: true
        property bool refreshing: false
        property bool actionBusy: false
        property bool factoryBusy: false
        property string actionKind: ""
        property string actionResult: "READY"
        property string actionTarget: ""
        property var batchStepResults: []
        property int batchStepFailureCount: 0
        property string batchRepository: ""
        property string batchRef: ""
        property var calls: []
        function refresh() { workflows = root.inventory(); }
        function runWorkflow(path, ref) { calls = calls.concat([{path:path,ref:ref,repo:repoSlug}]); }
        function deleteWorkflow(path) { throw Error("unexpected deletion"); }
        function runWorkflowBatch(paths, ref) { throw Error("unexpected queue execution"); }
    }
    WorkflowLibraryStore { id: store; githubService: remote }
    Window {
        width: 1100; height: 620; visible: true
        WorkflowLibraryView {
            id: view
            anchors.fill: parent
            githubService: remote
            libraryStore: store
            onWorkflowSelected: function(index) { root.controlIndex = index; }
        }
    }
    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const hit = find(child,name);
            if (hit) return hit;
        }
        return null;
    }
    function require(ok, message) {
        if (!ok) {
            console.error("GIT_WORKFLOW_LIBRARY_FAIL // " + message);
            Qt.exit(1);
        }
        return ok;
    }
    Timer {
        interval: 100; repeat: true; running: true
        onTriggered: {
            if (++root.ticks > 100) { root.require(false,"timeout at phase "+root.phase); return; }
            const list=root.find(view,"gitWorkflowResults");
            const input=root.find(view,"gitWorkflowSearch");
            if (!list || !input) return;
            if (root.phase===0) {
                if (!root.require(list.count===241,"full inventory")) return;
                list.positionViewAtEnd();
                root.phase=1;
                return;
            }
            if (root.phase===1) {
                if (!root.require(list.contentY>list.originY,"long inventory scrolls")) return;
                input.text="FeDoRa publish";
                root.phase=2;
                return;
            }
            if (root.phase===2) {
                if (!root.require(list.count===1,"search narrows inventory")) return;
                const row=list.itemAtIndex(0);
                if (!row) return;
                const run=root.find(row,"gitWorkflowRun"),control=root.find(row,"gitWorkflowControl"),queue=root.find(row,"gitWorkflowQueue");
                if (!root.require(run && control && queue && run.enabledAction,"actual row controls")) return;
                control.triggered();
                if (!root.require(root.controlIndex===240,"original source index")) return;
                queue.triggered();
                if (!root.require(store.queue.length===1 && store.queue[0].path===root.targetPath,"queue exact path")) return;
                run.triggered();
                if (!root.require(remote.calls.length===0 && run.label==="GO?","first click arms only")) return;
                remote.refresh();
                root.phase=3;
                return;
            }
            if (root.phase===3) {
                const row=list.itemAtIndex(0);
                if (!row) return;
                const run=root.find(row,"gitWorkflowRun");
                if (!root.require(run && run.label==="RUN","refresh clears authorization")) return;
                run.triggered();
                run.triggered();
                if (!root.require(remote.calls.length===1 && remote.calls[0].path===root.targetPath && remote.calls[0].ref==="","exact default-ref dispatch")) return;
                run.triggered();
                remote.repoSlug="fixture/other";
                root.phase=4;
                return;
            }
            if (root.phase===4) {
                const row=list.itemAtIndex(0);
                if (!row) return;
                const run=root.find(row,"gitWorkflowRun");
                if (!root.require(run && run.label==="RUN" && remote.calls.length===1,"repository change clears confirmation")) return;
                input.text="does not exist";
                root.phase=5;
                return;
            }
            if (root.phase===5) {
                if (!root.require(list.count===0,"empty filtered state")) return;
                console.log("GIT_WORKFLOW_LIBRARY_PASS");
                Qt.quit();
            }
        }
    }
}
