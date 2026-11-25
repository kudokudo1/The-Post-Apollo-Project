import QtQuick
import Quickshell
import Quickshell.Io
import "GitMapViewportPolicy.js" as Policy

// Candidate bridge. Explicit activation only, no live shell registration.
// A single bounded child at a time; pending pages are reprioritized on scroll.
Scope {
    id: root
    property var state: null
    property string custodyBase: ""
    property var custodyLease: null
    property var custodyGeneration: null
    property var requestCustody: null
    property bool custodyRefused: false
    signal custodyFault(var g)
    function sameCustody(a,b) { return a && b && a.directory===b.directory && a.repoId===b.repoId && a.key===b.key && a.manifest.snapshot===b.manifest.snapshot && a.device===b.device && a.inode===b.inode; }
    property bool requestsEnabled: true
    onRequestsEnabledChanged: if (requestsEnabled) schedule()
    property string directory: ""
    property var activeRequest: null
    property string activeDirectory: ""
    property bool faulted: false
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property string output: ""
    readonly property bool busy: activeRequest !== null
    readonly property bool readerBusy: busy || worker.running

    function activate(path, manifest, rowHeight, viewportHeight, anchor, generation) {
        if (faulted || typeof path !== "string" || !path.startsWith("/")) return false;
        const candidate = Policy.activate(state, manifest, rowHeight, viewportHeight, anchor);
        if (!candidate) return false;
        custodyGeneration=generation || null;
        custodyRefused=false;
        directory = path;
        state = candidate;
        schedule();
        return true;
    }
    function scroll(y) {
        if (!state) return;
        const next = Policy.scroll(state,y);
        if (next === state) return;
        state = next;
        schedule();
    }
    function resize(height) {
        if (!state) return;
        state = Policy.resize(state,height);
        schedule();
    }
    function retry(ordinal) {
        if (!state || !Policy.integer(ordinal,0,state.total-1)) return;
        state = Policy.retry(state,Math.floor(ordinal/128)*128);
        schedule();
    }
    function schedule() {
        // Coalesce multiple geometry updates in the current event turn.
        Qt.callLater(pump);
    }
    function pump() {
        if (!requestsEnabled || !state || faulted || busy || worker.running) return;
        if (custodyRefused) return;
        if (custodyBase && (!custodyGeneration || !custodyLease || !custodyLease.held || !sameCustody(custodyLease.generation,custodyGeneration))) { custodyRefused=true; custodyFault(custodyGeneration); return; }
        const plan = Policy.requests(state);
        state = plan.state;
        const wanted = Policy.wantedPages(state);
        let request = null;
        for (const start of wanted) {
            if (state.pending[start]) {
                request = state.pending[start];
                break;
            }
        }
        if (!request) return;
        requestCustody=custodyBase ? custodyGeneration : null;
        activeRequest = request;
        activeDirectory = directory;
        received = false;
        exited = false;
        exitOk = false;
        output = "";
        deadline.restart();
        if (requestCustody) worker.exec(["/usr/bin/timeout","--kill-after=1s","5s","/usr/bin/python3","-I","-B",Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),"--base",custodyBase,"--device",requestCustody.device,"--inode",requestCustody.inode,"page",request.repoId,requestCustody.key,request.snapshot,String(request.start)]);
        else worker.exec(["/usr/bin/timeout","--kill-after=1s","5s","/usr/bin/python3","-I","-B",
                     Quickshell.shellPath("scripts/git_map_history_index.py"),
                     "page", activeDirectory, request.snapshot, String(request.start)]);
    }
    function finish() {
        if (!busy || !received || !exited) return;
        deadline.stop();
        const request = activeRequest;
        if (state && Policy.sameRequest(state, request)) {
            let accepted = null;
            if (exitOk && output.length <= 4194304) {
                if (requestCustody) {
                    try { const reply=JSON.parse(output), g=requestCustody;
                        if (custodyLease && custodyLease.held && sameCustody(custodyLease.generation,g) && sameCustody(custodyGeneration,g) && reply.schema==="post-apollo-git-map-reader-v2-candidate" && reply.status==="READY" && reply.repoId===g.repoId && reply.key===g.key && reply.snapshot===g.manifest.snapshot && reply.device===g.device && reply.inode===g.inode && reply.reclamationAllowed===false) accepted=Policy.accept(state,request,reply.result);
                    } catch (error) {}
                } else try { accepted = Policy.accept(state,request,JSON.parse(output)); }
                catch (error) {}
            }
            state = accepted || Policy.fail(state,request);
            if (!accepted && requestCustody && sameCustody(requestCustody,custodyGeneration)) { custodyRefused=true; custodyFault(requestCustody); }
        }
        output = "";
        activeRequest = null;
        requestCustody=null;
        activeDirectory = "";
        schedule();
    }
    Timer {
        id: deadline
        interval: 8000
        repeat: false
        onTriggered: {
            if (!root.busy) return;
            // Missing terminal evidence: do not assign late output to a
            // subsequent request. Explicitly fail all pending visible pages.
            root.faulted = true;
            let s = root.state;
            if (s) {
                for (const req of Object.values(s.pending)) s = Policy.fail(s,req);
                root.state = s;
            }
            root.activeRequest = null;
            root.activeDirectory = "";
            root.output = "";
            worker.running = false;
        }
    }
    Process {
        id: worker
        onRunningChanged: if (!running && !root.faulted) root.schedule()
        stdout: StdioCollector {
            onStreamFinished: {
                if (!root.busy) return;
                root.output = this.text;
                root.received = true;
                root.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            if (!root.busy) return;
            root.exitOk = code === 0 && exitStatus === 0;
            root.exited = true;
            root.finish();
        }
    }
}
