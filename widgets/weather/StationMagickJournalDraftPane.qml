import QtQuick
import "../../components"
import "StationMagickJournalDraftPolicy.js" as Draft

// M7a // In-memory text editor ONLY. No file, journal receipt, cloud sync,
// keychain access, autosave, history, export or telemetry. Discard on hide.
Rectangle {
    id: journal
    color: Colors.black
    clip: true
    property bool clearArmed: false
    readonly property var preview: Draft.summary(titleField.text,bodyField.text)
    function discard() {
        titleField.text="";
        bodyField.text="";
        clearArmed=false;
    }
    onVisibleChanged: {
        if(!visible)discard();
    }
    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 6
        GohuText {
            width: parent.width
            height: 22
            font.pixelSize: 13
            color: Colors.magenta
            text: "GRIMOIRE // PRIVATE SCRATCHPAD"
            elide: Text.ElideRight
        }
        QuietText {
            width: parent.width
            height: 22
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "UNSAVED SESSION DRAFT // DISCARDED WHEN CLOSED"
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.cyan
            font.pixelSize: 10
            text: "TITLE"
        }
        Rectangle {
            width: parent.width
            height: 30
            color: Colors.dark
            border.color: Colors.blue
            border.width: 1
            TextInput {
                id: titleField
                anchors.fill: parent
                anchors.margins: 5
                font.family: "monospace"
                font.pixelSize: 12
                color: Colors.white
                selectByMouse: true
                maximumLength: Draft.MAX_TITLE
                onTextChanged: journal.clearArmed=false
            }
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.cyan
            font.pixelSize: 10
            text: "OBSERVATION / REFLECTION"
        }
        Rectangle {
            width: parent.width
            height: Math.max(125,journal.height-232)
            color: Colors.dark
            border.color: Colors.blue
            border.width: 1
            clip: true
            TextEdit {
                id: bodyField
                anchors.fill: parent
                anchors.margins: 6
                font.family: "monospace"
                font.pixelSize: 11
                color: Colors.white
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                selectByMouse: true
                onTextChanged: {
                    if(text.length>Draft.MAX_BODY)
                        text=text.slice(0,Draft.MAX_BODY);
                    journal.clearArmed=false;
                }
            }
        }
        QuietText {
            width: parent.width
            height: 20
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: journal.preview.valid
                ? journal.preview.wordCount+" WORDS // "+
                  journal.preview.characters+" CHARACTERS // NOT SAVED"
                : journal.preview.reason
        }
        Row {
            width: parent.width
            height: 26
            spacing: 7
            ActionButton {
                width: 126
                height: 25
                label: journal.clearArmed?"CONFIRM CLEAR":"CLEAR DRAFT"
                labelPixelSize: 9
                accentColor: journal.clearArmed?Colors.red:Colors.orange
                available: journal.preview.hasContent
                onClicked: {
                    if(journal.clearArmed)journal.discard();
                    else journal.clearArmed=true;
                }
            }
            QuietText {
                width: Math.max(12,parent.width-133)
                height: 25
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 9
                color: journal.clearArmed?Colors.red:Colors.cyan
                elide: Text.ElideRight
                text: journal.clearArmed?"SECOND CLICK DELETES":
                    "NO FILES // NO SYNC // NO HISTORY"
            }
        }
        QuietText {
            width: parent.width
            height: 18
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "PERSISTENT PRIVATE JOURNAL REQUIRES SEPARATE SECURITY APPROVAL"
        }
    }
}
