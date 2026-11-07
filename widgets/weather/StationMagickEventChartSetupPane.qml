import QtQuick
import qs.services.location
import "../../components"
import "StationMagickEventChartSetupPolicy.js" as Setup
import "StationMagickDateLocationPolicy.js" as Defaults

// M8d // Reuses TASKS date steppers. UTC TODAY/NOW are captured once on
// opening/click, never continuously. Location uses only the user's manually
// configured Post-Apollo Home (NOT current GPS); no IP or Explore inference.
// Typed coordinates override Home only as a complete latitude/longitude pair.
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
    readonly property var savedHome: PlaceRegistry.storageState==="ready"
        ? PlaceRegistry.homePlace : null
    readonly property var place: Defaults.location(
        latitudeText,longitudeText,savedHome)
    readonly property var draft: Setup.validate(
        utcDate,utcTime,place.latitude,place.longitude,zodiac,house)

    function setCurrentDate(){
        const d=Defaults.utcDay();
        if(d)utcDate=d;
    }
    function setCurrentInstant(){
        const current=Defaults.utcClock();
        if(!current)return;
        utcDate=current.date;
        timeInput.text=current.time;
    }
    function clearInput(){
        utcDate="";
        utcTime="";
        timeInput.text="";
        latitudeEntry.text="";
        longitudeEntry.text="";
        latitudeText="";
        longitudeText="";
        dateField.releaseFocus();
        timeInput.focus=false;
        latitudeEntry.focus=false;
        longitudeEntry.focus=false;
    }
    onVisibleChanged: {
        if(visible){
            if(!utcDate)setCurrentDate();
        } else clearInput();
    }

    Column {
        anchors.fill:parent
        anchors.margins:6
        spacing:3
        Row {
            width:parent.width;height:23;spacing:4
            GohuText {
                width:Math.max(10,parent.width-74)
                height:23
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
            width:parent.width;height:14
            font.pixelSize:8;color:Colors.yellow
            text:"UTC DATE / MONTH · DAY · YEAR // TASKS STEPPERS"
            elide:Text.ElideRight
        }
        StationMagickUtcDateField {
            id:dateField
            width:parent.width;height:26
            dateValue:eventSetup.utcDate
            onDateEdited:function(date){eventSetup.utcDate=date;}
        }
        Row {
            id:timeRow
            width:parent.width;height:26;spacing:4
            QuietText {
                width:62;height:25
                text:"TIME UTC"
                font.pixelSize:9;color:Colors.cyan
                verticalAlignment:Text.AlignVCenter
            }
            Rectangle {
                width:Math.max(52,timeRow.width-62-74-2*timeRow.spacing)
                height:25;color:Colors.dark
                border.width:1;border.color:Colors.blue
                TextInput {
                    id:timeInput
                    anchors.fill:parent;anchors.margins:3
                    color:Colors.white
                    font.pixelSize:11;font.family:"monospace"
                    maximumLength:5;selectByMouse:true
                    inputMethodHints:Qt.ImhTime
                    onTextChanged:eventSetup.utcTime=text
                }
            }
            ActionButton {
                width:74;height:25
                label:"NOW UTC";labelPixelSize:9
                accentColor:Colors.yellow
                onClicked:eventSetup.setCurrentInstant()
            }
        }
        Row {
            id:locationLabels
            width:parent.width;height:13;spacing:4
            QuietText {
                width:(locationLabels.width-4)/2;height:13
                font.pixelSize:8;color:Colors.cyan
                text:"LATITUDE (-90..90)"
                elide:Text.ElideRight
            }
            QuietText {
                width:(locationLabels.width-4)/2;height:13
                font.pixelSize:8;color:Colors.cyan
                text:"LONGITUDE (-180..180)"
                elide:Text.ElideRight
            }
        }
        Row {
            id:locationInputs
            width:parent.width;height:25;spacing:4
            Rectangle {
                width:(locationInputs.width-4)/2;height:25
                color:Colors.dark;border.width:1;border.color:Colors.blue
                TextInput {
                    id:latitudeEntry
                    anchors.fill:parent;anchors.margins:3
                    color:Colors.white;font.pixelSize:11
                    font.family:"monospace"
                    maximumLength:24;selectByMouse:true
                    onTextChanged:eventSetup.latitudeText=text
                }
                QuietText {
                    anchors.fill:latitudeEntry
                    visible:latitudeEntry.text===""&&!latitudeEntry.activeFocus
                        && eventSetup.place.source==="HOME"
                    color:Colors.yellow;font.pixelSize:10
                    opacity:.75
                    text:"AUTO "+eventSetup.place.latitude
                    verticalAlignment:Text.AlignVCenter
                    elide:Text.ElideRight
                }
            }
            Rectangle {
                width:(locationInputs.width-4)/2;height:25
                color:Colors.dark;border.width:1;border.color:Colors.blue
                TextInput {
                    id:longitudeEntry
                    anchors.fill:parent;anchors.margins:3
                    color:Colors.white;font.pixelSize:11
                    font.family:"monospace"
                    maximumLength:24;selectByMouse:true
                    onTextChanged:eventSetup.longitudeText=text
                }
                QuietText {
                    anchors.fill:longitudeEntry
                    visible:longitudeEntry.text===""&&!longitudeEntry.activeFocus
                        && eventSetup.place.source==="HOME"
                    color:Colors.yellow;font.pixelSize:10
                    opacity:.75
                    text:"AUTO "+eventSetup.place.longitude
                    verticalAlignment:Text.AlignVCenter
                    elide:Text.ElideRight
                }
            }
        }
        QuietText {
            width:parent.width;height:16;font.pixelSize:8
            color:eventSetup.place.ready?Colors.cyan:Colors.orange
            elide:Text.ElideRight
            text:eventSetup.place.source==="HOME"
                ? "AUTO HOME // SAVED DEFAULT, NOT LIVE GPS // "+eventSetup.place.label
                :eventSetup.place.label
        }
        Row {
            id:zodiacRow
            width:parent.width;height:23;spacing:3
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
            width:parent.width;height:23;spacing:3
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
            width:parent.width;height:16
            color:eventSetup.draft.valid&&eventSetup.zodiac==="tropical"
                ?Colors.green:Colors.orange
            font.pixelSize:8
            elide:Text.ElideRight
            text:eventSetup.zodiac==="sidereal"
                ?"SIDEREAL DISABLED // NO VERIFIED AYANAMSA"
                :eventSetup.draft.valid
                ?"VALID UTC EVENT // JPL CALCULATOR READY"
                :"REQUIRES "+eventSetup.draft.errors.join(", ")
        }
        ActionButton {
            width:parent.width;height:26
            label:"CALCULATE NATAL";labelPixelSize:10
            accentColor:Colors.magenta
            available:eventSetup.draft.valid&&eventSetup.zodiac==="tropical"
            onClicked:eventSetup.calculateRequested(eventSetup.draft)
        }
        QuietText {
            width:parent.width;height:14
            color:Colors.cyan;font.pixelSize:8
            text:"SESSION ONLY // NO PROFILE OR BIRTH DATA SAVED"
            elide:Text.ElideRight
        }
    }
}
