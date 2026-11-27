import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
            Column {
                id: taskManagerBody

    required property var host
    required property var presentationState
    // During the transitional two-view period, never label another process's
    // selected-detail history with this view's current identity.
    property bool graphDataAvailable: true
    required property var processController
    required property var graphGeometry
    required property var hunterGraph
    required property var searchInputTarget
    required property Component safetyLockComponent

    // Hosts choose placement; the shared action column owns visual order.
    property Item actionTarget: null
    property Item quickActionTarget: null
    property Item lockTarget: null
    property Item killActionTarget: null
    property Item freezeActionTarget: null
    property Item killLockTarget: null
    property Item restartLockTarget: null
    property Item freezeLockTarget: null
    readonly property bool headerActions: quickActionTarget !== null
    property bool metricGraphSelectionEnabled: false
    property var selectedGraphKeys: ["cpu", "mem"]
    signal metricGraphRequested(string key)
    function graphSelected(key) { return selectedGraphKeys.indexOf(key) >= 0; }
    property real viewportHeight: 0
    readonly property bool compact: viewportHeight > 0
    readonly property int graphCount: metricGraphSelectionEnabled ? selectedGraphKeys.length : taskCpuGraph.hunterMetricView && !taskCpuGraph.combiView ? 1 : 2
    readonly property real graphHeight: metricGraphSelectionEnabled
        ? Math.max(0, Math.min(180, Math.floor((viewportHeight - taskMetricGrid.implicitHeight
            - spacing * (graphCount + 1) - 4) / Math.max(1,graphCount))))
        : compact
        ? Math.max(48, Math.min(112, Math.floor((viewportHeight - taskMetricGrid.implicitHeight
            - (actionTarget ? 0 : actionColumn.implicitHeight + spacing)
            - spacing * graphCount - 12) / graphCount)))
        : 112
    property alias actionSection: actionColumn

    property alias cpuCanvas: taskCpuCanvas
    property alias combiScoreCanvas: taskCombiScoreCanvas
    property alias memCanvas: taskMemCanvas
    property alias restartAction: taskRestartAction
    property alias limitSlider: taskLimitSlider
    property alias freezeAction: taskFreezeAction
    property alias endAction: taskEndAction

                // Leave a real halo gutter around TASK MANAGER cards/graphs.
                // Their shadows used to meet the Flickable/content bounds and
                // were visibly hard-clipped on the top/left/right edges.
                width: parent.width - 16
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: compact ? 6 : 12

                visible: processController.currentTask !== null

                property var currentTask:
                    processController.currentTask

                GridLayout {
                    id: taskMetricGrid

                    width: parent.width
                    columns: taskManagerBody.metricGraphSelectionEnabled ? 4 : 3
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: {
                            const task = taskManagerBody.currentTask;
                            if (!task) return [];

                            const metrics = [
                                { id: "cpu", label: "CPU", value: Number(task.cpu || 0).toFixed(1) + "%", baseAccent: Colors.resourceColor("cpu"), critical: processController.metricIsCritical(task, "cpu") },
                                { id: "mem", label: "MEM", value: Number(task.mem || 0).toFixed(1) + "%", baseAccent: Colors.resourceColor("mem"), critical: processController.metricIsCritical(task, "mem") },
                                { id: "rss", label: "RSS", value: processController.formatMemory(task.rss), baseAccent: Colors.resourceColor("rss"), critical: processController.metricIsCritical(task, "rss") },
                                { id: "threads", label: "THREADS", value: String(task.threads || 0), baseAccent: Colors.resourceColor("threads"), critical: processController.metricIsCritical(task, "threads") },
                                { id: "pid", label: "PID", value: String(task.pid || "?"), baseAccent: Colors.resourceColor("pid"), critical: false },
                                { id: "uptime", label: "UPTIME", value: String(task.elapsed || "?"), baseAccent: Colors.resourceColor("uptime"), critical: false }
                            ];
                            if (taskManagerBody.metricGraphSelectionEnabled) {
                                const extra = presentationState.taskExtraDetailHistories || {};
                                const swap = extra.swap || [];
                                metrics[4] = {id:"swap",label:"SWAP",value:swap.length && taskManagerBody.graphDataAvailable
                                    ? Number(swap[swap.length-1]).toFixed(1)+" MiB" : "N/A",
                                    baseAccent:Colors.resourceColor("swap"),critical:false,noFavorite:true};
                                const io = extra.io || [];
                                metrics.push({id:"io",label:"I/O",value:io.length && taskManagerBody.graphDataAvailable
                                    ? Number(io[io.length-1]).toFixed(2)+" MiB/s" : "N/A",
                                    baseAccent:Colors.cyan,critical:false,noFavorite:true});
                                metrics.push({id:"combined",label:"COMBI",value:"HISTORY",
                                    baseAccent:Colors.yellow,critical:false,noFavorite:true});
                            }
                            return metrics;
                        }

                        Rectangle {
                            id: taskMetricCard
                            required property var modelData

                            readonly property color accent:
                                modelData.critical ? Colors.red : modelData.baseAccent
                            readonly property color glowColor:
                                accent === Colors.white ? Colors.cyan : accent
                            objectName: "taskMetricCard-"+modelData.id
                            readonly property string graphKey: modelData.id === "uptime" ? "age" : modelData.id
                            readonly property bool graphSelectable: taskManagerBody.metricGraphSelectionEnabled && modelData.id !== "pid"
                            readonly property bool graphSelected: graphSelectable && taskManagerBody.graphSelected(graphKey)
                            readonly property bool favorite:
                                host.isTaskMetricFavorite(
                                    taskManagerBody.currentTask,
                                    modelData.id
                                )

                            Layout.fillWidth: true
                            Layout.preferredHeight: taskManagerBody.compact ? 44 : 58
                            color: graphSelectable && (graphSelected || metricGraphMouse.containsMouse)
                                ? Qt.tint(Colors.black,Qt.rgba(modelData.baseAccent.r,modelData.baseAccent.g,modelData.baseAccent.b,
                                    graphSelected ? 0.24 : 0.13)) : Colors.black
                            border.width: 1
                            border.color: accent

                            RectangularShadow {
                                anchors.fill: parent
                                anchors.margins: -4
                                spread: 3
                                z: -1
                                opacity: taskMetricCard.graphSelected ? 0.58 : modelData.critical ? 0.58 : 0.28
                                color: taskMetricCard.glowColor
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: taskManagerBody.compact ? 4 : 7
                                spacing: taskManagerBody.compact ? 1 : 3

                                GohuText {
                                    text: modelData.label
                                    font.pixelSize: 10
                                    color: taskMetricCard.accent
                                    opacity: 0.90
                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: modelData.critical ? 9 : 5
                                        samples: 7
                                        opacity: modelData.critical ? 0.76 : 0.30
                                        color: taskMetricCard.glowColor
                                        transparentBorder: true
                                    }
                                }

                                GohuText {
                                    width: parent.width - 16
                                    text: modelData.value
                                    font.pixelSize: taskManagerBody.metricGraphSelectionEnabled ? 13 : 16
                                    color: taskMetricCard.accent
                                    elide: Text.ElideRight
                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: modelData.critical ? 10 : 5
                                        samples: 9
                                        opacity: modelData.critical ? 0.90 : 0.38
                                        color: taskMetricCard.glowColor
                                        transparentBorder: true
                                    }
                                }
                            }

                            MouseArea {
                                id: metricGraphMouse
                                objectName: "taskMetricToggle-"+modelData.id
                                anchors.fill: parent
                                enabled: taskMetricCard.graphSelectable
                                hoverEnabled: enabled
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                acceptedButtons: Qt.LeftButton
                                onClicked: taskManagerBody.metricGraphRequested(taskMetricCard.graphKey)
                            }
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 2
                                height: 2
                                visible: taskMetricCard.graphSelectable
                                color: taskMetricCard.modelData.baseAccent
                                opacity: taskMetricCard.graphSelected ? 1 : 0.22
                            }
                            Item {
                                visible: !modelData.noFavorite
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 2
                                anchors.topMargin: 2
                                width: 20
                                height: 20
                                z: 30

                                GohuText {
                                    anchors.centerIn: parent
                                    text: taskMetricCard.favorite ? "✦" : "✧"
                                    font.pixelSize: 13
                                    color: taskMetricCard.favorite ? taskMetricCard.accent : Colors.white
                                    opacity: taskMetricCard.favorite ? 1.0 : 0.48
                                    layer.enabled: taskMetricCard.favorite
                                    layer.effect: DropShadow {
                                        radius: 5
                                        samples: 5
                                        opacity: 0.46
                                        color: taskMetricCard.glowColor
                                        transparentBorder: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        host.toggleTaskMetricFavorite(
                                            taskManagerBody.currentTask,
                                            modelData.id
                                        );
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: taskCpuGraph
                    visible: !taskManagerBody.metricGraphSelectionEnabled
                        || taskManagerBody.graphSelected("cpu") || taskManagerBody.graphSelected("combined")

                    width: parent.width
                    height: taskManagerBody.graphHeight

                    readonly property bool hunterMetricView:
                        taskManagerBody.metricGraphSelectionEnabled ? taskManagerBody.graphSelected("combined") : host.hunterMetricView
                    readonly property bool combiView:
                        hunterMetricView
                        && hunterGraph.metricMode
                           === hunterGraph.metricCombined
                    readonly property color accent:
                        hunterMetricView
                        ? hunterGraph.metricAccent()
                        : Colors.orange
                    readonly property var historyValues: {
                        const miniRevision = presentationState.taskMiniHistoryRevision;
                        const detailRevision =
                            presentationState.taskHunterDetailHistoryRevision;
                        if (!taskManagerBody.graphDataAvailable || (taskManagerBody.metricGraphSelectionEnabled && !taskCpuGraph.visible)) return [];
                        if (hunterMetricView)
                            return hunterGraph.detailHistory();
                        return presentationState.taskCpuHistory;
                    }
                    readonly property real graphRange:
                        hunterMetricView
                        ? hunterGraph.metricGraphRange()
                        : 5.0

                    GohuText {
                        id: taskCpuGraphTitle
                        anchors.left: parent.left
                        anchors.top: parent.top
                        visible: !taskCpuGraph.combiView

                        text:
                            taskCpuGraph.hunterMetricView
                            ? "HUNTER "
                              + hunterGraph.metricGraphLabel()
                              + " HISTORY  "
                              + hunterGraph.metricGraphValue(
                                    taskManagerBody.currentTask
                                )
                            : "CPU HISTORY  "
                              + (taskManagerBody.currentTask
                                 ? Number(taskManagerBody.currentTask.cpu).toFixed(1)
                                 : "0.0")
                              + "%"

                        font.pixelSize: 12
                        color: taskCpuGraph.accent

                        layer.enabled: true
                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 5
                            samples: 5
                            opacity: 0.34
                            color: taskCpuGraph.accent
                            transparentBorder: true
                        }
                    }

                    Row {
                        id: taskCombiOverlayTitle
                        anchors.left: parent.left
                        anchors.top: parent.top
                        visible: taskCpuGraph.combiView
                        spacing: 0

                        GohuText {
                            text: "HUNTER " + hunterGraph.combiIcon + " HISTORY  •  "
                            font.pixelSize: 12
                            color: Colors.yellow
                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 5
                                samples: 5
                                opacity: 0.34
                                color: Colors.yellow
                                transparentBorder: true
                            }
                        }
                        GohuText {
                            text: "CPU"
                            font.pixelSize: 12
                            color: Colors.orange
                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4; samples: 5; opacity: 0.40
                                color: Colors.orange; transparentBorder: true
                            }
                        }
                        GohuText {
                            text: " / "
                            font.pixelSize: 12
                            color: Colors.white
                            opacity: 0.62
                        }
                        GohuText {
                            text: "MEM"
                            font.pixelSize: 12
                            color: Colors.magenta
                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4; samples: 5; opacity: 0.40
                                color: Colors.magenta; transparentBorder: true
                            }
                        }
                        GohuText {
                            text: " / "
                            font.pixelSize: 12
                            color: Colors.white
                            opacity: 0.62
                        }
                        GohuText {
                            text: "I/O"
                            font.pixelSize: 12
                            color: Colors.cyan
                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4; samples: 5; opacity: 0.40
                                color: Colors.cyan; transparentBorder: true
                            }
                        }
                        GohuText {
                            text: " / "
                            font.pixelSize: 12
                            color: Colors.white
                            opacity: 0.62
                        }
                        GohuText {
                            text: "AGE"
                            font.pixelSize: 12
                            color: Colors.white
                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4; samples: 5; opacity: 0.30
                                color: Colors.white; transparentBorder: true
                            }
                        }
                    }

                    Rectangle {
                        id: taskCpuGraphFrame

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top:
                            taskCpuGraph.combiView
                            ? taskCombiOverlayTitle.bottom
                            : taskCpuGraphTitle.bottom
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 5

                        color: Colors.black
                        border.width: 1
                        border.color: taskCpuGraph.accent

                        RectangularShadow {
                            anchors.fill: parent
                            anchors.margins: -4
                            spread: 3
                            z: -1
                            opacity: 0.30
                            color: taskCpuGraph.accent
                        }
                    }

                    Item {
                        id: taskCpuCanvas

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.fill: taskCpuGraphFrame
                        anchors.margins: 4
                        z: 2
                        clip: true

                        // Kept as a method because appendTaskHistoryValues() calls
                        // requestPaint(). Incrementing this revision simply forces the
                        // point binding to be reevaluated; rendering itself is QML.
                        property int graphRevision: 0
                        property real graphScrollOffset: 0
                        property int graphScrollPid: 0

                        NumberAnimation {
                            id: taskCpuGraphScrollAnimation
                            target: taskCpuCanvas
                            property: "graphScrollOffset"
                            to: 0
                            duration: presentationState.taskGraphScrollDuration
                            easing.type: Easing.Linear
                        }

                        function startGraphScroll() {
                            const pid = Number(presentationState.taskHistoryPid || 0);
                            const sameTask = pid > 0 && graphScrollPid === pid;

                            if (!sameTask) {
                                resetGraphScroll();
                                graphScrollPid = pid;
                                return;
                            }

                            taskCpuGraphScrollAnimation.stop();
                            graphScrollOffset =
                                width
                                / Math.max(
                                    1,
                                    presentationState.taskHistoryLimit - 1
                                );
                            taskCpuGraphScrollAnimation.restart();
                        }

                        function resetGraphScroll() {
                            taskCpuGraphScrollAnimation.stop();
                            graphScrollOffset = 0;
                        }

                        function requestPaint(animateScroll, resetScroll) {
                            const pid = Number(presentationState.taskHistoryPid || 0);
                            graphRevision += 1;

                            if (resetScroll === true)
                                resetGraphScroll();
                            else if (animateScroll === true)
                                startGraphScroll();

                            graphScrollPid = pid;
                        }

                        readonly property var graphPoints: {
                            const revision = graphRevision;
                            if (taskCpuGraph.combiView)
                                return [];
                            return graphGeometry.linePoints(
                                taskCpuGraph.historyValues,
                                width,
                                height,
                                taskCpuGraph.graphRange,
                                presentationState.taskHistoryLimit,
                                2,
                                2
                            );
                        }
                        readonly property var combiSeries: [
                            { metric: "cpu", label: "CPU", accent: Colors.orange },
                            { metric: "mem", label: "MEM", accent: Colors.magenta },
                            { metric: "io", label: "I/O", accent: Colors.cyan },
                            { metric: "age", label: "AGE", accent: Colors.white }
                        ]

                        // Match MEMORY HISTORY: three horizontal reference lines
                        // behind CPU, every HUNTER metric, and the COMBI overlay.
                        Repeater {
                            model: 3
                            delegate: Rectangle {
                                x: 0
                                y: taskCpuCanvas.height * (index + 1) / 4
                                width: taskCpuCanvas.width
                                height: 1
                                color: taskCpuGraph.accent
                                opacity: 0.16
                                z: 0
                            }
                        }

                        Repeater {
                            model:
                                taskCpuGraph.combiView
                                ? taskCpuCanvas.combiSeries : []

                            delegate: Item {
                                id: detailCombiTrace
                                required property var modelData
                                required property int index
                                anchors.fill: parent
                                z: 5

                                readonly property var metricHistory: {
                                    const revision =
                                        presentationState.taskHunterDetailHistoryRevision;
                                    if (!taskManagerBody.graphDataAvailable) return [];
                                    const metrics = ["cpu", "mem", "io", "age"];
                                    const histories = [];
                                    let commonLength = Number.MAX_SAFE_INTEGER;

                                    for (let i = 0; i < metrics.length; i++) {
                                        const values =
                                            presentationState.taskHunterDetailHistories[
                                                metrics[i]
                                            ];
                                        const history = Array.isArray(values)
                                                        ? values : [];
                                        histories.push(history);
                                        commonLength = Math.min(
                                            commonLength,
                                            history.length
                                        );
                                    }

                                    if (!Number.isFinite(commonLength)
                                            || commonLength <= 0)
                                        return [];

                                    const ownIndex = metrics.indexOf(modelData.metric);
                                    const own = ownIndex >= 0
                                                ? histories[ownIndex] : [];
                                    return own.slice(
                                        Math.max(0, own.length - commonLength)
                                    );
                                }
                                readonly property var metricDisplayHistory:
                                    graphGeometry.downsampleHistory(
                                        metricHistory,
                                        presentationState.taskCombiRenderPointLimit
                                    )
                                readonly property var metricPoints:
                                    graphGeometry.linePoints(
                                        metricDisplayHistory,
                                        width,
                                        height,
                                        hunterGraph.metricRangeForKey(
                                            modelData.metric
                                        ),
                                        presentationState.taskCombiRenderPointLimit,
                                        2,
                                        2
                                    )

                                // Compact legend: the traces themselves now occupy the
                                // exact same graph area rather than separate bands.
                                GohuText {
                                    x: 4 + index * 42
                                    y: 2
                                    width: 38
                                    horizontalAlignment: Text.AlignHCenter
                                    text: detailCombiTrace.modelData.label
                                    font.pixelSize: 7
                                    color: detailCombiTrace.modelData.accent
                                    opacity: 0.78
                                    z: 9
                                }

                                // Four metric tracks retain their independent colors.
                                // A single scene-graph translation per track moves
                                // all fills and strokes while the legend stays fixed.
                                Item {
                                    id: detailCombiTraceLayer
                                    anchors.fill: parent
                                    transform: Translate {
                                        x: taskCpuCanvas.graphScrollOffset
                                    }
                                    // Preserve the filled-graph look for COMBI too. Low
                                    // opacity keeps four overlapping fills readable.
                                    Repeater {
                                        model: detailCombiTrace.metricPoints.length

                                        delegate: Rectangle {
                                            readonly property point graphPoint:
                                                detailCombiTrace.metricPoints[index]
                                            x: graphPoint.x - width / 2
                                            y: graphPoint.y
                                            width: Math.max(
                                                2.0,
                                                detailCombiTrace.width
                                                / Math.max(
                                                    2,
                                                    presentationState.taskCombiRenderPointLimit - 1
                                                )
                                                + 1.0
                                            )
                                            height: Math.max(
                                                0,
                                                detailCombiTrace.height - graphPoint.y - 1
                                            )
                                            color: detailCombiTrace.modelData.accent
                                            opacity: 0.060
                                            antialiasing: true
                                            z: 1
                                        }
                                    }

                                    Repeater {
                                        model: Math.max(
                                            0,
                                            detailCombiTrace.metricPoints.length - 1
                                        )

                                        delegate: Item {
                                            anchors.fill: parent
                                            z: 4
                                            readonly property point p1:
                                                detailCombiTrace.metricPoints[index]
                                            readonly property point p2:
                                                detailCombiTrace.metricPoints[index + 1]
                                            readonly property real dx: p2.x - p1.x
                                            readonly property real dy: p2.y - p1.y
                                            readonly property real segmentLength:
                                                Math.sqrt(dx * dx + dy * dy)
                                            readonly property real segmentAngle:
                                                Math.atan2(dy, dx) * 180 / Math.PI

                                            Rectangle {
                                                x: parent.p1.x
                                                y: parent.p1.y - height / 2
                                                width: parent.segmentLength
                                                height: 6
                                                radius: 3
                                                rotation: parent.segmentAngle
                                                transformOrigin: Item.Left
                                                color: detailCombiTrace.modelData.accent
                                                opacity: 0.18
                                                antialiasing: true
                                            }

                                            Rectangle {
                                                x: parent.p1.x
                                                y: parent.p1.y - height / 2
                                                width: parent.segmentLength
                                                height: 2
                                                radius: 1
                                                rotation: parent.segmentAngle
                                                transformOrigin: Item.Left
                                                color: detailCombiTrace.modelData.accent
                                                opacity: 1.0
                                                antialiasing: true
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Preserve the fixed grid and COMBI legend. Translate
                        // normal CPU/HUNTER detail fill and stroke as one trace.
                        Item {
                            id: taskCpuNormalTraceLayer
                            anchors.fill: parent
                            transform: Translate {
                                x: taskCpuCanvas.graphScrollOffset
                            }
                            // Stable translucent area under the trace. Each point
                            // contributes a narrow vertical strip down to the graph floor;
                            // this recreates the old filled-graph look without Canvas.
                            Repeater {
                                model: taskCpuCanvas.graphPoints.length

                                delegate: Rectangle {
                                    readonly property point graphPoint:
                                        taskCpuCanvas.graphPoints[index]
                                    x: graphPoint.x - width / 2
                                    y: graphPoint.y
                                    width: Math.max(
                                        2.0,
                                        taskCpuCanvas.width
                                        / Math.max(
                                            2,
                                            presentationState.taskHistoryLimit - 1
                                        )
                                        + 1.4
                                    )
                                    height: Math.max(0, taskCpuCanvas.height - graphPoint.y - 1)
                                    color: taskCpuGraph.accent
                                    opacity: 0.10
                                    antialiasing: true
                                }
                            }

                            Repeater {
                                model: Math.max(0, taskCpuCanvas.graphPoints.length - 1)

                                delegate: Item {
                                    anchors.fill: parent

                                    readonly property point p1:
                                        taskCpuCanvas.graphPoints[index]
                                    readonly property point p2:
                                        taskCpuCanvas.graphPoints[index + 1]
                                    readonly property real dx: p2.x - p1.x
                                    readonly property real dy: p2.y - p1.y
                                    readonly property real segmentLength:
                                        Math.sqrt(dx * dx + dy * dy)
                                    readonly property real segmentAngle:
                                        Math.atan2(dy, dx) * 180 / Math.PI

                                    // Soft under-trace. This replaces the old Canvas
                                    // shadow/fill without depending on retained paint state.
                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 7
                                        radius: 3.5
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: taskCpuGraph.accent
                                        opacity: 0.20
                                        antialiasing: true
                                    }

                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 2
                                        radius: 1
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: taskCpuGraph.accent
                                        opacity: 1.0
                                        antialiasing: true
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: taskCombiScoreGraph

                    visible: taskCpuGraph.combiView
                        && (!taskManagerBody.metricGraphSelectionEnabled || taskManagerBody.graphSelected("score"))
                    width: parent.width
                    height: visible ? taskManagerBody.graphHeight : 0

                    readonly property color accent: Colors.yellow
                    readonly property var historyValues: {
                        const revision =
                            presentationState.taskHunterDetailHistoryRevision;
                        if (!taskManagerBody.graphDataAvailable) return [];
                        const values =
                            presentationState.taskHunterDetailHistories.combined;
                        return Array.isArray(values) ? values : [];
                    }
                    readonly property var displayHistory:
                        graphGeometry.downsampleHistory(
                            historyValues,
                            presentationState.taskCombiRenderPointLimit
                        )

                    GohuText {
                        id: taskCombiScoreGraphTitle
                        anchors.left: parent.left
                        anchors.top: parent.top

                        text:
                            hunterGraph.combiIcon
                            + "  COMBINED SCORE HISTORY  "
                            + hunterGraph.metricGraphValue(
                                  taskManagerBody.currentTask
                              )

                        font.pixelSize: 12
                        color: taskCombiScoreGraph.accent

                        layer.enabled: true
                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 5
                            samples: 5
                            opacity: 0.40
                            color: taskCombiScoreGraph.accent
                            transparentBorder: true
                        }
                    }

                    Rectangle {
                        id: taskCombiScoreGraphFrame
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: taskCombiScoreGraphTitle.bottom
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 5

                        color: Colors.black
                        border.width: 1
                        border.color: taskCombiScoreGraph.accent

                        RectangularShadow {
                            anchors.fill: parent
                            anchors.margins: -4
                            spread: 3
                            z: -1
                            opacity: 0.28
                            color: taskCombiScoreGraph.accent
                        }
                    }

                    Item {
                        id: taskCombiScoreCanvas
                        anchors.fill: taskCombiScoreGraphFrame
                        anchors.margins: 4
                        z: 2
                        clip: true

                        property real graphScrollOffset: 0
                        property int graphScrollPid: 0

                        NumberAnimation {
                            id: taskCombiScoreScrollAnimation
                            target: taskCombiScoreCanvas
                            property: "graphScrollOffset"
                            to: 0
                            duration: presentationState.taskGraphScrollDuration
                            easing.type: Easing.Linear
                        }

                        function startGraphScroll() {
                            const pid = Number(presentationState.taskHistoryPid || 0);
                            const sameTask = pid > 0 && graphScrollPid === pid;

                            if (!sameTask) {
                                resetGraphScroll();
                                graphScrollPid = pid;
                                return;
                            }

                            taskCombiScoreScrollAnimation.stop();
                            graphScrollOffset =
                                width
                                / Math.max(
                                    1,
                                    presentationState.taskCombiRenderPointLimit - 1
                                );
                            taskCombiScoreScrollAnimation.restart();
                        }

                        function resetGraphScroll() {
                            taskCombiScoreScrollAnimation.stop();
                            graphScrollOffset = 0;
                        }

                        function requestPaint(animateScroll, resetScroll) {
                            const pid = Number(presentationState.taskHistoryPid || 0);

                            if (resetScroll === true)
                                resetGraphScroll();
                            else if (animateScroll === true)
                                startGraphScroll();

                            graphScrollPid = pid;
                        }

                        readonly property var graphPoints: {
                            const revision =
                                presentationState.taskHunterDetailHistoryRevision;
                            return graphGeometry.linePoints(
                                taskCombiScoreGraph.displayHistory,
                                width,
                                height,
                                5.0,
                                presentationState.taskCombiRenderPointLimit,
                                2,
                                2
                            );
                        }

                        Repeater {
                            model: 3
                            delegate: Rectangle {
                                x: 0
                                y: taskCombiScoreCanvas.height * (index + 1) / 4
                                width: taskCombiScoreCanvas.width
                                height: 1
                                color: taskCombiScoreGraph.accent
                                opacity: 0.16
                                z: 0
                            }
                        }

                        // Animate one trace layer, not every fill/line rectangle.
                        // Reference grid stays fixed in the clipped canvas.
                        Item {
                            id: taskCombiScoreTraceLayer
                            anchors.fill: parent
                            transform: Translate {
                                x: taskCombiScoreCanvas.graphScrollOffset
                            }
                            // Filled space under the restored combined-score trace.
                            Repeater {
                                model: taskCombiScoreCanvas.graphPoints.length

                                delegate: Rectangle {
                                    readonly property point graphPoint:
                                        taskCombiScoreCanvas.graphPoints[index]
                                    x: graphPoint.x - width / 2
                                    y: graphPoint.y
                                    width: Math.max(
                                        2.0,
                                        taskCombiScoreCanvas.width
                                        / Math.max(
                                            2,
                                            presentationState.taskCombiRenderPointLimit - 1
                                        )
                                        + 1.4
                                    )
                                    height: Math.max(
                                        0,
                                        taskCombiScoreCanvas.height - graphPoint.y - 1
                                    )
                                    color: taskCombiScoreGraph.accent
                                    opacity: 0.10
                                    antialiasing: true
                                }
                            }

                            Repeater {
                                model: Math.max(
                                    0,
                                    taskCombiScoreCanvas.graphPoints.length - 1
                                )

                                delegate: Item {
                                    anchors.fill: parent

                                    readonly property point p1:
                                        taskCombiScoreCanvas.graphPoints[index]
                                    readonly property point p2:
                                        taskCombiScoreCanvas.graphPoints[index + 1]
                                    readonly property real dx: p2.x - p1.x
                                    readonly property real dy: p2.y - p1.y
                                    readonly property real segmentLength:
                                        Math.sqrt(dx * dx + dy * dy)
                                    readonly property real segmentAngle:
                                        Math.atan2(dy, dx) * 180 / Math.PI

                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 7
                                        radius: 3.5
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: taskCombiScoreGraph.accent
                                        opacity: 0.20
                                        antialiasing: true
                                    }

                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 2
                                        radius: 1
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: taskCombiScoreGraph.accent
                                        opacity: 1.0
                                        antialiasing: true
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: taskMemGraph

                    visible: taskManagerBody.metricGraphSelectionEnabled ? taskManagerBody.graphSelected("mem") : !taskCpuGraph.hunterMetricView

                    width: parent.width
                    height: taskManagerBody.graphHeight

                    GohuText {
                        id: taskMemGraphTitle
                        anchors.left: parent.left
                        anchors.top: parent.top

                        text:
                            "MEMORY HISTORY  "
                            + (taskManagerBody.currentTask
                               ? Number(taskManagerBody.currentTask.mem).toFixed(1)
                               : "0.0")
                            + "%"

                        font.pixelSize: 12
                        color: Colors.magenta

                        layer.enabled: true
                        layer.effect: DropShadow {
                            horizontalOffset: 0
                            verticalOffset: 0
                            radius: 5
                            samples: 5
                            opacity: 0.34
                            color: Colors.magenta
                            transparentBorder: true
                        }
                    }

                    Rectangle {
                        id: taskMemGraphFrame

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: taskMemGraphTitle.bottom
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 5

                        color: Colors.black
                        border.width: 1
                        border.color: Colors.magenta

                        RectangularShadow {
                            anchors.fill: parent
                            anchors.margins: -4
                            spread: 3
                            z: -1
                            opacity: 0.30
                            color: Colors.magenta
                        }
                    }

                    Item {
                        id: taskMemCanvas

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.fill: taskMemGraphFrame
                        anchors.margins: 4
                        z: 2
                        clip: true

                        property int graphRevision: 0
                        property real graphScrollOffset: 0
                        property int graphScrollPid: 0

                        NumberAnimation {
                            id: taskMemGraphScrollAnimation
                            target: taskMemCanvas
                            property: "graphScrollOffset"
                            to: 0
                            duration: presentationState.taskGraphScrollDuration
                            easing.type: Easing.Linear
                        }

                        function startGraphScroll() {
                            const pid = Number(presentationState.taskHistoryPid || 0);
                            const sameTask = pid > 0 && graphScrollPid === pid;

                            if (!sameTask) {
                                resetGraphScroll();
                                graphScrollPid = pid;
                                return;
                            }

                            taskMemGraphScrollAnimation.stop();
                            graphScrollOffset =
                                width
                                / Math.max(
                                    1,
                                    presentationState.taskHistoryLimit - 1
                                );
                            taskMemGraphScrollAnimation.restart();
                        }

                        function resetGraphScroll() {
                            taskMemGraphScrollAnimation.stop();
                            graphScrollOffset = 0;
                        }

                        function requestPaint(animateScroll, resetScroll) {
                            const pid = Number(presentationState.taskHistoryPid || 0);
                            graphRevision += 1;

                            if (resetScroll === true)
                                resetGraphScroll();
                            else if (animateScroll === true)
                                startGraphScroll();

                            graphScrollPid = pid;
                        }

                        readonly property var graphPoints: {
                            const revision = graphRevision;
                            return graphGeometry.linePoints(
                                taskManagerBody.graphDataAvailable && (!taskManagerBody.metricGraphSelectionEnabled || taskMemGraph.visible) ? presentationState.taskMemHistory : [],
                                width,
                                height,
                                0.35,
                                presentationState.taskHistoryLimit,
                                2,
                                2
                            );
                        }

                        Repeater {
                            model: 3
                            delegate: Rectangle {
                                x: 0
                                y: taskMemCanvas.height * (index + 1) / 4
                                width: taskMemCanvas.width
                                height: 1
                                color: Colors.magenta
                                opacity: 0.16
                            }
                        }

                        // Keep the memory reference grid stationary. Move all
                        // memory-history fills and strokes via one trace layer.
                        Item {
                            id: taskMemTraceLayer
                            anchors.fill: parent
                            transform: Translate {
                                x: taskMemCanvas.graphScrollOffset
                            }
                            // Stable translucent area under the memory trace.
                            Repeater {
                                model: taskMemCanvas.graphPoints.length

                                delegate: Rectangle {
                                    readonly property point graphPoint:
                                        taskMemCanvas.graphPoints[index]
                                    x: graphPoint.x - width / 2
                                    y: graphPoint.y
                                    width: Math.max(2.0,
                                        taskMemCanvas.width
                                        / Math.max(2, presentationState.taskHistoryLimit - 1)
                                        + 0.8)
                                    height: Math.max(0, taskMemCanvas.height - graphPoint.y - 1)
                                    color: Colors.magenta
                                    opacity: 0.10
                                    antialiasing: true
                                }
                            }

                            Repeater {
                                model: Math.max(0, taskMemCanvas.graphPoints.length - 1)

                                delegate: Item {
                                    anchors.fill: parent

                                    readonly property point p1:
                                        taskMemCanvas.graphPoints[index]
                                    readonly property point p2:
                                        taskMemCanvas.graphPoints[index + 1]
                                    readonly property real dx: p2.x - p1.x
                                    readonly property real dy: p2.y - p1.y
                                    readonly property real segmentLength:
                                        Math.sqrt(dx * dx + dy * dy)
                                    readonly property real segmentAngle:
                                        Math.atan2(dy, dx) * 180 / Math.PI

                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 7
                                        radius: 3.5
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: Colors.magenta
                                        opacity: 0.20
                                        antialiasing: true
                                    }

                                    Rectangle {
                                        x: parent.p1.x
                                        y: parent.p1.y - height / 2
                                        width: parent.segmentLength
                                        height: 2
                                        radius: 1
                                        rotation: parent.segmentAngle
                                        transformOrigin: Item.Left
                                        color: Colors.magenta
                                        opacity: 1.0
                                        antialiasing: true
                                    }
                                }
                            }
                        }
                    }
                }



                // Reparent the entire column once, never individual controls.
                Column {
                    id: actionColumn
                    objectName: "sharedProcessActionSection"
                    parent: taskManagerBody.actionTarget || taskManagerBody
                    width: parent.width
                    spacing: taskManagerBody.compact ? 6 : 12
                    visible: !!taskManagerBody.currentTask
                    Item {
                    id: taskTerminationHeaderBox

                    visible: !taskManagerBody.lockTarget
                    width: parent.width
                    height: 30

                    GohuText {
                        id: taskTerminationHeader

                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 16

                        text: "KILLING ACTIONS"
                        font.pixelSize: 13
                        color: Colors.red
                    }

                    DropShadow {
                        anchors.fill: taskTerminationHeader
                        source: taskTerminationHeader

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 10
                        samples: 9
                        opacity: 0.68
                        color: Colors.red
                        transparentBorder: true
                    }

                    Row {
                        id: taskActionLockRow
                        parent: taskManagerBody.lockTarget || taskTerminationHeaderBox
                        anchors.right: parent.right
                        // KILLING ACTION cards are parent.width - 10 and centered,
                        // so their right edge sits 5 px inside this column.
                        anchors.rightMargin: taskManagerBody.lockTarget ? 0 : 5
                        anchors.verticalCenter: taskManagerBody.lockTarget ? undefined : parent.verticalCenter
                        anchors.verticalCenterOffset: 0
                        spacing: 5

                        Loader {
                            id: taskLimitSafetyLockLoader
                            width: 30
                            height: 26
                            visible:
                                taskManagerBody.currentTask
                                && Number(taskManagerBody.currentTask.pid || 0) > 1
                                && processController.requiresDangerUnlock(
                                       taskManagerBody.currentTask
                                   )
                            sourceComponent:
                                visible ? taskManagerBody.safetyLockComponent : undefined
                            onLoaded: {
                                item.actionKind = "limit";
                                item.accentColor = Colors.yellow;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }

                        Loader {
                            id: taskFreezeSafetyLockLoader
                            parent: taskManagerBody.freezeLockTarget || taskActionLockRow
                            anchors.horizontalCenter: taskManagerBody.freezeLockTarget ? parent.horizontalCenter : undefined
                            width: taskManagerBody.freezeLockTarget ? parent.width : 30
                            height: taskManagerBody.freezeLockTarget ? parent.height : 26
                            visible:
                                taskManagerBody.currentTask
                                && Number(taskManagerBody.currentTask.pid || 0) > 1
                                && processController.requiresDangerUnlock(
                                       taskManagerBody.currentTask
                                   )
                            sourceComponent:
                                visible ? taskManagerBody.safetyLockComponent : undefined
                            onLoaded: {
                                item.actionKind = "freeze";
                                item.accentColor = Colors.cyan;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }

                        Loader {
                            id: taskKillSafetyLockLoader
                            parent: taskManagerBody.killLockTarget || taskActionLockRow
                            anchors.horizontalCenter: taskManagerBody.killLockTarget ? parent.horizontalCenter : undefined
                            width: taskManagerBody.killLockTarget ? parent.width : 30
                            height: taskManagerBody.killLockTarget ? parent.height : 26
                            visible:
                                taskManagerBody.currentTask
                                && Number(taskManagerBody.currentTask.pid || 0) > 1
                                && processController.requiresDangerUnlock(
                                       taskManagerBody.currentTask
                                   )
                            sourceComponent:
                                visible ? taskManagerBody.safetyLockComponent : undefined
                            onLoaded: {
                                item.actionKind = "kill";
                                item.accentColor = Colors.red;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }

                        Loader {
                            id: taskRestartSafetyLockLoader
                            parent: taskManagerBody.restartLockTarget || taskActionLockRow
                            anchors.horizontalCenter: taskManagerBody.restartLockTarget ? parent.horizontalCenter : undefined
                            width: taskManagerBody.restartLockTarget ? parent.width : 30
                            height: taskManagerBody.restartLockTarget ? parent.height : 26
                            visible:
                                taskManagerBody.currentTask
                                && Number(taskManagerBody.currentTask.pid || 0) > 1
                                && processController.requiresDangerUnlock(
                                       taskManagerBody.currentTask
                                   )
                            sourceComponent:
                                visible ? taskManagerBody.safetyLockComponent : undefined
                            onLoaded: {
                                item.actionKind = "restart";
                                item.accentColor = Colors.yellow;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }
                    }
                }



                ReloadButton {
                    id: taskRestartAction
                    parent: taskManagerBody.quickActionTarget || actionColumn
                    width: taskManagerBody.headerActions ? 34 : parent.width - 10
                    height: taskManagerBody.headerActions ? width : 34
                    anchors.horizontalCenter: taskManagerBody.headerActions ? undefined : parent.horizontalCenter

                    property bool protectedTask:
                        taskManagerBody.currentTask
                        && processController.requiresDangerUnlock(taskManagerBody.currentTask)
                    property bool canRestart:
                        taskManagerBody.currentTask
                        && Number(taskManagerBody.currentTask.pid || 0) > 1
                        && (!protectedTask
                            || processController.dangerActionUnlocked(
                                   taskManagerBody.currentTask, "restart"
                               ))
                    available: canRestart
                    suppressHover: host.keyboardActive
                    selected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 0
                    destructive: !taskManagerBody.headerActions
                    showLabel: taskManagerBody.headerActions
                    label: taskManagerBody.headerActions ? "⟳" : ""
                    labelPixelSize: 22
                    labelMinimumPixelSize: 7
                    labelFontSizeMode: taskManagerBody.headerActions ? Text.FixedSize : Text.Fit
                    contentPadding: taskManagerBody.headerActions ? 3 : 8
                    Accessible.name: "Restart process"
                    accentColor: taskManagerBody.headerActions ? Colors.yellow : Colors.cyan
                    idleForegroundColor: taskManagerBody.headerActions ? Colors.yellow : Colors.white
                    hoverForegroundColor: taskManagerBody.headerActions ? Colors.yellow : Colors.white
                    selectedForegroundColor: taskManagerBody.headerActions ? Colors.yellow : Colors.white
                    pointerCursorShape: Qt.ArrowCursor

                    idleFillColor: Colors.black
                    hoverFillColor: taskManagerBody.headerActions ? hoverSurfaceColor : Colors.yellow
                    selectedFillColor: taskManagerBody.headerActions ? hoverSurfaceColor : Colors.yellow
                    pressedFillColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    idleBorderColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    hoverBorderColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    selectedBorderColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    pressedBorderColor: Colors.black
                    unavailableOpacity: 0.34

                    contentGlowEnabled: taskManagerBody.headerActions
                    softGlowEnabled: true
                    softGlowSpread: taskManagerBody.headerActions ? 3 : 4
                    softGlowMargin: taskManagerBody.headerActions ? 0 : 4
                    idleSoftGlowColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    hoverSoftGlowColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    selectedSoftGlowColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    pressedSoftGlowColor: taskManagerBody.headerActions ? Colors.yellow : Colors.red
                    softGlowIdleOpacity: taskManagerBody.headerActions ? 0.48 : 0.30
                    softGlowHoverOpacity: taskManagerBody.headerActions ? 0.82 : 0.58
                    softGlowSelectedOpacity: taskManagerBody.headerActions ? 0.82 : 0.58
                    softGlowPressedOpacity: taskManagerBody.headerActions ? 0.92 : 0.58
                    wideGlowEnabled: taskManagerBody.headerActions

                    contentGlowIdleOpacity: taskManagerBody.headerActions ? 0.82 : 0
                    contentGlowHoverOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowSelectedOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowPressedOpacity: taskManagerBody.headerActions ? 0.92 : 0
                    idleContentGlowColor: Colors.yellow
                    hoverContentGlowColor: Colors.yellow
                    selectedContentGlowColor: Colors.yellow
                    pressedContentGlowColor: Colors.yellow
                    trackLabelGlowLocally: taskManagerBody.headerActions
                    contentGlowRadius: taskManagerBody.headerActions ? 8 : 7
                    contentGlowSamples: taskManagerBody.headerActions ? 9 : 7
                    keyboardSelectedContentGlowColor: taskManagerBody.headerActions ? Colors.yellow : Colors.orange
                    unavailableContentGlowOpacity: taskManagerBody.headerActions ? 0.25 : -1
                    onHoverEntered: {
                        host.setKeyboardActive(false);
                        host.clearModeRailFocus();
                        host.setDetailFocused(true);
                        host.setDetailActionIndex(0);
                    }

                    onTriggered: {
                        host.setDetailActionIndex(0);
                        processController.requestRestart();
                    }

                    Row {
                        visible: !taskManagerBody.headerActions
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 8
                        spacing: 8

                        GohuText {
                            text: "↻"
                            font.pixelSize: 20
                            color: taskRestartAction.pressed ? Colors.black : Colors.red
                            layer.enabled: !taskRestartAction.pressed
                            layer.effect: DropShadow {
                                radius: 8
                                samples: 7
                                opacity: taskRestartAction.hovered || taskRestartAction.selected ? 0.82 : 0.52
                                color: Colors.red
                                transparentBorder: true
                            }
                        }

                        GohuText {
                            text:
                                taskRestartAction.protectedTask
                                && !taskRestartAction.canRestart
                                ? "LOCKED • RESTART PROCESS"
                                : "RESTART PROCESS"
                            font.pixelSize: 13
                            color: taskRestartAction.pressed ? Colors.black : Colors.red
                            layer.enabled: !taskRestartAction.pressed
                            layer.effect: DropShadow {
                                radius: 8
                                samples: 7
                                opacity: taskRestartAction.hovered || taskRestartAction.selected ? 0.76 : 0.48
                                color: Colors.red
                                transparentBorder: true
                            }
                        }
                    }




                }

                Rectangle {
                    id: taskLimitSlider

                    width: parent.width - 10
                    height: 34
                    anchors.horizontalCenter: parent.horizontalCenter

                    property real previewPercent: -1
                    property bool editingValue: false
                    property string editText: ""
                    readonly property var currentTask: taskManagerBody.currentTask
                    readonly property var limitResult:
                        typeof processController.limitResultFor === "function"
                        ? processController.limitResultFor(currentTask)
                        : {state:"unknown",message:"LIMIT STATUS UNAVAILABLE"}
                    Accessible.description: limitResult.message
                    readonly property bool canAdjust:
                        currentTask
                        && limitResult.state !== "pending" && limitResult.state !== "unknown"
                        && Number(currentTask.pid || 0) > 1
                        && (
                            !processController.requiresDangerUnlock(currentTask)
                            || processController.dangerActionUnlocked(
                                   currentTask, "limit"
                               )
                        )
                    readonly property real activePercent:
                        previewPercent >= 0
                        ? previewPercent
                        : processController.limitPercent()
                    readonly property real trackStartX:
                        taskLimitValuePlate.x + taskLimitValuePlate.width + 6
                    readonly property real handleWidth: 22
                    readonly property real handleHalfWidth: handleWidth / 2
                    readonly property real trackEndMargin: 4
                    readonly property real trackSpan:
                        Math.max(handleWidth + 1, width - trackStartX - trackEndMargin)
                    readonly property real dragSpan:
                        Math.max(1, trackSpan - handleWidth)
                    readonly property real handleCenterMinX:
                        trackStartX + handleHalfWidth

                    function percentAt(positionX) {
                        return Math.max(0, Math.min(100,
                            ((positionX - handleCenterMinX) / dragSpan) * 100
                        ));
                    }

                    function mibForPercent(percent) {
                        const entry = currentTask;
                        if (!entry)
                            return 0;
                        const pct = Math.max(0, Math.min(100, Number(percent || 0)));
                        if (pct >= 99.5)
                            return processController.limitMaximumMiB(entry);
                        const minMiB = processController.limitMinimumMiB(entry);
                        const maxMiB = processController.limitMaximumMiB(entry);
                        return minMiB + (maxMiB - minMiB) * (pct / 98.5);
                    }

                    function displayValue() {
                        if (previewPercent >= 0) {
                            if (previewPercent >= 99.5)
                                return "REL";
                            return String(Math.round(mibForPercent(previewPercent)));
                        }
                        if (limitResult.state === "pending") return "WAIT";
                        if (limitResult.state === "unknown") return "N/A";
                        if (limitResult.state === "refused") return "ERR";
                        if (limitResult.state === "restored") return "REL";
                        if (limitResult.state === "draft") return "EDIT";
                        if (!processController.hasSoftLimit()) return "NONE";
                        return String(Math.round(processController.limitMiB()));
                    }

                    readonly property bool keyboardSelected:
                        host.detailFocused
                        && host.selectedDetailActionIndex === -2

                    function keyboardStep(deltaPercent) {
                        if (!canAdjust)
                            return;

                        const next = Math.max(
                            0,
                            Math.min(
                                100,
                                activePercent + Number(deltaPercent || 0)
                            )
                        );

                        previewPercent = -1;
                        processController.setLimitPercent(next);
                        // The shared gateway consumes the one-shot limit grant.
                    }

                    function commitEditorValue() {
                        if (!editingValue)
                            return;

                        const value = Number(editText || 0);
                        if (isFinite(value) && value > 0) {
                            processController.setLimitMiB(value);
                            // The shared gateway consumes the one-shot limit grant.
                        }

                        previewPercent = -1;
                        editingValue = false;
                    }

                    color: Colors.black
                    opacity: canAdjust ? 1.0 : 0.34
                    border.width: 1
                    border.color:
                        keyboardSelected ? Colors.magenta : Colors.yellow

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: parent.trackStartX
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.topMargin: 3
                        anchors.bottomMargin: 3
                        width: Math.max(0,
                            parent.trackSpan * Math.max(0, Math.min(100, parent.activePercent)) / 100)
                        color: Colors.yellow
                        opacity: 0.52
                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 6
                            samples: 7
                            opacity: 0.44
                            color: Colors.yellow
                            transparentBorder: true
                        }
                    }

                    Rectangle {
                        id: taskLimitHandle
                        z: 5
                        width: parent.handleWidth
                        height: parent.height - 4
                        y: 2
                        x: parent.trackStartX
                           + parent.dragSpan * Math.max(0, Math.min(100, parent.activePercent)) / 100
                        color: Colors.white
                        border.width: 1
                        border.color: Colors.yellow

                        GohuText {
                            anchors.centerIn: parent
                            text: "▮"
                            font.pixelSize: 12
                            color: Colors.black
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: taskLimitMouse.containsMouse || taskLimitMouse.pressed ? 0.68 : 0.44
                            color: Colors.yellow
                        }
                    }

                    Rectangle {
                        id: taskLimitValuePlate
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                        z: 30
                        width: 112
                        height: parent.height - 8
                        color: Colors.black
                        opacity: 0.96

                        MouseArea {
                            anchors.fill: parent
                            z: 0
                            onClicked: {
                                taskLimitSlider.commitEditorValue();
                                taskLimitEditor.focus = false;
                                host.setKeyboardActive(false);
                                host.clearModeRailFocus();
                                host.setDetailFocused(true);
                                host.setDetailActionIndex(-2);
                            }
                        }

                        Row {
                            z: 1
                            anchors.centerIn: parent
                            spacing: 5

                            GohuText {
                                text: "LIMIT"
                                height: taskLimitValuePlate.height
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: 10
                                color: Colors.yellow
                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 5
                                    opacity: 0.48
                                    color: Colors.yellow
                                    transparentBorder: true
                                }
                            }

                            Item {
                                width: 46
                                height: taskLimitValuePlate.height
                                anchors.verticalCenter: parent.verticalCenter

                                GohuText {
                                    id: taskLimitLiveValue
                                    anchors.fill: parent
                                    visible: !taskLimitSlider.editingValue
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                    text: taskLimitSlider.displayValue()
                                    font.pixelSize: 10
                                    color: Colors.white

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            taskLimitSlider.editingValue = true;
                                            taskLimitSlider.editText =
                                                processController.hasSoftLimit()
                                                ? String(Math.round(processController.limitMiB()))
                                                : String(Math.round(processController.limitMaximumMiB(taskManagerBody.currentTask)));
                                            taskLimitEditor.text = taskLimitSlider.editText;
                                            taskLimitEditor.forceActiveFocus();
                                            taskLimitEditor.selectAll();
                                        }
                                    }
                                }

                                TextInput {
                                    id: taskLimitEditor
                                    anchors.fill: parent
                                    visible: taskLimitSlider.editingValue
                                    verticalAlignment: TextInput.AlignVCenter
                                    horizontalAlignment: TextInput.AlignHCenter
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 10
                                    color: Colors.white
                                    selectionColor: Colors.yellow
                                    selectedTextColor: Colors.black
                                    selectByMouse: true
                                    validator: IntValidator {
                                        bottom: 1
                                        top: Math.max(1, Math.floor(processController.limitMaximumMiB(taskManagerBody.currentTask)))
                                    }

                                function returnToLimitNavigation(moveDirection) {
                                    taskLimitSlider.commitEditorValue();
                                    focus = false;
                                    host.setKeyboardActive(true);
                                    host.clearModeRailFocus();
                                    host.setDetailFocused(true);
                                    host.setDetailActionIndex(-2);
                                    Qt.callLater(function() {
                                        taskManagerBody.searchInputTarget.forceActiveFocus();
                                        if (moveDirection !== 0)
                                            host.moveDetailSelection(moveDirection);
                                        else
                                            host.ensureDetailActionVisible();
                                    });
                                }

                                onActiveFocusChanged: {
                                    if (activeFocus) {
                                        taskLimitSlider.editingValue = true;
                                        taskLimitSlider.editText =
                                            processController.hasSoftLimit()
                                            ? String(Math.round(processController.limitMiB()))
                                            : String(Math.round(processController.limitMaximumMiB(taskManagerBody.currentTask)));
                                        selectAll();
                                    } else {
                                        taskLimitSlider.commitEditorValue();
                                        host.clearModeRailFocus();
                                        host.setDetailFocused(true);
                                        host.setDetailActionIndex(-2);
                                        Qt.callLater(function() {
                                            if (host.menuOpen
                                                && host.detailFocused)
                                                taskManagerBody.searchInputTarget.forceActiveFocus();
                                        });
                                    }
                                }

                                onTextEdited: taskLimitSlider.editText = text

                                Keys.onReturnPressed: returnToLimitNavigation(0)
                                Keys.onEnterPressed: returnToLimitNavigation(0)
                                Keys.onEscapePressed: {
                                    taskLimitSlider.editingValue = false;
                                    focus = false;
                                    host.clearModeRailFocus();
                                    host.setDetailFocused(true);
                                    host.setDetailActionIndex(-2);
                                    Qt.callLater(function() { taskManagerBody.searchInputTarget.forceActiveFocus(); });
                                }
                                Keys.onPressed: function(event) {
                                    if (event.key === Qt.Key_Down || event.key === Qt.Key_Up) {
                                        returnToLimitNavigation(event.key === Qt.Key_Down ? 1 : -1);
                                        event.accepted = true;
                                    }
                                }
                                }
                            }

                            GohuText {
                                text: "MiB"
                                height: taskLimitValuePlate.height
                                verticalAlignment: Text.AlignVCenter
                                font.pixelSize: 9
                                color: Colors.yellow
                                opacity: 1.0
                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 5
                                    opacity: 0.36
                                    color: Colors.yellow
                                    transparentBorder: true
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: taskLimitMouse
                        anchors.fill: parent
                        z: 20
                        enabled: taskLimitSlider.canAdjust
                        hoverEnabled: true
                        preventStealing: true
                        acceptedButtons: Qt.LeftButton
                        property real dragOffsetX: 0

                        onEntered: {
                            host.setKeyboardActive(false);
                            host.clearModeRailFocus();
                            host.setDetailFocused(true);
                            host.setDetailActionIndex(-2);
                        }

                        // Leave the numeric value plate clickable/editable.
                        onPressed: function(mouse) {
                            if (mouse.x <= taskLimitValuePlate.x + taskLimitValuePlate.width) {
                                mouse.accepted = false;
                                return;
                            }
                            taskLimitSlider.commitEditorValue();
                            taskLimitEditor.focus = false;
                            host.setDetailActionIndex(-2);
                            const center = taskLimitHandle.x + taskLimitHandle.width / 2;
                            const overHandle =
                                mouse.x >= taskLimitHandle.x
                                && mouse.x <= taskLimitHandle.x + taskLimitHandle.width;
                            dragOffsetX = overHandle ? mouse.x - center : 0;
                            taskLimitSlider.previewPercent =
                                taskLimitSlider.percentAt(mouse.x - dragOffsetX);
                            mouse.accepted = true;
                        }
                        onPositionChanged: function(mouse) {
                            if (pressed && mouse.x > taskLimitValuePlate.x + taskLimitValuePlate.width)
                                taskLimitSlider.previewPercent =
                                    taskLimitSlider.percentAt(mouse.x - dragOffsetX);
                        }
                        onReleased: function(mouse) {
                            if (taskLimitSlider.previewPercent >= 0) {
                                processController.setLimitPercent(taskLimitSlider.previewPercent);
                                // The shared gateway consumes the one-shot limit grant.
                            }
                            taskLimitSlider.previewPercent = -1;
                            dragOffsetX = 0;
                            mouse.accepted = true;
                        }
                        onWheel: function(wheel) {
                            const delta = wheel.angleDelta.y !== 0
                                          ? wheel.angleDelta.y : wheel.pixelDelta.y;
                            const next = Math.max(0, Math.min(100,
                                taskLimitSlider.activePercent + (delta >= 0 ? 2 : -2)
                            ));
                            processController.setLimitPercent(next);
                            // The shared gateway consumes the one-shot limit grant.
                            wheel.accepted = true;
                        }
                    }

                    
                    RectangularShadow {
                        anchors.fill: parent
                        anchors.margins: -4
                        spread: 4
                        z: -1
                        opacity: taskLimitMouse.containsMouse || taskLimitMouse.pressed ? 0.68 : 0.38
                        color: Colors.yellow
                    }
                }

                ActionButton {
                    id: taskFreezeAction

                    parent: taskManagerBody.freezeActionTarget || taskManagerBody.quickActionTarget || actionColumn
                    width: taskManagerBody.headerActions ? 34 : parent.width - 10
                    height: taskManagerBody.headerActions ? width : 34
                    anchors.horizontalCenter: taskManagerBody.headerActions ? undefined : parent.horizontalCenter

                    property bool protectedTask:
                        taskManagerBody.currentTask
                        && processController.requiresDangerUnlock(taskManagerBody.currentTask)
                    property bool taskUnlocked:
                        taskManagerBody.currentTask
                        && (
                            !protectedTask
                            || processController.dangerActionUnlocked(
                                   taskManagerBody.currentTask, "freeze"
                               )
                        )
                    property bool canFreeze:
                        taskManagerBody.currentTask
                        && Number(taskManagerBody.currentTask.pid || 0) > 1
                        && taskUnlocked

                    available: canFreeze
                    suppressHover: host.keyboardActive
                    selected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 1
                    showLabel: taskManagerBody.headerActions
                    label: taskManagerBody.headerActions ? (processController.isFrozen() ? "♨" : "❆") : ""
                    labelPixelSize: taskManagerBody.headerActions ? 25 : 18
                    labelMinimumPixelSize: 7
                    labelFontSizeMode: Text.Fit
                    contentPadding: taskManagerBody.headerActions ? 2 : 8
                    Accessible.name: processController.isFrozen() ? "Thaw process" : "Freeze process"
                    accentColor: taskManagerBody.headerActions ? Colors.cyan : Colors.cyan
                    idleForegroundColor: taskManagerBody.headerActions ? Colors.cyan : Colors.white
                    hoverForegroundColor: taskManagerBody.headerActions ? Colors.cyan : Colors.white
                    selectedForegroundColor: taskManagerBody.headerActions ? Colors.cyan : Colors.white
                    pointerCursorShape: Qt.ArrowCursor

                    idleFillColor: Colors.black
                    hoverFillColor: Colors.yellow
                    selectedFillColor: Colors.yellow
                    pressedFillColor: Colors.magenta
                    idleBorderColor: Colors.cyan
                    hoverBorderColor: Colors.cyan
                    selectedBorderColor: Colors.cyan
                    pressedBorderColor: Colors.cyan
                    unavailableOpacity: 0.34

                    contentGlowEnabled: taskManagerBody.headerActions
                    softGlowEnabled: true
                    softGlowSpread: taskManagerBody.headerActions ? 5 : 4
                    softGlowMargin: 4
                    idleSoftGlowColor: Colors.cyan
                    hoverSoftGlowColor: Colors.cyan
                    selectedSoftGlowColor: Colors.cyan
                    pressedSoftGlowColor: Colors.cyan
                    softGlowIdleOpacity: taskManagerBody.headerActions ? 0.48 : 0.28
                    softGlowHoverOpacity: taskManagerBody.headerActions ? 0.82 : 0.54
                    softGlowSelectedOpacity: taskManagerBody.headerActions ? 0.82 : 0.54
                    softGlowPressedOpacity: taskManagerBody.headerActions ? 0.92 : 0.54
                    wideGlowEnabled: taskManagerBody.headerActions
                    idleWideGlowColor: Colors.cyan
                    hoverWideGlowColor: Colors.cyan
                    selectedWideGlowColor: Colors.cyan
                    pressedWideGlowColor: Colors.cyan
                    idleContentGlowColor: Colors.cyan
                    hoverContentGlowColor: Colors.cyan
                    selectedContentGlowColor: Colors.cyan

                    contentGlowIdleOpacity: taskManagerBody.headerActions ? 0.82 : 0
                    contentGlowHoverOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowSelectedOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowPressedOpacity: taskManagerBody.headerActions ? 0.92 : 0
                    pressedContentGlowColor: Colors.cyan
                    trackLabelGlowLocally: taskManagerBody.headerActions
                    contentGlowRadius: taskManagerBody.headerActions ? 8 : 7
                    contentGlowSamples: taskManagerBody.headerActions ? 9 : 7
                    keyboardSelectedContentGlowColor: taskManagerBody.headerActions ? Colors.cyan : Colors.orange
                    unavailableContentGlowOpacity: taskManagerBody.headerActions ? 0.25 : -1
                    onHoverEntered: {
                        host.setKeyboardActive(false);
                        host.clearModeRailFocus();
                        host.setDetailFocused(true);
                        host.setDetailActionIndex(1);
                    }

                    onTriggered: {
                        host.setDetailActionIndex(1);
                        processController.toggleFreeze();
                    }

                    Row {
                        visible: !taskManagerBody.headerActions
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        anchors.rightMargin: 38
                        spacing: 8

                        GohuText {
                            visible:
                                taskFreezeAction.protectedTask
                                && !processController.isFrozen()
                            text: "⚠︎"
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 13
                            color: taskFreezeAction.pressed ? Colors.black
                                   : taskFreezeAction.hovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: !taskFreezeAction.pressed
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.hovered || taskFreezeAction.selected ? 0.62 : 0.40
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }
                        GohuText {
                            text:
                                processController.isFrozen()
                                ? "⋆˙♨⋆˚."
                                : "₊°｡❆ ๋࣭⭑"
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize:
                                processController.isFrozen() ? 17 : 28
                            color: taskFreezeAction.pressed ? Colors.black
                                   : taskFreezeAction.hovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: !taskFreezeAction.pressed
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.hovered || taskFreezeAction.selected ? 0.68 : 0.44
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }
                        GohuText {
                            text:
                                processController.isFrozen()
                                ? "THAW PROCESS"
                                : !taskFreezeAction.taskUnlocked
                                ? "LOCKED • FREEZE PROCESS"
                                : "FREEZE PROCESS"
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 13
                            color: taskFreezeAction.pressed ? Colors.black
                                   : taskFreezeAction.hovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: !taskFreezeAction.pressed
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.hovered || taskFreezeAction.selected ? 0.62 : 0.40
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }
                    }



                    

                }

                ActionButton {
                    id: taskEndAction
                    property bool clickFirePulse: false
                    Timer {
                        id: taskEndFireTimer
                        interval: 420
                        repeat: false
                        onTriggered: taskEndAction.clickFirePulse = false
                    }

                    parent: taskManagerBody.killActionTarget || taskManagerBody.quickActionTarget || actionColumn
                    width: taskManagerBody.headerActions ? parent.width : parent.width - 10
                    height: taskManagerBody.headerActions ? 34 : 36
                    anchors.horizontalCenter: taskManagerBody.headerActions ? undefined : parent.horizontalCenter

                    property bool protectedTask:
                        taskManagerBody.currentTask
                        && processController.requiresDangerUnlock(taskManagerBody.currentTask)
                    property bool taskUnlocked:
                        taskManagerBody.currentTask
                        && (
                            !protectedTask
                            || processController.dangerActionUnlocked(
                                   taskManagerBody.currentTask, "kill"
                               )
                        )
                    property bool canEnd:
                        taskManagerBody.currentTask
                        && Number(taskManagerBody.currentTask.pid || 0) > 1
                        && taskUnlocked

                    available: canEnd
                    suppressHover: host.keyboardActive
                    selected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 2
                    destructive: true
                    showLabel: taskManagerBody.headerActions
                    label: taskManagerBody.headerActions ? ((taskEndAction.pressed || taskEndAction.clickFirePulse) ? "(=ᗜ=)デ╾━ ๋࣭⭑" : taskEndAction.hovered || taskEndAction.selected ? "ദ്ദി(-_•)デ╾━" : "(-_•)デ╾━") : ""
                    labelPixelSize: taskManagerBody.headerActions ? 14 : 10
                    labelMinimumPixelSize: 7
                    labelFontSizeMode: Text.Fit
                    contentPadding: taskManagerBody.headerActions ? 2 : 8
                    Accessible.name: "End process (TERM)"
                    accentColor: taskManagerBody.headerActions ? Colors.red : Colors.cyan
                    idleForegroundColor: taskManagerBody.headerActions ? Colors.red : Colors.white
                    hoverForegroundColor: taskManagerBody.headerActions ? Colors.red : Colors.white
                    selectedForegroundColor: taskManagerBody.headerActions ? Colors.red : Colors.white
                    pointerCursorShape: Qt.ArrowCursor

                    idleFillColor: Colors.black
                    hoverFillColor: Colors.yellow
                    selectedFillColor: Colors.yellow
                    pressedFillColor: Colors.red
                    idleBorderColor: Colors.red
                    hoverBorderColor: Colors.red
                    selectedBorderColor: Colors.red
                    pressedBorderColor: Colors.black
                    unavailableOpacity: 0.34

                    contentGlowEnabled: taskManagerBody.headerActions
                    softGlowEnabled: true
                    softGlowSpread: 5
                    softGlowMargin: 5
                    idleSoftGlowColor: Colors.red
                    hoverSoftGlowColor: Colors.red
                    selectedSoftGlowColor: Colors.red
                    pressedSoftGlowColor: Colors.red
                    softGlowIdleOpacity: 0.34
                    softGlowHoverOpacity: 0.82
                    softGlowSelectedOpacity: 0.82
                    softGlowPressedOpacity: 0.92
                    wideGlowEnabled: false

                    contentGlowIdleOpacity: taskManagerBody.headerActions ? 0.82 : 0
                    contentGlowHoverOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowSelectedOpacity: taskManagerBody.headerActions ? 1.0 : 0
                    contentGlowPressedOpacity: taskManagerBody.headerActions ? 0.92 : 0
                    idleContentGlowColor: Colors.red
                    hoverContentGlowColor: Colors.red
                    selectedContentGlowColor: Colors.red
                    pressedContentGlowColor: Colors.red
                    trackLabelGlowLocally: taskManagerBody.headerActions
                    contentGlowRadius: taskManagerBody.headerActions ? 8 : 7
                    contentGlowSamples: taskManagerBody.headerActions ? 9 : 7
                    keyboardSelectedContentGlowColor: taskManagerBody.headerActions ? Colors.red : Colors.orange
                    unavailableContentGlowOpacity: taskManagerBody.headerActions ? 0.25 : -1
                    onHoverEntered: {
                        host.setKeyboardActive(false);
                        host.clearModeRailFocus();
                        host.setDetailFocused(true);
                        host.setDetailActionIndex(2);
                    }

                    onTriggered: {
                        taskEndAction.clickFirePulse = true;
                        taskEndFireTimer.restart();
                        host.setDetailActionIndex(2);
                        processController.requestTerminate();
                    }

                    Row {
                        visible: !taskManagerBody.headerActions
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 10
                        anchors.rightMargin: 38
                        spacing: 8

                        GohuText {
                            visible: taskEndAction.protectedTask
                            text: "⚠︎"
                            font.pixelSize: 14
                            color:
                                taskEndAction.pressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: !taskEndAction.pressed
                            layer.effect: DropShadow {
                                horizontalOffset: 0
                                verticalOffset: 0
                                radius: 11
                                samples: 9
                                opacity: 0.72
                                color: Colors.red
                                transparentBorder: true
                            }
                        }

                        GohuText {
                            text:
                                (taskEndAction.pressed || taskEndAction.clickFirePulse)
                                ? "(=ᗜ=)デ╾━ ๋࣭⭑"
                                : taskEndAction.hovered || taskEndAction.selected
                                ? "ദ്ദി(-_•)デ╾━"
                                : "(-_•)デ╾━"
                            font.pixelSize: 14
                            color:
                                taskEndAction.pressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: !taskEndAction.pressed
                            layer.effect: DropShadow {
                                horizontalOffset: 0
                                verticalOffset: 0
                                radius: 13
                                samples: 11
                                opacity: 0.86
                                color: Colors.red
                                transparentBorder: true
                            }
                        }

                        GohuText {
                            text:
                                !taskEndAction.taskUnlocked
                                ? "LOCKED • END PROCESS  [TERM]"
                                : "END PROCESS  [TERM]"
                            font.pixelSize: 14
                            color:
                                taskEndAction.pressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: !taskEndAction.pressed
                            layer.effect: DropShadow {
                                horizontalOffset: 0
                                verticalOffset: 0
                                radius: 11
                                samples: 9
                                opacity: 0.72
                                color: Colors.red
                                transparentBorder: true
                            }
                        }
                    }



                    


                }

                }
            }
