import QtQuick
import Quickshell
import qs.components
import qs.components as Components

// A compact, viewport-anchored editor. It lives OUTSIDE the clipped Table
// Flickable, so horizontal scrolling cannot cut the editor off.
Item {
    id: root

    required property var projectService
    property var keyboardHost: null
    property var targetItem: null
    property string fieldKind: ""
    property int targetProjectNumber: 0
    property bool clearArmed: false

    signal dismissRequested()

    readonly property bool textEntry:
        fieldKind === "title" || fieldKind === "start" || fieldKind === "target"
    readonly property string fieldLabel:
        fieldKind === "title" ? "DRAFT TITLE"
        : String(root.projectService.editableFieldName(fieldKind) || fieldKind).toUpperCase()
    readonly property var choices:
        root.projectService.editableChoices(fieldKind)
    readonly property bool knownField:
        fieldKind === "title" || !!root.projectService.editableField(fieldKind)

    function closeEditor() {
        if (keyboardHost && keyboardHost.activeTextEditor === valueEditor) {
            keyboardHost.activeTextEditor = null;
            keyboardHost.restoreGitKeyboardFocus(false);
        }
        dismissRequested();
    }

    function save(value, clearValue) {
        if (root.projectService.busy)
            return;
        if (root.projectService.selectedNumber() !== targetProjectNumber) {
            root.closeEditor();
            return;
        }
        root.projectService.editItemField(
            targetItem, fieldKind, value, clearValue === true
        );
    }

    onVisibleChanged: {
        clearArmed = false;
        if (visible) {
            valueEditor.text = String(
                root.projectService.editableValue(targetItem, fieldKind) || ""
            );
            if (textEntry) {
                Qt.callLater(function() {
                    if (root.visible)
                        valueEditor.forceActiveFocus();
                });
            } else {
                Qt.callLater(function() {
                    if (root.visible)
                        panel.forceActiveFocus();
                });
            }
        } else if (keyboardHost && keyboardHost.activeTextEditor === valueEditor) {
            keyboardHost.activeTextEditor = null;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.05, 0.0, 0.08, 0.80)
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.closeEditor()
    }

    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: Math.max(150, Math.min(352, root.width - 10))
        height: Math.max(110, Math.min(230, root.height - 6))
        color: Colors.dark
        border.width: 2
        border.color: Colors.magenta
        focus: root.visible
        Keys.onEscapePressed: function(event) {
            root.closeEditor();
            event.accepted = true;
        }

        Column {
            anchors.fill: parent
            anchors.margins: 7
            spacing: 5

            Row {
                width: parent.width
                height: 26
                spacing: 5

                GohuText {
                    width: Math.max(0, parent.width - 33)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text: "EDIT // " + root.fieldLabel
                    font.pixelSize: 11
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
                width: parent.width
                text: root.projectService.itemTitle(root.targetItem)
                color: Colors.white
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            Rectangle {
                width: parent.width
                height: 27
                visible: root.textEntry
                color: Colors.black
                border.width: valueEditor.activeFocus ? 2 : 1
                border.color: Colors.magenta

                TextInput {
                    id: valueEditor
                    anchors.fill: parent
                    anchors.margins: 5
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    color: Colors.magenta
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    cursorDelegate: Rectangle {
                        width: 2
                        color: Colors.orange
                    }
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    clip: true
                    onActiveFocusChanged: {
                        if (!root.keyboardHost)
                            return;
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

            GohuText {
                width: parent.width
                visible: root.fieldKind === "start" || root.fieldKind === "target"
                text: "DATE // YYYY-MM-DD"
                font.pixelSize: 9
                color: Colors.orange
            }

            Flickable {
                id: choiceScroll
                width: parent.width
                height: Math.max(25, panel.height - 116)
                visible: !root.textEntry && root.knownField && root.choices.length > 0
                clip: true
                contentWidth: width
                contentHeight: choiceColumn.height

                Column {
                    id: choiceColumn
                    width: Math.max(0, choiceScroll.width - 20)
                    spacing: 3

                    Repeater {
                        model: root.choices

                        delegate: Components.ActionButton {
                            required property var modelData
                            width: choiceColumn.width
                            height: 27
                            label: String(modelData.label || "")
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            idleForegroundColor: Colors.magenta
                            idleBorderColor: Colors.cyan
                            onTriggered: root.save(modelData.id, false)
                            available: !root.projectService.busy
                        }
                    }
                }

                NeonScrollBar {
                    flickable: choiceScroll
                    handleStyle: "star"
                    visible: scrollable
                }
            }

            GohuText {
                width: parent.width
                visible: !root.textEntry && (!root.knownField || root.choices.length === 0)
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.orange
                text: !root.knownField
                      ? "FIELD NOT CONFIGURED // ADD IT IN GITHUB PROJECTS"
                      : root.fieldKind === "iteration"
                      ? "NO ITERATION IDS EXPOSED // CANNOT SAFELY SELECT A SPRINT"
                      : "NO SELECTABLE OPTIONS WITH GITHUB IDS"
            }

            GohuText {
                width: parent.width
                visible: !root.textEntry && root.choices.length > 0
                font.pixelSize: 9
                color: Colors.cyan
                text: "SELECT AN OPTION TO SAVE"
            }

            GohuText {
                width: parent.width
                visible: root.projectService.lastError.length > 0
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: Colors.red
                text: root.projectService.lastError
            }

            Item {
                width: 1
                height: Math.max(0, panel.height - 141
                                 - (root.textEntry ? 27 : 0)
                                 - (!root.textEntry && root.choices.length > 0
                                    ? Math.max(25, panel.height - 116) : 0))
            }

            Row {
                width: parent.width
                height: 27
                spacing: 5

                Components.ActionButton {
                    width: Math.max(65, (parent.width - 10) / 3)
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
                    width: Math.max(65, (parent.width - 10) / 3)
                    height: parent.height
                    label: "CANCEL"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: !root.projectService.busy
                    onTriggered: root.closeEditor()
                }

                Components.ActionButton {
                    width: Math.max(65, (parent.width - 10) / 3)
                    height: parent.height
                    label: "SAVE"
                    labelPixelSize: 10
                    accentColor: Colors.orange
                    available: root.textEntry && !root.projectService.busy
                    onTriggered: root.save(valueEditor.text, false)
                }
            }
        }
    }
}
