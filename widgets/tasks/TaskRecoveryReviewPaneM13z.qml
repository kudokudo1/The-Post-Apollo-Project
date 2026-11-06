import QtQuick
import "../../components"
import "TaskRecoveryReviewPolicyM13z.js" as ReviewPolicy

// TASKS M13z // operator-visible, read-only source-review EXAMPLES.
// The real M13y inspector is test-only and no live journal provider exists.
// This pane never reads files, watches a source, stores a draft, saves a
// receipt, authenticates a callback, or calls a write/recovery service.
Column {
    id: review
    width: parent ? parent.width : 400
    spacing: 8

    readonly property bool liveSourceInspectionConnected: false
    property string selectedExample: "baseline"
    readonly property var liveReview: ReviewPolicy.current()
    readonly property var exampleReview: ReviewPolicy.example(selectedExample)
    readonly property var examples: [
        {id:"baseline",label:"UNCHANGED"},
        {id:"expected",label:"UNSETTLED"},
        {id:"settled",label:"SETTLED"}
    ]

    GohuText {
        width: parent.width
        text: "SAVE REVIEW // POST-CRASH"
        color: Colors.magenta
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: review.liveReview.origin
        color: Colors.orange
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: "Real TASKS source and journal are not inspected here. "
              + "Choose an example below to see how a recovery decision "
              + "would be presented after independent verification."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }

    Row {
        id: exampleRail
        width: parent.width
        height: 29
        spacing: 3
        Repeater {
            model: review.examples
            delegate: ModeButton {
                required property var modelData
                width: Math.floor((exampleRail.width - exampleRail.spacing
                                   * (review.examples.length - 1))
                                   / review.examples.length)
                height: exampleRail.height
                textOnly: true
                labelText: modelData.label
                labelFontSize: 9
                bordered: false
                selected: review.selectedExample===modelData.id
                onTriggered: review.selectedExample=modelData.id
            }
        }
    }

    Rectangle {
        width: parent.width
        height: 168
        color: Colors.dark
        border.width: 1
        border.color: Colors.blue
        radius: 3

        Column {
            anchors.fill: parent
            anchors.margins: 9
            spacing: 9

            GohuText {
                width: parent.width
                text: review.exampleReview.origin
                color: Colors.cyan
                font.pixelSize: 9
                font.bold: true
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: review.exampleReview.title
                color: Colors.yellow
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: review.exampleReview.headline
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: review.exampleReview.explanation
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }

    GohuText {
        width: parent.width
        text: review.exampleReview.draftStatus + " // "
              + review.exampleReview.displayStatus
        color: Colors.yellow
        font.pixelSize: 10
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: "NO REPLAY // NO RESTORE // NO DRAFT DELETE"
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }

    GohuText {
        width: parent.width
        text: "These buttons change an example only. "
              + "The existing unsaved-editor indicator above remains "
              + "the live local signal."
        color: Colors.white
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
