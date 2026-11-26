import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import "../../components"

// Read-only information overlay. Selection and action authority remain host-owned.
Rectangle {
    id: root
    property var task: null
    property string purpose: ""
    property string scopeText: ""
    property string virtualMemory: "?"
    property bool contextActive: false
    property bool open: false
    // Host coordinates are in the same side-panel parent. Expansion moves the
    // top edge as well as increasing the available vertical space.
    property real compactTop: 0
    property real expandedTop: compactTop
    property real fullTop: expandedTop
    property real maximumHeight: 0 // from fullTop to the usable lower edge
    property int sizeLevel: 0
    y: sizeLevel === 2 ? fullTop : sizeLevel === 1 ? expandedTop : compactTop
    readonly property real availableHeight: Math.max(0, maximumHeight - Math.max(0, y - fullTop))
    readonly property int inset: 7
    readonly property int gap: 6
    readonly property real scopeNeed: Math.max(0, scopeValue.implicitHeight)
    readonly property real argumentsNeed: Math.max(0, argumentsValue.implicitHeight)
    readonly property real scopeMinimum: Math.min(36, scopeNeed)
    readonly property real argumentsMinimum: Math.min(28, argumentsNeed)
    // Only the two variable-length bodies consume flexible space. Titles, purpose
    // and technical fields remain stationary at every supported panel size.
    readonly property real fixedHeight: 2 * inset + header.height + 5 * gap
        + identity.implicitHeight + purposeBlock.implicitHeight
        + technicalBlock.implicitHeight + scopeFrame.chromeHeight + argumentsFrame.chromeHeight
    readonly property real naturalHeight: fixedHeight + scopeNeed + argumentsNeed
    readonly property real minimumReadableHeight: fixedHeight + scopeMinimum + argumentsMinimum
    readonly property real flexibleBudget: Math.max(0, height - fixedHeight)
    readonly property real baseNeed: scopeMinimum + argumentsMinimum
    readonly property real extraNeed: Math.max(0, scopeNeed + argumentsNeed - baseNeed)
    readonly property real baseFraction: baseNeed > 0 ? Math.min(1, flexibleBudget / baseNeed) : 0
    readonly property real extraFraction: extraNeed > 0
        ? Math.min(1, Math.max(0, flexibleBudget - baseNeed) / extraNeed) : 0
    readonly property real scopeAllocation: scopeMinimum * baseFraction
        + (scopeNeed - scopeMinimum) * extraFraction
    readonly property real argumentsAllocation: argumentsMinimum * baseFraction
        + (argumentsNeed - argumentsMinimum) * extraFraction
    readonly property string targetIdentity: task
        ? String(task.pid || 0) + "|" + String(task.startTicks || 0) + "|" + String(task.comm || "")
        : ""

    onTargetIdentityChanged: open = false
    onContextActiveChanged: if (!contextActive) open = false
    onOpenChanged: if (open) {
        if (!contextActive || !task) { open = false; return }
        sizeLevel = 0
        scopeScroll.contentY = 0
        argumentsScroll.contentY = 0
    }

    function resizeBy(delta) {
        sizeLevel = Math.max(0, Math.min(2, sizeLevel + delta))
    }
    // Like the CAP readout, semantic text is colored, punctuation and unit
    // suffixes are white. Escape even process-supplied metadata before markup.
    function semanticText(value, ink) {
        const tokens = String(value).match(/(?:[A-Za-z0-9]+|\s+|[^A-Za-z0-9\s]+)/g) || []
        return tokens.map(function(token) {
            const neutral = /^(?:B|KiB|MiB|GiB|TiB|KB|MB|GB|TB|Hz|kHz|MHz|GHz|ms|s|ns|us|kB)$/.test(token)
                || /^[^A-Za-z0-9\s]+$/.test(token)
            const safe = token.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;")
            return '<font color="' + (neutral ? Colors.white : ink) + '">' + safe + '</font>'
        }).join("")
    }

    function helpInk(word) {
        switch (String(word).toUpperCase()) {
        case "CPU": return Colors.orange
        case "MEM": case "MEMORY": return Colors.magenta
        case "I/O": case "FREEZE": case "THAW": case "RESUME": return Colors.cyan
        case "LIMIT": case "RESTART": case "RESET": return Colors.yellow
        case "KILL": case "END": case "TERMINATE": case "TERM": return Colors.red
        default: return Colors.white
        }
    }
    function helpText(value) {
        const tokens = String(value).match(/I\/O|[A-Za-z]+|[^A-Za-z]+/gi) || []
        return tokens.map(function(token) {
            const safe = token.replace(/&/g,"&amp;").replace(/</g,"&lt;")
                .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")
                .replace(/\n/g,"<br/>")
            return '<font color="' + helpInk(token) + '">' + safe + '</font>'
        }).join("")
    }

    visible: contextActive && open && !!task && height > 0
    // Compact fits its content when possible; upper/full are actual viewport
    // escalations, not merely larger caps on the same natural document height.
    height: Math.max(0, Math.min(availableHeight,
        sizeLevel === 2 ? availableHeight
        : sizeLevel === 1 ? Math.max(minimumReadableHeight, availableHeight * 0.78)
        : Math.max(minimumReadableHeight, Math.min(naturalHeight, availableHeight * 0.55))))
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true
    z: 400

    MouseArea {
        anchors.fill: parent
        onWheel: function(wheel) { wheel.accepted = true }
    }
    Column {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: root.inset
        spacing: root.gap
        Row {
            id: header
            width: parent.width
            height: 26
            spacing: 4
            GohuText {
                width: Math.max(0, parent.width - shrink.width - grow.width - close.width - 3 * parent.spacing)
                height: parent.height
                text: root.semanticText("PROCESS // INFORMATION", Colors.cyan)
                textFormat: Text.RichText
                color: Colors.cyan
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            ResizeButton {
                id: shrink
                objectName: "processInformationShrink"
                width: 26
                direction: "down"
                available: root.sizeLevel > 0
                onResizeRequested: delta => root.resizeBy(delta)
            }
            ResizeButton {
                id: grow
                objectName: "processInformationGrow"
                width: 26
                direction: "up"
                available: root.sizeLevel < 2
                onResizeRequested: delta => root.resizeBy(delta)
            }
            CloseButton {
                id: close
                objectName: "processInformationClose"
                width: 26
                height: 26
                onCloseRequested: root.open = false
            }
        }
        Column {
            id: identity
            width: parent.width
            spacing: 3
            GohuText {
                width: parent.width
                text: root.task ? root.semanticText(String(root.task.comm || "PROCESS")
                    + " // PID " + String(root.task.pid || "?")
                    + " • " + String(root.task.user || "?")
                    + " • " + String(root.task.state || "?"), Colors.orange) : ""
                textFormat: Text.RichText
                color: Colors.orange
                font.pixelSize: 13
                wrapMode: Text.WrapAnywhere
            }
            GohuText {
                objectName: "processInformationBirthIdentity"
                width: parent.width
                text: root.task ? "START TICKS " + String(root.task.startTicks || "?") + " • PID + START TICKS + NAME identify the exact live process. State is the Linux process status (e.g. S sleeping, R running, L locked pages, l multithreaded)." : ""
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
        }
        Column {
            id: purposeBlock
            width: parent.width
            spacing: 3
            GohuText {
                width: parent.width
                text: "PROCESS PURPOSE"
                color: Colors.orange
                font.pixelSize: 12
            }
            GohuText {
                id: purposeText
                objectName: "processInformationPurpose"
                width: parent.width
                text: root.helpText(root.purpose || "NO DESCRIPTION AVAILABLE")
                textFormat: Text.RichText
                wrapMode: Text.Wrap
                color: Colors.white
                font.pixelSize: 12
                GaussianBlur { anchors.fill: parent; source: purposeText; radius: 4; samples: 9; opacity: 0.55; z: -1 }
            }
        }
        Rectangle {
            id: scopeFrame
            objectName: "processInformationScope"
            width: parent.width
            readonly property real chromeHeight: scopeTitle.implicitHeight + 15
            height: chromeHeight + root.scopeAllocation
            color: Colors.black
            border.color: Colors.cyan
            clip: true
            GohuText {
                id: scopeTitle
                x: 7
                y: 5
                width: Math.max(0, parent.width - 14)
                text: root.helpText("PROCESS SCOPE // LIMIT = THIS PROCESS")
                textFormat: Text.RichText
                wrapMode: Text.Wrap
                color: Colors.cyan
                font.pixelSize: 11
            }
            Flickable {
                id: scopeScroll
                objectName: "processInformationScopeScroll"
                anchors.top: scopeTitle.bottom
                anchors.topMargin: 3
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 7
                anchors.left: parent.left
                anchors.leftMargin: 7
                anchors.right: parent.right
                anchors.rightMargin: 19
                contentWidth: width
                contentHeight: scopeValue.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick
                interactive: contentHeight > height
                onHeightChanged: contentY = Math.max(0, Math.min(contentY, contentHeight - height))
                onContentHeightChanged: contentY = Math.max(0, Math.min(contentY, contentHeight - height))
                GohuText {
                    id: scopeValue
                    width: scopeScroll.width
                    text: root.helpText(root.scopeText || "NO LIVE PROCESS SCOPE FOUND")
                    textFormat: Text.RichText
                    wrapMode: Text.WrapAnywhere
                    color: Colors.white
                    font.pixelSize: 11
                    GaussianBlur { anchors.fill: parent; source: scopeValue; radius: 4; samples: 9; opacity: 0.55; z: -1 }
                }
            }
            NeonScrollBar {
                objectName: "processInformationScopeRail"
                flickable: scopeScroll
                geometryMode: "box"
                geometryHost: scopeFrame
                visible: scrollable
                railColor: Colors.cyan
                handleColor: Colors.magenta
                wheelEnabled: false
            }
        }
        Column {
            id: technicalBlock
            width: parent.width
            spacing: 3
            GohuText {
                width: parent.width
                text: "TECHNICAL INFORMATION"
                color: Colors.magenta
                font.pixelSize: 12
            }
            Repeater {
                model: [
                    ["USER", root.task ? String(root.task.user || "?") : "?", Colors.cyan],
                    ["PPID", root.task ? String(root.task.ppid || "?") : "?", Colors.orange],
                    ["VIRT", root.virtualMemory, Colors.magenta],
                    ["STATE", root.task ? String(root.task.state || "?") : "?", Colors.cyan]
                ]
                delegate: RowLayout {
                    required property var modelData
                    width: technicalBlock.width
                    spacing: 8
                    GohuText {
                        Layout.preferredWidth: 64
                        text: modelData[0]
                        color: modelData[2]
                        font.pixelSize: 11
                    }
                    GohuText {
                        Layout.fillWidth: true
                        text: root.semanticText(modelData[1], modelData[2])
                        textFormat: Text.RichText
                        wrapMode: Text.WrapAnywhere
                        color: modelData[2]
                        font.pixelSize: 11
                    }
                }
            }
        }
        Rectangle {
            id: argumentsFrame
            objectName: "processInformationCommandFrame"
            width: parent.width
            readonly property real chromeHeight: argumentsTitle.implicitHeight + 15
            height: chromeHeight + root.argumentsAllocation
            color: Colors.black
            border.color: Colors.magenta
            clip: true
            GohuText {
                id: argumentsTitle
                x: 7
                y: 5
                width: Math.max(0, parent.width - 14)
                text: "COMMAND LINE"
                color: Colors.magenta
                font.pixelSize: 11
            }
            Flickable {
                id: argumentsScroll
                objectName: "processInformationArgumentsScroll"
                anchors.top: argumentsTitle.bottom
                anchors.topMargin: 3
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 7
                anchors.left: parent.left
                anchors.leftMargin: 7
                anchors.right: parent.right
                anchors.rightMargin: 19
                contentWidth: width
                contentHeight: argumentsValue.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick
                interactive: contentHeight > height
                onHeightChanged: contentY = Math.max(0, Math.min(contentY, contentHeight - height))
                onContentHeightChanged: contentY = Math.max(0, Math.min(contentY, contentHeight - height))
                GohuText {
                    id: argumentsValue
                    objectName: "processInformationArguments"
                    width: argumentsScroll.width
                    text: root.task ? String(root.task.args || "") : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: 10
                    color: Colors.white
                }
            }
            NeonScrollBar {
                objectName: "processInformationArgumentsRail"
                flickable: argumentsScroll
                geometryMode: "box"
                geometryHost: argumentsFrame
                visible: scrollable
                railColor: Colors.magenta
                handleColor: Colors.magenta
                wheelEnabled: false
            }
        }
    }
}
