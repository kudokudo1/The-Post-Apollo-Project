import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../../services/git/GitMapViewportPolicy.js" as Policy

// Explicit opt-in control-page host. Existing recent map stays mounted.
// No index lookup/build at startup, on visibility change, or on repo change.
Item {
    id: root
    property var topologyService: null
    property string repoRoot: ""
    property bool operatorActive: false
    property string titleText: "REPOSITORY BRANCH MAP"
    property string selectedSha: ""
    signal commitSelected(string sha)

    property bool fullWanted: false
    property bool allocated: false
    property string activeRepo: ""
    property var pendingResult: null
    property string pendingRepo: ""
    property string statusText: "RECENT // 48 COMMITS MAX"
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
    readonly property bool fullVisible: fullWanted && activeRepo === repoRoot
        && activeRepo !== "" && candidate.item !== null
    readonly property bool canAdopt: operatorActive && pendingResult !== null
        && pendingRepo === repoRoot && !busy && !faulted

    onRepoRootChanged: {
        repoEpoch += 1;
        fullWanted = false;
        activeRepo = "";
        pendingResult = null;
        pendingRepo = "";
        statusText = "RECENT // REPOSITORY CHANGED";
    }

    function recent() {
        fullWanted = false;
        statusText = "RECENT // 48 COMMITS MAX";
    }
    function openFull() {
        if (!operatorActive || busy || faulted) return false;
        if (activeRepo === repoRoot && candidate.item && candidate.item.mapState) {
            fullWanted = true;
            statusText = "FROZEN INDEX // RECHECK FOR NEW HISTORY";
            return true;
        }
        return request("lookup");
    }
    function request(action) {
        if (!canRequest || (action !== "lookup" && action !== "build")) return false;
        job = action;
        jobRepo = repoRoot;
        jobEpoch = repoEpoch;
        pendingResult = null;
        pendingRepo = "";
        received = false;
        exited = false;
        exitOk = false;
        output = "";
        statusText = action === "build" ? "BUILDING INDEX // RECENT MAP AVAILABLE" : "CHECKING DISK INDEX";
        watchdog.restart();
        worker.exec(["/usr/bin/timeout","--kill-after=2s",action === "build" ? "120s" : "20s",
                     "/usr/bin/python3","-I","-B",
                     Quickshell.shellPath("scripts/git_map_index_manager.py"),
                     action,jobRepo]);
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
        const repo = jobRepo;
        job = "";
        jobRepo = "";
        let result = null;
        if (exitOk && output.length <= 16384) {
            try { result = JSON.parse(output); } catch (error) {}
        }
        output = "";
        if (repo !== repoRoot || jobEpoch !== repoEpoch) return; // no old-repository receipt can activate
        if (!validReceipt(result)) {
            statusText = "INDEX UNAVAILABLE // RECENT MAP SAFE";
            return;
        }
        if (result.status === "MISSING") {
            statusText = "NO MATCHING INDEX // BUILD EXPLICITLY";
            return;
        }
        if (result.status === "CACHE LIMIT") {
            statusText = "CACHE LIMIT // EXISTING HISTORY PRESERVED";
            return;
        }
        pendingResult = result;
        pendingRepo = repo;
        if (activeRepo === repo && candidate.item && candidate.item.mapState
                && candidate.item.mapState.snapshot === result.manifest.snapshot) {
            pendingResult = null;
            pendingRepo = "";
            statusText = "INDEX CURRENT // POSITION RETAINED";
            return;
        }
        // A new generation never automatically changes the viewport. Even
        // an index that finishes while the menu is closed waits for OPEN.
        statusText = "INDEX READY // OPEN FROM TOP";
    }
    function openPending() {
        if (!canAdopt) return false;
        if (!allocated) {
            allocated = true;
            return true; // onLoaded owns first adoption
        }
        return candidate.item ? adoptPending() : true;
    }
    function adoptPending() {
        if (!canAdopt || !candidate.item) return false;
        const result = pendingResult;
        // This action is explicitly labelled OPEN FROM TOP. Anchor-preserving
        // automatic generation replacement is not enabled in this phase.
        if (!candidate.item.activate(result.directory,result.manifest,{top:true})) {
            statusText = "INDEX OPEN FAILED // RECENT MAP SAFE";
            return false;
        }
        activeRepo = pendingRepo;
        pendingResult = null;
        pendingRepo = "";
        fullWanted = true;
        statusText = "FROZEN INDEX // "+result.manifest.total+" COMMITS";
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
            root.statusText = "INDEX WORKER FAULT // RECENT MAP SAFE";
            worker.running = false;
        }
    }
    Process {
        id: worker
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

    Row {
        id: actions
        width: parent.width
        height: 24
        spacing: 4
        ActionButton {
            width: Math.max(0,(actions.width-12)/4)
            height: parent.height
            label: "RECENT"
            selected: !root.fullVisible
            available: root.operatorActive
            onLeftClicked: root.recent()
        }
        ActionButton {
            width: Math.max(0,(actions.width-12)/4)
            height: parent.height
            label: root.fullVisible ? "RECHECK" : "FULL MAP"
            selected: root.fullVisible
            available: root.canRequest
            onLeftClicked: root.fullVisible ? root.request("lookup") : root.openFull()
        }
        ActionButton {
            width: Math.max(0,(actions.width-12)/4)
            height: parent.height
            label: root.job === "build" ? "BUILDING" : "BUILD INDEX"
            available: root.canRequest
            onLeftClicked: root.request("build")
        }
        ActionButton {
            width: Math.max(0,(actions.width-12)/4)
            height: parent.height
            label: "OPEN // TOP"
            available: root.canAdopt
            onLeftClicked: root.openPending()
        }
    }
    GohuText {
        id: status
        anchors.top: actions.bottom
        width: parent.width
        height: 16
        font.pixelSize: 9
        color: Colors.orange
        textFormat: Text.PlainText
        text: root.statusText
        elide: Text.ElideRight
    }
    BranchMap {
        anchors.top: status.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: !root.fullVisible
        topologyService: root.topologyService
        titleText: root.titleText
        selectedSha: root.selectedSha
        onCommitSelected: function(sha) {root.commitSelected(sha);}
    }
    Loader {
        id: candidate
        anchors.top: status.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        active: root.allocated
        visible: root.fullVisible
        sourceComponent: GitMapVirtualViewport {
            requestsEnabled: root.operatorActive && root.fullVisible
            onCommitSelected: function(sha) {
                if (root.operatorActive && root.fullVisible) root.commitSelected(sha);
            }
        }
        onLoaded: root.adoptPending()
    }
}
