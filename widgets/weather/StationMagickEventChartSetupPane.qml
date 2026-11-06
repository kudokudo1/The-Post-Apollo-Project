import QtQuick
import "../../components"
import "StationMagickEventChartSetupPolicy.js" as Setup

// M7a // Temporary event geometry choices. No reading or storage.
Rectangle {
    id: eventSetup
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    signal closeRequested()
    property string zodiac: "tropical"
    property string house: "whole-sign"
    readonly property var draft: Setup.validate(
        eventDate.text,eventTime.text,eventLat.text,eventLon.text,
        zodiac,house)

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 7
        Row {
            width: parent.width
            height: 27
            spacing: 5
            GohuText {
                width: Math.max(25,parent.width-98)
                height: 26
                verticalAlignment: Text.AlignVCenter
                text: "ASTROLOGY // EVENT SETUP"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            ActionButton {
                width: 90
                height: 26
                label: "CLOSE"
                labelPixelSize: 10
                accentColor: Colors.red
                onClicked: eventSetup.closeRequested()
            }
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.yellow
            font.pixelSize: 9
            text: "SESSION-ONLY INPUT // NO BIRTH DETAILS SAVED"
            elide: Text.ElideRight
        }
        Repeater {
            model: [
                {label:"UTC DATE (YYYY-MM-DD)",id:"date"},
                {label:"UTC TIME (HH:MM)",id:"time"},
                {label:"LATITUDE (-90..90)",id:"lat"},
                {label:"LONGITUDE (-180..180)",id:"lon"}
            ]
            delegate: Item {
                required property var modelData
                width: eventSetup.width-20
                height: 48
                QuietText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    height: 17
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.cyan
                    text: modelData.label
                }
                // Four actual inputs live outside the Repeater for stable
                // named bindings, so this row is labels-only.
            }
        }
        // Separate explicitly bound fields, using the user's own event UTC
        // rather than secretly using the host machine's local clock.
    }
    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.top: parent.top
        anchors.topMargin: 89
        spacing: 28
        Repeater {
            model: [0,1,2,3]
            delegate: Rectangle {
                required property int modelData
                width: parent.width
                height: 25
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue
                // The single actual focusable field is chosen by stack,
                // not dynamically created JS. This keeps per-field state.
                TextInput {
                    visible: modelData===0
                    id: eventDate
                    anchors.fill: parent
                    anchors.margins: 4
                    color: Colors.white
                    font.family: "monospace"
                    font.pixelSize: 12
                    selectByMouse: true
                    maximumLength: 10
                }
                TextInput {
                    visible: modelData===1
                    id: eventTime
                    anchors.fill: parent
                    anchors.margins: 4
                    color: Colors.white
                    font.family: "monospace"
                    font.pixelSize: 12
                    selectByMouse: true
                    maximumLength: 5
                }
                TextInput {
                    visible: modelData===2
                    id: eventLat
                    anchors.fill: parent
                    anchors.margins: 4
                    color: Colors.white
                    font.family: "monospace"
                    font.pixelSize: 12
                    selectByMouse: true
                    maximumLength: 24
                }
                TextInput {
                    visible: modelData===3
                    id: eventLon
                    anchors.fill: parent
                    anchors.margins: 4
                    color: Colors.white
                    font.family: "monospace"
                    font.pixelSize: 12
                    selectByMouse: true
                    maximumLength: 24
                }
            }
        }
    }
    // Input models live in one self-contained overlay with no submission
    // to JPL; actual full-chart calculation requires a new owner contract.
    Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.top: parent.top
        anchors.topMargin: 321
        height: 27
        spacing: 5
        ActionButton {
            width: Math.max(60,(parent.width-5)/2)
            height: 27
            label: "TROPICAL"
            selected: eventSetup.zodiac==="tropical"
            accentColor: selected?Colors.magenta:Colors.cyan
            onClicked: eventSetup.zodiac="tropical"
        }
        ActionButton {
            width: Math.max(60,(parent.width-5)/2)
            height: 27
            label: "SIDEREAL"
            selected: eventSetup.zodiac==="sidereal"
            accentColor: selected?Colors.magenta:Colors.cyan
            onClicked: eventSetup.zodiac="sidereal"
        }
    }
    Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.top: parent.top
        anchors.topMargin: 352
        height: 27
        spacing: 5
        ActionButton {
            width: Math.max(60,(parent.width-5)/2)
            height: 27
            label: "WHOLE SIGN"
            selected: eventSetup.house==="whole-sign"
            accentColor: selected?Colors.magenta:Colors.cyan
            onClicked: eventSetup.house="whole-sign"
        }
        ActionButton {
            width: Math.max(60,(parent.width-5)/2)
            height: 27
            label: "EQUAL"
            selected: eventSetup.house==="equal"
            accentColor: selected?Colors.magenta:Colors.cyan
            onClicked: eventSetup.house="equal"
        }
    }
    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.top: parent.top
        anchors.topMargin: 392
        spacing: 6
        QuietText {
            width: parent.width
            height: 18
            font.pixelSize: 10
            color: eventSetup.draft.valid?Colors.green:Colors.orange
            elide: Text.ElideRight
            text: eventSetup.draft.valid
                ? "VALID INPUT // FULL CHART ENGINE NOT CONNECTED"
                : "INPUT NEEDED // "+eventSetup.draft.errors.join(", ")
        }
        QuietText {
            width: parent.width
            height: 18
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "JPL CURRENT SERVICE REPORTS A SELECTED PAIR ONLY"
        }
        QuietText {
            width: parent.width
            height: 18
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "NO ASCENDANT, HOUSES, FULL NATAL OR TRANSIT CLAIMS"
        }
    }
}
