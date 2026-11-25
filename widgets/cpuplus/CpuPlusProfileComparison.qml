import QtQuick
import Quickshell.Io
import "../../components"
import "CpuPlusProfileCatalog.js" as Catalog
import "CpuPlusProfileComparison.js" as Compare
import "CpuPlusZramPolicy.js" as Zram
import "CpuPlusAdvancedPolicy.js" as Advanced

// Explicit read only. No polling, startup command or protected write.
// The parent snapshot supplies priority and locator/size hints; sysfs/proc
// reads are sequential and are not protected device-identity evidence.
Column {
    id: root
    objectName: "cpuplusProfileComparison"
    required property var draft
    required property var sample
    required property bool observationReady
    required property bool operationBusy
    property Item controlsTarget: null
    property var comparison: null
    property var pending: null
    property var capturedSample: null
    property string status: "NOT COMPARED"
    property double completedAt: 0
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property string output: ""
    readonly property bool canRead: visible && observationReady && !operationBusy && !reader.running && pending===null
        && Catalog.validDraft(draft) && (draft.zram!==null || draft.priority!==null || draft.advanced!==null)
    function invalidate() {
        comparison=null; pending=null; capturedSample=null; completedAt=0;
        status="RECHECK REQUIRED";
        if(reader.running)reader.running=false;
    }
    onDraftChanged: invalidate()
    onOperationBusyChanged: if(operationBusy)invalidate()
    onVisibleChanged: if(!visible)invalidate()
    // A finished report is a dated observation, not continuously live.
    // While reading, discard any result if the parent snapshot changed.
    onSampleChanged: if(pending!==null && sample!==capturedSample)invalidate()
    function refresh() {
        if(!canRead)return;
        const next=Compare.plan(draft,sample,observationReady,Catalog.validDraft,Zram.algorithmPath,Advanced.paths);
        if(!next)return;
        comparison=null; completedAt=0; capturedSample=sample; pending=next;
        received=false; exited=false; exitOk=false; output="";
        status="READING";
        if(!next.paths.length){received=true;exited=true;exitOk=true;finish();return;}
        reader.command=["/usr/bin/timeout","--kill-after=1s","3s","/usr/bin/cat"].concat(next.paths);
        reader.running=true;
    }
    function finish() {
        if(!pending||!received||!exited)return;
        if(!observationReady||operationBusy||sample!==capturedSample){invalidate();return;}
        comparison=Compare.compare(pending,output,exitOk,Zram.parseAlgorithms,Advanced.parse,Advanced.previewSpec,Advanced.validPreview);
        pending=null;capturedSample=null;output="";
        completedAt=Date.now();
        status=comparison?(exitOk?"OBSERVED // HISTORICAL":"PARTIAL // READ FAILED"):"UNAVAILABLE";
    }
    Process {
        id: reader
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if(!root.pending)return;
                root.output=this.text;root.received=true;root.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,exitStatus) {
            if(!root.pending)return;
            root.exitOk=code===0&&exitStatus===0;root.exited=true;root.finish();
        }
    }
    spacing: 4
    GohuText {
        width: parent.width
        text: "EXTENDED ACTUAL VS TARGET // "+root.status
            +(root.completedAt?"\nCOMPARISON AT // "+new Date(root.completedAt).toLocaleString():"")
            +"\nPRIORITY FROM MEMORY SNAPSHOT; SYSFS / VM READS SEQUENTIAL. NOT DEVICE IDENTITY OR APPLY AUTHORITY."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.comparison?root.comparison.rows:[]
        delegate: GohuText {
            required property var modelData
            width: root.width
            text: modelData.label+"\nACTUAL // "+modelData.actual+"\nTARGET // "+modelData.target
                +"\n"+modelData.status+(modelData.delta===null?"":" // CHANGE "+(modelData.delta>0?"+":"")+modelData.delta)
            color: Colors.cyan
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
        }
    }
    ActionButton {
        parent: root.controlsTarget || root
        objectName: "cpuplusProfileCompare"
        width: parent.width
        height: 26
        label: root.pending!==null?"COMPARING":"COMPARE EXTENDED"
        available: root.canRead
        contentPadding: 2
        acceptedButtons: Qt.LeftButton
        keyboardActivationSignal: "leftClicked"
        onLeftClicked: root.refresh()
    }
}
