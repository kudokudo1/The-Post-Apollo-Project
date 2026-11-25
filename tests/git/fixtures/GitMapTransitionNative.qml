import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "widgets/git"

ShellRoot {
    id: root
    readonly property string repo: Quickshell.env("MAP_MANAGED_REPO")
    readonly property string other: Quickshell.env("MAP_OTHER_REPO")
    readonly property string mode: Quickshell.env("MAP_TRANSITION_MODE")
    property string selectedRepo: repo
    property bool operatorActive: false
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property bool witnessed: false
    property bool advanced: false
    property string oldDirectory: ""
    property string oldSnapshot: ""
    property string pendingDirectory: ""
    function check(ok,message) {
        if (!ok) {
            console.error("GIT_MAP_TRANSITION_FAIL "+mode+" "+message);
            done=true; Qt.quit();
        }
        return ok;
    }
    function probe(args) {
        witnessed=false;
        witness.exec(["/usr/bin/python3","-I","-B",Quickshell.shellPath("probe.py")].concat(args));
    }
    GitMapCustodyController { id: pool }
    Process {
        id: witness
        stdout: SplitParser { onRead: function(data) { console.log(data); } }
        stderr: SplitParser { onRead: function(data) { console.error(data); } }
        onExited: function(code,status) {
            if (root.check(code===0 && status===0,"kernel witness")) root.witnessed=true;
        }
    }
    Process {
        id: advance
        onExited: function(code,status) {
            if (root.check(code===0 && status===0,"disposable commit")) root.advanced=true;
        }
    }
    Window {
        width: 720; height: 480; visible: true
        GitMapControlHost {
            id: host
            anchors.fill: parent
            repoRoot: root.selectedRepo
            operatorActive: root.operatorActive
            custodyController: pool
        }
    }
    Timer {
        interval: 25; repeat: true; running: !root.done
        onTriggered: {
            if (++root.ticks>1000) {root.check(false,"timeout phase "+root.phase+" "+host.statusText);return;}
            if (root.phase===0) {
                root.operatorActive=true; root.phase=1;
            } else if (root.phase===1 && host.fullVisible && host.viewport.rowAt(0) && !host.viewport.readerBusy) {
                root.oldDirectory=host.activeDirectory;
                root.oldSnapshot=host.viewport.mapState.snapshot;
                if (root.mode==="page") {
                    host.viewport.scrollTo(260*24+5);
                    root.phase=2;
                    root.probe(["started",root.oldDirectory]);
                } else {
                    host.viewport.scrollTo(5*24+5);
                    root.phase=3;
                }
            } else if (root.phase===2 && root.witnessed) {
                if (!root.check(host.viewport.readerBusy && host.viewport.activePageStart===256,
                    "old page must be in flight")) return;
                root.selectedRepo=root.other;
                root.phase=4;
            } else if (root.phase===3 && host.viewport.currentAnchor() && !host.viewport.readerBusy) {
                if (!root.check(host.viewport.currentAnchor().ordinal===5,"historical anchor")) return;
                root.operatorActive=false;
                advance.exec(["/usr/bin/git","-C",root.repo,"-c","user.name=Fixture",
                    "-c","user.email=fixture@example.invalid","commit","--allow-empty","-m","advance"]);
                root.phase=5;
            } else if (root.phase===5 && root.advanced) {
                root.operatorActive=true;
                root.phase=6;
            } else if (root.phase===6 && host.job==="locate" && host.pendingLease && host.pendingLease.held) {
                root.pendingDirectory=host.pendingResult.directory;
                root.phase=7;
                root.probe(["started",root.pendingDirectory]);
            } else if (root.phase===7 && root.witnessed) {
                if (!root.check(host.job==="locate" && host.fullVisible,"locate still active")) return;
                root.selectedRepo=root.other;
                root.phase=8;
            } else if (root.phase===4 && host.pendingLease && host.pendingLease.held) {
                if (!root.check(!host.fullVisible && host.viewport.readerBusy
                        && host.activeLease && host.activeLease.held
                        && host.activeLease.generation.directory===root.oldDirectory,
                        "replacement must wait for old page completion")) return;
                root.phase=9;
                root.probe(["pair-release",root.oldDirectory,host.pendingResult.directory]);
            } else if (root.phase===8 && pool.leaseCount===1) {
                if (!root.check(!host.fullVisible && host.job==="locate" && !host.pendingLease
                        && host.activeLease && host.activeLease.held,
                        "pending helper retired while locate remains in flight")) return;
                root.phase=9;
                root.probe(["pair-release",root.oldDirectory,root.pendingDirectory]);
            } else if (root.phase===9 && root.witnessed && host.fullVisible && host.viewport.rowAt(0)
                        && !host.viewport.readerBusy && pool.leaseCount===1) {
                if (!root.check(host.activeRepo===root.other && host.activeLease.held
                        && host.viewport.mapState.snapshot!==root.oldSnapshot
                        && host.viewport.mapState.total===1
                        && host.viewport.rowAt(0).subject==="other repository"
                        && host.viewport.scrollPosition===0,
                        "new repo only; stale page or locate must not publish")) return;
                root.phase=10;
                root.probe(["final",host.activeDirectory,root.oldDirectory,root.pendingDirectory||root.oldDirectory]);
            } else if (root.phase===10 && root.witnessed) {
                root.done=true;
                console.log("GIT_MAP_TRANSITION_PASS "+root.mode);
                Qt.quit();
            }
        }
    }
}
