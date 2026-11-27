import QtQuick
import QtQuick.Window
import Quickshell
import qs.components
import "widgets"

ShellRoot {
    Window {
        id: lab
        width: 620
        height: 275
        visible: true
        property int stage: 0
        property bool failed: false
        property int previewCalls: 0
        property int executeCalls: 0
        property int dequeueCalls: 0
        property var viewport: null
        property var refreshButton: null
        property var previewButton: null
        property var executeButton: null
        property var dequeuePreview: null
        property var dequeueButton: null

        function require(ok, message) {
            if (!ok) {
                failed = true;
                console.error("QUEUE_NATIVE_FAIL " + message);
                Qt.quit();
            }
            return ok;
        }
        function named(item, name) {
            if (!item) return null;
            if (item.objectName === name) return item;
            for (let i=0; i<item.children.length; ++i) {
                const hit=named(item.children[i],name);
                if (hit) return hit;
            }
            return null;
        }

        QtObject {
            id: ordinary
            property bool busy: false
            property string lastError: ""
            property string phase: "READY"
            property string operation: ""
            signal mutationFinished(bool mutationSucceeded, bool evidenceVerified, string operation, var evidence)
        }
        QtObject {
            id: threads
            property bool busy: false
            property var threads: []
            property string lastError: ""
            property string status: "READY"
            function refresh(repository, number) { return false; }
            function threadAt(index) { return null; }
        }
        QtObject {
            id: threadActions
            property bool busy: false
            property string lastError: ""
            signal mutationFinished(bool mutationSucceeded, bool evidenceVerified, string operation, var evidence)
            signal threadChanged(string repository, int number, string threadId, var evidence)
        }
        QtObject {
            id: queue
            property bool busy: false
            property bool queueAvailable: false
            property string repositorySlug: "fixture/repository"
            property string branchName: "main"
            property string status: "READY"
            property string lastError: ""
            property var entries: []
            property int totalCount: entries.length
            signal refreshed()
            function entryForPullRequest(number) {
                return entries.find(e=>e.pullRequest.number===number) || null;
            }
            function refresh(repository, branch) {
                if (busy) return false;
                repositorySlug=repository;
                branchName=branch;
                busy=true; status="READING"; lastError="";
                return true;
            }
            function finish(available, rows) {
                queueAvailable=available;
                entries=rows;
                busy=false;
                status=available ? "QUEUE READ" : "MERGE QUEUE // NOT CONFIGURED";
                refreshed();
            }
        }
        QtObject {
            id: queueActions
            property bool busy: false
            property string phase: "READY"
            property string status: "MERGE QUEUE // READY"
            property string lastError: ""
            property var preview: ({})
            property string operation: ""
            signal previewReady(var preview)
            signal previewFailed(string detail)
            signal mutationFinished(bool mutationSucceeded, bool evidenceVerified, string operation, var evidence)
            signal queueChanged(string repository, int number, bool queued, var evidence)
            function previewEnqueue(repository, number, head) {
                lab.previewCalls++;
                operation="enqueue"; busy=true; phase="PREVIEW";
                return true;
            }
            function previewDequeue(repository, number) {
                lab.previewCalls++;
                operation="dequeue"; busy=true; phase="PREVIEW";
                return true;
            }
            function finishPreview() {
                preview={action:operation,repository:view.repositorySlug,number:view.pullRequestNumber,
                    baseBranch:view.pullRequestBaseRef,headSha:view.pullRequestHeadSha,pullRequestId:"fixture"};
                busy=false; phase="READY"; previewReady(preview);
            }
            function executeEnqueue() {
                lab.executeCalls++; busy=true; phase="MUTATING"; return true;
            }
            function executeDequeue(confirmed) {
                if (!confirmed) return false;
                lab.dequeueCalls++; busy=true; phase="MUTATING"; return true;
            }
            function finishMutation(verified) {
                busy=false; phase="READY";
                mutationFinished(true,verified,operation,{});
                preview=({});
            }
        }
        GitHubPullRequestControlView {
            id: view
            anchors.fill: parent
            lifecycleService: ordinary
            queueProvider: queue
            queueLifecycleService: queueActions
            threadProvider: threads
            threadLifecycleService: threadActions
            repositorySlug: "fixture/repository"
            pullRequestNumber: 7
            pullRequestTitle: "Disposable queue layout"
            pullRequestState: "OPEN"
            pullRequestBaseRef: "main"
            pullRequestHeadRef: "fixture"
            pullRequestHeadSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            externallyManagedTarget: true
        }

        Timer {
            interval: 160
            repeat: true
            running: !lab.failed
            onTriggered: {
                if(lab.stage===0) {
                    queue.finish(false,[]);
                    view.mode="queue";
                } else if(lab.stage===1) {
                    lab.viewport=lab.named(view,"queueViewport");
                    if(!lab.require(lab.viewport && lab.viewport.clip && lab.viewport.height>0,
                        "bounded native queue viewport")) return;
                    const p=lab.viewport.mapToItem(view,0,lab.viewport.height);
                    if(!lab.require(p.y<=view.height && lab.viewport.footerItem.text.indexOf("NO MERGE QUEUE CONFIGURED")>=0,
                        "no clipping or fabricated queue entries")) return;
                    lab.refreshButton=lab.named(lab.viewport,"queue-refresh");
                    lab.previewButton=lab.named(lab.viewport,"queue-preview-enqueue");
                    lab.executeButton=lab.named(lab.viewport,"queue-execute-enqueue");
                    lab.dequeuePreview=lab.named(lab.viewport,"queue-preview-dequeue");
                    lab.dequeueButton=lab.named(lab.viewport,"queue-execute-dequeue");
                    if(!lab.require(lab.refreshButton && lab.previewButton && lab.executeButton &&
                        lab.dequeuePreview && lab.dequeueButton && !lab.previewButton.enabledAction,
                        "all five controls mounted; unavailable queue protected")) return;
                    lab.refreshButton.triggered();
                } else if(lab.stage===2) {
                    if(!lab.require(lab.refreshButton.loading && !lab.previewButton.loading && queue.busy,
                        "refresh owns only its own bar")) return;
                    queue.finish(true,[]);
                } else if(lab.stage===3) {
                    if(!lab.require(view.completedQueueSuccess && lab.viewport.footerItem.text.indexOf("QUEUE EMPTY")>=0
                        && lab.previewButton.enabledAction && !lab.executeButton.enabledAction,
                        "configured empty queue; verified refresh; preview required")) return;
                    lab.previewButton.triggered();
                } else if(lab.stage===4) {
                    if(!lab.require(lab.previewButton.loading && !lab.executeButton.loading && lab.previewCalls===1,
                        "preview loading belongs to correct button")) return;
                    queueActions.finishPreview();
                } else if(lab.stage===5) {
                    if(!lab.require(view.completedQueueSuccess && lab.executeButton.enabledAction,
                        "matching preview permits execution")) return;
                    lab.executeButton.triggered();
                } else if(lab.stage===6) {
                    if(!lab.require(lab.executeButton.loading && lab.executeCalls===1,
                        "execute loading belongs to correct button")) return;
                    queueActions.finishMutation(false);
                } else if(lab.stage===7) {
                    if(!lab.require(!view.completedQueueSuccess && lab.executeButton.visualPhase==="failure",
                        "unverified mutation cannot complete as success")) return;
                    queue.finish(true,Array.from({length:12},(_,i)=>({position:i+1,stateLabel:"QUEUED",
                        pullRequest:{number:i+7,title:"Fixture entry "+i}})));
                } else if(lab.stage===8) {
                    if(!lab.require(lab.viewport.count===12 && lab.viewport.contentHeight>lab.viewport.height
                        && lab.dequeuePreview.enabledAction,"populated queue scrolls inside viewport")) return;
                    lab.dequeuePreview.triggered();
                } else if(lab.stage===9) {
                    queueActions.finishPreview();
                } else if(lab.stage===10) {
                    if(!lab.require(lab.dequeueButton.enabledAction,"matched dequeue preview")) return;
                    lab.dequeueButton.triggered();
                    if(!lab.require(view.armedAction==="dequeue" && lab.dequeueCalls===0,
                        "first click only arms")) return;
                    lab.dequeueButton.triggered();
                } else if(lab.stage===11) {
                    if(!lab.require(lab.dequeueButton.loading && lab.dequeueCalls===1,
                        "second click owns dequeue loading")) return;
                    queueActions.finishMutation(true);
                } else if(lab.stage===12) {
                    if(!lab.require(view.completedQueueSuccess && view.completedQueueAction==="queue-execute-dequeue",
                        "verified dequeue result completes correct control")) return;
                    console.log("QUEUE_NATIVE_PASS bounded viewport; empty states; five action identities; verified completion; two-click dequeue");
                    Qt.quit(); return;
                }
                lab.stage++;
            }
        }
    }
}
