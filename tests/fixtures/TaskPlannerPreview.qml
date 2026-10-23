import QtQuick
import QtQuick.Window
import "../../widgets/tasks"

// Isolated preview only. No singleton store, persistence, network, or host wiring.
// Run from repository root with the same QML import environment as Quickshell.
Window {
    id: preview
    width: 432
    height: 768
    visible: true
    title: "PLANNER M2 // ISOLATED PREVIEW"
    color: "#1B0623"
    property string openedId: ""
    readonly property var demoSnapshot: ({
        state: "ready",
        items: [
            {id:"t1",title:"Review calendar proportions",done:false,dueDate:"2026-10-23",priority:"high",projectId:"p1"},
            {id:"t2",title:"Verify completed task appearance",done:true,dueDate:"2026-10-23",priority:"low",projectId:"p1"},
            {id:"t3",title:"Long task title to exercise the constrained agenda layout and truncation",done:false,dueDate:"2026-10-23",priority:"urgent"},
            {id:"t4",title:"Check neighboring date indicators",done:false,dueDate:"2026-10-24",priority:"medium"},
            {id:"t5",title:"Unscheduled item",done:false,dueDate:null,priority:"none"}
        ]
    })
    TaskPlannerPane {
        id: planner
        anchors.fill: parent
        anchors.margins: 15
        todoSnapshot: preview.demoSnapshot
        monthKey: "2026-10-01"
        selectedDate: "2026-10-23"
        onOpenTaskRequested: function(taskId) {
            preview.openedId = taskId;
        }
    }
}
