import QtQuick
import Quickshell.Io
import "../../components"
import "CpuPlusAdvancedPolicy.js" as Policy

// Standalone presentation slice. No autostart or timer, no sysctl writer.
Column {
    id: root
    objectName: "cpuplusAdvancedPolicyPane"
    spacing: 6
    property var observation: null
    property string status: "NOT CHECKED"
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property string raw: ""
    property double observedAt: 0
    property string selectedKey: ""
    property var stagedValue: null
    readonly property var selectedSpec: Policy.previewSpec(observation, selectedKey)
    readonly property bool canStage: visible && !busy && selectedSpec !== null
    function selectPreview(key) {
        if (!visible || busy) return;
        const spec = Policy.previewSpec(observation, key);
        if (!spec || !Policy.validPreview(spec,spec.value)) return;
        selectedKey = key;
        stagedValue = spec.value;
    }
    function stagePreview(value) {
        if (!canStage || !Policy.validPreview(selectedSpec,value)) return;
        stagedValue = value;
    }
    function resetPreview() {
        if (canStage) stagePreview(selectedSpec.value);
    }
    function clearPreview() {
        selectedKey = "";
        stagedValue = null;
    }
    onVisibleChanged: if (!visible) clearPreview()
    readonly property bool busy: reader.running || status === "READING"
    readonly property var cards: observation ? [
        {key:"cachePressure",label:"METADATA CACHE PRESSURE", value:String(observation.cachePressure),
            detail:"Inode / directory-entry reclaim preference; not RAM usage."},
        {key:"background",label:"BACKGROUND WRITEBACK", value:Policy.pairLabel(observation.background),
            detail:"RATIO " + observation.background.ratio + "% // BYTES " + observation.background.bytes + " B"},
        {key:"writer",label:"WRITER WRITEBACK", value:Policy.pairLabel(observation.writer),
            detail:"RATIO " + observation.writer.ratio + "% // BYTES " + observation.writer.bytes + " B"},
        {key:"writebackCentisecs",label:"FLUSH INTERVAL", value:observation.writebackCentisecs === 0 ? "DISABLED" : Policy.seconds(observation.writebackCentisecs),
            detail:"Periodic flusher wake interval."},
        {key:"expireCentisecs",label:"DIRTY DATA AGE", value:Policy.seconds(observation.expireCentisecs),
            detail:"Age at which dirty data becomes eligible for writeout."}
    ] : []
    function refresh() {
        if (!visible || busy) return;
        clearPreview();
        observation = null;
        observedAt = 0;
        received = false;
        exited = false;
        exitOk = false;
        raw = "";
        status = "READING";
        reader.running = true;
    }
    function finish() {
        if (!received || !exited) return;
        clearPreview();
        observation = exitOk ? Policy.parse(raw) : null;
        observedAt = observation ? Date.now() : 0;
        status = observation ? "OBSERVED // EXPLICIT READ" : "UNAVAILABLE // RECHECK";
        raw = "";
    }
    Process {
        id: reader
        running: false
        command: ["/usr/bin/cat"].concat(Policy.paths())
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
    Row {
        width: parent.width
        height: 28
        spacing: 4
        GohuText {
            width: Math.max(0,parent.width-refreshButton.width-parent.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            text: "ADVANCED // WRITEBACK"
            color: Colors.magenta
            font.pixelSize: 12
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
            available: !root.busy
            onLeftClicked: root.refresh()
        }
    }
    GohuText {
        width: parent.width
        text: root.status + (root.observedAt > 0 ? "\n" + new Date(root.observedAt).toLocaleString() : "")
        color: root.observation ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: root.cards
        delegate: Rectangle {
            id: policyCard
            required property var modelData
            width: root.width
            height: cardBody.implicitHeight + 8
            color: Colors.black
            border.color: Colors.cyan
            border.width: 1
            Column {
                id: cardBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.label
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: modelData.value
                    color: Colors.cyan
                    font.pixelSize: 14
                    fontSizeMode: Text.HorizontalFit
                    minimumPixelSize: 8
                }
                GohuText {
                    width: parent.width
                    text: modelData.detail
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                ActionButton {
                    width: parent.width
                    height: 26
                    label: "TARGET"
                    selected: root.selectedKey === modelData.key
                    available: !root.busy && Policy.previewSpec(root.observation,modelData.key) !== null
                    onLeftClicked: root.selectPreview(modelData.key)
                }
                Column {
                    width: parent.width
                    spacing: 4
                    visible: root.selectedKey === modelData.key && root.selectedSpec !== null
                    GohuText {
                        width: parent.width
                        text: "TARGET // " + Policy.previewLabel(root.selectedSpec,root.stagedValue)
                        color: Colors.yellow
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    Grid {
                        width: parent.width
                        columns: 2
                        spacing: 4
                        Repeater {
                            model: root.selectedSpec ? [-root.selectedSpec.coarse,-root.selectedSpec.step,
                                root.selectedSpec.step,root.selectedSpec.coarse] : []
                            delegate: ActionButton {
                                required property real modelData
                                width: Math.max(0,(parent.width-4)/2)
                                height: 26
                                label: (modelData > 0 ? "+" : "-") + (root.selectedSpec && root.selectedSpec.unit === "B"
                                    ? Math.abs(modelData)/1048576 + " MiB"
                                    : root.selectedSpec && root.selectedSpec.unit === "cs"
                                    ? Math.abs(modelData)/100 + " s" : Math.abs(modelData))
                                labelFontSizeMode: Text.HorizontalFit
                                contentPadding: 2
                                available: root.canStage && root.selectedKey === policyCard.modelData.key
                                    && Policy.validPreview(root.selectedSpec,root.stagedValue + modelData)
                                onLeftClicked: root.stagePreview(root.stagedValue + modelData)
                            }
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 26
                        label: "RESET TARGET"
                        available: root.canStage
                        onLeftClicked: root.resetPreview()
                    }
                    GohuText {
                        width: parent.width
                        text: Policy.pairWarning(root.observation,root.selectedKey,root.stagedValue)
                        visible: text.length > 0
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: "PREVIEW ONLY // DEFAULT / APPLY NOT CONNECTED"
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
    }
    GohuText {
        width: parent.width
        text: "Dirty limits use ratio OR bytes, not both. Ratios refer to kernel-eligible memory, not installed RAM. Reads are sequential, not an atomic snapshot. Zero / conflicting pairs are shown without guessing. Preview stays in the observed unit; refresh or selecting another card discards it. Preview bounds are not kernel safety approval."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
