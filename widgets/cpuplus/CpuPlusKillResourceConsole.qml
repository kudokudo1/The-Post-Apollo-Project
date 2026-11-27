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
    readonly property var reviewLines: Draft.summary(staged)
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
        staged = Draft.stageValue(staged,key,field,number);
        reviewing = false;
    }
    function accentFor(key) {
        if (key === "cpu") return Colors.orange;
        if (key === "memory") return Colors.magenta;
        if (key === "swap") return Colors.yellow;
        if (key === "disk") return Colors.blue;
        if (key === "threads" || key === "gpu") return Colors.omnitrix;
        return Colors.cyan;
    }

    Column {
        id: heading
        objectName: "cpuPlusResourceConsoleHeader"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 3
        GohuText {
            width: parent.width
            text: "RESOURCE CONTROL // DRAFT"
            font.pixelSize: 12
            color: Colors.orange
            elide: Text.ElideRight
        }
        GohuText {
            width: parent.width
            text: root.selectionReady ? "EXACT PROCESS SELECTED // NOT APPLIED"
                : "SELECT VERIFIED PROCESS // READ ONLY"
            font.pixelSize: 9
            color: root.selectionReady ? Colors.white : Colors.yellow
            elide: Text.ElideRight
        }
        Rectangle { width: parent.width; height: 1; color: Colors.red }
    }

    // All resource categories remain visible in a single filter row.
    Row {
        id: resourceFilters
        objectName: "cpuPlusResourceCategoryFilters"
        anchors.top: heading.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
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

    // The standard Post-Apollo information control stays in the top-right
    // immediately beneath the category row, never in the left control area.
    Item {
        id: resourceInfoStrip
        objectName: "cpuPlusResourceInformationStrip"
        anchors.top: resourceFilters.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        height: 24
        z: 10
        ProcessInformationButton {
            id: resourceInformationButton
            objectName: "cpuPlusResourceInformationButton"
            anchors.right: parent.right
            anchors.top: parent.top
            selected: root.informationOpen
            onLeftClicked: root.informationOpen = !root.informationOpen
        }
        Rectangle {
            id: resourceInformationPopup
            objectName: "cpuPlusResourceInformationPopup"
            anchors.right: parent.right
            anchors.top: resourceInformationButton.bottom
            anchors.topMargin: 3
            width: Math.min(320, Math.max(0,root.width - 6))
            height: informationContent.implicitHeight + 12
            color: Colors.black
            border.width: 1
            border.color: Colors.yellow
            visible: root.informationOpen
            z: 11
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
                    text: "OFF / MANUAL / AUTO / HOLD ARE DRAFTS ONLY. "
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
        anchors.top: resourceInfoStrip.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 4
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
                    GohuText {
                        width: parent.width
                        text: resourcePanel.spec.title + " // CONTROLS"
                        color: resourcePanel.ink
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                        Column {
                            width: parent.width
                            visible: true
                            spacing: 5
                            GohuText {
                                width: parent.width
                                text: resourcePanel.spec.scope
                                color: resourcePanel.ink
                                font.pixelSize: 9
                                wrapMode: Text.Wrap
                            }
                            GohuText {
                                width: parent.width
                                text: "CAPABILITY AND WRITE PERMISSION // NOT VERIFIED"
                                color: Colors.orange
                                font.pixelSize: 9
                                wrapMode: Text.Wrap
                            }
                            GohuText {
                                width: parent.width
                                visible: resourcePanel.spec.controls.length > 0
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
                                model: resourcePanel.spec.controls
                                delegate: Column {
                                    id: field
                                    required property var modelData
                                    required property int index
                                    width: detailContent.width
                                    spacing: 3
                                    Row {
                                        id: instrumentRow
                                        objectName: "cpuPlusResourceInstrumentRow-" + resourcePanel.key + "-" + field.modelData.key
                                        width: field.width
                                        height: 58
                                        spacing: 4
                                        CpuPlusDiagnosticSlider {
                                            objectName: "cpuPlusDraftSlider-" + resourcePanel.key + "-" + field.modelData.key
                                            width: Math.max(75,instrumentRow.width - modeCluster.width - instrumentRow.spacing)
                                            height: 54
                                            compact: true
                                            title: field.modelData.title
                                            shortTitle: title
                                            readout: String(root.valueFor(resourcePanel.key,field.modelData.key))
                                                + " " + field.modelData.unit
                                            minimumValue: field.modelData.min
                                            maximumValue: field.modelData.max
                                            valueStep: field.modelData.step
                                            currentValue: root.valueFor(resourcePanel.key,field.modelData.key)
                                            subjectColor: resourcePanel.ink
                                            fillColor: resourcePanel.ink
                                            adjustable: root.selectionReady && root.modeFor(resourcePanel.key) === "manual"
                                            onValueRequested: function(value) {
                                                root.stageNumber(resourcePanel.key,field.modelData.key,Number(value));
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
                                            text: "EXACT DRAFT // " + field.modelData.unit
                                            color: Colors.white
                                            elide: Text.ElideRight
                                            font.pixelSize: 9
                                        }
                                        TextField {
                                            objectName: "cpuPlusDraftInput-" + resourcePanel.key + "-" + field.modelData.key
                                            width: 92
                                            height: 26
                                            text: String(root.valueFor(resourcePanel.key,field.modelData.key))
                                            color: Colors.white
                                            font.pixelSize: 11
                                            horizontalAlignment: TextInput.AlignHCenter
                                            selectByMouse: true
                                            enabled: root.selectionReady
                                            validator: IntValidator {
                                                bottom: field.modelData.min
                                                top: field.modelData.max
                                            }
                                            background: Rectangle {
                                                color: Colors.black
                                                border.width: 1
                                                border.color: resourcePanel.ink
                                            }
                                            onEditingFinished: {
                                                if (acceptableInput)
                                                    root.stageNumber(resourcePanel.key,field.modelData.key,Number(text));
                                                else
                                                    text = String(root.valueFor(resourcePanel.key,field.modelData.key));
                                            }
                                        }
                                    }
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
                                    onLeftClicked: root.clearDraft()
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
            width: parent.width
            height: 32
            label: "APPLY LOCKED // UNVERIFIED"
            labelPixelSize: 10
            normalFace: true
            accentColor: Colors.green
            available: false
        }
    }
}
