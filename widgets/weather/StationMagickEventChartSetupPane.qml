import QtQuick
import "../../components"
import "StationMagickEventChartSetupPolicy.js" as Setup

// M8b // Ephemeral explicit UTC event input. No birth records saved.
// Sidereal UI remains visible but cannot launch until ayanamsa is validated.
Rectangle {
    id: eventSetup
    color: Colors.black
    border.width:1
    border.color:Colors.magenta
    signal closeRequested()
    signal calculateRequested(var draft)
    property string utcDate: ""
    property string utcTime: ""
    property string latitudeText: ""
    property string longitudeText: ""
    property string zodiac: "tropical"
    property string house: "whole-sign"
    readonly property var draft: Setup.validate(
        utcDate,utcTime,latitudeText,longitudeText,zodiac,house)

    function clearInput(){
        for(let i=0;i<fields.count;i++){
            const item=fields.itemAt(i);
            if(item)item.clearField();
        }
        utcDate="";utcTime="";latitudeText="";longitudeText="";
    }
    onVisibleChanged: if(!visible)clearInput()

    Column {
        anchors.fill:parent
        anchors.margins:7
        spacing:4
        Row {
            width:parent.width;height:24;spacing:4
            GohuText {
                width:Math.max(10,parent.width-75)
                height:24
                verticalAlignment:Text.AlignVCenter
                text:"ASTROLOGY // PRIVATE EVENT SETUP"
                color:Colors.magenta
                font.pixelSize:11
                elide:Text.ElideRight
            }
            ActionButton {
                width:70;height:23
                label:"CLOSE";labelPixelSize:9
                accentColor:Colors.red
                onClicked:eventSetup.closeRequested()
            }
        }
        QuietText {
            width:parent.width;height:16
            font.pixelSize:9;color:Colors.yellow
            text:"SESSION-ONLY INPUT // EXPLICIT UTC // NOT SAVED"
            elide:Text.ElideRight
        }
        Grid {
            id:fieldsGrid
            width:parent.width
            columns:2
            spacing:4
            Repeater {
                id:fields
                model:[
                    {id:"date",label:"UTC DATE YYYY-MM-DD",max:10},
                    {id:"time",label:"UTC TIME HH:MM",max:5},
                    {id:"lat",label:"LATITUDE -90..90",max:24},
                    {id:"lon",label:"LONGITUDE -180..180",max:24}
                ]
                delegate:Column {
                    required property var modelData
                    width:Math.max(40,(fieldsGrid.width-fieldsGrid.spacing)/2)
                    height:43;spacing:2
                    function clearField(){entry.text="";}
                    QuietText {
                        width:parent.width;height:14
                        text:modelData.label;color:Colors.cyan
                        font.pixelSize:8
                        elide:Text.ElideRight
                    }
                    Rectangle {
                        width:parent.width;height:25
                        border.width:1;border.color:Colors.blue
                        color:Colors.dark
                        TextInput {
                            id:entry
                            anchors.fill:parent
                            anchors.margins:3
                            color:Colors.white
                            font.pixelSize:11
                            font.family:"monospace"
                            maximumLength:modelData.max
                            selectByMouse:true
                            onTextChanged:{
                                if(modelData.id==="date")eventSetup.utcDate=text;
                                else if(modelData.id==="time")eventSetup.utcTime=text;
                                else if(modelData.id==="lat")eventSetup.latitudeText=text;
                                else eventSetup.longitudeText=text;
                            }
                        }
                    }
                }
            }
        }
        Row {
            id:zodiacRow
            width:parent.width;height:24;spacing:3
            ActionButton {
                width:(zodiacRow.width-3)/2;height:23
                label:"TROPICAL";labelPixelSize:9
                selected:eventSetup.zodiac==="tropical"
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:eventSetup.zodiac="tropical"
            }
            ActionButton {
                width:(zodiacRow.width-3)/2;height:23
                label:"SIDEREAL";labelPixelSize:9
                selected:eventSetup.zodiac==="sidereal"
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:eventSetup.zodiac="sidereal"
            }
        }
        Row {
            id:houseRow
            width:parent.width;height:24;spacing:3
            ActionButton {
                width:(houseRow.width-3)/2;height:23
                label:"WHOLE SIGN";labelPixelSize:9
                selected:eventSetup.house==="whole-sign"
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:eventSetup.house="whole-sign"
            }
            ActionButton {
                width:(houseRow.width-3)/2;height:23
                label:"EQUAL";labelPixelSize:9
                selected:eventSetup.house==="equal"
                accentColor:selected?Colors.magenta:Colors.cyan
                onClicked:eventSetup.house="equal"
            }
        }
        QuietText {
            width:parent.width;height:19
            color:eventSetup.draft.valid&&eventSetup.zodiac==="tropical"
                ? Colors.green:Colors.orange
            font.pixelSize:9
            elide:Text.ElideRight
            text:eventSetup.zodiac==="sidereal"
                ? "SIDEREAL DISABLED // NO VERIFIED AYANAMSA"
                : eventSetup.draft.valid
                ? "VALID UTC EVENT // JPL CALCULATOR READY"
                : "REQUIRES "+eventSetup.draft.errors.join(", ")
        }
        ActionButton {
            width:parent.width;height:26
            label:"CALCULATE NATAL"
            labelPixelSize:10
            accentColor:Colors.magenta
            available:eventSetup.draft.valid&&eventSetup.zodiac==="tropical"
            onClicked:eventSetup.calculateRequested(eventSetup.draft)
        }
        QuietText {
            width:parent.width;height:15
            color:Colors.cyan;font.pixelSize:8
            text:"JPL POSITIONS / GEOMETRIC ASC + MC / NO DATA SAVED"
            elide:Text.ElideRight
        }
    }
}
