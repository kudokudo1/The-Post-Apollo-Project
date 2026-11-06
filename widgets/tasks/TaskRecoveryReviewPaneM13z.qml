import QtQuick
import "../../components"
import "TaskRecoveryReviewPolicyM13z.js" as ReviewPolicy
import "TaskLiveNativeSavePolicyM14a.js" as NativeSavePolicy

// TASKS M13z // operator-visible, read-only source-review EXAMPLES.
// The real M13y inspector is test-only and no live journal provider exists.
// This pane never reads files, watches a source, stores a draft, saves a
// receipt, authenticates a callback, or calls a write/recovery service.
Column {
    id: review
    width: parent ? parent.width : 400
    spacing: 8

    readonly property bool liveSourceInspectionConnected: false
    // M14a // Metadata from the real existing FileView lifecycle only.
    // It is not an independent source readback or a trusted save receipt.
    property var nativeSaveSignals: null
    readonly property var nativeSaveReport: NativeSavePolicy.view(nativeSaveSignals)
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

    Rectangle {
        width: parent.width
        height: nativeSignalBody.implicitHeight + 18
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        radius: 3

        Column {
            id: nativeSignalBody
            x: 9
            y: 9
            width: parent.width - 18
            spacing: 7

            GohuText {
                width: parent.width
                text: "LIVE // NATIVE SAVE SIGNAL"
                font.pixelSize: 10
                font.bold: true
                color: Colors.magenta
            }

            GohuText {
                width: parent.width
                text: review.nativeSaveReport.status
                font.pixelSize: 10
                color: Colors.yellow
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: review.nativeSaveReport.sourceStatus
                font.pixelSize: 9
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: review.nativeSaveReport.explanation
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: review.nativeSaveReport.proof
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }

    GohuText {
        width: parent.width
        text: "POST-CRASH SCENARIOS // EXAMPLES ONLY"
        color: Colors.magenta
        font.pixelSize: 10
        font.bold: true
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
        height: detailBody.implicitHeight + 18
        color: Colors.dark
        border.width: 1
        border.color: Colors.blue
        radius: 3

        Column {
            id: detailBody
            x: 9
            y: 9
            width: parent.width - 18
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
