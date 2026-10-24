import QtQuick
import "../components"

// M4 side-by-side evidence, limited to two explicitly inspected filings.
// This display does not infer price impact, insider intent or correlations.
Item {
    id: comparison
    property var evidenceSlots: []
    readonly property bool wide: width >= 550
    implicitHeight: comparisonGrid.implicitHeight

    Grid {
        id: comparisonGrid
        width: parent.width
        columns: comparison.wide ? 2 : 1
        rowSpacing: 8
        columnSpacing: 8
        Repeater {
            model: comparison.evidenceSlots
            delegate: Rectangle {
                id: card
                required property var modelData
                required property int index
                width: comparison.wide ? (comparison.width - 8) / 2 : comparison.width
                height: fields.implicitHeight + 20
                color: Colors.black
                border.width: 1
                border.color: card.index === 0 ? Colors.cyan : Colors.magenta

                Column {
                    id: fields
                    anchors.top: parent.top
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 9
                    anchors.right: parent.right
                    anchors.rightMargin: 9
                    spacing: 9
                    GohuText {
                        width: parent.width
                        text: card.index === 0 ? "EVIDENCE A" : "EVIDENCE B"
                        font.pixelSize: 11
                        font.bold: true
                        color: card.index === 0 ? Colors.cyan : Colors.magenta
                    }
                    GohuText {
                        width: parent.width
                        text: "FORM " + card.modelData.form + " // " + card.modelData.filedAt
                        font.pixelSize: 10
                        color: Colors.white
                    }
                    GohuText {
                        width: parent.width
                        text: card.modelData.facts.label + "\n" + card.modelData.facts.summary
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.orange
                    }
                    GohuText {
                        width: parent.width
                        text: card.modelData.facts.secondary
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                        color: Colors.white
                    }
                    Repeater {
                        model: card.modelData.facts.excerpts
                        delegate: GohuText {
                            required property string modelData
                            width: fields.width
                            text: "• " + modelData
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                            color: Colors.white
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: card.modelData.documentUrl
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 9
                        color: Colors.cyan
                    }
                    GohuText {
                        width: parent.width
                        text: card.modelData.facts.caveat
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                        font.pixelSize: 9
                        color: Colors.orange
                    }
                }
            }
        }
    }
}
