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
    readonly property var manifestA: JSON.parse(Quickshell.env("MAP_FIXTURE_A"))
    readonly property var manifestB: JSON.parse(Quickshell.env("MAP_FIXTURE_B"))
    readonly property string dirA: Quickshell.env("MAP_FIXTURE_DIR_A")
    readonly property string dirB: Quickshell.env("MAP_FIXTURE_DIR_B")
    readonly property var manifestC: JSON.parse(Quickshell.env("MAP_FIXTURE_C"))
    readonly property string dirC: Quickshell.env("MAP_FIXTURE_DIR_C")
    property real expectedY: 0
    property string chosen: ""
    readonly property bool inputTest: Quickshell.env("MAP_FIXTURE_INPUT")==="1"
    property bool inputDone: false
    function runInput(args) {
        inputDone=false;
        input.exec(["/usr/bin/xdotool"].concat(args));
    }
    function move(point) {
        return ["mousemove", String(Math.round(point.x)), String(Math.round(point.y))];
    }
    function dragRail(toBottom) {
        const rail=map.scrollRail;
        const handle=rail.handleItem;
        const start=handle.mapToGlobal(handle.width/2,handle.height/2);
        const end=rail.mapToGlobal(rail.width/2,toBottom?rail.height-1:1);
        runInput(move(start).concat(["mousedown","1","sleep","0.15"],move(end),["sleep","0.15","mouseup","1"]));
    }
    function wheel(button) {
        const viewport=map.scrollViewport;
        const point=viewport.mapToGlobal(viewport.width/2,viewport.height/2);
        runInput(move(point).concat(["click","--repeat","4",String(button)]));
    }
    function dense() {
        if (!check(map.activate(dirC,manifestC,{top:true}),"activate wide merge")) return;
        phase=13;
    }
    function pass() {
        console.log("GIT_MAP_NATIVE_PASS");
        done=true;
        Qt.quit();
    }
    Process {
        id: input
        onExited: function(code,exitStatus) {
            if (!root.check(code===0 && exitStatus===0,"synthetic pointer input failed")) return;
            root.inputDone=true;
        }
    }
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
        title: "Disposable Git Map fixture"
        x: 0; y: 0
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
            if (++root.ticks>700) {
                root.check(false,"timeout phase "+root.phase+" // "+map.bottomStatus);
                return;
            }
            if (root.phase===0) {
                if (!root.check(map.activate(root.dirA,root.manifestA,null),"activate A")) return;
                root.phase=1;
                return;
            }
            if (root.phase===1) {
                if (map.activePageStart!==0) return;
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
                // Require actual outstanding old-repository work, not a race.
                if (map.activePageStart!==49920) return;
                if (!root.check(map.activate(root.dirB,root.manifestB,{top:true}),"switch B")) return;
                root.phase=5;
                return;
            }
            if (root.phase===5) {
                if (!root.check(map.scrollPosition===0 && map.mapState.repoId===root.manifestB.repoId,"switch position/identity")) return;
                if (!map.rowAt(0)) return;
                if (!root.check(map.rowAt(0).sha===root.sha(200000),"old repo response contaminated B")) return;
                if (!root.check(map.nodeGlyph(map.rowAt(0))==="✧","legacy ordinary commit glyph")) return;
                if (!root.check(map.renderedRows<=24 && map.graphSurfaceHeight<480,"renderer bound after switch")) return;
                map.scrollTo(124*24+5);
                root.expectedY=map.scrollPosition;
                root.phase=6;
                return;
            }
            if (root.phase===6) {
                if (!root.check(map.scrollPosition===root.expectedY,"merge page moved viewport")) return;
                const a=map.mapState.cache[0], b=map.mapState.cache[128];
                if (!a || !b || !map.rowAt(130)) return;
                const edge=a.rows[0].parents[1];
                if (!root.check(edge.ordinal===130 && edge.sha===map.rowAt(130).sha
                        && edge.lane===map.rowAt(130).lane
                        && b.frontier.some(f=>f.sha===edge.sha && f.lane===edge.lane),
                        "cross-page branch continuity")) return;
                map.visible=false;
                root.phase=7;
                return;
            }
            if (root.phase===7) {
                map.visible=true;
                if (!root.check(map.scrollPosition===root.expectedY,"hidden candidate lost position")) return;
                if (!root.inputTest) {root.dense();return;}
                root.dragRail(true);
                root.phase=8;
                return;
            }
            if (root.phase===8) {
                if (!root.inputDone) return;
                const bottom=map.scrollExtent-map.scrollViewport.height;
                if (!root.check(Math.abs(map.scrollPosition-bottom)<0.5,"star drag did not reach true bottom")) return;
                root.expectedY=map.scrollPosition;
                root.wheel(5);
                root.phase=9;
                return;
            }
            if (root.phase===9) {
                if (!root.inputDone) return;
                if (!root.check(Math.abs(map.scrollPosition-root.expectedY)<0.5,"wheel at bottom wrapped or moved")) return;
                root.wheel(4);
                root.phase=10;
                return;
            }
            if (root.phase===10) {
                if (!root.inputDone || map.scrollViewport.moving) return;
                if (!root.check(map.scrollPosition<root.expectedY,"reverse wheel did not move upward")) return;
                root.dragRail(false);
                root.phase=11;
                return;
            }
            if (root.phase===11) {
                if (!root.inputDone) return;
                if (!root.check(Math.abs(map.scrollPosition)<0.5,"star drag did not return to top")) return;
                root.wheel(4);
                root.phase=12;
                return;
            }
            if (root.phase===12) {
                if (!root.inputDone) return;
                if (!root.check(Math.abs(map.scrollPosition)<0.5,"wheel at top wrapped")) return;
                root.dense();
                return;
            }
            if (root.phase===13) {
                if (!map.rowAt(32)) return;
                if (!root.check(map.mapState.maxLane>=31 && map.graphSurfaceWidth>190 && map.laneMaxOffset>0,"responsive wide graph and pan")) return;
                if (!root.check(map.graphLaneVisible(0) && !map.graphLaneVisible(31),"initial lane window")) return;
                map.scrollTo(32*24);
                root.expectedY=map.scrollPosition;
                if (!root.check(map.choose(32) && map.graphLaneVisible(map.rowAt(32).lane),"select high-lane commit reveals exact star")) return;
                if (!root.check(map.scrollPosition===root.expectedY && map.renderedRows<=24 && map.graphSurfaceHeight<480,"horizontal navigation preserves bounded vertical viewport")) return;
                map.setLaneOffset(99999);
                if (!root.check(map.laneOffset===map.laneMaxOffset && map.graphLaneVisible(map.mapState.maxLane),"last lane reachable")) return;
                map.setLaneOffset(-99);
                if (!root.check(map.laneOffset===0 && map.graphLaneVisible(0),"first lane reachable")) return;
                console.log("GIT_MAP_DENSE_LANES_PASS");
                map.scrollTo(99999999);
                root.expectedY=map.scrollPosition;
                root.phase=14;
                return;
            }
            if (root.phase===14) {
                if (!map.rowAt(63)) return;
                if (!root.check(map.visibleLaneCount===1 && map.graphSurfaceWidth===2*map.laneMargin && map.laneOffset===map.laneMinOffset,"graph contracts in narrow tail")) return;
                if (!root.check(map.scrollPosition===root.expectedY,"contraction preserves vertical position")) return;
                map.scrollTo(0);
                root.phase=15;
                return;
            }
            if (root.phase===15) {
                if (!map.rowAt(0)) return;
                if (!root.check(map.visibleLaneCount>=32 && map.graphSurfaceWidth>190 && map.laneMaxOffset>map.laneMinOffset && map.scrollPosition===0,"graph re-expands on wide ancestry")) return;
                console.log("GIT_MAP_REACTIVE_LANES_PASS");
                root.pass();
            }
        }
    }
}
