import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/git"

ShellRoot {
    id: root
    readonly property string repo: Quickshell.env("MAP_FOOTPRINT_REPO")
    readonly property bool enabled: Quickshell.env("MAP_FOOTPRINT_MODE")==="on"
    property bool firstActive: false
    property bool secondActive: false
    property bool hidden: false
    property int ticks: 0
    property int phase: 0
    function ready(host) {
        return host.fullVisible && !host.busy && !host.viewport.readerBusy
            && host.viewport.rowAt(0) && host.viewport.mapState.total===1000;
    }
    GitMapCustodyController { id: pool }
    Window {
        width: 720; height: 480; visible: !root.hidden
        GitMapControlHost {
            id: first
            anchors.fill: parent
            repoRoot: root.repo
            operatorActive: root.firstActive
            custodyController: root.enabled ? pool : null
        }
    }
    Window {
        width: 720; height: 480; visible: !root.hidden
        GitMapControlHost {
            id: second
            anchors.fill: parent
            repoRoot: root.repo
            operatorActive: root.secondActive
            custodyController: root.enabled ? pool : null
        }
    }
    Timer {
        interval: 100
        repeat: true
        onTriggered: {
            if (++root.ticks>150 && root.phase!==4) {
                console.error("GIT_MAP_FOOTPRINT_FAIL timeout phase "+root.phase+" "+first.statusText+" / "+second.statusText);
                Qt.quit();
                return;
            }
            if (root.phase!==4 && root.ticks%10===0)
                console.log("GIT_MAP_FOOTPRINT_PROGRESS "+root.phase+" "+first.statusText+" / "+second.statusText
                    +" jobs "+first.jobsStarted+"/"+second.jobsStarted+" busy "+first.viewport.readerBusy+"/"+second.viewport.readerBusy
                    +" rows "+(first.viewport.mapState ? first.viewport.mapState.total : -1)+"/"+(second.viewport.mapState ? second.viewport.mapState.total : -1));
            if (root.phase===0) {
                root.firstActive=true;
                root.phase=1;
            } else if (root.phase===1 && root.ready(first)) {
                root.secondActive=true;
                root.phase=2;
            } else if (root.phase===2 && root.ready(first) && root.ready(second)) {
                if (first.viewport.mapState.snapshot!==second.viewport.mapState.snapshot
                    || pool.heldCount!==(root.enabled?1:0)
                    || (root.enabled && (first.activeLease!==second.activeLease
                        || first.activeLease.owners!==2))) {
                    console.error("GIT_MAP_FOOTPRINT_FAIL ownership");
                    Qt.quit(); return;
                }
                root.firstActive=false;
                root.secondActive=false;
                root.hidden=true;
                root.phase=3;
            } else if (root.phase===3 && root.ready(first) && root.ready(second)) {
                console.log("GIT_MAP_FOOTPRINT_READY "+first.viewport.mapState.snapshot);
                root.phase=4;
                stop();
            }
        }
    }
}
