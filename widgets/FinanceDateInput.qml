import QtQuick
import "../components"
import "tasks" as TaskFields
import "../services/finance/FinanceInputPolicy.js" as Rules

// Three separate numeric controls; always emits a calendar-valid ISO date.
Item {
    id: dateField
    property string value: ""
    property string fallbackDate: ""
    property bool canEdit: true
    signal valueEdited(string value)
    width: parent ? parent.width : 0
    height: 48

    function commit(part,text) {
        if(!canEdit)return;
        const next=Rules.editDatePart(value,fallbackDate,part,text);
        if(next && next!==value)valueEdited(next);
    }
    function step(part,delta) {
        if(!canEdit)return;
        const next=Rules.stepDatePart(value,fallbackDate,part,delta);
        if(next && next!==value)valueEdited(next);
    }
    readonly property var parts: Rules.parseDate(value)
    Row {
        anchors.fill: parent
        spacing: 4
        Repeater {
            model: [
                {part:"month",title:"MONTH",placeholder:"MM",digits:2},
                {part:"day",title:"DAY",placeholder:"DD",digits:2},
                {part:"year",title:"YEAR",placeholder:"YYYY",digits:4}
            ]
            delegate: Column {
                required property var modelData
                width: (dateField.width-8)/3
                height: dateField.height
                spacing: 4
                GohuText {
                    text: modelData.title
                    font.pixelSize: 9
                    color: Colors.cyan
                }
                TaskFields.TaskDateSegment {
                    width: parent.width
                    part: modelData.part
                    placeholder: modelData.placeholder
                    digitCount: modelData.digits
                    canEdit: dateField.canEdit
                    displayValue: dateField.parts
                        ? String(dateField.parts[modelData.part]).padStart(modelData.digits,"0")
                        : ""
                    onEditCommitted: function(part,value) {dateField.commit(part,value);}
                    onStepRequested: function(part,direction) {dateField.step(part,direction);}
                }
            }
        }
    }
}
