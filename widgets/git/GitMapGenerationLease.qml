import QtQuick
import Quickshell
import Quickshell.Io

// Candidate-only lease, held by one helper per generation.
Item {
    id: root
    visible: false
    property var generation: null
    property int owners: 0
    property string custodyState: "NEW"
    property bool reaped: false
    readonly property bool held: custodyState==="HELD" && keeper.running
    readonly property bool terminal: custodyState==="FAILED" || custodyState==="CLOSED"
    signal ended()
    function start() {
        if (custodyState!=="NEW" || !generation) return false;
        custodyState="STARTING";
        deadline.restart();
        keeper.exec(["/usr/bin/python3","-I","-B",
            Quickshell.shellPath("scripts/git_map_reader_candidate.py"),
            generation.repoId,generation.key,generation.manifest.snapshot]);
        return true;
    }
    function stop() {
        deadline.stop();
        if (terminal) return;
        custodyState="CLOSING";
        keeper.stdinEnabled=false;
    }
    function fail() {
        deadline.stop();
        custodyState="FAILED";
        keeper.stdinEnabled=false;
        keeper.running=false;
    }
    Timer {
        id: deadline
        interval: 5000
        repeat: false
        onTriggered: root.fail()
    }
    Process {
        id: keeper
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                if (root.custodyState==="CLOSING") return;
                let m=null;
                try { if (data.length<=2048) m=JSON.parse(data); } catch (error) {}
                const g=root.generation;
                if (root.custodyState!=="STARTING" || !m || !g
                    || m.schema!=="post-apollo-git-map-reader-candidate-v1"
                    || m.status!=="HELD" || m.repoId!==g.repoId || m.key!==g.key
                    || m.snapshot!==g.manifest.snapshot || m.reclamationAllowed!==false) {
                    root.fail(); return;
                }
                deadline.stop();
                root.custodyState="HELD";
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            deadline.stop();
            root.custodyState=root.custodyState==="CLOSING" && code===0 && status===0
                ? "CLOSED" : "FAILED";
            root.reaped=true;
            root.ended();
        }
    }
}
