import QtQuick
import "../components"
import "../services/forest/ForestAutoPolicyPreview.js" as AutoPreview
import "../services/forest/ForestModelFormPolicy.js" as ModelFormPolicy

// Explicit example inputs only. Never reads the composer or sets equipment.
Item {
    id: pane
    property var equipment: null
    property string inventoryStatus: "NOT_CHECKED"
    property var inventoryModels: []
    property string complexity: "unset"
    property string failure: "unset"
    property string suitability: "unset"
    readonly property var result: AutoPreview.preview(complexity, failure, suitability)
    function resetExample() {
        complexity = "unset";
        failure = "unset";
        suitability = "unset";
    }
    onVisibleChanged: if (!visible) resetExample()

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: body.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: body
            width: parent.width
            spacing: 5
            GohuText {
                width: parent.width
                text: "AUTO // OFFLINE POLICY PREVIEW"
                color: Colors.magenta
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "Choose example evidence. No real task assessed, no model started."
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: [
                    { key:"complexity", title:"TASK COMPLEXITY", values:["unset","low","normal","high"] },
                    { key:"failure", title:"KNOWN SMALL FAILURE", values:["unset","absent","present"] },
                    { key:"suitability", title:"SMALL CAPABILITY", values:["unset","sufficient","insufficient","unknown"] }
                ]
                delegate: Column {
                    id: group
                    required property var modelData
                    width: body.width
                    spacing: 2
                    GohuText {
                        text: group.modelData.title
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Flow {
                        width: parent.width
                        spacing: 3
                        Repeater {
                            model: group.modelData.values
                            delegate: Rectangle {
                                required property string modelData
                                readonly property bool chosen: pane[group.modelData.key] === modelData
                                width: Math.max(48, optionText.implicitWidth + 12)
                                height: 23
                                color: chosen ? Colors.yellow : Colors.dark
                                border.width: 1
                                border.color: chosen ? Colors.magenta : Colors.cyan
                                Accessible.name: group.modelData.title + ": " + modelData
                                GohuText {
                                    id: optionText
                                    anchors.centerIn: parent
                                    text: parent.modelData.toUpperCase()
                                    font.pixelSize: 9
                                    color: parent.chosen ? Colors.magenta : Colors.cyan
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (group.modelData.key === "complexity") pane.complexity = parent.modelData;
                                        else if (group.modelData.key === "failure") pane.failure = parent.modelData;
                                        else if (group.modelData.key === "suitability") pane.suitability = parent.modelData;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "EXAMPLE RECOMMENDATION // " + pane.result.form
                font.pixelSize: 11
                color: Colors.yellow
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: pane.result.reasons.join(" / ")
                font.pixelSize: 9
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: pane.result.form === "UNKNOWN" ? "SLOT // UNRESOLVED"
                    : "EQUIPPED SLOT // " + ModelFormPolicy.slotLabel(pane.equipment,
                        pane.result.form.toLowerCase(), pane.inventoryStatus, pane.inventoryModels)
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "PREVIEW ONLY // NO RESOURCE OR PERMISSION DECISION // REASONING INDEPENDENT"
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
