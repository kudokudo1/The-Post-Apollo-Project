import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/git"

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    readonly property string repo: Quickshell.env("MAP_MANAGED_REPO")
    property bool operatorActive: false
    property var oldAnchor: null
    property string oldSnapshot: ""
    property bool commitDone: false
    Process {
        id: mutateFixture
        onExited: function(code,exitStatus) {
            if (!root.check(code===0 && exitStatus===0,"disposable repo advance")) return;
            root.commitDone=true;
        }
    }
    QtObject {
        id: recent
        property string repoPath: root.repo
        property string repoRoot: root.repo
        property int topologyRevision: 1
        property bool refreshing: false
        property int commitCount: 2
        property string headFull: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        function commitAt(i) {
            if (i===0) return {sha:headFull, lane:0, subject:"Recent head",
                refsText:"main",isHead:true,parents:"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"};
            if (i===1) return {sha:"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",lane:1,
                subject:"Recent parent",refsText:"",isHead:false,parents:""};
            return null;
        }
    }
    function check(ok,message) {
        if (!ok) {
            console.error("GIT_MAP_MANAGED_FAIL // "+message);
            done=true;
            Qt.quit();
        }
        return ok;
    }
    Window {
        width: 720
        height: 480
        visible: true
        GitMapControlHost {
            id: host
            anchors.fill: parent
            repoRoot: root.repo
            topologyService: recent
            operatorActive: root.operatorActive
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: !root.done
        onTriggered: {
            if (++root.ticks>250) {
                root.check(false,"timeout // "+host.statusText);
                return;
            }
            if (root.phase===0 && root.ticks>=5) {
                if (!root.check(!host.busy && !host.allocated && !host.fullVisible,"startup must not read/build")) return;
                if (!root.check(!host.request("build"),"hidden build refused")) return;
                if (!root.check(host.viewport.mapState.total===2
                        && host.viewport.nodeGlyph(host.viewport.rowAt(0))==="★"
                        && host.viewport.nodeGlyph(host.viewport.rowAt(1))==="✧"
                        && host.viewport.rowAt(0).parents[0].lane===1,
                        "same viewport renders bounded recent rows and exact legacy glyphs")) return;
                recent.repoRoot="/wrong-repo";
                if (!root.check(host.viewport.mapState.total===0,"reject stale recent repo")) return;
                recent.repoRoot=root.repo;
                if (!root.check(host.viewport.mapState.total===2,"recover matching recent repo")) return;
                root.operatorActive=true;
                root.phase=1;
                return;
            }
            if (root.phase===1) {
                if (!host.fullVisible || !host.viewport.rowAt(0)) return;
                if (!root.check(host.jobsStarted===2 && host.viewport.mapState.total===40,
                        "automatic lookup and single missing-cache build/adopt")) return;
                root.operatorActive=false;
                root.phase=2;
                return;
            }
            if (root.phase===2) {
                if (!root.check(host.jobsStarted===2 && host.fullVisible,
                        "hidden state retained, no new work")) return;
                root.operatorActive=true;
                root.phase=3;
                return;
            }
            if (root.phase===3 && !host.busy && host.jobsStarted===3) {
                if (!root.check(host.statusText==="INDEX CURRENT // POSITION RETAINED" && host.fullVisible,
                        "reopen automatically reuses snapshot")) return;
                host.viewport.scrollTo(5*24+5);
                root.phase=4;
                return;
            }
            if (root.phase===4) {
                const anchor=host.viewport.currentAnchor();
                if (!anchor || !anchor.sha) return;
                if (!root.check(anchor.ordinal===5 && anchor.offset===5,"historical anchor before refresh")) return;
                root.oldAnchor=anchor;
                root.oldSnapshot=host.viewport.mapState.snapshot;
                root.operatorActive=false;
                mutateFixture.exec(["/usr/bin/git","-C",root.repo,"-c","user.name=Fixture",
                    "-c","user.email=fixture@example.invalid","commit","--allow-empty","-m","new head"]);
                root.phase=5;
                return;
            }
            if (root.phase===5 && root.commitDone) {
                if (!root.check(host.jobsStarted===3 && host.viewport.mapState.snapshot===root.oldSnapshot,
                        "hidden generation must stay frozen")) return;
                root.operatorActive=true;
                root.phase=6;
                return;
            }
            if (root.phase===6) {
                if (host.busy || host.viewport.mapState.snapshot===root.oldSnapshot) return;
                const anchor=host.viewport.currentAnchor();
                if (!anchor || !anchor.sha) return;
                if (!root.check(host.jobsStarted===6 && host.viewport.mapState.total===41
                        && anchor.sha===root.oldAnchor.sha && anchor.offset===root.oldAnchor.offset
                        && anchor.ordinal===root.oldAnchor.ordinal+1,
                        "new index exact SHA and intra-row position preserved")) return;
                host.searchQuery="commit 20";
                if (!root.check(host.searchHistory(false),"search launches on adopted snapshot")) return;
                root.phase=7;
                return;
            }
            if (root.phase===7 && !host.busy) {
                if (!root.check(host.lastMatch && host.lastMatch.ordinal===20,
                        "exact historical ordinal found")) return;
                const row=host.viewport.rowAt(host.lastMatch.ordinal);
                if (!row) return;
                if (!root.check(row.sha===host.lastMatch.sha && row.subject==="commit 20",
                        "same virtual viewport loads matching commit")) return;
                if (!root.check(host.searchHistory(true),"next search launches")) return;
                root.phase=8;
                return;
            }
            if (root.phase===8 && !host.busy) {
                if (!root.check(host.searchStatus.startsWith("NO FURTHER MATCH"),"no-match terminal result")) return;
                root.operatorActive=false;
                if (!root.check(!host.searchHistory(false),"hidden search refused")) return;
                console.log("GIT_MAP_MANAGED_PASS");
                root.done=true;
                Qt.quit();
            }
        }
    }
}
