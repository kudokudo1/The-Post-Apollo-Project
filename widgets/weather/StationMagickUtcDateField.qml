import QtQuick
import "../../components"
import "../tasks" as TasksFields
import "../tasks/TaskDateSegments.js" as Segments
import "StationMagickEventChartSetupPolicy.js" as Setup
import "StationMagickDateLocationPolicy.js" as Defaults

// M8d // Reuse TASKS's actual M/D/Y spinboxes without touching TASKS code.
// This is a UTC date draft, not a local TASKS due-date or a stored event.
Item {
    id: dateField
    property string dateValue: ""
    property bool canEdit: true
    signal dateEdited(string value)
    height:26

    function part(kind){return Segments.part(dateValue,kind);}
    function currentBase(){
        return Setup.eventDate(dateValue)?dateValue:Defaults.utcDay();
    }
    function editPart(kind,value){
        if(!canEdit)return;
        const source=currentBase();
        if(!source)return;
        const next=Segments.setPart(source,kind,value);
        if(next.accepted&&Setup.eventDate(next.date))
            dateEdited(next.date);
    }
    function stepPart(kind,direction){
        if(!canEdit)return;
        const source=currentBase();
        if(!source)return;
        const next=Segments.step(source,kind,direction);
        if(Setup.eventDate(next))dateEdited(next);
    }
    function today(){
        if(!canEdit)return;
        const today=Defaults.utcDay();
        if(today)dateEdited(today);
    }
    function releaseFocus(){
        month.releaseFocus();day.releaseFocus();year.releaseFocus();
    }

    Row {
        id: segments
        anchors.fill:parent
        spacing:3
        readonly property real usable:Math.max(0,width-54-3*spacing)
        TasksFields.TaskDateSegment {
            id:month
            width:segments.usable*.29
            part:"month"
            placeholder:"MM"
            digitCount:2
            displayValue:dateField.part("month")
            canEdit:dateField.canEdit
            onEditCommitted:function(part,value){dateField.editPart(part,value);}
            onStepRequested:function(part,direction){dateField.stepPart(part,direction);}
        }
        TasksFields.TaskDateSegment {
            id:day
            width:segments.usable*.29
            part:"day"
            placeholder:"DD"
            digitCount:2
            displayValue:dateField.part("day")
            canEdit:dateField.canEdit
            onEditCommitted:function(part,value){dateField.editPart(part,value);}
            onStepRequested:function(part,direction){dateField.stepPart(part,direction);}
        }
        TasksFields.TaskDateSegment {
            id:year
            width:segments.usable*.42
            part:"year"
            placeholder:"YYYY"
            digitCount:4
            displayValue:dateField.part("year")
            canEdit:dateField.canEdit
            onEditCommitted:function(part,value){dateField.editPart(part,value);}
            onStepRequested:function(part,direction){dateField.stepPart(part,direction);}
        }
        ActionButton {
            width:54;height:26
            label:"TODAY"
            labelPixelSize:9
            accentColor:Colors.yellow
            available:dateField.canEdit
            onClicked:dateField.today()
        }
    }
}
