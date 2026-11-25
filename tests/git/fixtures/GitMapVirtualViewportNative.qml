import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/git"

ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property bool done: false
    readonly property var manifestA: JSON.parse(Quickshell.env("MAP_FIXTURE_A"))
    readonly property var manifestB: JSON.parse(Quickshell.env("MAP_FIXTURE_B"))
    readonly property string dirA: Quickshell.env("MAP_FIXTURE_DIR_A")
    readonly property string dirB: Quickshell.env("MAP_FIXTURE_DIR_B")
    property real expectedY: 0
    property string chosen: ""
    function check(ok,message) {
        if (!ok) {
            console.error("GIT_MAP_NATIVE_FAIL // "+message);
            done=true;
            Qt.quit();
        }
        return ok;
    }
    function sha(n) { return (n+1).toString(16).padStart(40,"0"); }
    Window {
        width: 720
        height: 480
        visible: true
        GitMapVirtualViewport {
            id: map
            anchors.fill: parent
            onCommitSelected: function(sha) { root.chosen=sha; }
        }
    }
    Timer {
        interval: 50
        repeat: true
        running: !root.done
        onTriggered: {
            if (++root.ticks>500) {
                root.check(false,"timeout phase "+root.phase+" // "+map.bottomStatus);
                return;
            }
            if (root.phase===0) {
                if (!root.check(map.activate(root.dirA,root.manifestA,null),"activate A")) return;
                root.phase=1;
                return;
            }
            if (root.phase===1) {
                if (!root.check(map.scrollExtent===2400000,"full extent")) return;
                if (!root.check(map.renderedRows<=24 && map.graphSurfaceHeight<480,"bounded renderer")) return;
                // Jump while the first page is still artificially delayed.
                map.scrollTo(999999999);
                root.expectedY=map.scrollPosition;
                if (!root.check(root.expectedY>2399000 && map.bottomStatus==="LOADING END RANGE","reserved bottom")) return;
                root.phase=2;
                return;
            }
            if (root.phase===2) {
                if (!root.check(map.scrollPosition===root.expectedY,"late response moved viewport")) return;
                if (map.bottomStatus!=="END RANGE UNAVAILABLE") return;
                if (!root.check(map.rowAt(99999)===null && !map.choose(99999),"failed page must not select")) return;
                map.retry(99999);
                root.phase=3;
                return;
            }
            if (root.phase===3) {
                if (!root.check(map.scrollPosition===root.expectedY,"retry moved viewport")) return;
                if (map.bottomStatus!=="END OF INDEXED LOCAL HISTORY") return;
                if (!root.check(map.rowAt(99999).sha===root.sha(99999),"last SHA mismatch")) return;
                if (!root.check(map.choose(99999) && root.chosen===root.sha(99999),"exact selection")) return;
                map.scrollTo(50000*24);
                root.phase=4;
                return;
            }
            if (root.phase===4) {
                // Old repository may still have an in-flight page.
                if (!root.check(map.activate(root.dirB,root.manifestB,{top:true}),"switch B")) return;
                root.phase=5;
                return;
            }
            if (root.phase===5) {
                if (!root.check(map.scrollPosition===0 && map.mapState.repoId===root.manifestB.repoId,"switch position/identity")) return;
                if (!map.rowAt(0)) return;
                if (!root.check(map.rowAt(0).sha===root.sha(200000),"old repo response contaminated B")) return;
                if (!root.check(map.renderedRows<=24 && map.graphSurfaceHeight<480,"renderer bound after switch")) return;
                console.log("GIT_MAP_NATIVE_PASS");
                root.done=true;
                Qt.quit();
            }
        }
    }
}
