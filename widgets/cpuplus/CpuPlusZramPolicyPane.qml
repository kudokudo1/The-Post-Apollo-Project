import QtQuick
import Quickshell.Io
import "../../components"
import "CpuPlusZramPolicy.js" as Policy

// Demand-loaded, explicit read only. No timer, shell, device writes or apply.
Column {
    id: root
    objectName: "cpuplusZramPolicyPane"
    required property var sample
    required property bool operationBusy
    spacing: 6
    readonly property var devices: Policy.activeDevices(sample)
    signal profileCopyRequested(var value)
    function copyToProfile() {
        if(!canStage||!received||!exited||!exitOk||!observation.options.includes(targetAlgorithm)
            ||!Policy.observedDevice(sample,selectedDevice,selectedSize))return;
        profileCopyRequested({deviceHint:selectedDevice,sizeKiB:selectedSize,algorithm:targetAlgorithm});
    }
    property string selectedDevice: ""
    property real selectedSize: 0
    property var observation: null
    property string targetAlgorithm: ""
    property string feedback: "SELECT ACTIVE ZRAM"
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property string raw: ""
    readonly property bool selectionLive: Policy.observedDevice(sample, selectedDevice, selectedSize) !== null
    readonly property bool canStage: visible && selectionLive && !operationBusy
        && !reader.running && observation !== null
    function invalidate() {
        observation = null;
        targetAlgorithm = "";
    }
    onSampleChanged: {
        if (sample && selectedDevice && !selectionLive) {
            invalidate();
            feedback = "DEVICE CHANGED // RESELECT";
            selectedDevice = "";
            selectedSize = 0;
        }
    }
    onOperationBusyChanged: if (operationBusy) {
        invalidate();
        feedback = "OPERATION // REFRESH REQUIRED";
    }
    function selectDevice(name) {
        if (!visible || operationBusy || reader.running) return;
        const row = devices.find(entry => entry.name === name);
        if (!row) return;
        selectedDevice = row.name;
        selectedSize = row.size;
        refresh();
    }
    function refresh() {
        const path = Policy.algorithmPath(selectedDevice);
        if (!visible || operationBusy || reader.running || !selectionLive || !path) return;
        invalidate();
        received = false;
        exited = false;
        exitOk = false;
        raw = "";
        feedback = "READING";
        reader.command = ["/usr/bin/cat", path];
        reader.running = true;
    }
    function finish() {
        if (!received || !exited) return;
        observation = exitOk && selectionLive && !operationBusy
            ? Policy.parseAlgorithms(raw) : null;
        targetAlgorithm = observation ? observation.actual : "";
        feedback = observation ? "OBSERVED // EXPLICIT READ" : "ALGORITHMS UNAVAILABLE";
        raw = "";
    }
    function stageAlgorithm(name) {
        if (!canStage || !observation.options.includes(name)) return;
        targetAlgorithm = name;
    }
    Process {
        id: reader
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                root.raw = this.text;
                root.received = true;
                root.finish();
            }
        }
        onExited: function(code, exitStatus) {
            root.exited = true;
            root.exitOk = code === 0 && exitStatus === 0;
            root.finish();
        }
    }
    GohuText {
        width: parent.width
        text: "ZRAM // COMPRESSION"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        visible: root.devices.length === 0
        text: root.sample ? "NO ACTIVE ZRAM OBSERVED" : "LIVE DATA UNAVAILABLE"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: root.devices
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 28
            label: modelData.name
            selected: root.selectionLive && root.selectedDevice === modelData.name
            available: !root.operationBusy && !reader.running
            onLeftClicked: root.selectDevice(modelData.name)
        }
    }
    Row {
        width: parent.width
        height: 28
        spacing: 4
        GohuText {
            width: Math.max(0,parent.width - refreshButton.width - parent.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            text: root.feedback
            color: root.observation && root.selectionLive ? Colors.cyan : Colors.orange
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        ActionButton {
            id: refreshButton
            width: 76
            height: parent.height
            label: "REFRESH"
            accentColor: Colors.yellow
            idleFillColor: Colors.yellow
            idleForegroundColor: Colors.magenta
            idleBorderColor: Colors.orange
            contentPadding: 2
            available: root.selectionLive && !root.operationBusy && !reader.running
            onLeftClicked: root.refresh()
        }
    }
    Row {
        width: parent.width
        spacing: 4
        Repeater {
            model: [
                {label:"ACTUAL",value:root.selectionLive && root.observation ? root.observation.actual : "—",accent:Colors.cyan},
                {label:"TARGET",value:root.selectionLive && root.targetAlgorithm ? root.targetAlgorithm : "—",accent:Colors.yellow}
            ]
            delegate: Rectangle {
                required property var modelData
                width: Math.max(0,(root.width - 4)/2)
                height: 40
                color: Colors.black
                border.color: modelData.accent
                border.width: 1
                Column {
                    anchors.fill: parent
                    anchors.margins: 3
                    GohuText {
                        width: parent.width
                        text: modelData.label
                        color: Colors.white
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignHCenter
                    }
                    GohuText {
                        width: parent.width
                        text: modelData.value
                        textFormat: Text.PlainText
                        color: modelData.accent
                        font.pixelSize: 13
                        fontSizeMode: Text.HorizontalFit
                        minimumPixelSize: 8
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
    Grid {
        width: parent.width
        columns: 2
        spacing: 4
        Repeater {
            model: root.selectionLive && root.observation ? root.observation.options : []
            delegate: ActionButton {
                required property string modelData
                width: Math.max(0,(root.width-4)/2)
                height: 28
                label: modelData
                labelFontSizeMode: Text.HorizontalFit
                selected: root.targetAlgorithm === modelData
                available: root.canStage
                onLeftClicked: root.stageAlgorithm(modelData)
            }
        }
    }
    ActionButton {
        width: parent.width
        height: 28
        label: "RESET TARGET"
        available: root.canStage
        onLeftClicked: root.stageAlgorithm(root.observation.actual)
    }
    ActionButton {
        width: parent.width
        height: 28
        label: "COPY ZRAM TO CUSTOM"
        available: root.canStage && root.received && root.exited && root.exitOk
        onLeftClicked: root.copyToProfile()
    }
    GohuText {
        width: parent.width
        text: "PREVIEW ONLY // APPLY NOT CONNECTED"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "Compression trades CPU time for RAM savings. Changing the primary algorithm of an initialized device may require safe withdrawal and reset. No device changes are performed here."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
