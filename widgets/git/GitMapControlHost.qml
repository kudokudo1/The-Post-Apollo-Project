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
    property string observedHead: ""
    property string activeRepo: ""
    property string activeDirectory: ""
    property var custodyController: null
    property var activeLease: null
    property bool custodyLost: false
    property var pendingLease: null
    readonly property bool custodyEnabled: custodyController!==null
    readonly property bool custodyV2: custodyEnabled && custodyController.v2Mode
    readonly property string custodyBase: custodyV2 ? custodyController.v2Base : ""
    function sameCustody(a,b) { return a && b && a.directory===b.directory && a.repoId===b.repoId && a.key===b.key && a.manifest.snapshot===b.manifest.snapshot && a.device===b.device && a.inode===b.inode; }
    function v2Reply(reply,g,lease) { return reply && g && lease && lease.held && sameCustody(lease.generation,g) && reply.schema==="post-apollo-git-map-reader-v2-candidate" && reply.status==="READY" && reply.repoId===g.repoId && reply.key===g.key && reply.snapshot===g.manifest.snapshot && reply.device===g.device && reply.inode===g.inode && reply.reclamationAllowed===false ? reply.result : null; }
    readonly property bool pendingCustodyReady: !custodyEnabled || (pendingLease!==null && pendingLease.held)
    property alias searchQuery: searchInput.text
    property string searchStatus: ""
    property var searchRequest: null
    property int searchEpoch: 0
    property var lastMatch: null
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
        && (!custodyEnabled || (!custodyLost && (!activeLease || activeLease.held)))
    readonly property bool fullVisible: activeRepo === repoRoot && activeRepo !== ""
        && (!custodyEnabled || (activeLease!==null && activeLease.held))
    readonly property bool canAdopt: operatorActive && pendingResult !== null
        && pendingRepo === repoRoot && !busy && !faulted && !custodyLost && pendingCustodyReady
        && (!custodyEnabled || !activeLease || activeLease.held) && (!custodyEnabled || !candidate.readerBusy)

    function clearPending() {
        const previous=pendingLease;
        pendingLease=null;
        if (previous && custodyController) custodyController.release(previous);
        pendingResult=null;
        pendingRepo="";
    }
    Connections {
        target: root.pendingLease
        function onHeldChanged() { root.schedule(); }
        function onCustodyStateChanged() { root.schedule(); }
    }
    Connections {
        target: root.activeLease
        // Do not release the lease from inside its held binding evaluation.
        // fullVisible/canRequest/canAdopt already fail closed immediately.
        function onHeldChanged() { Qt.callLater(root.handleCustodyLoss); }
    }
    function invalidateCustodyV2() {
        custodyLost=true; repoEpoch++; searchEpoch++; activeRepo=""; activeDirectory=""; searchRequest=null; lastMatch=null;
        searchStatus="SEARCH DISCARDED // CUSTODY LOST"; lookupQueued=false; buildQueued=false; clearPending();
        const lost=activeLease; activeLease=null; if (lost && custodyController) custodyController.release(lost);
        statusText="CUSTODY LOST // REOPEN TO RECHECK";
    }
    function handleCustodyLoss() {
        const lost=activeLease;
        if (!lost || lost.held) return;
        custodyLost=true;
        repoEpoch++;
        searchEpoch++;
        activeRepo="";
        activeDirectory="";
        searchRequest=null;
        lastMatch=null;
        searchStatus="SEARCH DISCARDED // CUSTODY LOST";
        lookupQueued=false;
        buildQueued=false;
        clearPending();
        activeLease=null;
        if (custodyController) custodyController.release(lost);
        statusText="CUSTODY LOST // REOPEN TO RECHECK";
    }
    Component.onDestruction: {
        clearPending();
        if (activeLease && custodyController) custodyController.release(activeLease);
    }
    onRepoRootChanged: {
        repoEpoch += 1;
        custodyLost=false;
        activeRepo = "";
        activeDirectory = "";
        searchRequest=null;
        lastMatch=null;
        searchStatus="";
        clearPending();
        statusText = "AVAILABLE HISTORY // REPOSITORY CHANGED";
        lookupQueued = true;
        buildQueued = false;
        locateAnchor = null;
        observedHead = "";
        schedule();
    }

    onOperatorActiveChanged: {
        if (!operatorActive) searchEpoch++;
        if (operatorActive) {
            custodyLost=false;
            if (!pendingResult && !busy && !buildQueued) lookupQueued = true;
            schedule();
        }
    }
    // A completed Git refresh after a pull/commit may expose a new HEAD.
    // No polling, no repeated rebuild just because the status refreshes.
    Connections {
        target: root.topologyService
        ignoreUnknownSignals: true
        function onRefreshed() {
            const service=root.topologyService;
            if (!service || service.repoPath!==root.repoRoot || service.repoRoot!==root.repoRoot
                    || !Policy.sha(String(service.headFull))) return;
            const head=String(service.headFull);
            if (root.observedHead && root.observedHead!==head && root.operatorActive && !root.custodyLost) {
                root.lookupQueued=true;
                root.schedule();
            }
            root.observedHead=head;
        }
    }
    function schedule() { Qt.callLater(pump); }
    function pump() {
        if (!canRequest) return;
        if (pendingResult) {
            if (custodyEnabled && (!pendingLease || pendingLease.terminal)) {
                clearPending();
                statusText="CUSTODY UNAVAILABLE // CURRENT MAP RETAINED";
                return;
            }
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
        clearPending();
        received = false;
        exited = false;
        exitOk = false;
        output = "";
        statusText = action === "build" ? "INDEXING // CURRENT MAP RETAINED" : "CHECKING HISTORY";
        watchdog.restart();
        if (custodyV2) worker.exec(["/usr/bin/timeout","--kill-after=2s",action === "build" ? "120s" : "20s","/usr/bin/python3","-I","-B",Quickshell.shellPath("scripts/git_map_v2_manager_candidate.py"),"--base",custodyBase,action,jobRepo]);
        else worker.exec(["/usr/bin/timeout","--kill-after=2s",action === "build" ? "120s" : "20s",
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
        if (custodyV2) worker.exec(["/usr/bin/timeout","--kill-after=2s","20s","/usr/bin/python3","-I","-B",Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),"--base",custodyBase,"--device",pendingResult.device,"--inode",pendingResult.inode,"locate",pendingResult.repoId,pendingResult.key,pendingResult.manifest.snapshot,anchor.sha]);
        else worker.exec(["/usr/bin/timeout","--kill-after=2s","20s","/usr/bin/python3","-I","-B",
                     Quickshell.shellPath("scripts/git_map_history_index.py"),
                     "locate",pendingResult.directory,pendingResult.manifest.snapshot,anchor.sha]);
        return true;
    }
    function searchHistory(next) {
        const query=searchInput.text.trim();
        const s=candidate.mapState;
        if (!canRequest || pendingResult || !fullVisible || !s || !activeDirectory
                || !query || query.length>128 || /[\x00-\x1f\x7f]/.test(query)) return false;
        const start=next && lastMatch && lastMatch.query===query
            && lastMatch.snapshot===s.snapshot ? lastMatch.ordinal+1 : 0;
        if (start>s.total) return false;
        searchRequest={query:query,start:start,snapshot:s.snapshot,repoId:s.repoId,total:s.total,epoch:searchEpoch};
        job="search";
        jobRepo=repoRoot;
        jobEpoch=repoEpoch;
        received=false; exited=false; exitOk=false; output="";
        searchStatus="SEARCHING";
        watchdog.restart();
        if (custodyV2) worker.exec(["/usr/bin/timeout","--kill-after=1s","5s","/usr/bin/python3","-I","-B",Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),"--base",custodyBase,"--device",activeLease.generation.device,"--inode",activeLease.generation.inode,"search",s.repoId,activeLease.generation.key,s.snapshot,"--",query,String(start)]);
        else worker.exec(["/usr/bin/timeout","--kill-after=1s","5s","/usr/bin/python3","-I","-B",
            Quickshell.shellPath("scripts/git_map_history_index.py"),
            "search",activeDirectory,s.snapshot,"--",query,String(start)]);
        return true;
    }
    function finishSearch(result) {
        const req=searchRequest;
        searchRequest=null;
        const s=candidate.mapState;
        if (!req || req.epoch!==searchEpoch || !operatorActive || !fullVisible || !s
                || req.query!==searchInput.text.trim() || req.snapshot!==s.snapshot
                || req.repoId!==s.repoId || req.total!==s.total) {
            searchStatus="SEARCH DISCARDED";
            return;
        }
        if (!Policy.identity(result) || result.snapshot!==req.snapshot
                || result.repoId!==req.repoId || result.query!==req.query
                || result.start!==req.start) {
            searchStatus="SEARCH UNAVAILABLE";
            return;
        }
        if (result.match===null) {
            searchStatus="NO FURTHER MATCH // SEARCH TO RESTART";
            return;
        }
        const m=result.match;
        if (!m || !Policy.sha(m.sha) || !Policy.integer(m.ordinal,req.start,s.total-1)) {
            searchStatus="SEARCH UNAVAILABLE";
            return;
        }
        lastMatch={query:req.query,snapshot:req.snapshot,ordinal:m.ordinal,sha:m.sha};
        candidate.scrollTo(m.ordinal*candidate.rowHeight);
        searchStatus="MATCH "+(m.ordinal+1)+" / "+s.total+" // "+m.sha.slice(0,10);
    }
    function validReceipt(value) {
        if (custodyV2) return value && value.schema==="post-apollo-git-map-custody-v2" && value.reclamationAllowed===false && typeof value.repoId==="string" && /^[0-9a-f]{64}$/.test(value.repoId) && typeof value.key==="string" && /^[0-9a-f]{64}$/.test(value.key) && ["READY","MISSING","CACHE LIMIT"].includes(value.status) && (value.status!=="READY" || (Policy.manifest(value.manifest) && value.manifest.repoId===value.repoId && !value.manifest.shallow && value.directory===custodyBase+"/post-apollo-git-map-custody-v2/"+value.repoId+"/"+value.key && typeof value.device==="string" && typeof value.inode==="string" && /^(0|[1-9][0-9]{0,19})$/.test(value.device) && /^(0|[1-9][0-9]{0,19})$/.test(value.inode)));
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
        if (custodyV2 && (action==="search" || action==="locate")) {
            const lease=action==="locate" ? pendingLease : activeLease;
            result=v2Reply(result,action==="locate" ? pendingResult : (lease ? lease.generation : null),lease);
            if (!result) { invalidateCustodyV2(); return; }
        }
        if (action==="search") { finishSearch(result); schedule(); return; }
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
                clearPending();
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
                && candidate.mapState.snapshot === result.manifest.snapshot && (!custodyV2 || (activeLease && sameCustody(activeLease.generation,result)))) {
            statusText = "INDEX CURRENT // POSITION RETAINED";
            schedule();
            return;
        }
        pendingResult = result;
        pendingRepo = repo;
        if (custodyEnabled) {
            pendingLease=custodyController.acquire(result);
            if (!pendingLease) {
                clearPending();
                statusText="CUSTODY UNAVAILABLE // CURRENT MAP RETAINED";
                return;
            }
        }
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
        if (!candidate.activate(result.directory,result.manifest,anchor,custodyV2 ? result : null)) {
            statusText="INDEX OPEN FAILED // CURRENT MAP SAFE";
            clearPending();
            return false;
        }
        const previousLease=activeLease;
        activeLease=pendingLease;
        pendingLease=null;
        activeRepo=pendingRepo;
        activeDirectory=result.directory;
        if (previousLease && custodyController) custodyController.release(previousLease);
        lastMatch=null;
        searchStatus="";
        pendingResult=null;
        pendingRepo="";
        allocated=true;
        statusText="INDEXED HISTORY // "+result.manifest.total+" COMMITS";
        schedule();
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
            root.clearPending();
            root.searchRequest=null;
            root.searchStatus="SEARCH / INDEX WORKER FAULT";
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
    Row {
        id: searchRow
        anchors.top: status.bottom
        width: parent.width
        height: 28
        spacing: 4
        Rectangle {
            width: Math.max(0,parent.width-112)
            height: parent.height
            color: Colors.dark
            border.color: Colors.cyan
            border.width: 1
            radius: 0
            TextInput {
                id: searchInput
                anchors.fill: parent
                anchors.margins: 5
                maximumLength: 128
                enabled: root.operatorActive && root.fullVisible
                selectByMouse: true
                clip: true
                font.pixelSize: 11
                color: Colors.white
                selectionColor: Colors.magenta
                selectedTextColor: Colors.white
                verticalAlignment: TextInput.AlignVCenter
                onTextChanged: { root.searchEpoch++; root.lastMatch=null; root.searchStatus=""; }
                onAccepted: root.searchHistory(false)
            }
            GohuText {
                anchors.fill: searchInput
                visible: !searchInput.text.length && !searchInput.activeFocus
                text: "SHA / AUTHOR / SUBJECT"
                color: Colors.cyan
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        ActionButton {
            width: 60; height: parent.height
            label: "FIND"
            available: root.canRequest && root.fullVisible && !root.pendingResult && !!searchInput.text.trim()
            onLeftClicked: root.searchHistory(false)
        }
        ActionButton {
            width: 44; height: parent.height
            label: "NEXT"
            available: root.canRequest && root.fullVisible && !root.pendingResult && !!root.lastMatch
            onLeftClicked: root.searchHistory(true)
        }
    }
    GohuText {
        id: searchFeedback
        anchors.top: searchRow.bottom
        width: parent.width
        height: root.searchStatus.length ? 16 : 0
        visible: height>0
        text: root.searchStatus
        color: Colors.orange
        font.pixelSize: 9
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }
    GitMapVirtualViewport {
        id: candidate
        anchors.top: searchFeedback.bottom
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
        custodyBase: root.custodyBase
        custodyLease: root.custodyV2 ? root.activeLease : null
        onCustodyFault: function(g) { Qt.callLater(()=>{ if (root.custodyV2 && root.activeLease && root.sameCustody(root.activeLease.generation,g)) root.invalidateCustodyV2(); }); }
        onReaderBusyChanged: if (!readerBusy && root.pendingResult) root.schedule()
        onScrollPositionChanged: if (root.pendingResult && scrollPosition===0) root.schedule()
        onCommitSelected: function(sha) {
            if (root.operatorActive) root.commitSelected(sha);
        }
    }
}
