import QtQuick
import "../components"
import "../services/finance/FinanceCategoryPlan.js" as CategoryPlan
import "../services/finance/FinanceCategoryGroupPlan.js" as GroupPlan

// Category create/rename staging. Only an explicitly armed confirmation can
// reach M2's independently gated writer; preview never changes Actual.
Item {
    id: categoryPane
    property var snapshot: null
    property string filterText: ""
    property string openMode: "" // "", "create", "rename"
    property string sourceAtOpen: ""
    property string monthAtOpen: ""
    property string selectedCategoryId: ""
    property string originalNameAtOpen: ""
    property string selectedGroupId: ""
    property string draftName: ""
    property bool previewVisible: false
    property bool approvalArmed: false
    property bool submitted: false
    // M4: expense-group management is PREVIEW ONLY, separate from M3 writes.
    property string groupDraftMode: "" // "", "create", "rename"
    property string groupDraftId: ""
    property string groupSourceAtOpen: ""
    property string groupMonthAtOpen: ""
    property string groupOriginalNameAtOpen: ""
    property string groupDraftName: ""
    property bool groupPreviewVisible: false
    property string writeState: "idle"
    property string writeMessage: ""
    signal editBudgetRequested(var category)
    signal saveRequested(var payload)
    readonly property bool busy: writeState==="pending" || writeState==="uncertain"

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
    readonly property var groupPlan: GroupPlan.previewGroupPlan(
        snapshot,groupDraftMode,groupDraftId,groupDraftName)
    readonly property bool proposalEligible: previewVisible && !!plan && plan.ok
        && !busy && !submitted && snapshot && snapshot.readOnly===true
        && plan.sourceKey===sourceAtOpen
        && plan.sourceKey===snapshot.sourceKey
        && plan.month===monthAtOpen && plan.month===snapshot.month

    width: parent ? parent.width : 0
    height: content.implicitHeight

    function clearGroupDraft(){
        if(busy)return false;
        groupPreviewVisible=false;
        groupDraftMode="";
        groupDraftId="";
        groupSourceAtOpen="";
        groupMonthAtOpen="";
        groupOriginalNameAtOpen="";
        groupDraftName="";
        return true;
    }
    function beginCreateGroup(){
        if(busy || !snapshot || snapshot.readOnly!==true)return false;
        clearDraft();
        groupSourceAtOpen=snapshot.sourceKey;
        groupMonthAtOpen=snapshot.month;
        groupDraftMode="create";
        return true;
    }
    function beginRenameGroup(row){
        if(busy || !snapshot || snapshot.readOnly!==true || !row)return false;
        if(groups.filter(function(g){return g && g.id===row.id
                && g.name===row.name;}).length!==1)return false;
        clearDraft();
        groupSourceAtOpen=snapshot.sourceKey;
        groupMonthAtOpen=snapshot.month;
        groupDraftId=row.id;
        groupOriginalNameAtOpen=row.name;
        groupDraftName=row.name;
        groupDraftMode="rename";
        return true;
    }
    function clearDraft(){
        if(busy)return false;
        clearGroupDraft();
        previewVisible=false;
        approvalArmed=false;
        submitted=false;
        openMode="";
        sourceAtOpen="";
        monthAtOpen="";
        selectedCategoryId="";
        originalNameAtOpen="";
        selectedGroupId="";
        draftName="";
        return true;
    }
    function requestSave(){
        if(!proposalEligible || !approvalArmed)return false;
        let requestId="";
        for(let i=0;i<32;i++)
            requestId+=Math.floor(Math.random()*16).toString(16);
        submitted=true;
        saveRequested({
            mode:plan.mode, requestId:requestId, sourceKey:plan.sourceKey,
            month:plan.month, groupId:plan.groupId,
            categoryId:plan.categoryId, expectedName:plan.originalName,
            proposedName:plan.proposedName
        });
        return true;
    }
    function beginCreate(){
        if(busy || !snapshot || snapshot.readOnly!==true || !groups.length)return false;
        clearDraft();
        sourceAtOpen=snapshot.sourceKey;
        monthAtOpen=snapshot.month;
        selectedGroupId=groups.length===1 ? groups[0].id : "";
        openMode="create";
        return true;
    }
    function beginRename(row){
        if(busy || !snapshot || snapshot.readOnly!==true || !row)return false;
        const matches=categories.filter(function(c){return c && c.id===row.id;});
        if(matches.length!==1 || !groups.some(function(g){
            return g && g.id===row.groupId;
        }))return false;
        clearDraft();
        sourceAtOpen=snapshot.sourceKey;
        monthAtOpen=snapshot.month;
        selectedCategoryId=row.id;
        originalNameAtOpen=row.name;
        selectedGroupId=row.groupId;
        draftName=row.name;
        openMode="rename";
        return true;
    }
    function stepGroup(delta){
        if(busy || submitted || openMode!=="create" || !groups.length)return false;
        const current=groups.findIndex(function(g){return g && g.id===selectedGroupId;});
        const next=current<0 ? (delta<0 ? groups.length-1 : 0)
            : (current+(delta<0?-1:1)+groups.length)%groups.length;
        selectedGroupId=groups[next].id;
        return true;
    }
    onDraftNameChanged: {
        previewVisible=false;
        approvalArmed=false;
    }
    onSelectedGroupIdChanged: {
        previewVisible=false;
        approvalArmed=false;
    }
    onGroupDraftNameChanged: groupPreviewVisible=false
    onSnapshotChanged: {
        approvalArmed=false;
        if(groupDraftMode) {
            if(!snapshot || snapshot.sourceKey!==groupSourceAtOpen
                    || snapshot.month!==groupMonthAtOpen) {
                clearGroupDraft();
            } else {
                groupPreviewVisible=false;
                if(groupDraftMode==="rename"
                        && !groups.some(function(g){
                            return g && g.id===groupDraftId
                                && g.name===groupOriginalNameAtOpen;
                        }))clearGroupDraft();
            }
        }
        if(!openMode)return;
        if(!snapshot || snapshot.sourceKey!==sourceAtOpen
                || snapshot.month!==monthAtOpen){
            clearDraft();
        } else {
            // A same-source refresh is not approval. Re-preview current data.
            previewVisible=false;
            if(openMode==="rename" && !categories.some(function(c){
                return c && c.id===selectedCategoryId
                    && c.groupId===selectedGroupId
                    && c.name===originalNameAtOpen;
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
                    available: categoryPane.plan.ok && !categoryPane.busy
                        && !categoryPane.submitted
                    onLeftClicked: {
                        categoryPane.approvalArmed=false;
                        categoryPane.previewVisible=categoryPane.plan.ok;
                    }
                }
                ActionButton {
                    width: (parent.width-6)/2
                    height: 28
                    label: "CANCEL"
                    labelPixelSize: 9
                    accentColor: Colors.red
                    trackLabelGlowLocally: true
                    available: !categoryPane.busy
                    onLeftClicked: categoryPane.clearDraft()
                }
            }
            ActionButton {
                width: parent.width
                height: 29
                label: categoryPane.submitted ? "REQUEST SUBMITTED"
                    : categoryPane.approvalArmed ? "CONFIRM SAVE" : "ARM SAVE"
                labelPixelSize: 10
                accentColor: categoryPane.approvalArmed
                    ? Colors.magenta : Colors.orange
                trackLabelGlowLocally: true
                available: categoryPane.proposalEligible
                onLeftClicked: {
                    if(categoryPane.proposalEligible) {
                        if(!categoryPane.approvalArmed)
                            categoryPane.approvalArmed=true;
                        else
                            categoryPane.requestSave();
                    }
                }
            }
            GohuText {
                width: parent.width
                text: categoryPane.plan.ok
                    ? "PREVIEW VALID // EXPLICIT CONFIRMATION REQUIRED"
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
                text: categoryPane.submitted
                    ? "SAVE REQUEST SENT // CHECK WRITER STATUS"
                    : "NOT SAVED // ACTUAL IS UNCHANGED"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: categoryPane.writeState==="pending"
                    || categoryPane.writeState==="blocked"
                    || categoryPane.writeState==="uncertain"
                text: categoryPane.writeMessage
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }

        // M4 group management has no submit signal, save button, or writer.
        Row {
            id: groupHeader
            width: parent.width
            spacing: 6
            GohuText {
                width: parent.width - addGroup.width - 6
                height: 28
                verticalAlignment: Text.AlignVCenter
                text: "CATEGORY GROUPS // "+categoryPane.groups.length
                font.pixelSize: 10
                color: Colors.cyan
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            ActionButton {
                id: addGroup
                width: 111
                height: 28
                label: categoryPane.groupDraftMode==="create"
                    ? "CLOSE GROUP" : "+ NEW GROUP"
                labelPixelSize: 9
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                available: !!categoryPane.snapshot
                    && categoryPane.snapshot.readOnly===true
                    && !categoryPane.busy
                onLeftClicked: {
                    if(categoryPane.groupDraftMode==="create")
                        categoryPane.clearGroupDraft();
                    else
                        categoryPane.beginCreateGroup();
                }
            }
        }
        Column {
            id: groupEditor
            width: parent.width
            visible: categoryPane.groupDraftMode!==""
            spacing: 6
            GohuText {
                width: parent.width
                text: categoryPane.groupDraftMode==="create"
                    ? "NEW EXPENSE GROUP // DRAFT"
                    : "RENAME EXPENSE GROUP // DRAFT"
                font.pixelSize: 10
                color: Colors.magenta
                textFormat: Text.PlainText
            }
            Rectangle {
                width: parent.width
                height: 32
                color: Colors.dark
                border.color: Colors.cyan
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 7
                    visible: !groupNameEditor.text
                    text: "GROUP NAME"
                    color: Colors.cyan
                    font.pixelSize: 10
                }
                TextInput {
                    id: groupNameEditor
                    anchors.fill: parent
                    anchors.margins: 7
                    text: categoryPane.groupDraftName
                    color: Colors.white
                    font.pixelSize: 11
                    selectByMouse: true
                    clip: true
                    onTextEdited: categoryPane.groupDraftName=text
                }
            }
            Row {
                width: parent.width
                spacing: 6
                ActionButton {
                    width: (parent.width-6)/2
                    height: 28
                    label: "PREVIEW GROUP"
                    labelPixelSize: 9
                    accentColor: Colors.orange
                    trackLabelGlowLocally: true
                    available: categoryPane.groupPlan.ok
                        && !categoryPane.busy
                        && categoryPane.groupSourceAtOpen
                            ===categoryPane.snapshot.sourceKey
                        && categoryPane.groupMonthAtOpen
                            ===categoryPane.snapshot.month
                    onLeftClicked: categoryPane.groupPreviewVisible=
                        categoryPane.groupPlan.ok
                }
                ActionButton {
                    width: (parent.width-6)/2
                    height: 28
                    label: "CANCEL GROUP"
                    labelPixelSize: 9
                    accentColor: Colors.red
                    trackLabelGlowLocally: true
                    available: !categoryPane.busy
                    onLeftClicked: categoryPane.clearGroupDraft()
                }
            }
            GohuText {
                width: parent.width
                text: categoryPane.groupPlan.ok
                    ? "GROUP PREVIEW AVAILABLE // NO SAVE"
                    : categoryPane.groupPlan.reason
                color: categoryPane.groupPlan.ok ? Colors.cyan : Colors.orange
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: categoryPane.groupPreviewVisible
                    && categoryPane.groupPlan.ok
                text: categoryPane.groupPlan.mode==="create"
                    ? "WOULD CREATE GROUP // "+categoryPane.groupPlan.proposedName
                    : "WOULD RENAME GROUP // "+categoryPane.groupPlan.originalName
                        +" → "+categoryPane.groupPlan.proposedName
                color: Colors.magenta
                font.pixelSize: 10
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: categoryPane.groupPreviewVisible
                text: "PREVIEW ONLY // GROUP NOT SAVED IN ACTUAL"
                color: Colors.orange
                font.pixelSize: 9
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
        Repeater {
            model: categoryPane.groups
            delegate: Row {
                id: groupRow
                required property var modelData
                width: content.width
                height: 28
                spacing: 5
                GohuText {
                    width: parent.width - renameGroupButton.width - 5
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: modelData.name
                    font.pixelSize: 10
                    color: Colors.white
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                }
                ActionButton {
                    id: renameGroupButton
                    width: 104
                    height: 26
                    label: "RENAME GROUP"
                    labelPixelSize: 8
                    accentColor: Colors.cyan
                    trackLabelGlowLocally: true
                    available: !categoryPane.busy
                    onLeftClicked: categoryPane.beginRenameGroup(groupRow.modelData)
                }
            }
        }
        GohuText {
            width: parent.width
            visible: categoryPane.groups.length===0
            text: "NO EXPENSE GROUPS // CREATE PREVIEW AVAILABLE"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
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
            text: "CREATE / RENAME SAVE REQUIRES A SEPARATE OPERATOR PERMIT // DELETE UNAVAILABLE"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
