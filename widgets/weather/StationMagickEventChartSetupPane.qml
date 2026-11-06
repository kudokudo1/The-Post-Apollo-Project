import QtQuick
import "../../components"
import "StationMagickEventChartSetupPolicy.js" as Setup

// M7a // Explicit, ephemeral event-chart specification. A *valid spec*
// does not imply a computed natal chart. Never persist event/birth details.
Rectangle {
    id: eventSetup
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    signal closeRequested()
    property string utcDate: ""
    property string utcTime: ""
    property string latitudeText: ""
    property string longitudeText: ""
    property string zodiac: "tropical"
    property string house: "whole-sign"
    readonly property var draft: Setup.validate(
        utcDate,utcTime,latitudeText,longitudeText,zodiac,house)

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 6
        Row {
            width: parent.width
            height: 26
            spacing: 5
            GohuText {
                width: Math.max(25,parent.width-95)
                height: 25
                verticalAlignment: Text.AlignVCenter
                text: "ASTROLOGY // EVENT SETUP"
                color: Colors.magenta
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            ActionButton {
                width: 90
                height: 25
                label: "CLOSE"
                labelPixelSize: 10
                accentColor: Colors.red
                onClicked: eventSetup.closeRequested()
            }
        }
        QuietText {
            width: parent.width
            height: 17
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "SESSION-ONLY INPUT // NO BIRTH DETAILS SAVED"
        }
        Repeater {
            model: [
                {name:"date",label:"UTC DATE (YYYY-MM-DD)",max:10},
                {name:"time",label:"UTC TIME (HH:MM)",max:5},
                {name:"lat",label:"LATITUDE (-90..90)",max:24},
                {name:"lon",label:"LONGITUDE (-180..180)",max:24}
            ]
            delegate: Column {
                required property var modelData
                width: eventSetup.width-18
                height: 47
                spacing: 3
                QuietText {
                    width: parent.width
                    height: 15
                    font.pixelSize: 9
                    color: Colors.cyan
                    text: modelData.label
                }
                Rectangle {
                    width: parent.width
                    height: 27
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.blue
                    TextInput {
                        anchors.fill: parent
                        anchors.margins: 4
                        color: Colors.white
                        font.family: "monospace"
                        font.pixelSize: 12
                        selectByMouse: true
                        maximumLength: modelData.max
                        onTextChanged: {
                            if(modelData.name==="date")eventSetup.utcDate=text;
                            else if(modelData.name==="time")eventSetup.utcTime=text;
                            else if(modelData.name==="lat")eventSetup.latitudeText=text;
                            else eventSetup.longitudeText=text;
                        }
                    }
                }
            }
        }
        Row {
            width: parent.width
            height: 26
            spacing: 4
            ActionButton {
                width: Math.max(60,(parent.width-4)/2)
                height: 25
                label: "TROPICAL"
                labelPixelSize: 9
                selected: eventSetup.zodiac==="tropical"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: eventSetup.zodiac="tropical"
            }
            ActionButton {
                width: Math.max(60,(parent.width-4)/2)
                height: 25
                label: "SIDEREAL"
                labelPixelSize: 9
                selected: eventSetup.zodiac==="sidereal"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: eventSetup.zodiac="sidereal"
            }
        }
        Row {
            width: parent.width
            height: 26
            spacing: 4
            ActionButton {
                width: Math.max(60,(parent.width-4)/2)
                height: 25
                label: "WHOLE SIGN"
                labelPixelSize: 9
                selected: eventSetup.house==="whole-sign"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: eventSetup.house="whole-sign"
            }
            ActionButton {
                width: Math.max(60,(parent.width-4)/2)
                height: 25
                label: "EQUAL"
                labelPixelSize: 9
                selected: eventSetup.house==="equal"
                accentColor: selected?Colors.magenta:Colors.cyan
                onClicked: eventSetup.house="equal"
            }
        }
        QuietText {
            width: parent.width
            height: 20
            font.pixelSize: 10
            color: eventSetup.draft.valid?Colors.green:Colors.orange
            elide: Text.ElideRight
            text: eventSetup.draft.valid
                ? "VALID INPUT // FULL CHART ENGINE NOT CONNECTED"
                : "INPUT NEEDED // "+eventSetup.draft.errors.join(", ")
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.yellow
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "JPL CURRENT SERVICE REPORTS A SELECTED PAIR ONLY"
        }
        QuietText {
            width: parent.width
            height: 19
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
            text: "NO ASCENDANT, HOUSES, FULL NATAL OR TRANSIT CLAIMS"
        }
    }
}
