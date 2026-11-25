import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/git"

ShellRoot {
    id: root
    readonly property string repo: Quickshell.env("MAP_MANAGED_REPO")
    property bool firstActive: false
    property bool secondActive: false
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property bool advanced: false
    property string prior: ""
    property var second: secondLoader.item
    property bool witnessed: false
    property string oldDirectory: ""
    property string currentDirectory: ""
    function check(ok,message) {
        if (!ok) {
            console.error("GIT_MAP_SHARED_CUSTODY_FAIL "+message);
            done=true; Qt.quit();
        }
        return ok;
    }
    GitMapCustodyController { id: pool }
    Process {
        id: advance
        onExited: function(code,status) {
            if (root.check(code===0 && status===0,"disposable commit")) root.advanced=true;
        }
    }
    Window {
        width: 720; height: 480; visible: true
        GitMapControlHost {
            id: first
            anchors.fill: parent
            repoRoot: root.repo
            operatorActive: root.firstActive
            custodyController: pool
        }
    }
    Window {
        width: 720; height: 480; visible: true
        Loader {
            id: secondLoader
            anchors.fill: parent
            active: true
            sourceComponent: GitMapControlHost {
                repoRoot: root.repo
                operatorActive: root.secondActive
                custodyController: pool
            }
        }
    }
    Process {
        id: witness
        stdout: SplitParser { onRead: function(data) { console.log(data); } }
        stderr: SplitParser { onRead: function(data) { console.error(data); } }
        onExited: function(code,status) {
            if (root.check(code===0 && status===0,"independent kernel witness")) root.witnessed=true;
        }
    }
    function probe(mode,lease,oldPath) {
        witnessed=false;
        witness.exec(["/usr/bin/python3","-I","-B",Quickshell.shellPath("probe.py"),
            mode,lease.generation.directory,String(lease.helperPid),
            lease.generation.manifest.snapshot,oldPath||""]);
    }
    Timer {
        interval: 50; repeat: true; running: !root.done
        onTriggered: {
            if (++root.ticks>750) {root.check(false,"timeout "+root.phase+" "+first.statusText+" "+second.statusText);return;}
            if (root.phase===0) {
                if (!root.check(pool.leaseCount===0,"hidden startup acquired lease")) return;
                root.firstActive=true; root.phase=1;
            } else if (root.phase===1 && first.fullVisible && first.viewport.rowAt(0)) {
                root.prior=first.viewport.mapState.snapshot;
                root.oldDirectory=first.activeDirectory;
                root.secondActive=true; root.phase=2;
            } else if (root.phase===2 && second.fullVisible && second.viewport.rowAt(0)) {
                if (!root.check(first.activeLease===second.activeLease && pool.leaseCount===1
                        && first.activeLease.owners===2 && first.activeLease.held,"same generation shares one helper")) return;
                root.firstActive=false; root.secondActive=false;
                root.phase=20;
                root.probe("held",first.activeLease,"");
            } else if (root.phase===20 && root.witnessed) {
                root.phase=3;
                advance.exec(["/usr/bin/git","-C",root.repo,"-c","user.name=Fixture",
                    "-c","user.email=fixture@example.invalid","commit","--allow-empty","-m","next"]);
            } else if (root.phase===3 && root.advanced) {
                if (!root.check(first.activeLease===second.activeLease && pool.heldCount===1
                    && first.activeLease.owners===2,"hidden views retain custody")) return;
                root.firstActive=true; root.phase=4;
            } else if (root.phase===4 && first.fullVisible && first.viewport.rowAt(0)
                    && first.viewport.mapState.snapshot!==root.prior) {
                if (!root.check(second.viewport.mapState.snapshot===root.prior
                    && first.activeLease!==second.activeLease && pool.heldCount===2
                    && second.activeLease.owners===1,"old hidden generation remains protected")) return;
                root.currentDirectory=first.activeDirectory;
                root.phase=40;
                root.probe("overlap",first.activeLease,root.oldDirectory);
            } else if (root.phase===40 && root.witnessed) {
                root.secondActive=true; root.phase=5;
            } else if (root.phase===5 && second.fullVisible && second.viewport.rowAt(0)
                    && second.viewport.mapState.snapshot===first.viewport.mapState.snapshot
                    && pool.leaseCount===1) {
                if (!root.check(first.activeLease===second.activeLease && first.activeLease.owners===2
                    && first.activeLease.held,"handoff converges to one held helper")) return;
                root.phase=6;
                secondLoader.active=false;
            } else if (root.phase===6 && !root.second && first.activeLease.owners===1) {
                if (!root.check(pool.leaseCount===1 && first.fullVisible,"destroyed host releases only its owner")) return;
                if (!first.canRequest) return;
                first.searchQuery="commit 20";
                if (!root.check(first.searchHistory(false),"start finite search before helper loss")) return;
                root.phase=7;
                root.probe("kill",first.activeLease,root.oldDirectory);
            } else if (root.phase===7 && root.witnessed && pool.leaseCount===0) {
                if (!root.check(!first.fullVisible && !first.activeLease && !first.searchHistory(false)
                        && first.statusText==="CUSTODY LOST // REOPEN TO RECHECK",
                        "helper loss must refuse indexed use")) return;
                if (!root.check(first.busy && first.job==="search" && first.custodyLost,
                        "finite search remains in flight after helper loss")) return;
                root.phase=70;
                root.witnessed=false;
                witness.exec(["/usr/bin/python3","-I","-B",Quickshell.shellPath("probe.py"),"release"]);
            } else if (root.phase===70 && root.witnessed && !first.busy) {
                if (!root.check(!first.lastMatch && first.custodyLost && !first.fullVisible
                        && pool.leaseCount===0,"stale search discarded; no spontaneous retry")) return;
                root.phase=8;
                root.firstActive=false;
            } else if (root.phase===8) {
                if (!root.check(pool.leaseCount===0,"no automatic helper restart")) return;
                root.firstActive=true;
                root.phase=9;
            } else if (root.phase===9 && first.fullVisible && first.activeLease && first.viewport.rowAt(0)) {
                if (!root.check(pool.leaseCount===1 && first.activeLease.owners===1
                        && first.activeDirectory===root.currentDirectory,"explicit reopen reacquires custody")) return;
                root.phase=10;
                root.probe("held",first.activeLease,"");
            } else if (root.phase===10 && root.witnessed) {
                root.done=true; console.log("GIT_MAP_SHARED_CUSTODY_PASS"); Qt.quit();
            }
        }
    }
}
