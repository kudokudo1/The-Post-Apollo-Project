import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../../services/git/GitMapViewportPolicy.js" as Policy

// One public map; one finite lookup per active visit, with a bounded build on cache miss.
// Never start a job or adopt a result while hidden. No periodic polling.
Item {
    id: root
    property var topologyService: null
    property string repoRoot: ""
    property bool operatorActive: false
    property string titleText: "REPOSITORY BRANCH MAP"
    property string selectedSha: ""
    signal commitSelected(string sha)

    property alias viewport: candidate
    property bool allocated: false
    property bool lookupQueued: false
    property bool buildQueued: false
    property var locateAnchor: null
    property int jobsStarted: 0
    property string activeRepo: ""
    property var pendingResult: null
    property string pendingRepo: ""
    property string statusText: "AVAILABLE HISTORY // 48 COMMITS MAX"
    property string job: ""
    property string jobRepo: ""
    property int repoEpoch: 0
    property int jobEpoch: -1
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property string output: ""
    property bool faulted: false
    readonly property bool busy: job !== ""
    readonly property bool canRequest: operatorActive && !busy && !faulted && !worker.running
        && repoRoot.startsWith("/") && repoRoot.length > 1
    readonly property bool fullVisible: activeRepo === repoRoot && activeRepo !== ""
    readonly property bool canAdopt: operatorActive && pendingResult !== null
        && pendingRepo === repoRoot && !busy && !faulted

    onRepoRootChanged: {
        repoEpoch += 1;
        activeRepo = "";
        pendingResult = null;
        pendingRepo = "";
        statusText = "AVAILABLE HISTORY // REPOSITORY CHANGED";
        lookupQueued = true;
        buildQueued = false;
        locateAnchor = null;
        schedule();
    }

    onOperatorActiveChanged: {
        if (operatorActive) {
            if (!pendingResult && !busy && !buildQueued) lookupQueued = true;
            schedule();
        }
    }
    function schedule() { Qt.callLater(pump); }
    function pump() {
        if (!canRequest) return;
        if (pendingResult) {
            adoptPending();
            return;
        }
        if (buildQueued) {
            buildQueued=false;
            request("build");
        } else if (lookupQueued) {
            lookupQueued=false;
            request("lookup");
        }
    }
    function request(action) {
        if (!canRequest || (action !== "lookup" && action !== "build")) return false;
        job = action;
        jobRepo = repoRoot;
        jobEpoch = repoEpoch;
        jobsStarted++;
        pendingResult = null;
        pendingRepo = "";
        received = false;
        exited = false;
        exitOk = false;
        output = "";
        statusText = action === "build" ? "INDEXING // CURRENT MAP RETAINED" : "CHECKING HISTORY";
        watchdog.restart();
        worker.exec(["/usr/bin/timeout","--kill-after=2s",action === "build" ? "120s" : "20s",
                     "/usr/bin/python3","-I","-B",
                     Quickshell.shellPath("scripts/git_map_index_manager.py"),
                     action,jobRepo]);
        return true;
    }
    function locate() {
        const anchor=candidate.currentAnchor();
        if (!anchor || !anchor.sha || !canAdopt || worker.running) {
            statusText="NEW HISTORY READY // POSITION RETAINED";
            return false;
        }
        locateAnchor=anchor;
        job="locate";
        jobRepo=repoRoot;
        jobEpoch=repoEpoch;
        jobsStarted++;
        received=false; exited=false; exitOk=false; output="";
        watchdog.restart();
        worker.exec(["/usr/bin/timeout","--kill-after=2s","20s","/usr/bin/python3","-I","-B",
                     Quickshell.shellPath("scripts/git_map_history_index.py"),
                     "locate",pendingResult.directory,pendingResult.manifest.snapshot,anchor.sha]);
        return true;
    }
    function validReceipt(value) {
        return value && value.schema === "post-apollo-git-map-cache-v1"
            && typeof value.repoId === "string" && /^[0-9a-f]{64}$/.test(value.repoId)
            && typeof value.key === "string" && /^[0-9a-f]{64}$/.test(value.key)
            && ["READY","MISSING","CACHE LIMIT"].indexOf(value.status) >= 0
            && (value.status !== "READY" || (Policy.manifest(value.manifest)
                && value.manifest.repoId === value.repoId
                && typeof value.directory === "string" && value.directory.startsWith("/")
                && value.directory.endsWith("/"+value.repoId+"/"+value.key)));
    }
    function finish() {
        if (!busy || !received || !exited) return;
        watchdog.stop();
        const repo = jobRepo, action=job;
        job = "";
        jobRepo = "";
        let result = null;
        if (exitOk && output.length <= 16384) {
            try { result = JSON.parse(output); } catch (error) {}
        }
        output = "";
        if (repo !== repoRoot || jobEpoch !== repoEpoch) { schedule(); return; }
        if (action==="locate") {
            const anchor=locateAnchor;
            locateAnchor=null;
            const current=candidate.currentAnchor();
            if (operatorActive && pendingResult && anchor && current
                    && current.sha===anchor.sha && current.offset===anchor.offset
                    && Policy.identity(result) && result.repoId===pendingResult.manifest.repoId
                    && result.snapshot===pendingResult.manifest.snapshot && result.sha===anchor.sha
                    && Policy.integer(result.ordinal,0,pendingResult.manifest.total-1)) {
                adopt(Object.assign({},result,{offset:anchor.offset}));
            } else {
                // Never jump or repeatedly retry if the anchor vanished/moved.
                pendingResult=null;
                pendingRepo="";
                statusText="NEW HISTORY NOT ADOPTED // POSITION RETAINED";
            }
            return;
        }
        if (!validReceipt(result)) {
            statusText = "INDEX UNAVAILABLE // CURRENT MAP SAFE";
            return;
        }
        if (result.status === "MISSING") {
            // A lookup can initiate one build; a build receipt cannot loop.
            buildQueued = action==="lookup";
            statusText = "HISTORY INDEX MISSING";
            schedule();
            return;
        }
        if (result.status === "CACHE LIMIT") {
            statusText = "CACHE LIMIT // EXISTING HISTORY PRESERVED";
            return;
        }
        if (fullVisible && candidate.mapState
                && candidate.mapState.snapshot === result.manifest.snapshot) {
            statusText = "INDEX CURRENT // POSITION RETAINED";
            return;
        }
        pendingResult = result;
        pendingRepo = repo;
        statusText = "NEW HISTORY READY";
        schedule();
    }
    function adoptPending() {
        if (!canAdopt || worker.running) return false;
        if (fullVisible && candidate.scrollPosition>0) return locate();
        if (!fullVisible && candidate.scrollPosition>0) {
            // The recent adapter has no indexed generation identity yet.
            // Do not silently reset a user who is reading recent history.
            statusText="HISTORY READY // RETURN TO TOP TO EXPAND";
            return false;
        }
        return adopt({top:true});
    }
    function adopt(anchor) {
        if (!canAdopt) return false;
        const result=pendingResult;
        if (!candidate.activate(result.directory,result.manifest,anchor)) {
            statusText="INDEX OPEN FAILED // CURRENT MAP SAFE";
            pendingResult=null;
            pendingRepo="";
            return false;
        }
        activeRepo=pendingRepo;
        pendingResult=null;
        pendingRepo="";
        allocated=true;
        statusText="INDEXED HISTORY // "+result.manifest.total+" COMMITS";
        return true;
    }

    Timer {
        id: watchdog
        interval: 125000
        repeat: false
        onTriggered: {
            if (!root.busy) return;
            root.faulted = true;
            root.job = "";
            root.jobRepo = "";
            root.output = "";
            root.pendingResult=null;
            root.pendingRepo="";
            root.buildQueued=false;
            root.lookupQueued=false;
            root.statusText = "INDEX WORKER FAULT // AVAILABLE HISTORY SAFE";
            worker.running = false;
        }
    }
    Process {
        id: worker
        onRunningChanged: if (!running) root.schedule()
        stdout: StdioCollector {
            onStreamFinished: {
                if (!root.busy) return;
                root.output = this.text;
                root.received = true;
                root.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,exitStatus) {
            if (!root.busy) return;
            root.exitOk = code === 0 && exitStatus === 0;
            root.exited = true;
            root.finish();
        }
    }

    GohuText {
        id: status
        anchors.top: parent.top
        width: parent.width
        height: 16
        font.pixelSize: 9
        color: Colors.orange
        textFormat: Text.PlainText
        text: root.statusText
        elide: Text.ElideRight
    }
    GitMapVirtualViewport {
        id: candidate
        anchors.top: status.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        indexedActive: root.fullVisible
        externalSelection: true
        selectedSha: root.selectedSha
        recentTopology: root.topologyService
        recentRepo: root.repoRoot
        titleText: root.titleText
        requestsEnabled: root.operatorActive && root.fullVisible
        onScrollPositionChanged: if (root.pendingResult && scrollPosition===0) root.schedule()
        onCommitSelected: function(sha) {
            if (root.operatorActive) root.commitSelected(sha);
        }
    }
}
