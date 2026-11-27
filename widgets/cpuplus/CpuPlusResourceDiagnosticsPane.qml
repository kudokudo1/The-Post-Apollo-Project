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
    readonly property bool informationOpen: resourceInfoButton.hovered

    Column {
        id: header
        objectName: "cpuplusResourceDiagnosticsHeader"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4
        Row {
            objectName: "cpuplusResourceMenuRail"
            width: parent.width
            height: 28
            ActionButton {
                objectName: "cpuplusResourceMode-DIAG"
                width: Math.max(0,Math.floor((parent.width-4*(parent.width>=240?5:2))/(parent.width>=240?6:3)))
                height: 28
                label: "DIAG"
                contentPadding: 2
                selected: true
                accentColor: Colors.cyan
                selectedForegroundColor: Colors.magenta
                selectedBorderColor: Colors.magenta
                normalFace: true
                onLeftClicked: diagnostics.selectView("WORK")
            }
        }
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
                id: resourceInfoButton
                objectName: "cpuplusResourceDiagnosticsInfo"
                selected: root.informationOpen
            }
        }
        Rectangle {
            id: resourceDivider
            objectName: "cpuplusResourceDiagnosticsDivider"
            width: parent.width
            height: 1
            color: root.subjectColor
        }
        // Mirror MEMORY DIAG: status on the left, square selectors on
        // the right. The three readout lines and selector height share
        // one size calculation, including when the panel is resized.
        Item {
            id: statusBand
            objectName: "cpuplusResourceStatusBand"
            width: parent.width
            readonly property bool general: root.subject==="SYSTEM"
            readonly property bool stacked: false
            readonly property int lineHeight: general ? 12 : Math.max(7,Math.min(11,
                Math.floor((Math.min(36,Math.floor((width*0.57-3*Math.max(0,root.instrumentKinds.length-1))/Math.max(1,root.instrumentKinds.length)))-2)/3)))
            readonly property int toolSize: 3*lineHeight+2
            readonly property int railColumns: general ? 5 : Math.max(1,root.instrumentKinds.length)
            readonly property int railRows: Math.max(1,Math.ceil(root.instrumentKinds.length/railColumns))
            readonly property int railButtonSize: general
                ? Math.max(1,Math.min(36,Math.floor((width-Math.max(52,Math.min(145,Math.floor(width*0.36)))-16)/5)))
                : toolSize
            readonly property int railHeight: railRows*railButtonSize+3*(railRows-1)
            readonly property real readoutHeight: general ? lineHeight : (railHeight-2)/3
            height: Math.max(statusBlock.height,filterHost.height)
            clip: true
            Column {
                id: statusBlock
                objectName: "cpuplusResourceStatusBlock"
                width: Math.max(0,parent.width-(filterHost.visible&&!statusBand.stacked?filterHost.width+4:0))
                x: 0
                y: statusBand.stacked ? 0 : (parent.height-height)/2
                spacing: 1
                clip: true
                CpuPlusMemoryReadout {
                    width: parent.width
                    height: statusBand.readoutHeight
                    clip: true
                    wrapMode: Text.NoWrap
                    text: CpuPlusDiagnostics.feedback
                    color: CpuPlusDiagnostics.busy || CpuPlusDiagnostics.faulted ? Colors.orange : Colors.cyan
                    font.pixelSize: 11
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 7
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                CpuPlusMemoryReadout {
                    width: parent.width
                    height: statusBand.readoutHeight
                    clip: true
                    wrapMode: Text.NoWrap
                    text: root.subject==="SYSTEM" ? (statusBlock.width<150?"PSI // CPU / SWAP":"PSI // CPU / SWAP CAPTURES") : root.subject==="CPU" ? "PSI // HOST CAPTURE ONLY" : "PSI // NOT MEASURED"
                    color: Colors.yellow
                    font.pixelSize: 10
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 7
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                CpuPlusMemoryReadout {
                    objectName: "cpuplusResourceTargetReadout"
                    width: parent.width
                    height: statusBand.readoutHeight
                    clip: true
                    wrapMode: Text.NoWrap
                    visible: filterHost.visible
                    text: diagnostics.workshopTargetText
                    color: Colors.purple
                    font.pixelSize: 9
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 7
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
            }
            Item {
                id: filterHost
                objectName: "cpuplusResourceFilterHost"
                visible: diagnostics.workshopOpen
                readonly property int selectorColumns: statusBand.railColumns
                readonly property int selectorButtonSize: statusBand.railButtonSize
                width: visible?selectorColumns*selectorButtonSize+3*Math.max(0,selectorColumns-1):0
                height: visible?statusBand.railHeight:0
                x: Math.max(0,parent.width-width)
                y: statusBand.stacked ? statusBlock.height+4 : (parent.height-height)/2
            }
        }
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
            headerTarget: header
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
        Item {
            id: footerControls
            width: parent.width
            height: diagnostics.footerHeight
        }
    }
    Rectangle {
        objectName: "cpuplusResourceDiagnosticsInfoPopup"
        visible: root.informationOpen && root.visible
        z: 401
        x: 0
        y: header.y+resourceDivider.y+resourceDivider.height+3
        width: root.width
        height: Math.min(Math.max(0,root.height-y),resourceHelpText.implicitHeight+12)
        color: Colors.black
        border.color: Colors.yellow
        clip: true
        GohuText {
            id: resourceHelpText
            width: Math.max(0,parent.width-12)
            x: 6
            y: 6
            text: root.subject==="SYSTEM" ? "General diagnostic workshop: all ten instruments, shared reports and workflow sets. Select any combination; calibration and capture budgets still apply. Selecting a resource row does not change this workshop." : root.subject==="CPU"
                ? "Read-only host CPU capture, same-user process census and Quickshell threads. Host busy is 0–100% of aggregate capacity; process CPU can exceed 100%. Driver frequency and kernel PSI may be unavailable. Host capture runs alone; the report archive and sequential workflow queue are shared."
                : root.subject==="GPU" ? "All hardware DRM cards are observed independently, regardless of the selected SYSTEM row. Busy, VRAM and uniquely associated hwmon temp1 depend on driver support. No process attribution, stress test or clock changes. Reports and workflow queue are shared."
                : root.subject==="NETWORK" ? "Read-only RX/TX bytes, packets, errors and drops per visible interface, including virtual and loopback. No aggregate across stacked interfaces, no test traffic, endpoint inspection or latency measurement. Reports and workflow queue are shared."
                : root.subject==="STORAGE" ? "Observe 18 fixed Post-Apollo file metadata targets: size, modification time, replacement and availability. No file contents or directory traversal. Scope is independent of the selected disk row; this does not measure physical disk throughput, writes, transactions or writer identity. DISK I/O is a separate whole-device counter instrument; no partition or virtual-layer aggregation. Reports and workflow queue are shared."
                : "No qualified resource-specific instrument."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }
}
