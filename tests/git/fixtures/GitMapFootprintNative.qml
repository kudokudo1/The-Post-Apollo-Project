import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/git"

ShellRoot {
    id: root
    readonly property string repo: Quickshell.env("MAP_FOOTPRINT_REPO")
    readonly property bool enabled: Quickshell.env("MAP_FOOTPRINT_MODE")==="on"
    property bool active: true
    property int ticks: 0
    property int phase: 0
    function ready(host) {
        return host.fullVisible && !host.busy && !host.viewport.readerBusy
            && host.viewport.rowAt(0) && host.viewport.mapState.total===1000;
    }
    GitMapCustodyController { id: pool }
    Window {
        width: 720; height: 480; visible: true
        GitMapControlHost {
            id: first
            anchors.fill: parent
            repoRoot: root.repo
            operatorActive: root.active
            custodyController: root.enabled ? pool : null
        }
    }
    Window {
        width: 720; height: 480; visible: true
        GitMapControlHost {
            id: second
            anchors.fill: parent
            repoRoot: root.repo
            operatorActive: root.active
            custodyController: root.enabled ? pool : null
        }
    }
    Timer {
        interval: 100
        repeat: true
        onTriggered: {
            if (++root.ticks>200) {
                console.error("GIT_MAP_FOOTPRINT_FAIL timeout");
                Qt.quit();
                return;
            }
            if (root.phase===0 && root.ready(first) && root.ready(second)) {
                if (first.viewport.mapState.snapshot!==second.viewport.mapState.snapshot
                    || pool.heldCount!==(root.enabled?1:0)
                    || (root.enabled && (first.activeLease!==second.activeLease
                        || first.activeLease.owners!==2))) {
                    console.error("GIT_MAP_FOOTPRINT_FAIL ownership");
                    Qt.quit(); return;
                }
                root.active=false;
                root.phase=1;
            } else if (root.phase===1 && root.ready(first) && root.ready(second)) {
                console.log("GIT_MAP_FOOTPRINT_READY "+first.viewport.mapState.snapshot);
                root.phase=2;
            }
        }
    }
}
