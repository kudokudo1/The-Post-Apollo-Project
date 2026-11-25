import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/git"

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    readonly property string repo: Quickshell.env("MAP_MANAGED_REPO")
    property bool operatorActive: false
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
                if (!root.check(host.openFull(),"explicit lookup")) return;
                root.phase=1;
                return;
            }
            if (root.phase===1 && !host.busy) {
                if (!root.check(host.statusText.indexOf("NO MATCHING INDEX")===0 && !host.allocated,"missing lookup must not build")) return;
                if (!root.check(host.request("build"),"explicit build")) return;
                root.operatorActive=false;
                root.phase=2;
                return;
            }
            if (root.phase===2 && !host.busy) {
                if (!root.check(host.pendingResult && !host.allocated && !host.fullVisible,"hidden result waits for adoption")) return;
                if (!root.check(!host.openPending(),"hidden adoption refused")) return;
                root.operatorActive=true;
                if (!root.check(host.openPending(),"explicit adoption")) return;
                root.phase=3;
                return;
            }
            if (root.phase===3) {
                if (!host.fullVisible || !host.viewport.rowAt(0)) return;
                if (!root.check(host.viewport.mapState.total===1 && host.viewport.indexedActive,"same viewport adopts real index")) return;
                root.operatorActive=false;
                if (!root.check(host.fullVisible && host.allocated && !host.busy,"hidden map retains adopted index")) return;
                root.operatorActive=true;
                if (!root.check(host.fullVisible && !host.busy,"reopen retains index")) return;
                if (!root.check(host.openFull(),"explicit recheck")) return;
                root.phase=4;
                return;
            }
            if (root.phase===4 && !host.busy) {
                if (!root.check(host.statusText==="INDEX CURRENT // POSITION RETAINED" && host.fullVisible && !host.pendingResult,"recheck reuses snapshot")) return;
                console.log("GIT_MAP_MANAGED_PASS");
                root.done=true;
                Qt.quit();
            }
        }
    }
}
