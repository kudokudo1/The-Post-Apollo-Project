import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io

// Disposable native fixture, not mounted in the production widget.
ShellRoot {
    id: root
    readonly property var oldGen: JSON.parse(Quickshell.env("CUSTODY_OLD"))
    readonly property var newGen: JSON.parse(Quickshell.env("CUSTODY_NEW"))
    readonly property bool crashMode: Quickshell.env("CUSTODY_MODE")==="crash"
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property bool firstHeld: false
    property bool secondHeld: false
    property bool nextHeld: false
    property bool firstClosed: false
    property bool secondClosed: false
    property bool nextClosed: false
    property bool probeDone: false
    function fail(message) {
        if (done) return;
        done=true;
        console.error("GIT_MAP_CUSTODY_FAIL // "+message);
        Qt.quit();
    }
    function readerCommand(g) {
        return ["/usr/bin/python3","-I","-B",Quickshell.shellPath("scripts/git_map_reader_candidate.py"),
            g.repoId,g.key,g.manifest.snapshot];
    }
    function receipt(data,g) {
        try {
            const v=JSON.parse(data);
            return v.schema==="post-apollo-git-map-reader-candidate-v1" && v.status==="HELD"
                && v.repoId===g.repoId && v.key===g.key && v.snapshot===g.manifest.snapshot
                && v.reclamationAllowed===false;
        } catch (error) {return false;}
    }
    function checkLocks(oldLocked,newLocked,pids) {
        probeDone=false;
        witness.exec(["/usr/bin/python3","-I","-B",Quickshell.shellPath("probe.py"),
            oldGen.directory,newGen.directory,oldLocked?"1":"0",newLocked?"1":"0"]
            .concat(pids.map(pid=>String(pid))));
    }
    Window { id: firstView; width: 320; height: 160; visible: true }
    Window { id: secondView; width: 320; height: 160; visible: true }
    Process {
        id: first
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                if (root.firstHeld || !root.receipt(data,root.oldGen)) root.fail("first receipt");
                else root.firstHeld=true;
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            if (root.phase!==3 || code!==0 || status!==0) root.fail("first unexpected exit");
            else root.firstClosed=true;
        }
    }
    Process {
        id: second
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                if (root.secondHeld || !root.receipt(data,root.oldGen)) root.fail("second receipt");
                else root.secondHeld=true;
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            if (root.phase!==5 || code!==0 || status!==0) root.fail("second unexpected exit");
            else root.secondClosed=true;
        }
    }
    Process {
        id: replacement
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                if (root.nextHeld || !root.receipt(data,root.newGen)) root.fail("replacement receipt");
                else root.nextHeld=true;
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            if (root.phase!==7 || code!==0 || status!==0) root.fail("replacement unexpected exit");
            else root.nextClosed=true;
        }
    }
    Process {
        id: witness
        stdout: SplitParser { onRead: function(data) { console.log(data); } }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            if (code!==0 || status!==0) root.fail("exclusive lock witness failed");
            else root.probeDone=true;
        }
    }
    Timer {
        interval: 25
        repeat: true
        running: !root.done
        onTriggered: {
            if (++root.ticks>800) {root.fail("timeout phase "+root.phase);return;}
            if (root.phase===0) {
                root.phase=1;
                first.exec(root.readerCommand(root.oldGen));
                second.exec(root.readerCommand(root.oldGen));
            } else if (root.phase===1 && root.firstHeld && root.secondHeld) {
                firstView.visible=false;
                secondView.visible=false;
                root.phase=2;
                root.checkLocks(true,false,[first.processId,second.processId]);
            } else if (root.phase===2 && root.probeDone) {
                replacement.exec(root.readerCommand(root.newGen));
                root.phase=3;
            } else if (root.phase===3 && root.nextHeld && first.stdinEnabled) {
                first.stdinEnabled=false;
            } else if (root.phase===3 && root.firstClosed) {
                root.phase=4;
                root.checkLocks(true,true,[second.processId,replacement.processId]);
            } else if (root.phase===4 && root.probeDone) {
                if (root.crashMode) {
                    root.phase=9;
                    console.log("GIT_MAP_CUSTODY_CRASH_READY");
                } else {
                    root.phase=5;
                    second.stdinEnabled=false;
                }
            } else if (root.phase===5 && root.secondClosed) {
                root.phase=6;
                root.checkLocks(false,true,[replacement.processId]);
            } else if (root.phase===6 && root.probeDone) {
                root.phase=7;
                replacement.stdinEnabled=false;
            } else if (root.phase===7 && root.nextClosed) {
                root.phase=8;
                root.checkLocks(false,false,[]);
            } else if (root.phase===8 && root.probeDone) {
                root.done=true;
                console.log("GIT_MAP_CUSTODY_NATIVE_PASS");
                Qt.quit();
            }
        }
    }
}
