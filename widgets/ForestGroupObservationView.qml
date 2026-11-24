import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/forest/ForestGroupObservationPolicy.js" as Policy

// Operator-selected existing group only. No discovery or automatic sampling.
Column {
    id: pane
    spacing: 4
    property bool expanded: false
    property bool busy: false
    property bool discard: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property bool refused: false
    property string output: ""
    property string submittedGroup: ""
    property string observedAt: ""
    property var report: null
    property string status: "NOT CHECKED"

    function clearReport() {
        report = null;
        observedAt = "";
        status = "NOT CHECKED";
        if (busy) discard = true;
    }
    onVisibleChanged: if (!visible) clearReport()
    onExpandedChanged: if (!expanded) clearReport()

    function checkGroup() {
        if (!visible || !expanded || busy || worker.running) return;
        clearReport();
        if (!Policy.validGroup(groupInput.text)) {
            status = "INVALID NON-ROOT GROUP PATH";
            return;
        }
        submittedGroup = groupInput.text;
        discard = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        refused = false;
        output = "";
        busy = true;
        status = "SAMPLING";
        worker.exec(["/usr/bin/python3", "-B",
            Quickshell.shellPath("scripts/forest/cgroup_observation_i5.py"),
            "observe", "--cgroup", submittedGroup, "--samples", "5", "--interval-ms", "250"]);
    }
    function finish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen) return;
        if (!discard && visible && expanded && submittedGroup === groupInput.text) {
            report = refused ? null : Policy.parse(output);
            status = report ? "LAST OBSERVATION // READ ONLY" : "OBSERVATION UNAVAILABLE";
            observedAt = report ? Qt.formatTime(new Date(), "HH:mm:ss") : "";
        }
        output = "";
        submittedGroup = "";
        busy = false;
    }
    Process {
        id: worker
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (!pane.busy) return;
                if (pane.stdoutSeen) pane.refused = true;
                pane.stdoutSeen = true;
                pane.output = String(this.text || "");
                pane.finish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (!pane.busy) return;
                if (pane.stderrSeen || String(this.text || "").trim().length) pane.refused = true;
                pane.stderrSeen = true;
                pane.finish();
            }
        }
        onExited: function(code,exitStatus) {
            if (!pane.busy) return;
            if (pane.exitSeen || code !== 0 || exitStatus !== 0) pane.refused = true;
            pane.exitSeen = true;
            pane.finish();
        }
    }
    ActionButton {
        width: pane.width
        height: 27
        label: pane.expanded ? "− RESOURCE GROUP // I5" : "+ RESOURCE GROUP // I5"
        onLeftClicked: pane.expanded = !pane.expanded
    }
    Column {
        width: pane.width
        visible: pane.expanded
        spacing: 4
        GohuText {
            width: parent.width
            text: "SELECT YOUR EXISTING NON-ROOT CGROUP // NO SUDO"
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 27
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            clip: true
            TextInput {
                id: groupInput
                anchors.fill: parent
                anchors.margins: 5
                color: Colors.cyan
                font.pixelSize: 10
                maximumLength: 513
                readOnly: pane.busy
                selectByMouse: true
                Accessible.name: "Existing authorized non-root cgroup hierarchy path"
                onTextChanged: pane.clearReport()
            }
            GohuText {
                anchors.centerIn: parent
                visible: !groupInput.text.length
                text: "ENTER EXISTING GROUP PATH"
                font.pixelSize: 9
                color: Colors.orange
            }
        }
        ActionButton {
            width: parent.width
            height: 27
            available: !pane.busy && Policy.validGroup(groupInput.text)
            label: pane.busy ? "SAMPLING..." : "CHECK GROUP"
            onLeftClicked: pane.checkGroup()
        }
        GohuText {
            width: parent.width
            text: pane.status + (pane.observedAt ? " / " + pane.observedAt : "")
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        Column {
            width: parent.width
            visible: !!pane.report
            spacing: 3
            Repeater {
                model: [
                    {label:"CHARGED MEMORY FIRST",key:"charged_memory_first_bytes"},
                    {label:"CHARGED MEMORY LAST",key:"charged_memory_last_bytes"},
                    {label:"SAMPLED MAXIMUM",key:"charged_memory_sampled_max_bytes"},
                    {label:"SAMPLED INCREASE",key:"charged_memory_sampled_increase_bytes"},
                    {label:"KERNEL PEAK (NOT TRIAL PEAK)",key:"kernel_memory_peak_last_bytes_reported"},
                    {label:"SWAP",key:"swap_last_bytes_reported"},
                    {label:"ANON",key:"anon_last_bytes_reported"},
                    {label:"FILE",key:"file_last_bytes_reported"},
                    {label:"SHMEM (OVERLAPPING COUNTER)",key:"shmem_last_bytes_reported"}
                ]
                delegate: GohuText {
                    required property var modelData
                    width: pane.width
                    text: modelData.label + " // " + Policy.mib(pane.report ? pane.report[modelData.key] : null)
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
            GohuText {
                width: parent.width
                text: "LOCAL LIMIT // " + Policy.limit(pane.report)
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "CPU USAGE DELTA // " + Policy.cpu(pane.report ? pane.report.cpu_usage_usec_delta : null)
                    + " / USER " + Policy.cpu(pane.report ? pane.report.cpu_user_usec_delta : null)
                    + " / SYSTEM " + Policy.cpu(pane.report ? pane.report.cpu_system_usec_delta : null)
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "TASKS // " + (pane.report && pane.report.tasks_last_reported !== null ? pane.report.tasks_last_reported : "?")
                    + " / SAMPLES " + (pane.report ? pane.report.sample_count : "?")
                    + " / ELAPSED " + (pane.report ? (pane.report.elapsed_ns/1000000000).toFixed(3) + " s" : "?")
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
        GohuText {
            width: parent.width
            text: "GROUP + DESCENDANTS // HISTORICAL COUNTERS, NOT MODEL MEMORY OR FREE CAPACITY"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
