import QtQuick
import QtQuick.Controls as Controls
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticWidgetLifecycle.js" as Lifecycle
import "../../components"

Controls.Popup {
    id: root
    objectName: "cpuplusWorkshopLifecyclePicker"
    padding: 5
    modal: true
    focus: true
    closePolicy: Controls.Popup.CloseOnEscape | Controls.Popup.CloseOnPressOutside
    background: Rectangle { color: Colors.black; border.color: Colors.purple }
    readonly property var chosen: CpuPlusDiagnostics.lifecycleSelection
    readonly property bool locked: CpuPlusDiagnostics.workshopPresetLocked
    function toggleId(id) {
        const next=chosen.includes(id)?chosen.filter(x=>x!==id):chosen.concat([id]);
        if(next.length)CpuPlusDiagnostics.setLifecycleSelection(next);
    }
    contentItem: Column {
        spacing: 4
        Row {
            width: parent.width
            spacing: 4
            GohuText {
                width: Math.max(0,parent.width-34)
                height: 26
                text: "POST-APOLLO DUMP // "+root.chosen.length+"/"+Lifecycle.lifecycleIds().length
                color: Colors.purple
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            ActionButton {
                width: 30; height: 26
                label: "X"; normalFace: true; accentColor: Colors.red
                onLeftClicked: root.close()
            }
        }
        Row {
            width: parent.width
            spacing: 4
            ActionButton {
                width: Math.max(0,parent.width-104); height: 26
                label: "ALL WIDGETS"; normalFace: true; accentColor: Colors.magenta
                available: !root.locked
                onLeftClicked: CpuPlusDiagnostics.setLifecycleSelection(Lifecycle.lifecycleIds())
            }
            Controls.ComboBox {
                objectName: "cpuplusLifecycleDuration"
                width: 100; height: 26
                model: [5,10,30,60,120]
                currentIndex: model.indexOf(CpuPlusDiagnostics.lifecycleDurationSeconds)
                enabled: !root.locked
                onActivated: CpuPlusDiagnostics.setLifecycleDuration(Number(currentText))
            }
        }
        ListView {
            width: parent.width
            height: Math.max(0,parent.height-116)
            clip: true
            spacing: 2
            model: Lifecycle.lifecycleTargets()
            delegate: ActionButton {
                required property var modelData
                objectName: "cpuplusLifecycle-"+modelData.id
                width: ListView.view.width; height: 25
                normalFace: true; accentColor: Colors.purple
                label: (root.chosen.includes(modelData.id)?"✓ ":"")+modelData.label
                selected: root.chosen.includes(modelData.id)
                available: !root.locked
                onLeftClicked: root.toggleId(modelData.id)
            }
        }
        GohuText {
            width: parent.width; height: 14
            text: CpuPlusDiagnostics.lifecycleActive?"RECORDING // USE WIDGETS NORMALLY":
                CpuPlusDiagnostics.lifecycleReport ? CpuPlusDiagnostics.lifecycleReport.status+" // "+
                (CpuPlusDiagnostics.lifecycleReport.stats?CpuPlusDiagnostics.lifecycleReport.stats.length+" WIDGETS / "+CpuPlusDiagnostics.lifecycleReport.events.length+" EVENTS":CpuPlusDiagnostics.lifecycleReport.reason):
                "LIFECYCLE ONLY // CPU AND MEMORY PENDING"
            color: CpuPlusDiagnostics.lifecycleActive?Colors.green:Colors.cyan
            font.pixelSize: 9; elide: Text.ElideRight
        }
        Row {
            width: parent.width
            spacing: 4
            ActionButton {
                objectName: "cpuplusLifecycleStart"
                width: Math.max(0,parent.width-76); height: 26
                label: "START DUMP"; normalFace: true; accentColor: Colors.omnitrix
                available: CpuPlusDiagnostics.lifecycleAvailable && !root.locked
                onLeftClicked: if(CpuPlusDiagnostics.startLifecycleCapture()) root.close()
            }
            ActionButton {
                objectName: "cpuplusLifecycleStop"
                width: 72; height: 26
                label: "STOP"; destructive: true; accentColor: Colors.red
                available: CpuPlusDiagnostics.lifecycleActive
                onLeftClicked: CpuPlusDiagnostics.cancelLifecycleCapture()
            }
        }
    }
}
