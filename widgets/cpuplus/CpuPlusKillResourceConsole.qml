import QtQuick
import QtQuick.Controls
import "../../components"
import "../appcontrol"
import "CpuPlusKillResourceDraft.js" as Draft

// K8d // CPU++-owned presentation only. No process action backend.
// A displayed draft is not a Linux resource setting or permission finding.
Item {
    id: root
    objectName: "cpuPlusKillResourceConsole"
    required property var target
    property bool selectionReady: false
    property var inspectionResult: null
    property string inspectionStatus: "NOT INSPECTED"
    property bool inspectionBusy: false
    signal inspectionRequested()
    readonly property var exactInspection: inspectionResult && inspectionResult.key===targetIdentity ? inspectionResult : null
    function observationLabel(value) {
        return (value || "not_inspected").replace(/_/g," ").toUpperCase();
    }
    // Projection of the existing left-side draft and shared limit owner.
    property int memoryDraftPercent: -1
    property real memoryMinimumMiB: 0
    property real memoryMaximumMiB: 0
    property real memoryCurrentPercent: 100
    property bool memoryManaged: false
    property bool memoryOwnerReady: false
    property string memoryStatus: "LIMIT STATUS UNAVAILABLE"
    signal memoryStageRequested(int percent)
    signal memoryClearRequested()
    signal memoryReviewRequested(int percent)
    readonly property bool memoryEditable: selectionReady && memoryOwnerReady
        && memoryMinimumMiB>0 && memoryMaximumMiB>=4*memoryMinimumMiB
    readonly property bool memoryFiniteDraft: memoryDraftPercent>=0 && memoryDraftPercent<=97
    readonly property bool memoryRestoreDraft: memoryDraftPercent===100
    readonly property bool memoryCanReview: memoryEditable && selectedKey==="memory"
        && Draft.summary(staged).length===0
        && (memoryFiniteDraft || (memoryRestoreDraft && memoryManaged))
    function memoryPreviewPercent() {
        return memoryFiniteDraft ? memoryDraftPercent
            : memoryManaged ? Math.max(0,Math.min(97,Math.round(memoryCurrentPercent))) : 50;
    }
    function memoryPreviewMiB(percent) {
        return Math.round(memoryMinimumMiB + (memoryMaximumMiB-memoryMinimumMiB)*percent/98.5);
    }
    function memoryDraftLine() {
        if (memoryDraftPercent<0) return "";
        if (memoryRestoreDraft) return "MEMORY // RESTORE ORIGINAL";
        if (memoryFiniteDraft) return "MEMORY // LIMIT "+memoryDraftPercent+"% OF CONTROL RANGE (~"+memoryPreviewMiB(memoryDraftPercent)+" MiB)";
        return "MEMORY // LEGACY ENDPOINT DRAFT; SELECT LIMIT OR RESTORE AGAIN";
    }
    onMemoryDraftPercentChanged: reviewing = false
    property var resourceEvidence: null
    readonly property var exactEvidence: resourceEvidence && resourceEvidence.key===targetIdentity ? resourceEvidence : null
    readonly property var allowedCpuIds: Draft.cpuIds(exactEvidence ? exactEvidence.cpuMask : "")
    readonly property string allowedCpuKey: allowedCpuIds.join(",")
    readonly property var selectedCpuIds: Draft.affinitySelection(staged,allowedCpuIds)
    // A changed effective mask invalidates the old selection; never silently
    // carry a narrowing request to a different kernel mask.
    onAllowedCpuKeyChanged: {
        staged = Draft.dropAffinity(staged);
        reviewing = false;
    }
    function priorityValue() {
        if (Draft.hasValue(staged,"cpu","nice")) return Draft.value(staged,"cpu","nice");
        const v=exactEvidence ? exactEvidence.niceValue : null;
        return Number.isInteger(v)&&v>=-20&&v<=19 ? v : 0;
    }
    function priorityObserved() {
        const v=exactEvidence ? exactEvidence.niceValue : null;
        return Number.isInteger(v)&&v>=-20&&v<=19;
    }
    function setAffinity(ids) {
        if (!selectionReady || selectedKey!=="cpu" || modeFor("cpu")!=="manual") return;
        staged = Draft.stageAffinity(staged,allowedCpuIds,ids);
        reviewing = false;
    }
    function toggleAffinity(cpu) {
        const next=selectedCpuIds.slice();
        const i=next.indexOf(cpu);
        if(i>=0) { if(next.length===1) return; next.splice(i,1); }
        else next.push(cpu);
        setAffinity(next);
    }
    readonly property string targetIdentity: Draft.identity(target)
    readonly property var categories: Draft.cards()
    property var staged: ({})
    // One resource selector controls one below-panel editor, matching other
    // Post-Apollo filter bars. Switching views does not change staged values.
    property string selectedKey: "cpu"
    readonly property var selectedResource: Draft.find(selectedKey)
    function selectResource(key) {
        if (!Draft.find(key)) return false;
        selectedKey = key;
        reviewing = false;
        bodyScroll.contentY = 0;
        return true;
    }
    function filterLabel(key) {
        return ({cpu:"CPU",memory:"MEM",swap:"SWAP",disk:"DISK",
            threads:"THR",gpu:"GPU",network:"NET"})[key] || key.toUpperCase();
    }
    property bool informationOpen: false
    onSelectedKeyChanged: informationOpen = false
    property bool reviewing: false
    readonly property var reviewLines: {
        const lines=Draft.summary(staged);
        const memory=memoryDraftLine();
        if (memory) lines.push(memory);
        return lines;
    }
    readonly property bool hasDraft: reviewLines.length > 0

    function clearDraft() {
        staged = ({});
        reviewing = false;
    }
    onTargetIdentityChanged: root.clearDraft()
    onSelectionReadyChanged: if (!selectionReady) root.clearDraft()

    function modeFor(key) { return Draft.mode(staged,key); }
    function valueFor(key,field) { return Draft.value(staged,key,field); }
    function stageMode(key,mode) {
        if (!selectionReady) return;
        staged = Draft.stageMode(staged,key,mode);
        reviewing = false;
    }
    function stageNumber(key,field,number) {
        if (!selectionReady) return;
        if (key==="cpu" && field==="quota") { stageQuota("budget",number); return; }
        if (key==="disk" && (field==="read" || field==="write")) {
            stageBandwidth(field,"budget",number); return;
        }
        staged = Draft.stageValue(staged,key,field,number);
        reviewing = false;
    }
    function choosePriorityPreset(key) {
        if (!selectionReady || selectedKey !== "cpu") return;
        staged = Draft.stagePriorityPreset(staged,key);
        reviewing = false;
    }
    function priorityPresetSelected(nice) {
        return modeFor("cpu") === "manual"
            && priorityValue() === nice;
    }
    function stageIoClass(kind) {
        if (!selectionReady || selectedKey!=="disk") return;
        const current=Draft.ioPriority(staged);
        staged=Draft.stageIoPriority(staged,kind,current.kind==="best_effort"?current.level:4);
        reviewing=false;
    }
    function stageIoLevel(level) {
        if (!selectionReady || selectedKey!=="disk" || modeFor("disk")!=="manual"
                || Draft.ioPriority(staged).kind!=="best_effort") return;
        staged=Draft.stageIoPriority(staged,"best_effort",level);
        reviewing=false;
    }
    readonly property var swapDraft: Draft.swapChoice(staged)
    function stageSwap(kind,mib) {
        if (!selectionReady || selectedKey!=="swap") return;
        staged=Draft.stageSwap(staged,kind,mib);
        reviewing=false;
    }
    function swapPreviewMiB() { return swapDraft.kind==="uncapped" ? 1024 : swapDraft.mib; }
    readonly property var quotaDraft: Draft.quotaChoice(staged)
    readonly property int quotaMaximum: Draft.quotaRange(staged,allowedCpuIds)
    function quotaPreviewPercent() { return quotaDraft.kind==="uncapped" ? 75 : quotaDraft.percent; }
    function stageQuota(kind,percent) {
        if (!selectionReady || selectedKey!=="cpu" || modeFor("cpu")!=="manual") return;
        staged=Draft.stageQuota(staged,kind,percent,quotaMaximum);
        reviewing=false;
    }
    function bandwidthChoice(direction) { return Draft.bandwidthChoice(staged,direction); }
    function bandwidthPreview(direction) {
        const choice=bandwidthChoice(direction);
        return !choice || choice.kind==="uncapped" ? 64 : choice.mib;
    }
    function stageBandwidth(direction,kind,mib) {
        if (!selectionReady || selectedKey!=="disk" || modeFor("disk")!=="manual") return;
        staged=Draft.stageBandwidth(staged,direction,kind,mib);
        reviewing=false;
    }
    readonly property var taskDraft: Draft.taskChoice(staged)
    function taskPreviewCount() { return taskDraft.kind==="uncapped" ? 64 : taskDraft.count; }
    function stageTasks(kind,count) {
        if (!selectionReady || selectedKey!=="threads") return;
        staged=Draft.stageTasks(staged,kind,count);
        reviewing=false;
    }
    function stepTasks(delta) {
        if (!selectionReady || selectedKey!=="threads") return;
        staged=Draft.stepTasks(staged,delta);
        reviewing=false;
    }
    function accentFor(key) {
        if (key === "cpu") return Colors.orange;
        if (key === "memory") return Colors.magenta;
        if (key === "swap") return Colors.yellow;
        if (key === "disk") return Colors.blue;
        if (key === "threads" || key === "gpu") return Colors.omnitrix;
        return Colors.cyan;
    }

    // Favorites / ID Management structure: a fixed UNBOXED top region
    // separated by two horizontal rules, never an enclosing frame.
    Item {
        id: resourceHeaderSection
        objectName: "cpuPlusResourceHeaderSection"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: headerContent.implicitHeight + 16
        z: 10

        Column {
            id: headerContent
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            anchors.topMargin: 8
            spacing: 5

            GohuText {
                objectName: "cpuPlusResourceHeaderTitle"
                width: parent.width
                height: 17
                text: "RESOURCE CONTROL // DRAFT"
                font.pixelSize: 12
                color: Colors.orange
                elide: Text.ElideRight
            }
            // First horizontal rule goes immediately below the title.
            // No status or label is allowed between rule and resource tabs.
            Rectangle {
                objectName: "cpuPlusResourceTitleDivider"
                width: parent.width
                height: 2
                color: Colors.red
            }
            // The seven category selectors are one stable header rail.
            Row {
                id: resourceFilters
                objectName: "cpuPlusResourceCategoryFilters"
                width: parent.width
                height: 30
                spacing: 2
                Repeater {
                    model: root.categories
                    delegate: ActionButton {
                        required property var modelData
                        objectName: "cpuPlusResourceFilter-" + modelData.key
                        readonly property color filterInk: root.accentFor(modelData.key)
                        width: Math.max(1,(resourceFilters.width
                            - resourceFilters.spacing * (root.categories.length-1))
                            / root.categories.length)
                        height: resourceFilters.height
                        label: root.filterLabel(modelData.key)
                        labelPixelSize: 9
                        labelMinimumPixelSize: 7
                        contentPadding: 1
                        normalFace: true
                        selected: root.selectedKey === modelData.key
                        accentColor: filterInk
                        onLeftClicked: root.selectResource(modelData.key)
                    }
                }
            }

            // Selected-resource identity and contextual info belong to the
            // fixed top region, not the instrument control workspace.
            Item {
                id: resourceInfoStrip
                objectName: "cpuPlusResourceInformationStrip"
                width: parent.width
                height: 26
                GohuText {
                    id: activeResourceHeading
                    objectName: "cpuPlusResourceSelectedTitle"
                    anchors.left: parent.left
                    anchors.right: resourceInformationButton.left
                    anchors.rightMargin: 5
                    anchors.verticalCenter: parent.verticalCenter
                    height: 23
                    text: root.selectedResource.title + " // " + root.selectedResource.scope
                    color: root.accentFor(root.selectedKey)
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
                ProcessInformationButton {
                    id: resourceInformationButton
                    objectName: "cpuPlusResourceInformationButton"
                    anchors.right: parent.right
                    anchors.top: parent.top
                    selected: root.informationOpen
                    onLeftClicked: root.informationOpen = !root.informationOpen
                }
            }
            GohuText {
                objectName: "cpuPlusResourceIdentityStatus"
                width: parent.width
                height: 13
                text: root.selectionReady ? "EXACT PROCESS SELECTED // NOT APPLIED"
                    : "SELECT VERIFIED PROCESS // READ ONLY"
                font.pixelSize: 9
                color: root.selectionReady ? Colors.white : Colors.yellow
                elide: Text.ElideRight
            }
            GohuText {
                objectName: "cpuPlusResourceCapabilityStatus"
                width: parent.width
                height: 13
                text: root.selectedKey==="memory"
                    ? "EXISTING LIMIT OWNER // CONFIRMATION REQUIRED"
                    : "CAPABILITY / WRITE PERMISSION // NOT VERIFIED"
                color: Colors.yellow
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            Rectangle {
                objectName: "cpuPlusResourceHeaderDivider"
                width: parent.width
                height: 2
                color: Colors.red
            }
        }

        // Overlay help while keeping the header's measured height fixed.
        // This popup never controls a resource or authorizes a write.
        Rectangle {
            id: resourceInformationPopup
            objectName: "cpuPlusResourceInformationPopup"
            anchors.right: headerContent.right
            y: headerContent.y + resourceInfoStrip.y + resourceInfoStrip.height + 3
            width: Math.min(320,Math.max(0,root.width - 14))
            height: informationContent.implicitHeight + 12
            color: Colors.black
            border.width: 1
            border.color: Colors.yellow
            visible: root.informationOpen
            z: 12
            Column {
                id: informationContent
                x: 6
                y: 6
                width: Math.max(0,parent.width-12)
                spacing: 4
                GohuText {
                    width: parent.width
                    text: root.selectedResource.title + " // RESOURCE INFORMATION"
                    color: root.accentFor(root.selectedKey)
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                GohuText {
                    width: parent.width
                    text: root.selectedResource.scope + "\\n" + root.selectedResource.note
                    color: Colors.white
                    wrapMode: Text.Wrap
                    font.pixelSize: 10
                }
                GohuText {
                    width: parent.width
                    text: root.selectedKey==="memory"
                        ? "RLIMIT_AS LIMITS VIRTUAL ADDRESS SPACE. RESTORE RETURNS THE ORIGINAL KILL-CAPTURED SOFT LIMIT. REVIEW AND CONFIRM THROUGH THE EXISTING OWNER."
                        : "OFF / MANUAL / AUTO / HOLD ARE DRAFTS ONLY. "
                        + "APPLY REMAINS LOCKED UNTIL THE RESOURCE BACKEND IS VERIFIED."
                    color: Colors.yellow
                    wrapMode: Text.Wrap
                    font.pixelSize: 10
                }
            }
        }
    }

    Flickable {
        id: bodyScroll
        objectName: "cpuPlusResourceConsoleScroll"
        anchors.top: resourceHeaderSection.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: draftActionsStrip.top
        anchors.bottomMargin: 5
        clip: true
        contentWidth: width
        contentHeight: cardStack.implicitHeight + 8
        interactive: contentHeight > height + 1
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: cardStack
            x: 3
            y: 3
            width: Math.max(0,bodyScroll.width-16)
            spacing: 6
            Rectangle {
                objectName: "cpuPlusResourceDraftReview"
                width: parent.width
                height: root.reviewing ? reviewBody.implicitHeight + 12 : 0
                visible: root.reviewing
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: reviewBody
                    x: 6; y: 6
                    width: Math.max(0,parent.width-12)
                    spacing: 4
                    GohuText {
                        width: parent.width
                        text: "REVIEW // NOT AN EXECUTABLE REQUEST"
                        color: Colors.cyan
                        wrapMode: Text.Wrap
                        font.pixelSize: 10
                    }
                    Repeater {
                        model: root.reviewLines
                        delegate: GohuText {
                            required property string modelData
                            width: reviewBody.width
                            wrapMode: Text.Wrap
                            text: modelData
                            color: Colors.white
                            font.pixelSize: 10
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: "APPLY REQUIRES VERIFIED KERNEL BACKEND AND PERMISSION"
                        color: Colors.orange
                        wrapMode: Text.Wrap
                        font.pixelSize: 9
                    }
                }
            }


            // The selected editor has no enclosing card/frame; modes and
            // instruments share the same open control surface.
            Item {
                id: resourcePanel
                objectName: "cpuPlusResourceSelectedPanel"
                readonly property var spec: root.selectedResource
                readonly property string key: root.selectedKey
                readonly property color ink: root.accentFor(key)
                width: cardStack.width
                height: detailContent.implicitHeight + 4

                Column {
                    id: detailContent
                    x: 2
                    y: 2
                    width: Math.max(0,parent.width-4)
                    spacing: 5
                    // Controls begin immediately here; the selected title,
                    // scope and capability status live in the fixed header.
                    Column {
                        width: parent.width
                        visible: true
                        spacing: 5
                            GohuText {
                                width: parent.width
                                visible: resourcePanel.key!=="memory" && resourcePanel.key!=="swap" && resourcePanel.key!=="threads" && resourcePanel.spec.controls.length > 0
                                text: root.modeFor(resourcePanel.key) === "auto"
                                    ? "AUTO // POLICY NOT CONFIGURED; DRAFT ONLY"
                                    : root.modeFor(resourcePanel.key) === "off"
                                    ? "OFF // DRAFT CHOICE; NO LIMIT RELEASED"
                                    : root.modeFor(resourcePanel.key) === "hold"
                                    ? "HOLD // NO CHANGES REQUESTED"
                                    : "MANUAL // VALUES BELOW ARE STAGED ONLY"
                                color: Colors.white
                                font.pixelSize: 9
                                wrapMode: Text.Wrap
                            }
                            // The operating-mode buttons live beside the FIRST
                            // slider, sharing its footprint instead of another
                            // menu row. A future dial occupies the same left slot.
                            Repeater {
                                model: resourcePanel.key==="memory" || resourcePanel.key==="swap" || resourcePanel.key==="threads" ? [] : resourcePanel.spec.controls
                                delegate: Column {
                                    id: field
                                    required property var modelData
                                    required property int index
                                    width: detailContent.width
                                    readonly property bool priorityField: resourcePanel.key === "cpu" && modelData.key === "nice"
                                    readonly property bool quotaField: resourcePanel.key === "cpu" && modelData.key === "quota"
                                    readonly property bool bandwidthField: resourcePanel.key==="disk" && (modelData.key==="read" || modelData.key==="write")
                                    readonly property var bandwidth: bandwidthField ? root.bandwidthChoice(modelData.key) : null
                                    spacing: 3
                                    Row {
                                        id: instrumentRow
                                        objectName: "cpuPlusResourceInstrumentRow-" + resourcePanel.key + "-" + field.modelData.key
                                        width: field.width
                                        height: field.priorityField ? 150 : 58
                                        spacing: 4
                                        CpuPlusDiagnosticSlider {
                                            objectName: "cpuPlusDraftSlider-" + resourcePanel.key + "-" + field.modelData.key
                                            visible: !field.priorityField
                                            width: Math.max(75,instrumentRow.width - modeCluster.width - instrumentRow.spacing)
                                            height: 54
                                            compact: true
                                            title: field.modelData.title
                                            shortTitle: title
                                            readout: field.quotaField ? (root.quotaDraft.kind==="uncapped" ? "NO CAP" : root.quotaPreviewPercent()+"%")
                                                : field.bandwidthField ? (field.bandwidth.kind==="uncapped" ? "NO CAP" : root.bandwidthPreview(field.modelData.key)+" MiB/s")
                                                : String(root.valueFor(resourcePanel.key,field.modelData.key))+" "+field.modelData.unit
                                            minimumValue: field.modelData.min
                                            maximumValue: field.quotaField ? root.quotaMaximum : field.modelData.max
                                            valueStep: field.quotaField ? 1 : field.modelData.step
                                            currentValue: field.quotaField ? root.quotaPreviewPercent() : field.bandwidthField ? root.bandwidthPreview(field.modelData.key) : root.valueFor(resourcePanel.key,field.modelData.key)
                                            subjectColor: resourcePanel.ink
                                            fillColor: resourcePanel.ink
                                            adjustable: root.selectionReady && root.modeFor(resourcePanel.key) === "manual"
                                            onValueRequested: function(value) {
                                                root.stageNumber(resourcePanel.key,field.modelData.key,Number(value));
                                            }
                                        }
                                        // CPU priority uses the existing shared rotary instrument.
                                        // No separate card or new actuator is introduced.
                                        Loader {
                                            id: priorityDialSlot
                                            active: field.priorityField
                                            visible: active
                                            width: Math.max(70, Math.min(142,(instrumentRow.width-instrumentRow.spacing)*0.54))
                                            height: 148
                                            sourceComponent: SelectorDial {
                                                id: priorityDial
                                                objectName: "cpuPlusPriorityDial"
                                                labelText: "PRIORITY / NICE"
                                                titleColor: Colors.orange
                                                titlePixelSize: 9
                                                selectorMode: "continuous"
                                                minimumValue: -20
                                                maximumValue: 19
                                                valueStep: 1
                                                valueDecimals: 0
                                                snapContinuousToStep: true
                                                currentValue: root.priorityValue()
                                                readoutText: (previewNumericValue>0?"+":"")+Math.round(previewNumericValue)
                                                options: ["-20","-10","0","+10","+19"]
                                                displayOptions: options
                                                numericReferenceValues: [-20,-10,0,10,19]
                                                numericLabelPixelSize: 9
                                                showInstrumentChassis: false
                                                accentColor: Colors.orange
                                                markerColor: Colors.orange
                                                activeDetentColor: Colors.orange
                                                labelColor: Colors.white
                                                interactive: visible && root.selectionReady
                                                    && root.modeFor("cpu")==="manual"
                                                onValueRequested: function(value) {
                                                    if (visible && interactive)
                                                        root.stageNumber("cpu","nice",Math.round(value));
                                                }
                                            }
                                        }
                                        Column {
                                            id: priorityPresetColumn
                                            objectName: "cpuPlusPriorityPresets"
                                            visible: field.priorityField
                                            width: Math.max(1,instrumentRow.width-priorityDialSlot.width-instrumentRow.spacing)
                                            anchors.verticalCenter: parent.verticalCenter
                                            spacing: 4
                                            Repeater {
                                                model: field.priorityField ? Draft.priorityPresets() : []
                                                delegate: ActionButton {
                                                    required property var modelData
                                                    objectName: "cpuPlusPriorityPreset-"+modelData.key
                                                    width: priorityPresetColumn.width
                                                    height: 28
                                                    label: modelData.label
                                                    labelPixelSize: 10
                                                    labelMinimumPixelSize: 7
                                                    normalFace: true
                                                    accentColor: Colors.orange
                                                    selected: root.priorityPresetSelected(modelData.nice)
                                                    available: field.priorityField && root.selectionReady
                                                    onLeftClicked: root.choosePriorityPreset(modelData.key)
                                                }
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: Draft.hasValue(root.staged,"cpu","nice") ? "PRIORITY // DRAFT"
                                                    : root.priorityObserved() ? "PRIORITY // OBSERVED" : "NORMAL // PREVIEW"
                                                color: Colors.white
                                                font.pixelSize: 9
                                                elide: Text.ElideRight
                                            }
                                        }
                                        Grid {
                                            id: modeCluster
                                            objectName: "cpuPlusResourceInlineModes"
                                            visible: field.index === 0
                                            width: visible ? Math.max(112,Math.min(142,instrumentRow.width * 0.45)) : 0
                                            columns: 2
                                            rowSpacing: 3
                                            columnSpacing: 3
                                            Repeater {
                                                model: ["off","manual","auto","hold"]
                                                delegate: ActionButton {
                                                    required property string modelData
                                                    objectName: "cpuPlusResourceMode-" + modelData
                                                    width: Math.max(1,(modeCluster.width - modeCluster.columnSpacing)/2)
                                                    height: 26
                                                    normalFace: true
                                                    accentColor: resourcePanel.ink
                                                    label: modelData.toUpperCase()
                                                    labelPixelSize: 9
                                                    labelMinimumPixelSize: 7
                                                    contentPadding: 1
                                                    selected: root.modeFor(resourcePanel.key) === modelData
                                                    available: root.selectionReady
                                                    onLeftClicked: root.stageMode(resourcePanel.key,modelData)
                                                }
                                            }
                                        }
                                    }
                                    Row {
                                        width: parent.width
                                        height: visible ? 27 : 0
                                        visible: root.modeFor(resourcePanel.key) === "manual"
                                        spacing: 4
                                        GohuText {
                                            width: Math.max(1,parent.width-100)
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: field.priorityField ? "LEADER THREAD // NICE" : "EXACT DRAFT // " + field.modelData.unit
                                            color: Colors.white
                                            elide: Text.ElideRight
                                            font.pixelSize: 9
                                        }
                                        TextField {
                                            id: exactField
                                            objectName: "cpuPlusDraftInput-" + resourcePanel.key + "-" + field.modelData.key
                                            width: 92
                                            height: 26
                                            text: field.quotaField || field.bandwidthField ? "" : field.priorityField ? String(root.priorityValue()) : String(root.valueFor(resourcePanel.key,field.modelData.key))
                                            Binding {
                                                target: exactField
                                                property: "text"
                                                value: field.bandwidthField ? (field.bandwidth.kind==="uncapped" ? "" : String(root.bandwidthPreview(field.modelData.key)))
                                                    : root.quotaDraft.kind==="uncapped" ? "" : String(root.quotaPreviewPercent())
                                                when: (field.quotaField || field.bandwidthField) && !exactField.activeFocus
                                                restoreMode: Binding.RestoreNone
                                            }
                                            property string editIdentity: ""
                                            onActiveFocusChanged: if (activeFocus) editIdentity=root.targetIdentity
                                            placeholderText: field.priorityField ? "UNSET" : ""
                                            color: Colors.white
                                            font.pixelSize: 11
                                            horizontalAlignment: TextInput.AlignHCenter
                                            selectByMouse: true
                                            enabled: root.selectionReady
                                            validator: IntValidator {
                                                bottom: field.modelData.min
                                                top: field.quotaField ? root.quotaMaximum : field.modelData.max
                                            }
                                            background: Rectangle {
                                                color: Colors.black
                                                border.width: 1
                                                border.color: resourcePanel.ink
                                            }
                                            onAccepted: {
                                                if (field.quotaField && acceptableInput && text.length>0
                                                        && editIdentity===root.targetIdentity)
                                                    root.stageQuota("budget",Number(text));
                                                else if (field.bandwidthField && acceptableInput && text.length>0
                                                        && editIdentity===root.targetIdentity)
                                                    root.stageBandwidth(field.modelData.key,"budget",Number(text));
                                            }
                                            onEditingFinished: {
                                                if (field.quotaField || field.bandwidthField) return;
                                                if (acceptableInput)
                                                    root.stageNumber(resourcePanel.key,field.modelData.key,Number(text));
                                                else
                                                    text = String(field.priorityField ? root.priorityValue() : root.valueFor(resourcePanel.key,field.modelData.key));
                                            }
                                        }
                                    }
                                    Row {
                                        id: bandwidthChoices
                                        visible: field.bandwidthField
                                        width: field.width
                                        height: visible ? 28 : 0
                                        spacing: 3
                                        Repeater {
                                            model: field.bandwidthField ? [{key:"budget",label:"SET CAP"},{key:"uncapped",label:"NO CAP"},{key:"restore",label:"RESTORE"}] : []
                                            delegate: ActionButton {
                                                required property var modelData
                                                objectName: "cpuPlusBandwidth-"+field.modelData.key+"-"+modelData.key
                                                width: Math.max(1,(bandwidthChoices.width-2*bandwidthChoices.spacing)/3)
                                                height: 28
                                                label: modelData.label
                                                labelPixelSize: 9
                                                labelMinimumPixelSize: 7
                                                normalFace: true
                                                accentColor: Colors.blue
                                                available: root.selectionReady && root.modeFor("disk")==="manual" && modelData.key!=="restore"
                                                selected: field.bandwidthField && root.modeFor("disk")==="manual" && field.bandwidth.kind===modelData.key
                                                onLeftClicked: {
                                                    if (!available) return;
                                                    if (modelData.key==="budget") root.stageBandwidth(field.modelData.key,"budget",root.bandwidthPreview(field.modelData.key));
                                                    else if (modelData.key==="uncapped") root.stageBandwidth(field.modelData.key,"uncapped",0);
                                                }
                                            }
                                        }
                                    }
                                    GohuText {
                                        width: parent.width
                                        visible: field.bandwidthField
                                        height: visible ? implicitHeight : 0
                                        text: !field.bandwidthField ? "" : field.bandwidth.kind==="preview"
                                            ? "64 MiB/s // PREVIEW, NOT OBSERVED"
                                            : field.bandwidth.kind==="uncapped" ? "DRAFT // NO LOCAL CAP"
                                            : "DRAFT // "+field.bandwidth.mib+" MiB/s"
                                        color: Colors.white
                                        font.pixelSize: 9
                                        wrapMode: Text.Wrap
                                    }
                                    Row {
                                        id: quotaChoices
                                        visible: field.quotaField
                                        width: field.width
                                        height: visible ? 28 : 0
                                        spacing: 3
                                        Repeater {
                                            model: field.quotaField ? [{key:"one",label:"ONE CPU"},{key:"uncapped",label:"NO CAP"},{key:"restore",label:"RESTORE"}] : []
                                            delegate: ActionButton {
                                                required property var modelData
                                                objectName: "cpuPlusQuotaChoice-"+modelData.key
                                                width: Math.max(1,(quotaChoices.width-2*quotaChoices.spacing)/3)
                                                height: 28
                                                label: modelData.label
                                                labelPixelSize: 9
                                                labelMinimumPixelSize: 7
                                                normalFace: true
                                                accentColor: Colors.orange
                                                available: root.selectionReady && root.modeFor("cpu")==="manual" && modelData.key!=="restore"
                                                selected: root.modeFor("cpu")==="manual" && (modelData.key==="one"
                                                    ? root.quotaDraft.kind==="budget" && root.quotaDraft.percent===100
                                                    : modelData.key==="uncapped" && root.quotaDraft.kind==="uncapped")
                                                onLeftClicked: {
                                                    if (!available) return;
                                                    if (modelData.key==="one") root.stageQuota("budget",100);
                                                    else if (modelData.key==="uncapped") root.stageQuota("uncapped",0);
                                                }
                                            }
                                        }
                                    }
                                    GohuText {
                                        width: parent.width
                                        visible: field.quotaField
                                        height: visible ? implicitHeight : 0
                                        text: (root.quotaDraft.kind==="preview" ? "PREVIEW // NOT OBSERVED"
                                            : root.quotaDraft.kind==="uncapped" ? "DRAFT // NO LOCAL CAP"
                                            : "DRAFT // "+(root.quotaDraft.percent/100).toFixed(2)+" CPU EQUIVALENT")
                                            + "\n"+(root.allowedCpuIds.length ? "RANGE REFERENCE // "+root.allowedCpuIds.length+" OBSERVED LEADER CPUs" : "RANGE REFERENCE // ONE CPU")
                                            + "\nGROUP CAPACITY UNVERIFIED // RESTORE LOCKED"
                                        color: Colors.white
                                        font.pixelSize: 9
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                            Column {
                                objectName: "cpuPlusSharedMemoryControls"
                                width: parent.width
                                visible: resourcePanel.key==="memory"
                                spacing: 5
                                GohuText {
                                    width: parent.width
                                    text: root.memoryStatus
                                    color: Colors.magenta
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 10
                                }
                                Row {
                                    id: memoryRow
                                    width: parent.width
                                    height: 62
                                    spacing: 5
                                    CpuPlusDiagnosticSlider {
                                        objectName: "cpuPlusSharedMemorySlider"
                                        width: Math.max(1,memoryRow.width-memoryButtons.width-memoryRow.spacing)
                                        height: 58
                                        compact: true
                                        title: "ADDRESS SPACE"
                                        shortTitle: title
                                        minimumValue: 0
                                        maximumValue: 97
                                        valueStep: 1
                                        currentValue: root.memoryPreviewPercent()
                                        readout: root.memoryRestoreDraft ? "RESTORE"
                                            : root.memoryMinimumMiB>0 ? "~"+root.memoryPreviewMiB(currentValue)+" MiB" : "UNAVAILABLE"
                                        subjectColor: Colors.magenta
                                        fillColor: Colors.magenta
                                        adjustable: root.memoryEditable
                                        onValueRequested: function(value) {
                                            if (root.memoryEditable)
                                                root.memoryStageRequested(Math.round(value));
                                        }
                                    }
                                    Column {
                                        id: memoryButtons
                                        width: Math.min(142,Math.max(102,memoryRow.width*0.45))
                                        spacing: 3
                                        ActionButton {
                                            objectName: "cpuPlusMemorySetLimit"
                                            width: parent.width
                                            height: 28
                                            normalFace: true
                                            accentColor: Colors.magenta
                                            label: "SET LIMIT"
                                            selected: root.memoryFiniteDraft
                                            available: root.memoryEditable
                                            onLeftClicked: root.memoryStageRequested(root.memoryPreviewPercent())
                                        }
                                        ActionButton {
                                            objectName: "cpuPlusMemoryRestore"
                                            width: parent.width
                                            height: 28
                                            normalFace: true
                                            accentColor: Colors.magenta
                                            label: "RESTORE ORIGINAL"
                                            labelPixelSize: 9
                                            labelMinimumPixelSize: 7
                                            selected: root.memoryRestoreDraft
                                            available: root.memoryEditable && root.memoryManaged
                                            onLeftClicked: root.memoryStageRequested(100)
                                        }
                                    }
                                }
                                GohuText {
                                    width: parent.width
                                    text: root.memoryDraftLine() || "NO MEMORY DRAFT // SLIDER IS A PREVIEW"
                                    color: Colors.white
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 10
                                }
                                GohuText {
                                    width: parent.width
                                    text: "RANGE "+root.memoryMinimumMiB+"–"+root.memoryPreviewMiB(97)
                                        +" MiB (ESTIMATE) // VIRTUAL ADDRESS SPACE, NOT RSS"
                                    color: Colors.yellow
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 9
                                    visible: root.memoryEditable
                                }
                                GohuText {
                                    width: parent.width
                                    text: "OTHER RESOURCE DRAFTS MUST BE CLEARED BEFORE MEMORY APPLY"
                                    color: Colors.yellow
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 9
                                    visible: Draft.summary(root.staged).length>0
                                }
                            }
                            Loader {
                                objectName: "cpuPlusTaskBudgetSlot"
                                width: parent.width
                                active: resourcePanel.key==="threads"
                                visible: active
                                height: active && item ? item.implicitHeight : 0
                                sourceComponent: Column {
                                    spacing: 5
                                    GohuText {
                                        width: parent.width
                                        text: "CGROUP TASK BUDGET // DRAFT ONLY"
                                        color: Colors.omnitrix
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Row {
                                        id: taskNumberRow
                                        width: parent.width
                                        height: 40
                                        spacing: 5
                                        ActionButton {
                                            objectName: "cpuPlusTaskMinus"
                                            width: Math.min(40,taskNumberRow.width*0.2)
                                            height: 40
                                            normalFace: true
                                            accentColor: Colors.omnitrix
                                            label: "−"
                                            labelPixelSize: 18
                                            available: root.selectionReady && root.taskPreviewCount()>1
                                            onLeftClicked: if (available) root.stepTasks(-1)
                                        }
                                        TextField {
                                            id: taskExact
                                            objectName: "cpuPlusTaskExactInput"
                                            width: Math.max(1,taskNumberRow.width-2*Math.min(40,taskNumberRow.width*0.2)-2*taskNumberRow.spacing)
                                            height: 40
                                            enabled: root.selectionReady
                                            color: Colors.omnitrix
                                            font.pixelSize: 20
                                            horizontalAlignment: TextInput.AlignHCenter
                                            selectByMouse: true
                                            placeholderText: "NO CAP"
                                            validator: IntValidator { bottom: 1; top: 512 }
                                            property string editIdentity: ""
                                            onActiveFocusChanged: if (activeFocus) editIdentity=root.targetIdentity
                                            Binding {
                                                target: taskExact
                                                property: "text"
                                                value: root.taskDraft.kind==="uncapped" ? "" : String(root.taskPreviewCount())
                                                when: !taskExact.activeFocus
                                                restoreMode: Binding.RestoreNone
                                            }
                                            background: Rectangle {
                                                color: Colors.black
                                                border.width: 1
                                                border.color: Colors.omnitrix
                                            }
                                            onAccepted: {
                                                if (acceptableInput && editIdentity===root.targetIdentity && text.length>0)
                                                    root.stageTasks("budget",Number(text));
                                            }
                                        }
                                        ActionButton {
                                            objectName: "cpuPlusTaskPlus"
                                            width: Math.min(40,taskNumberRow.width*0.2)
                                            height: 40
                                            normalFace: true
                                            accentColor: Colors.omnitrix
                                            label: "+"
                                            labelPixelSize: 18
                                            available: root.selectionReady && root.taskPreviewCount()<512
                                            onLeftClicked: if (available) root.stepTasks(1)
                                        }
                                    }
                                    Row {
                                        id: taskChoices
                                        width: parent.width
                                        height: 28
                                        spacing: 3
                                        Repeater {
                                            model: [{key:"budget",label:"SET CAP"},{key:"uncapped",label:"NO CAP"},{key:"restore",label:"RESTORE"}]
                                            delegate: ActionButton {
                                                required property var modelData
                                                objectName: "cpuPlusTaskChoice-"+modelData.key
                                                width: Math.max(1,(taskChoices.width-2*taskChoices.spacing)/3)
                                                height: 28
                                                label: modelData.label
                                                labelPixelSize: 9
                                                labelMinimumPixelSize: 7
                                                normalFace: true
                                                accentColor: Colors.omnitrix
                                                available: root.selectionReady && modelData.key!=="restore"
                                                selected: root.taskDraft.kind===modelData.key
                                                onLeftClicked: {
                                                    if (!available) return;
                                                    if (modelData.key==="budget") root.stageTasks("budget",root.taskPreviewCount());
                                                    else if (modelData.key==="uncapped") root.stageTasks("uncapped",0);
                                                }
                                            }
                                        }
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: root.taskDraft.kind==="preview" ? "64 TASKS // PREVIEW, NOT OBSERVED"
                                            : root.taskDraft.kind==="uncapped" ? "DRAFT // NO LOCAL CAP (max)"
                                            : "DRAFT // "+root.taskDraft.count+" TASKS"
                                        color: Colors.white
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: "1–512 TASKS // ENTER TO STAGE. CAP RESTRICTS NEW TASK CREATION, NOT EXISTING THREADS."
                                        color: Colors.white
                                        font.pixelSize: 9
                                        wrapMode: Text.Wrap
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: "GROUP COUNT / MEMBERSHIP UNVERIFIED. NO CAP IS NOT RESTORE. RESTORE LOCKED."
                                        color: Colors.yellow
                                        font.pixelSize: 9
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                            Loader {
                                objectName: "cpuPlusSwapBudgetSlot"
                                width: parent.width
                                active: resourcePanel.key==="swap"
                                visible: active
                                height: active && item ? item.implicitHeight : 0
                                sourceComponent: Column {
                                    spacing: 5
                                    GohuText {
                                        width: parent.width
                                        text: "CGROUP SWAP LIMIT // DRAFT ONLY"
                                        color: Colors.yellow
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Row {
                                        id: swapRow
                                        width: parent.width
                                        height: 62
                                        spacing: 5
                                        CpuPlusDiagnosticSlider {
                                            objectName: "cpuPlusSwapBudgetSlider"
                                            width: Math.max(1,swapRow.width-swapButtons.width-swapRow.spacing)
                                            height: 58
                                            compact: true
                                            title: "SWAP BUDGET"
                                            shortTitle: title
                                            minimumValue: 0
                                            maximumValue: 8192
                                            valueStep: 128
                                            currentValue: root.swapPreviewMiB()
                                            readout: root.swapDraft.kind==="uncapped" ? "NO CAP" : String(currentValue)+" MiB"
                                            subjectColor: Colors.yellow
                                            fillColor: Colors.yellow
                                            adjustable: root.selectionReady
                                            onValueRequested: function(value) {
                                                root.stageSwap("budget",Math.round(value));
                                            }
                                        }
                                        Grid {
                                            id: swapButtons
                                            width: Math.min(162,Math.max(112,swapRow.width*0.49))
                                            columns: 2
                                            columnSpacing: 3
                                            rowSpacing: 3
                                            Repeater {
                                                model: [{key:"budget",label:"SET BUDGET"},{key:"zero",label:"NO SWAP"},
                                                    {key:"uncapped",label:"NO CAP"},{key:"restore",label:"RESTORE"}]
                                                delegate: ActionButton {
                                                    required property var modelData
                                                    objectName: "cpuPlusSwapChoice-"+modelData.key
                                                    width: Math.max(1,(swapButtons.width-swapButtons.columnSpacing)/2)
                                                    height: 28
                                                    label: modelData.label
                                                    labelPixelSize: 9
                                                    labelMinimumPixelSize: 7
                                                    normalFace: true
                                                    accentColor: Colors.yellow
                                                    available: root.selectionReady && modelData.key!=="restore"
                                                    selected: modelData.key==="uncapped" ? root.swapDraft.kind==="uncapped"
                                                        : modelData.key==="zero" ? root.swapDraft.kind==="budget" && root.swapDraft.mib===0
                                                        : modelData.key==="budget" && root.swapDraft.kind==="budget" && root.swapDraft.mib>0
                                                    onLeftClicked: {
                                                        if (!available) return;
                                                        if (modelData.key==="zero") root.stageSwap("budget",0);
                                                        else if (modelData.key==="uncapped") root.stageSwap("uncapped",0);
                                                        else if (modelData.key==="budget") root.stageSwap("budget",Math.max(1,root.swapPreviewMiB()));
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    Row {
                                        width: parent.width
                                        height: 28
                                        spacing: 5
                                        GohuText {
                                            width: Math.max(1,parent.width-101)
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: "EXACT MiB // ENTER"
                                            color: Colors.white
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }
                                        TextField {
                                            id: swapExact
                                            objectName: "cpuPlusSwapExactInput"
                                            width: 96
                                            height: 28
                                            enabled: root.selectionReady
                                            color: Colors.white
                                            font.pixelSize: 11
                                            horizontalAlignment: TextInput.AlignHCenter
                                            selectByMouse: true
                                            placeholderText: "MiB"
                                            validator: IntValidator { bottom: 0; top: 8192 }
                                            property string editIdentity: ""
                                            onActiveFocusChanged: if (activeFocus) editIdentity=root.targetIdentity
                                            Binding {
                                                target: swapExact
                                                property: "text"
                                                value: root.swapDraft.kind==="uncapped" ? "" : String(root.swapPreviewMiB())
                                                when: !swapExact.activeFocus
                                            }
                                            background: Rectangle {
                                                color: Colors.black
                                                border.width: 1
                                                border.color: Colors.yellow
                                            }
                                            onAccepted: {
                                                if (acceptableInput && editIdentity===root.targetIdentity && text.length>0)
                                                    root.stageSwap("budget",Number(text));
                                            }
                                        }
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: root.swapDraft.kind==="preview" ? "1024 MiB // PREVIEW, NOT OBSERVED"
                                            : root.swapDraft.kind==="uncapped" ? "DRAFT // NO CAP (max)"
                                            : "DRAFT // "+root.swapDraft.mib+" MiB"
                                        color: Colors.white
                                        wrapMode: Text.Wrap
                                        font.pixelSize: 10
                                    }
                                    GohuText {
                                        width: parent.width
                                        text: "0 DOES NOT PURGE EXISTING SWAP. NO CAP IS NOT RESTORE. RESTORE LOCKED // ORIGINAL NOT CAPTURED."
                                        color: Colors.yellow
                                        wrapMode: Text.Wrap
                                        font.pixelSize: 9
                                    }
                                }
                            }
                            Loader {
                                objectName: "cpuPlusIoPrioritySlot"
                                width: parent.width
                                active: resourcePanel.key==="disk"
                                visible: active
                                height: active ? 158 : 0
                                sourceComponent: Row {
                                    id: ioRow
                                    spacing: 5
                                    readonly property var priority: Draft.ioPriority(root.staged)
                                    readonly property bool bestEffort: priority.kind==="best_effort"
                                    SelectorDial {
                                        id: ioDial
                                        objectName: "cpuPlusIoPriorityDial"
                                        width: Math.max(70,Math.min(142,(ioRow.width-5)*0.54))
                                        height: 150
                                        labelText: "I/O PRIORITY"
                                        titleColor: Colors.blue
                                        titlePixelSize: 9
                                        selectorMode: "continuous"
                                        minimumValue: 0
                                        maximumValue: 7
                                        valueStep: 1
                                        valueDecimals: 0
                                        snapContinuousToStep: true
                                        currentValue: ioRow.bestEffort ? ioRow.priority.level : 4
                                        readoutText: ioRow.bestEffort ? String(Math.round(previewNumericValue)) : "N/A"
                                        options: ["0","1","2","3","4","5","6","7"]
                                        displayOptions: options
                                        numericReferenceValues: [0,1,2,3,4,5,6,7]
                                        numericLabelPixelSize: 9
                                        showInstrumentChassis: false
                                        accentColor: Colors.blue
                                        markerColor: Colors.blue
                                        activeDetentColor: Colors.blue
                                        labelColor: Colors.white
                                        interactive: root.selectionReady && root.modeFor("disk")==="manual" && ioRow.bestEffort
                                        onValueRequested: function(value) {
                                            if (interactive) root.stageIoLevel(Math.round(value));
                                        }
                                    }
                                    Column {
                                        width: Math.max(1,ioRow.width-ioDial.width-ioRow.spacing)
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 4
                                        Repeater {
                                            model: [{key:"best_effort",label:"BEST EFFORT"},{key:"idle",label:"IDLE"}]
                                            delegate: ActionButton {
                                                required property var modelData
                                                objectName: "cpuPlusIoClass-"+modelData.key
                                                width: parent.width
                                                height: 28
                                                label: modelData.label
                                                labelPixelSize: 9
                                                labelMinimumPixelSize: 7
                                                normalFace: true
                                                accentColor: Colors.blue
                                                selected: root.modeFor("disk")==="manual" && ioRow.priority.kind===modelData.key
                                                available: root.selectionReady
                                                onLeftClicked: root.stageIoClass(modelData.key)
                                            }
                                        }
                                        ActionButton {
                                            objectName: "cpuPlusIoRealtimeLocked"
                                            width: parent.width
                                            height: 28
                                            label: "REALTIME // LOCKED"
                                            labelPixelSize: 8
                                            normalFace: true
                                            accentColor: Colors.blue
                                            available: false
                                        }
                                        GohuText {
                                            width: parent.width
                                            text: Draft.hasValue(root.staged,"disk","ioPriority") ? "CLASS // DRAFT"
                                                : "PREVIEW // NOT OBSERVED"
                                            color: Colors.white
                                            wrapMode: Text.Wrap
                                            font.pixelSize: 9
                                        }
                                    }
                                }
                            }
                            Column {
                                objectName: "cpuPlusAffinityControls"
                                visible: resourcePanel.key==="cpu"
                                width: parent.width
                                spacing: 4
                                GohuText {
                                    width: parent.width
                                    text: "AFFINITY // LEADER THREAD"
                                    color: Colors.orange
                                    font.pixelSize: 11
                                }
                                GohuText {
                                    width: parent.width
                                    text: root.allowedCpuIds.length ? root.selectedCpuIds.length+"/"+root.allowedCpuIds.length+" CURRENTLY ALLOWED CPUs"
                                        : "CPU MASK NOT OBSERVED"
                                    color: Colors.white
                                    font.pixelSize: 9
                                    wrapMode: Text.Wrap
                                }
                                Grid {
                                    id: affinityButtons
                                    width: parent.width
                                    columns: Math.max(1,Math.floor(width/48))
                                    rowSpacing: 3
                                    columnSpacing: 3
                                    Repeater {
                                        model: resourcePanel.key==="cpu" ? root.allowedCpuIds : []
                                        delegate: ActionButton {
                                            required property int modelData
                                            objectName: "cpuPlusAffinityCpu-"+modelData
                                            width: Math.max(1,(affinityButtons.width-(affinityButtons.columns-1)*affinityButtons.columnSpacing)/affinityButtons.columns)
                                            height: 26
                                            label: String(modelData)
                                            normalFace: true
                                            accentColor: Colors.orange
                                            selected: root.selectedCpuIds.indexOf(modelData)>=0
                                            available: root.selectionReady && root.modeFor("cpu")==="manual"
                                            onLeftClicked: root.toggleAffinity(modelData)
                                        }
                                    }
                                }
                                Row {
                                    width: parent.width
                                    spacing: 4
                                    ActionButton {
                                        objectName: "cpuPlusAffinityAll"
                                        width: (parent.width-parent.spacing)/2
                                        height: 28
                                        label: "ALL ALLOWED"
                                        labelPixelSize: 9
                                        labelMinimumPixelSize: 7
                                        normalFace: true
                                        accentColor: Colors.orange
                                        available: root.selectionReady && root.allowedCpuIds.length>0 && root.modeFor("cpu")==="manual"
                                        onLeftClicked: root.setAffinity(root.allowedCpuIds)
                                    }
                                    ActionButton {
                                        objectName: "cpuPlusAffinityOne"
                                        width: (parent.width-parent.spacing)/2
                                        height: 28
                                        label: "ONE CPU"
                                        labelPixelSize: 9
                                        normalFace: true
                                        accentColor: Colors.orange
                                        available: root.selectionReady && root.allowedCpuIds.length>0 && root.modeFor("cpu")==="manual"
                                        onLeftClicked: root.setAffinity(root.selectedCpuIds.slice(0,1))
                                    }
                                }
                            }
                            Column {
                                objectName: "cpuPlusReadOnlyResourceInspection"
                                width: parent.width
                                spacing: 5
                                visible: resourcePanel.key==="gpu" || resourcePanel.key==="network"
                                GohuText {
                                    width: parent.width
                                    text: resourcePanel.key==="gpu" ? "GPU // PROCESS DRM EVIDENCE" : "NETWORK // NAMESPACE EVIDENCE"
                                    color: resourcePanel.ink
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                                ActionButton {
                                    objectName: "cpuPlusResourceInspect"
                                    width: parent.width
                                    height: 32
                                    label: root.inspectionBusy ? "INSPECTING" : "INSPECT"
                                    normalFace: true
                                    accentColor: resourcePanel.ink
                                    available: root.selectionReady && !root.inspectionBusy
                                    onLeftClicked: if (available) root.inspectionRequested()
                                }
                                GohuText {
                                    objectName: "cpuPlusResourceInspectionState"
                                    width: parent.width
                                    text: root.inspectionStatus
                                    color: Colors.white
                                    font.pixelSize: 10
                                    wrapMode: Text.Wrap
                                }
                                GohuText {
                                    objectName: "cpuPlusResourceObservation"
                                    width: parent.width
                                    text: resourcePanel.key==="gpu"
                                        ? "DRM FDINFO // "+root.observationLabel(root.exactInspection ? root.exactInspection.gpu : null)
                                        : "NETWORK NAMESPACE COUNTERS // "+root.observationLabel(root.exactInspection ? root.exactInspection.network : null)
                                    color: resourcePanel.ink
                                    font.pixelSize: 10
                                    wrapMode: Text.Wrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: resourcePanel.key==="gpu"
                                        ? "BOUNDED DRM SCAN. NOT OBSERVED DOES NOT MEAN NO GPU USE. GPU UTILIZATION / VRAM LIMIT NOT VERIFIED."
                                        : "NAMESPACE COUNTERS ARE NOT PER-PROCESS TRAFFIC. NO VERIFIED PER-PROCESS RATE OR BANDWIDTH LIMIT."
                                    color: Colors.white
                                    font.pixelSize: 9
                                    wrapMode: Text.Wrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: "ACTUATION // NOT VERIFIED"
                                    color: Colors.yellow
                                    font.pixelSize: 10
                                    wrapMode: Text.Wrap
                                }
                            }
                            GohuText {
                                width: parent.width
                                text: resourcePanel.spec.note
                                color: Colors.orange
                                wrapMode: Text.Wrap
                                font.pixelSize: 9
                            }
                            GohuText {
                                width: parent.width
                                visible: resourcePanel.spec.controls.length === 0
                                text: "OBSERVATION ONLY // NO PROCESS ACTUATOR"
                                color: Colors.white
                                wrapMode: Text.Wrap
                                font.pixelSize: 10
                            }
                        }
                }
            }
        }
    }

    NeonScrollBar {
        objectName: "cpuPlusResourceConsoleScrollBar"
        flickable: bodyScroll
        geometryMode: "viewport"
        reserveSpace: false
        x: bodyScroll.x + bodyScroll.width - width
        y: bodyScroll.y
        height: bodyScroll.height
        topInset: 0
        bottomInset: 0
        handleStyle: "bar"
        railColor: Colors.orange
        handleColor: Colors.magenta
        visible: bodyScroll.contentHeight > bodyScroll.height + 1
        wheelEnabled: false
    }

    // These are workspace actions, not modes. Keep them visible above the
    // red footer divider even when the selected resource has many controls.
    Column {
        id: draftActionsStrip
        objectName: "cpuPlusResourceDraftActionsStrip"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 6
        spacing: 4
        GohuText {
            objectName: "cpuPlusResourceDraftStatus"
            width: parent.width
            text: root.selectionReady
                ? root.hasDraft ? "DRAFT CHANGES // " + root.reviewLines.length + " CATEGORIES"
                    : "NO RESOURCE CHANGES STAGED"
                : "DRAFT INPUT LOCKED // VERIFY TARGET"
            color: root.hasDraft ? Colors.yellow : Colors.white
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        // Actions act on this resource workspace, not the
        // operating mode; they belong ABOVE the footer rule.
        Row {
            id: resourceActions
            objectName: "cpuPlusResourceWorkspaceActions"
            width: parent.width
            height: 30
            spacing: 5
            ActionButton {
                objectName: "cpuPlusResourceClearDraft"
                width: Math.max(1,(parent.width-parent.spacing)/2)
                height: 30
                label: "CLEAR DRAFT"
                labelPixelSize: 10
                normalFace: true
                accentColor: Colors.red
                available: root.selectionReady && root.hasDraft
                onLeftClicked: { root.clearDraft(); root.memoryClearRequested(); }
            }
            ActionButton {
                objectName: "cpuPlusResourceReviewDraft"
                width: Math.max(1,(parent.width-parent.spacing)/2)
                height: 30
                label: "REVIEW"
                labelPixelSize: 10
                selected: root.reviewing
                normalFace: true
                accentColor: Colors.yellow
                available: root.selectionReady && root.hasDraft
                onLeftClicked: {
                    root.reviewing = !root.reviewing;
                    if (root.reviewing) bodyScroll.contentY = 0;
                }
            }
        }

    }

    // Only final actuation occupies the lower footer. It remains deliberately
    // unavailable until native capability and authorization are established.
    Column {
        id: footer
        objectName: "cpuPlusResourceConsoleFooter"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 4
        Rectangle {
            objectName: "cpuPlusResourceFooterDivider"
            width: parent.width
            height: 1
            color: Colors.red
        }
        ActionButton {
            objectName: "cpuPlusResourceApplyLocked"
            visible: root.selectedKey!=="memory"
            width: parent.width
            height: 32
            label: "APPLY LOCKED // UNVERIFIED"
            labelPixelSize: 10
            normalFace: true
            accentColor: Colors.green
            available: false
        }
        ActionButton {
            objectName: "cpuPlusMemoryApplyReview"
            visible: root.selectedKey==="memory"
            width: parent.width
            height: 32
            label: root.memoryCanReview
                ? root.memoryRestoreDraft ? "RESTORE // REVIEW" : "APPLY LIMIT // REVIEW"
                : "APPLY LOCKED // CHECK DRAFT"
            labelPixelSize: 10
            normalFace: true
            accentColor: Colors.green
            available: root.memoryCanReview
            onLeftClicked: if (root.memoryCanReview) root.memoryReviewRequested(root.memoryDraftPercent)
        }
    }
}
