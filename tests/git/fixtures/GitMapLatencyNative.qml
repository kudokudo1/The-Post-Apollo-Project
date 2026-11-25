import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/git"
import "services/git/GitMapViewportPolicy.js" as Policy

ShellRoot {
    id: root
    readonly property var manifest: JSON.parse(Quickshell.env("MAP_BENCH_MANIFEST"))
    readonly property string directory: Quickshell.env("MAP_BENCH_DIRECTORY")
    readonly property var targets: [8192,65536,16384,90112,32768,4096,73728,24576,98304,49152,12288,57344]
    property int cursor: 0
    property int target: -1
    property double started: 0
    property bool finished: false
    property bool active: false
    property int ticks: 0
    property var measurements: []
    function fail(message) {
        if (finished) return;
        finished=true;
        console.error("GIT_MAP_LATENCY_FAIL // "+message);
        Qt.quit();
    }
    function settled() {
        const s=map.mapState;
        if (!s || map.activePageStart!==-1 || Object.keys(s.pending).length) return false;
        return Policy.wantedPages(s).every(start=>!!s.cache[start]);
    }
    function sample() {
        if (finished || target<0) return;
        const s=map.mapState;
        if (!s || s.snapshot!==manifest.snapshot || map.bridgeFaulted
                || Object.keys(s.errors).length) { fail("page failure or identity"); return; }
        const visible=Policy.visibleRange(s);
        if (visible.first!==target || Math.abs(map.scrollPosition-target*map.rowHeight)>0.5) return;
        for (let i=visible.first;i<visible.stop;i++) {
            const row=map.rowAt(i);
            if (!row) return;
            if (row.sha!==(i+1).toString(16).padStart(40,"0")) {
                fail("incorrect commit at "+i); return;
            }
        }
        if (map.renderedRows>24 || map.graphSurfaceHeight>480) {
            fail("renderer bound"); return;
        }
        const elapsed=Date.now()-started;
        if (elapsed<0) {fail("clock reversed");return;}
        measurements=measurements.concat([elapsed]);
        target=-1;
        cursor++;
    }
    Window {
        width: 720
        height: 480
        visible: true
        GitMapVirtualViewport {
            id: map
            anchors.fill: parent
            onMapStateChanged: root.sample()
        }
    }
    Timer {
        interval: 10
        repeat: true
        running: !root.finished
        onTriggered: {
            if (++root.ticks>3000) { root.fail("timeout"); return; }
            if (!root.active) {
                if (!map.activate(root.directory,root.manifest,null)) {root.fail("activate");return;}
                root.active=true;
                return;
            }
            if (root.target>=0 || !root.settled()) return;
            if (root.cursor===root.targets.length) {
                root.finished=true;
                console.log("GIT_MAP_LATENCY_PASS "+JSON.stringify(root.measurements));
                Qt.quit();
                return;
            }
            const ordinal=root.targets[root.cursor];
            if (map.rowAt(ordinal)!==null) {root.fail("target already cached");return;}
            root.target=ordinal;
            root.started=Date.now();
            map.scrollTo(ordinal*map.rowHeight);
        }
    }
}
