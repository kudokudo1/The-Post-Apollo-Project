import QtQuick
import QtQuick.Controls as Controls
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticWidgetLifecycle.js" as Lifecycle
import "../../services/diagnostics/DiagnosticWorkflowReceipt.js" as Receipt
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
    property bool saveOpen: false
    property string pendingName: ""
    property var pendingPlan: null
    property bool pendingFavorite: false
    property string notice: ""
    function openSave() {
        if(locked||!CpuPlusDiagnostics.lifecycleAvailable)return false;
        saveOpen=true; notice=""; favoriteButton.selected=false;
        if(CpuPlusDiagnostics.workflowCatalogStatus==="NOT LOADED")CpuPlusDiagnostics.loadWorkflowCatalog();
        return true;
    }
    function confirmSave() {
        if(!saveOpen||locked||pendingName)return false;
        if(!CpuPlusDiagnostics.workflowCatalogReady)return CpuPlusDiagnostics.loadWorkflowCatalog();
        const name=nameInput.text.trim(), plan=CpuPlusDiagnostics.lifecyclePlan();
        if(!name){notice="ENTER WORKFLOW NAME";return false;}
        const favorite=favoriteButton.selected;
        if(!CpuPlusDiagnostics.saveLifecyclePreset(name,favorite)){notice=CpuPlusDiagnostics.workshopPresetFeedback;return false;}
        pendingName=name;pendingPlan=plan;pendingFavorite=favorite;
        notice="SAVING // WAIT FOR CONFIRMATION";return true;
    }
    Connections {
        target: CpuPlusDiagnostics
        function onWorkflowCatalogCompleted(outcome,wasEdit,confirmedDocument) {
            if(!root.pendingName||!wasEdit)return;
            const match=outcome==="READY"&&confirmedDocument&&confirmedDocument.rows.some(r=>
                r.name===root.pendingName&&r.execution==="dump"&&r.favorite===root.pendingFavorite&&Receipt.sameValue(r.plan,root.pendingPlan));
            root.pendingName="";root.pendingPlan=null;
            if(match){root.saveOpen=false;nameInput.text="";root.notice="SAVED // WORKFLOW LIBRARY";}
            else root.notice="SAVE NOT CONFIRMED // RELOAD";
        }
    }
    onClosed: if(!pendingName){saveOpen=false;nameInput.text="";notice="";}
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
                available: !root.locked && !root.saveOpen
                onLeftClicked: CpuPlusDiagnostics.setLifecycleSelection(Lifecycle.lifecycleIds())
            }
            Controls.ComboBox {
                objectName: "cpuplusLifecycleDuration"
                width: 100; height: 26
                model: [5,10,30,60,120]
                currentIndex: model.indexOf(CpuPlusDiagnostics.lifecycleDurationSeconds)
                enabled: !root.locked && !root.saveOpen
                onActivated: CpuPlusDiagnostics.setLifecycleDuration(Number(currentText))
            }
        }
        ListView {
            width: parent.width
            height: Math.max(0,parent.height-116)
            clip: true
            spacing: 2
            model: Lifecycle.lifecycleTargets()
            delegate: Row {
                id: targetRow
                required property var modelData
                width: ListView.view.width; height: 25
                spacing: 3
                ActionButton {
                    objectName: "cpuplusLifecycle-"+targetRow.modelData.id
                    width: Math.max(0,parent.width-47); height: parent.height
                    normalFace: true; accentColor: Colors.purple
                    label: (root.chosen.includes(targetRow.modelData.id)?"✓ ":"")+targetRow.modelData.label
                    selected: root.chosen.includes(targetRow.modelData.id)
                    available: !root.locked && !root.saveOpen
                    onLeftClicked: root.toggleId(targetRow.modelData.id)
                }
                ActionButton {
                    objectName: "cpuplusLifecycleOnly-"+targetRow.modelData.id
                    width: 44; height: parent.height
                    normalFace: true; accentColor: Colors.cyan
                    label: "ONLY"; labelPixelSize: 9
                    available: !root.locked && !root.saveOpen
                    onLeftClicked: CpuPlusDiagnostics.setLifecycleSelection([targetRow.modelData.id])
                }
            }
        }
        GohuText {
            width: parent.width; height: 14
            text: root.notice || (CpuPlusDiagnostics.lifecycleActive?(CpuPlusDiagnostics.lifecycleRecorder.finalizing?"FINALIZING // RESOURCE RECEIPT":"RECORDING // USE WIDGETS NORMALLY"):
                CpuPlusDiagnostics.lifecycleReport ? CpuPlusDiagnostics.lifecycleReport.status+" // "+
                (CpuPlusDiagnostics.lifecycleReport.stats?CpuPlusDiagnostics.lifecycleReport.stats.length+" WIDGETS / "+CpuPlusDiagnostics.lifecycleReport.events.length+" EVENTS":CpuPlusDiagnostics.lifecycleReport.reason):
                "LIFECYCLE + SHELL CPU / MEMORY / STALL")
            color: CpuPlusDiagnostics.lifecycleActive?Colors.green:Colors.cyan
            font.pixelSize: 9; elide: Text.ElideRight
        }
        Row {
            visible: !root.saveOpen
            height: visible?26:0
            width: parent.width
            spacing: 4
            ActionButton {
                objectName: "cpuplusLifecycleSave"
                width: 56; height: 26
                label: "SAVE"; normalFace: true; accentColor: Colors.magenta
                available: !root.locked && CpuPlusDiagnostics.lifecycleAvailable
                onLeftClicked: root.openSave()
            }
            ActionButton {
                objectName: "cpuplusLifecycleStart"
                width: Math.max(0,parent.width-136); height: 26
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
        Row {
            visible: root.saveOpen
            height: visible?26:0
            width: parent.width
            spacing: 4
            TextInput {
                id: nameInput
                objectName: "cpuplusLifecycleSaveName"
                width: Math.max(0,parent.width-128); height: 26
                color: Colors.white; font.pixelSize: 11
                maximumLength: 32; selectByMouse: true
                enabled: !root.locked
                onAccepted: root.confirmSave()
            }
            ActionButton {
                id: favoriteButton
                objectName: "cpuplusLifecycleSaveFavorite"
                width: 28; height: 26
                label: selected?"★":"☆"; normalFace: true; accentColor: Colors.magenta
                available: !root.locked
                onLeftClicked: selected=!selected
            }
            ActionButton {
                objectName: "cpuplusLifecycleConfirmSave"
                width: 60; height: 26
                label: CpuPlusDiagnostics.workflowCatalogReady?"SAVE":"RELOAD"
                normalFace: true; accentColor: Colors.cyan
                available: !root.locked
                onLeftClicked: root.confirmSave()
            }
            ActionButton {
                width: 28; height: 26
                label: "X"; normalFace: true; accentColor: Colors.red
                available: !root.locked
                onLeftClicked: {root.saveOpen=false;nameInput.text="";root.notice="";}
            }
        }
    }
}
