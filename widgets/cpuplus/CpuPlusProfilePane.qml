import QtQuick
import "../../components"
import "CpuPlusProfilePreview.js" as Profile
import "CpuPlusProfileCatalog.js" as Catalog

Column {
    id: root
    objectName: "cpuplusProfilePane"
    property Item headerTarget: null
    property Item footerTarget: null
    required property string selectedProfile
    required property var customDraft
    required property var actualKiB
    required property var actualSwappiness
    required property int capacityTarget
    required property int policyTarget
    required property bool observationReady
    required property bool operationBusy
    signal profileSelected(string name)
    signal draftCapture(string key)
    signal draftCleared()
    property var catalog: null
    property string catalogStatus: "NOT LOADED"
    property bool catalogBusy: false
    property string saveName: ""
    property string selectedSaved: ""
    readonly property var savedRows: catalog ? catalog.profiles : []
    readonly property bool catalogReady: !catalogBusy && Catalog.document(catalog)!==null
    signal catalogLoadRequested()
    signal catalogSaveRequested(string name)
    signal savedDraftRequested(string name)
    onCatalogChanged: if(!catalog || !catalog.profiles.some(x=>x.name===selectedSaved)) selectedSaved=""
    readonly property var view: Profile.preview(selectedProfile,customDraft,actualKiB,actualSwappiness)
    spacing: 6
    GohuText {
        parent: root.headerTarget || root
        width: parent.width
        text: "PROF // "+(root.selectedProfile || "SELECT PROFILE")+" // PREVIEW ONLY"
        color: Colors.magenta
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.selectedProfile==="CUSTOM"
            ? "CUSTOM DRAFT // SAVE EXPLICITLY TO CATALOG"
            : root.selectedProfile ? "PRESET VALUES NOT DECIDED // NO SETTINGS SELECTED" : "SELECT A PROFILE // NO ACTIVE PROFILE"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.view ? "MANAGED DISK SWAP\nACTUAL // "+Profile.gib(root.view.capacity.actual)
            +"\nPROFILE TARGET // "+(root.view.capacity.target===null?"NOT SET":root.view.capacity.target+" GiB")
            +"\nCHANGE // "+Profile.delta(root.view.capacity.deltaKiB===null?null:root.view.capacity.deltaKiB/1048576,"GiB")
            : "PROFILE UNAVAILABLE"
        color: Colors.cyan
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: root.view ? "SWAPPINESS\nACTUAL // "+(root.view.swappiness.actual===null?"UNAVAILABLE":root.view.swappiness.actual)
            +"\nPROFILE TARGET // "+(root.view.swappiness.target===null?"NOT SET":root.view.swappiness.target)
            +"\nCHANGE // "+Profile.delta(root.view.swappiness.delta,"") : "POLICY UNAVAILABLE"
        color: Colors.cyan
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "CAP STAGED // "+root.capacityTarget+" GiB\nPOL STAGED // "+(Profile.policy(root.policyTarget)?root.policyTarget:"UNAVAILABLE")
            +"\nCopy explicitly into CUSTOM. Existing targets are not modified."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "NOT INCLUDED // ZRAM, DEVICE PRIORITY, ADVANCED POLICY, PROCESS LIMITS, AUTOMATION, NOTIFICATIONS\nNo automatic defaults, apply or rollback. Saved profiles are local data only. Zero disk target is not supported removal. Changes would require independent permission and readback."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "SAVED PROFILES // "+root.catalogStatus
        color: Colors.magenta
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "SELECT A SAVED PROFILE THEN LOAD DRAFT (REPLACES TEMPORARY CUSTOM DRAFT ONLY)"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.savedRows
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 28
            label: modelData.name + " // " + (modelData.targets.capacityGiB===null?"CAP UNSET":modelData.targets.capacityGiB+" GiB")
                + " / " + (modelData.targets.swappiness===null?"POL UNSET":modelData.targets.swappiness)
            labelFontSizeMode: Text.HorizontalFit
            labelMinimumPixelSize: 8
            contentPadding: 2
            available: root.catalogReady
            selected: root.selectedSaved===modelData.name
            acceptedButtons: Qt.LeftButton
            keyboardActivationSignal: "leftClicked"
            onLeftClicked: root.selectedSaved=modelData.name
        }
    }
    GohuText {
        width: parent.width
        text: "NEW PROFILE NAME // MAX 32 CHARACTERS"
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Rectangle {
        width: parent.width
        height: 27
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        TextInput {
            anchors.fill: parent
            anchors.margins: 4
            text: root.saveName
            color: Colors.white
            maximumLength: 32
            font.pixelSize: 10
            selectByMouse: true
            clip: true
            onTextEdited: root.saveName=text
        }
    }
    Column {
        parent: root.footerTarget || root
        objectName: "cpuplusProfileBottomControls"
        width: parent.width
        spacing: 3
        Grid {
            id: profiles
            width: parent.width
            columns: 3
            spacing: 3
            Repeater {
                model: Profile.names()
                delegate: ActionButton {
                    required property string modelData
                    width: Math.max(0,(profiles.width-2*profiles.spacing)/3)
                    height: 26
                    label: modelData
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    contentPadding: 2
                    selected: root.selectedProfile===modelData
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.profileSelected(modelData)
                }
            }
        }
        Row {
            id: catalogRail
            width: parent.width
            spacing: 3
            Repeater {
                model: ["LOAD LIST","SAVE NEW","LOAD DRAFT"]
                delegate: ActionButton {
                    required property string modelData
                    objectName: modelData==="LOAD LIST"?"cpuplusProfileLoadList":modelData==="SAVE NEW"?"cpuplusProfileSaveNew":"cpuplusProfileLoadDraft"
                    width: Math.max(0,(catalogRail.width-2*catalogRail.spacing)/3)
                    height: 26
                    label: modelData
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    contentPadding: 2
                    available: modelData==="LOAD LIST" ? !root.catalogBusy
                        : root.catalogReady && (modelData==="SAVE NEW"
                            ? root.selectedProfile==="CUSTOM" && Catalog.create(root.catalog,root.saveName,root.customDraft)!==null
                            : root.savedRows.some(x=>x.name===root.selectedSaved))
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: {
                        if(modelData==="LOAD LIST")root.catalogLoadRequested();
                        else if(modelData==="SAVE NEW")root.catalogSaveRequested(root.saveName);
                        else root.savedDraftRequested(root.selectedSaved);
                    }
                }
            }
        }
        Grid {
            id: draftActions
            width: parent.width
            columns: 3
            spacing: 3
            Repeater {
                model: [{label:"COPY CAP",key:"capacityGiB"},{label:"COPY POL",key:"swappiness"},{label:"CLEAR",key:"clear"}]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(0,(draftActions.width-2*draftActions.spacing)/3)
                    height: 26
                    label: modelData.label
                    labelFontSizeMode: Text.HorizontalFit
                    labelMinimumPixelSize: 8
                    contentPadding: 2
                    available: root.selectedProfile==="CUSTOM" && (modelData.key==="clear"
                        || (root.observationReady && !root.operationBusy && (modelData.key==="capacityGiB"
                            ? root.actualKiB!==null && Profile.capacity(root.capacityTarget)
                            : root.actualSwappiness!==null && Profile.policy(root.policyTarget))))
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: {
                        if(modelData.key==="clear") root.draftCleared();
                        else root.draftCapture(modelData.key);
                    }
                }
            }
        }
    }
}
