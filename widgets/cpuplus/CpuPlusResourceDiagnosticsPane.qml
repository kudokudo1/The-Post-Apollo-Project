import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticCalibration.js" as Calibration
import "../../components"

// One resource workspace, one existing session owner. No telemetry reader or
// runner is instantiated by changing SYSTEM targets.
Item {
    id: root
    objectName: "cpuplusResourceDiagnosticsPane"
    required property string subject
    readonly property color subjectColor: Colors.resourceColor(subject)
    readonly property var instrumentKinds: Calibration.workshopSubjectKinds(subject)
    property bool informationOpen: false

    Column {
        id: header
        objectName: "cpuplusResourceDiagnosticsHeader"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4
        Row {
            width: parent.width
            spacing: 4
            GohuText {
                width: Math.max(0,parent.width-28)
                height: 24
                verticalAlignment: Text.AlignVCenter
                text: root.subject+" // OBSERVATION"
                color: root.subjectColor
                font.pixelSize: 12
                elide: Text.ElideRight
            }
            InformationButton {
                objectName: "cpuplusResourceDiagnosticsInfo"
                selected: root.informationOpen
                onLeftClicked: root.informationOpen=!root.informationOpen
            }
        }
        GohuText {
            width: parent.width
            visible: root.informationOpen
            text: root.subject==="CPU"
                ? "Read-only host CPU capture, same-user process census and Quickshell threads. Host busy is 0–100% of aggregate capacity; process CPU can exceed 100%. Driver frequency and kernel PSI may be unavailable. Host capture runs alone; the report archive and sequential workflow queue are shared."
                : "No qualified resource-specific instrument."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            spacing: 4
            readonly property int toolSize: Math.max(16,Math.min(36,Math.floor((width*0.57-3*Math.max(0,root.instrumentKinds.length-1))/Math.max(1,root.instrumentKinds.length))))
            GohuText {
                width: Math.max(0,parent.width-(filterHost.visible?filterHost.width+parent.spacing:0))
                height: parent.toolSize
                verticalAlignment: Text.AlignVCenter
                text: diagnostics.workshopOpen ? diagnostics.workshopTargetText : "SHARED REPORTS / WORKFLOWS"
                color: Colors.purple
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            Item {
                id: filterHost
                objectName: "cpuplusResourceFilterHost"
                visible: diagnostics.workshopOpen
                width: visible?root.instrumentKinds.length*parent.toolSize+3*Math.max(0,root.instrumentKinds.length-1):0
                height: visible?parent.toolSize:0
            }
        }
        Rectangle { width: parent.width; height: 1; color: root.subjectColor }
    }
    Flickable {
        id: scroll
        objectName: "cpuplusResourceDiagnosticsScroll"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: footer.top
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height,diagnostics.implicitHeight)
        interactive: contentHeight>height+1
        CpuPlusDiagnosticsPane {
            id: diagnostics
            width: scroll.width
            workshopSubject: root.subject
            workshopViewportHeight: scroll.height
            workshopFilterTarget: filterHost
            footerTarget: footerControls
            onNavigationChanged: scroll.contentY=0
        }
    }
    Column {
        id: footer
        objectName: "cpuplusResourceDiagnosticsFooter"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 3
        Rectangle { width: parent.width; height: 1; color: Colors.cyan }
        Item {
            id: footerControls
            width: parent.width
            height: 53
        }
    }
}
