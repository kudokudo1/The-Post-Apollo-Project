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
                if (!host.fullVisible) return;
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
