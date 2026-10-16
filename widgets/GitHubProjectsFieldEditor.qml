import QtQuick
import Quickshell
import qs.components
import qs.components as Components

// The host is the whole GitHub Projects panel, not the clipped Table viewport.
// Edits target exactly one existing Project item; no speculative field IDs.
Item {
    id: root

    required property var projectService
    property var keyboardHost: null
    property var targetItem: null
    property string fieldKind: ""
    property int targetProjectNumber: 0
    property bool clearArmed: false
    property bool setupArmed: false

    signal dismissRequested()

    readonly property bool isDate: fieldKind === "start" || fieldKind === "target"
    readonly property bool textEntry: fieldKind === "title" || isDate
    readonly property string fieldLabel:
        fieldKind === "title" ? "DRAFT TITLE"
        : String(projectService.editableFieldName(fieldKind) || fieldKind).toUpperCase()
    readonly property var choices: projectService.editableChoices(fieldKind)
    readonly property color optionAccent:
        fieldKind === "status" ? Colors.yellow
        : fieldKind === "priority" ? Colors.magenta
        : fieldKind === "iteration" ? Colors.orange
        : Colors.cyan
    readonly property bool knownField: fieldKind === "title" || !!projectService.editableField(fieldKind)
    readonly property bool canSetup:
        !knownField && ["status", "priority", "start", "target"].indexOf(fieldKind) >= 0
    readonly property bool canOpenProject:
        fieldKind === "iteration"
        && String(projectService.selectedProjectUrl() || "").length > 0

    function closeEditor() {
        dateInput.releaseFocus();
        if (keyboardHost && keyboardHost.activeTextEditor === valueEditor)
            keyboardHost.activeTextEditor = null;
        if (keyboardHost)
            keyboardHost.restoreGitKeyboardFocus(false);
        dismissRequested();
    }

    function save(value, clearValue) {
        if (projectService.busy)
            return;
        if (projectService.selectedNumber() !== targetProjectNumber) {
            closeEditor();
            return;
        }
        projectService.editItemField(
            targetItem, fieldKind, value, clearValue === true
        );
    }

    onVisibleChanged: {
        clearArmed = false;
        setupArmed = false;
        if (visible) {
            const current = String(projectService.editableValue(targetItem, fieldKind) || "");
            valueEditor.text = current;
            dateInput.reset(current);
            if (fieldKind === "title") {
                Qt.callLater(function() {
                    if (root.visible) valueEditor.forceActiveFocus();
                });
            } else if (!isDate) {
                Qt.callLater(function() {
                    if (root.visible) panel.forceActiveFocus();
                });
            }
        } else {
            dateInput.releaseFocus();
            if (keyboardHost && keyboardHost.activeTextEditor === valueEditor)
                keyboardHost.activeTextEditor = null;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.05, 0.0, 0.08, 0.84)
    }
    MouseArea {
        anchors.fill: parent
        onClicked: root.closeEditor()
    }

    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: Math.max(180, Math.min(356, root.width - 12))
        height: Math.max(150, Math.min(root.isDate ? 225 : 228, root.height - 10))
        color: Colors.dark
        border.width: 2
        border.color: Colors.magenta
        focus: root.visible
        Keys.onEscapePressed: function(event) {
            root.closeEditor();
            event.accepted = true;
        }

        // Clicks on empty panel space must not fall through to the outside
        // dismiss area, but these controls do not cover any action buttons.
        MouseArea {
            anchors.fill: parent
            onClicked: function(mouse) { mouse.accepted = true; }
        }

        Row {
            id: header
            x: 8; y: 7
            width: parent.width - 16
            height: 26
            spacing: 5

            GohuText {
                width: Math.max(0, parent.width - 32)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "EDIT // " + root.fieldLabel
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            Components.ActionButton {
                width: 27
                height: 25
                label: "×"
                labelPixelSize: 12
                accentColor: Colors.orange
                idleForegroundColor: Colors.orange
                idleBorderColor: Colors.orange
                onTriggered: root.closeEditor()
            }
        }

        GohuText {
            id: itemTitle
            x: 8; y: 36
            width: parent.width - 16
            text: root.projectService.itemTitle(root.targetItem)
            color: Colors.white
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        Rectangle {
            id: titleField
            x: 8; y: 61
            width: parent.width - 16
            height: 32
            visible: root.fieldKind === "title"
            color: Colors.black
            border.width: valueEditor.activeFocus ? 2 : 1
            border.color: Colors.magenta

            TextInput {
                id: valueEditor
                anchors.fill: parent
                anchors.margins: 5
                verticalAlignment: TextInput.AlignVCenter
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 12
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                selectByMouse: true
                clip: true
                cursorDelegate: Rectangle {
                    width: 2
                    color: Colors.orange
                }
                onActiveFocusChanged: {
                    if (!root.keyboardHost) return;
                    if (activeFocus)
                        root.keyboardHost.activeTextEditor = valueEditor;
                    else if (root.keyboardHost.activeTextEditor === valueEditor)
                        root.keyboardHost.activeTextEditor = null;
                }
                Keys.onEscapePressed: function(event) {
                    root.closeEditor();
                    event.accepted = true;
                }
                onAccepted: root.save(text, false)
            }
        }

        GitHubProjectsDateInput {
            id: dateInput
            x: 8; y: 63
            width: parent.width - 16
            height: 58
            visible: root.isDate
            keyboardHost: root.keyboardHost
            onSubmitted: function(isoDate) { root.save(isoDate, false); }
        }

        GohuText {
            x: 8; y: 127
            width: parent.width - 16
            visible: root.isDate
            font.pixelSize: 10
            color: Colors.cyan
            text: "DATE // " + (dateInput.preview || "DAY / MONTH / YEAR")
        }

        Flickable {
            id: choiceScroll
            x: 8; y: 59
            width: parent.width - 16
            height: Math.max(25, panel.height - 101)
            visible: !root.textEntry && root.knownField && root.choices.length > 0
            clip: true
            contentWidth: width
            contentHeight: choiceColumn.height
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: choiceColumn
                // Each option uses the entire popup width. Wheel/touch
                // scrolling still works if the menu contains more choices.
                width: choiceScroll.width
                spacing: 4

                Repeater {
                    model: root.choices
                    delegate: Components.ActionButton {
                        required property var modelData
                        width: choiceColumn.width
                        height: 30
                        label: String(modelData.label || "")
                        labelPixelSize: 11
                        accentColor: root.optionAccent
                        idleForegroundColor: Colors.magenta
                        hoverForegroundColor: Colors.magenta
                        pressedForegroundColor: Colors.magenta
                        selectedForegroundColor: Colors.magenta
                        idleBorderColor: root.optionAccent
                        hoverBorderColor: root.optionAccent
                        pressedBorderColor: root.optionAccent
                        selectedBorderColor: root.optionAccent
                        selectedBorderWidth: 2
                        idleFillColor: Colors.black
                        hoverFillColor: Colors.black
                        pressedFillColor: Colors.black
                        selectedFillColor: Colors.black
                        selected: root.projectService.editableValue(
                            root.targetItem, root.fieldKind
                        ) === String(modelData.label || "")
                        onTriggered: root.save(modelData.id, false)
                        available: !root.projectService.busy
                    }
                }
            }

            // Retain the scrollbar contract, but this compact choice menu
            // intentionally has NO visible star, interactive rail or gutter.
            // Flickable still receives normal wheel/trackpad/touch scrolling.
            NeonScrollBar {
                flickable: choiceScroll
                handleStyle: "star"
                mountingParent: panel
                reserveSpace: false
                visible: false
                interactive: false
                wheelEnabled: false
            }
        }

        GohuText {
            id: missingInfo
            x: 8; y: 65
            width: parent.width - 16
            height: 53
            visible: !root.textEntry && (!root.knownField || root.choices.length === 0)
            wrapMode: Text.WordWrap
            font.pixelSize: 10
            color: Colors.orange
            text: !root.knownField
                  ? root.fieldKind === "iteration"
                    ? "ITERATION FIELD MISSING // CONFIGURE IT IN GITHUB"
                    : "FIELD NOT CONFIGURED // SET UP BELOW"
                  : root.fieldKind === "iteration"
                    ? "NO ITERATION IDS EXPOSED // OPEN GITHUB PROJECT FIELDS"
                    : "NO SELECTABLE OPTIONS WITH GITHUB IDS"
        }

        Components.ActionButton {
            x: 8
            y: root.isDate ? 150 : 129
            width: parent.width - 16
            height: root.isDate ? 30 : 32
            visible: root.canSetup
            label: root.setupArmed
                   ? "CONFIRM CREATE " + root.fieldLabel
                   : "CREATE " + root.fieldLabel + " FIELD"
            labelPixelSize: 10
            accentColor: Colors.orange
            idleForegroundColor: Colors.orange
            idleBorderColor: Colors.orange
            available: !root.projectService.busy
            onTriggered: {
                if (root.setupArmed)
                    root.projectService.setupMissingField(root.fieldKind);
                else
                    root.setupArmed = true;
            }
        }

        Components.ActionButton {
            x: 8; y: 129
            width: parent.width - 16
            height: 32
            visible: root.canOpenProject && !root.canSetup
                     && (!root.knownField || root.choices.length === 0)
            label: "OPEN GITHUB PROJECT FIELDS"
            labelPixelSize: 10
            accentColor: Colors.cyan
            available: !root.projectService.busy
            onTriggered: {
                const url = root.projectService.selectedProjectUrl();
                if (url)
                    Qt.openUrlExternally(url);
            }
        }

        GohuText {
            x: 8
            y: root.isDate ? 146 : 170
            width: parent.width - 16
            height: 24
            visible: root.projectService.lastError.length > 0
                     && !root.canSetup
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            color: Colors.red
            text: root.projectService.lastError
            elide: Text.ElideRight
        }

        Row {
            id: actionRow
            x: 8; y: panel.height - 34
            width: parent.width - 16
            height: 27
            spacing: 5

            Components.ActionButton {
                width: Math.max(50, (parent.width - 10) / 3)
                height: parent.height
                label: root.clearArmed ? "CLEAR?" : "CLEAR"
                labelPixelSize: 10
                destructive: true
                accentColor: Colors.red
                available: root.fieldKind !== "title"
                           && root.knownField
                           && !root.projectService.busy
                onTriggered: {
                    if (root.clearArmed)
                        root.save("", true);
                    else
                        root.clearArmed = true;
                }
            }

            Components.ActionButton {
                width: Math.max(50, (parent.width - 10) / 3)
                height: parent.height
                label: "CANCEL"
                labelPixelSize: 10
                accentColor: Colors.cyan
                available: !root.projectService.busy
                onTriggered: root.closeEditor()
            }

            Components.ActionButton {
                width: Math.max(50, (parent.width - 10) / 3)
                height: parent.height
                label: "SAVE"
                labelPixelSize: 10
                accentColor: Colors.orange
                available: root.textEntry && root.knownField
                           && !root.projectService.busy
                onTriggered: root.save(
                    root.isDate ? dateInput.isoValue() : valueEditor.text, false
                )
            }
        }
    }
}
