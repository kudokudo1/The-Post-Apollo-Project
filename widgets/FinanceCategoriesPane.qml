import QtQuick
import "../components"
import "../services/finance/FinanceCategoryPlan.js" as CategoryPlan

// Category creation/rename planning on the existing authenticated snapshot.
// The preview is intentionally NOT a writer or authorization surface.
Item {
    id: categoryPane
    property var snapshot: null
    property string filterText: ""
    property string openMode: "" // "", "create", "rename"
    property string sourceAtOpen: ""
    property string monthAtOpen: ""
    property string selectedCategoryId: ""
    property string selectedGroupId: ""
    property string draftName: ""
    property bool previewVisible: false
    signal editBudgetRequested(var category)

    readonly property var categories: snapshot && Array.isArray(snapshot.categories)
        ? snapshot.categories : []
    readonly property var groups: snapshot && Array.isArray(snapshot.categoryGroups)
        ? snapshot.categoryGroups : []
    readonly property var chosenGroup: {
        const rows=groups.filter(function(g) {
            return g && g.id===selectedGroupId;
        });
        return rows.length===1 ? rows[0] : null;
    }
    readonly property var displayed: {
        const needle=filterText.trim().toLowerCase();
        if(!needle)return categories;
        return categories.filter(function(c){
            return c && (String(c.name||"").toLowerCase().indexOf(needle)>=0
                 || String(c.group||"").toLowerCase().indexOf(needle)>=0);
        });
    }
    readonly property var plan: CategoryPlan.previewCategoryPlan(
        snapshot,openMode,selectedCategoryId,selectedGroupId,draftName)

    width: parent ? parent.width : 0
    height: content.implicitHeight

    function clearDraft(){
        previewVisible=false;
        openMode="";
        sourceAtOpen="";
        monthAtOpen="";
        selectedCategoryId="";
        selectedGroupId="";
        draftName="";
    }
    function beginCreate(){
        if(!snapshot || snapshot.readOnly!==true || !groups.length)return false;
        clearDraft();
        sourceAtOpen=snapshot.sourceKey;
        monthAtOpen=snapshot.month;
        selectedGroupId=groups.length===1 ? groups[0].id : "";
        openMode="create";
        return true;
    }
    function beginRename(row){
        if(!snapshot || snapshot.readOnly!==true || !row)return false;
        const matches=categories.filter(function(c){return c && c.id===row.id;});
        if(matches.length!==1 || !groups.some(function(g){
            return g && g.id===row.groupId;
        }))return false;
        clearDraft();
        sourceAtOpen=snapshot.sourceKey;
        monthAtOpen=snapshot.month;
        selectedCategoryId=row.id;
        selectedGroupId=row.groupId;
        draftName=row.name;
        openMode="rename";
        return true;
    }
    function stepGroup(delta){
        if(openMode!=="create" || !groups.length)return false;
        const current=groups.findIndex(function(g){return g && g.id===selectedGroupId;});
        const next=(current+(delta<0?-1:1)+groups.length)%groups.length;
        selectedGroupId=groups[next].id;
        return true;
    }
    onDraftNameChanged: previewVisible=false
    onSelectedGroupIdChanged: previewVisible=false
    onSnapshotChanged: {
        if(!openMode)return;
        if(!snapshot || snapshot.sourceKey!==sourceAtOpen
                || snapshot.month!==monthAtOpen){
            clearDraft();
        } else {
            // A same-source refresh is not approval. Re-preview current data.
            previewVisible=false;
            if(openMode==="rename" && !categories.some(function(c){
                return c && c.id===selectedCategoryId && c.groupId===selectedGroupId;
            }))clearDraft();
        }
    }
    onVisibleChanged: if(!visible)clearDraft()

    Column {
        id: content
        width: categoryPane.width
        spacing: 7

        Row {
            width: parent.width
            spacing: 6
            GohuText {
                width: parent.width - newCategory.width - 6
                height: 28
                verticalAlignment: Text.AlignVCenter
                text: "CATEGORIES"
                font.pixelSize: 12
                color: Colors.cyan
            }
            ActionButton {
                id: newCategory
                width: 125
                height: 28
                label: categoryPane.openMode==="create" ? "CLOSE DRAFT" : "+ NEW CATEGORY"
                labelPixelSize: 9
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                available: categoryPane.groups.length>0
                onLeftClicked: {
                    if(categoryPane.openMode==="create")categoryPane.clearDraft();
                    else categoryPane.beginCreate();
                }
            }
        }

        Column {
            id: categoryEditor
            width: parent.width
            visible: categoryPane.openMode!==""
            spacing: 6

            GohuText {
                width: parent.width
                text: categoryPane.openMode==="create" ? "CREATE CATEGORY // DRAFT"
                    : "RENAME CATEGORY // DRAFT"
                font.pixelSize: 10
                color: Colors.magenta
            }
            Row {
                id: groupChooser
                width: parent.width
                spacing: 5
                visible: categoryPane.openMode==="create"
                ActionButton {
                    width: 29
                    height: 28
                    label: "‹"
                    labelPixelSize: 15
                    accentColor: Colors.cyan
                    trackLabelGlowLocally: true
                    available: categoryPane.groups.length>1
                    onLeftClicked: categoryPane.stepGroup(-1)
                }
                GohuText {
                    width: groupChooser.width-68
                    height: 28
                    verticalAlignment: Text.AlignVCenter
                    text: categoryPane.chosenGroup
                        ? "GROUP // "+categoryPane.chosenGroup.name
                        : "CHOOSE GROUP"
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                ActionButton {
                    width: 29
                    height: 28
                    label: "›"
                    labelPixelSize: 15
                    accentColor: Colors.cyan
                    trackLabelGlowLocally: true
                    available: categoryPane.groups.length>1
                    onLeftClicked: categoryPane.stepGroup(1)
                }
            }
            GohuText {
                width: parent.width
                visible: categoryPane.openMode==="rename"
                text: categoryPane.chosenGroup
                    ? "GROUP // "+categoryPane.chosenGroup.name : "GROUP UNAVAILABLE"
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            Rectangle {
                width: parent.width
                height: 33
                color: Colors.dark
                border.color: Colors.magenta
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 7
                    text: "CATEGORY NAME"
                    visible: !nameEditor.text
                    font.pixelSize: 10
                    color: Colors.cyan
                }
                TextInput {
                    id: nameEditor
                    anchors.fill: parent
                    anchors.margins: 7
                    text: categoryPane.draftName
                    color: Colors.white
                    font.pixelSize: 11
                    selectByMouse: true
                    clip: true
                    onTextEdited: categoryPane.draftName=text
                }
            }
            Row {
                width: parent.width
                spacing: 6
                ActionButton {
                    width: (parent.width-6)/2
                    height: 28
                    label: "PREVIEW"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    trackLabelGlowLocally: true
                    available: categoryPane.plan.ok
                    onLeftClicked: categoryPane.previewVisible=categoryPane.plan.ok
                }
                ActionButton {
                    width: (parent.width-6)/2
                    height: 28
                    label: "CANCEL"
                    labelPixelSize: 9
                    accentColor: Colors.red
                    trackLabelGlowLocally: true
                    onLeftClicked: categoryPane.clearDraft()
                }
            }
            GohuText {
                width: parent.width
                text: categoryPane.plan.ok
                    ? "PREVIEW AVAILABLE // NO SAVE YET"
                    : categoryPane.plan.reason
                font.pixelSize: 9
                color: categoryPane.plan.ok ? Colors.cyan : Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: categoryPane.previewVisible && categoryPane.plan.ok
                text: categoryPane.plan.mode==="create"
                    ? "WOULD CREATE // "+categoryPane.plan.proposedName
                      +" / "+categoryPane.plan.groupName
                    : "WOULD RENAME // "+categoryPane.plan.originalName
                      +" → "+categoryPane.plan.proposedName
                font.pixelSize: 10
                color: Colors.magenta
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: categoryPane.previewVisible
                text: "NOT SAVED // ACTUAL IS UNCHANGED"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }

        Rectangle {
            width: parent.width
            height: 30
            color: Colors.dark
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 6
                text: categoryPane.filterText
                color: Colors.white
                font.pixelSize: 11
                selectByMouse: true
                onTextEdited: categoryPane.filterText=text
            }
        }
        GohuText {
            width: parent.width
            text: "CATEGORY / GROUP // "+categoryPane.displayed.length
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            elide: Text.ElideRight
        }
        Repeater {
            model: categoryPane.displayed
            delegate: Rectangle {
                id: item
                required property var modelData
                width: content.width
                height: 66
                color: Colors.black
                border.color: modelData.availableCents<0?Colors.orange:Colors.cyan
                GohuText {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.topMargin: 4
                    width: parent.width-10
                    text: modelData.name+" / "+modelData.group
                    font.pixelSize: 10
                    color: Colors.white
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 5
                    anchors.bottomMargin: 8
                    width: parent.width-150
                    text: "SET $"+(modelData.budgetedCents/100).toFixed(2)
                        +"  LEFT $"+(modelData.availableCents/100).toFixed(2)
                    font.pixelSize: 9
                    color: Colors.cyan
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 5
                    spacing: 4
                    ActionButton {
                        width: 58
                        height: 25
                        label: "RENAME"
                        labelPixelSize: 8
                        accentColor: Colors.cyan
                        trackLabelGlowLocally: true
                        onLeftClicked: categoryPane.beginRename(item.modelData)
                    }
                    ActionButton {
                        width: 85
                        height: 25
                        label: "EDIT SET"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        trackLabelGlowLocally: true
                        onLeftClicked: categoryPane.editBudgetRequested(item.modelData)
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            visible: categoryPane.displayed.length===0
            text: "NO MATCHING CATEGORIES"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
        }
        GohuText {
            width: parent.width
            text: "CREATE / RENAME ARE PREVIEW ONLY // DELETE REQUIRES A SEPARATE GUARDED WRITE PATH"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
