import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
            Column {
                id: taskManagerBody

    required property var host
    required property var presentationState
    required property var processController
    required property var graphGeometry
    required property var hunterGraph
    required property var searchInputTarget
    required property Component safetyLockComponent

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
                spacing: 12

                visible: processController.currentTask !== null

                property var currentTask:
                    processController.currentTask

                GridLayout {
                    id: taskMetricGrid

                    width: parent.width
                    columns: 3
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: {
                            const task = taskManagerBody.currentTask;
                            if (!task) return [];

                            return [
                                { id: "cpu", label: "CPU", value: Number(task.cpu || 0).toFixed(1) + "%", baseAccent: Colors.orange, critical: processController.metricIsCritical(task, "cpu") },
                                { id: "mem", label: "MEM", value: Number(task.mem || 0).toFixed(1) + "%", baseAccent: Colors.magenta, critical: processController.metricIsCritical(task, "mem") },
                                { id: "rss", label: "RSS", value: processController.formatMemory(task.rss), baseAccent: Colors.cyan, critical: processController.metricIsCritical(task, "rss") },
                                { id: "threads", label: "THREADS", value: String(task.threads || 0), baseAccent: Colors.omnitrix, critical: processController.metricIsCritical(task, "threads") },
                                { id: "pid", label: "PID", value: String(task.pid || "?"), baseAccent: Colors.yellow, critical: false },
                                { id: "uptime", label: "UPTIME", value: String(task.elapsed || "?"), baseAccent: Colors.white, critical: false }
                            ];
                        }

                        Rectangle {
                            id: taskMetricCard
                            required property var modelData

                            readonly property color accent:
                                modelData.critical ? Colors.red : modelData.baseAccent
                            readonly property color glowColor:
                                accent === Colors.white ? Colors.cyan : accent
                            readonly property bool favorite:
                                host.isTaskMetricFavorite(
                                    taskManagerBody.currentTask,
                                    modelData.id
                                )

                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            color: Colors.black
                            border.width: 1
                            border.color: accent

                            RectangularShadow {
                                anchors.fill: parent
                                anchors.margins: -4
                                spread: 3
                                z: -1
                                opacity: modelData.critical ? 0.58 : 0.28
                                color: taskMetricCard.glowColor
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 3

                                GohuText {
                                    text: modelData.label
                                    font.pixelSize: 10
                                    color: taskMetricCard.accent
                                    opacity: 0.90
                                    layer.enabled: Window.window !== null
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
                                    font.pixelSize: 16
                                    color: taskMetricCard.accent
                                    elide: Text.ElideRight
                                    layer.enabled: Window.window !== null
                                    layer.effect: DropShadow {
                                        radius: modelData.critical ? 10 : 5
                                        samples: 9
                                        opacity: modelData.critical ? 0.90 : 0.38
                                        color: taskMetricCard.glowColor
                                        transparentBorder: true
                                    }
                                }
                            }

                            Item {
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
                                    layer.enabled: Window.window !== null && (taskMetricCard.favorite)
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

                    width: parent.width
                    height: 112

                    readonly property bool hunterMetricView:
                        host.hunterMetricView
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

                        layer.enabled: Window.window !== null
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
                            layer.enabled: Window.window !== null
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
                            layer.enabled: Window.window !== null
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
                            layer.enabled: Window.window !== null
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
                            layer.enabled: Window.window !== null
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
                            layer.enabled: Window.window !== null
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

                                // Preserve the filled-graph look for COMBI too. Low
                                // opacity keeps four overlapping fills readable.
                                Repeater {
                                    model: detailCombiTrace.metricPoints.length

                                    delegate: Rectangle {
                                        readonly property point graphPoint:
                                            detailCombiTrace.metricPoints[index]
                                        x: graphPoint.x - width / 2 + taskCpuCanvas.graphScrollOffset
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
                                            x: parent.p1.x + taskCpuCanvas.graphScrollOffset
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
                                            x: parent.p1.x + taskCpuCanvas.graphScrollOffset
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

                        // Stable translucent area under the trace. Each point
                        // contributes a narrow vertical strip down to the graph floor;
                        // this recreates the old filled-graph look without Canvas.
                        Repeater {
                            model: taskCpuCanvas.graphPoints.length

                            delegate: Rectangle {
                                readonly property point graphPoint:
                                    taskCpuCanvas.graphPoints[index]
                                x: graphPoint.x - width / 2 + taskCpuCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskCpuCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskCpuCanvas.graphScrollOffset
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

                Item {
                    id: taskCombiScoreGraph

                    visible: taskCpuGraph.combiView
                    width: parent.width
                    height: visible ? 112 : 0

                    readonly property color accent: Colors.yellow
                    readonly property var historyValues: {
                        const revision =
                            presentationState.taskHunterDetailHistoryRevision;
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

                        layer.enabled: Window.window !== null
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

                        // Filled space under the restored combined-score trace.
                        Repeater {
                            model: taskCombiScoreCanvas.graphPoints.length

                            delegate: Rectangle {
                                readonly property point graphPoint:
                                    taskCombiScoreCanvas.graphPoints[index]
                                x: graphPoint.x - width / 2 + taskCombiScoreCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskCombiScoreCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskCombiScoreCanvas.graphScrollOffset
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

                Item {
                    id: taskMemGraph

                    visible: !taskCpuGraph.hunterMetricView

                    width: parent.width
                    height: 112

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

                        layer.enabled: Window.window !== null
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
                                presentationState.taskMemHistory,
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

                        // Stable translucent area under the memory trace.
                        Repeater {
                            model: taskMemCanvas.graphPoints.length

                            delegate: Rectangle {
                                readonly property point graphPoint:
                                    taskMemCanvas.graphPoints[index]
                                x: graphPoint.x - width / 2 + taskMemCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskMemCanvas.graphScrollOffset
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
                                    x: parent.p1.x + taskMemCanvas.graphScrollOffset
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



                // KILLING ACTIONS sit immediately below the graphs.
Item {
                    id: taskTerminationHeaderBox

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
                        anchors.right: parent.right
                        // KILLING ACTION cards are parent.width - 10 and centered,
                        // so their right edge sits 5 px inside this column.
                        anchors.rightMargin: 5
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.verticalCenterOffset: 8
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
                                item.actionKind = "freeze";
                                item.accentColor = Colors.cyan;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }

                        Loader {
                            id: taskKillSafetyLockLoader
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
                                item.actionKind = "kill";
                                item.accentColor = Colors.red;
                                item.taskItem = Qt.binding(function() {
                                    return taskManagerBody.currentTask;
                                });
                            }
                        }
                    }
                }



                Rectangle {
                    id: taskRestartAction
                    width: parent.width - 10
                    height: 34
                    anchors.horizontalCenter: parent.horizontalCenter

                    property bool protectedTask:
                        taskManagerBody.currentTask
                        && processController.requiresDangerUnlock(taskManagerBody.currentTask)
                    property bool canRestart:
                        taskManagerBody.currentTask
                        && Number(taskManagerBody.currentTask.pid || 0) > 1
                        && (!protectedTask
                            || processController.dangerActionUnlocked(
                                   taskManagerBody.currentTask, "kill"
                               ))
                    property bool isHovered:
                        canRestart
                        && !host.keyboardActive
                        && taskRestartActionMouse.containsMouse
                    property bool isPressed: canRestart && taskRestartActionMouse.pressed
                    property bool isSelected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 0

                    color:
                        isPressed ? Colors.red
                        : isHovered || isSelected ? Colors.yellow
                        : Colors.black
                    opacity: canRestart ? 1.0 : 0.34
                    border.width: 1
                    border.color: isPressed ? Colors.black : Colors.red

                    Row {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 8
                        spacing: 8

                        GohuText {
                            text: "↻"
                            font.pixelSize: 20
                            color: taskRestartAction.isPressed ? Colors.black : Colors.red
                            layer.enabled: Window.window !== null && (!taskRestartAction.isPressed)
                            layer.effect: DropShadow {
                                radius: 8
                                samples: 7
                                opacity: taskRestartAction.isHovered || taskRestartAction.isSelected ? 0.82 : 0.52
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
                            color: taskRestartAction.isPressed ? Colors.black : Colors.red
                            layer.enabled: Window.window !== null && (!taskRestartAction.isPressed)
                            layer.effect: DropShadow {
                                radius: 8
                                samples: 7
                                opacity: taskRestartAction.isHovered || taskRestartAction.isSelected ? 0.76 : 0.48
                                color: Colors.red
                                transparentBorder: true
                            }
                        }
                    }

                    MouseArea {
                        id: taskRestartActionMouse
                        anchors.fill: parent
                        enabled: taskRestartAction.canRestart
                        hoverEnabled: true
                        onEntered: {
                            host.setKeyboardActive(false);
                            host.clearModeRailFocus();
                            host.setDetailFocused(true);
                            host.setDetailActionIndex(0);
                        }
                        onClicked: {
                            host.setDetailActionIndex(0);
                            processController.requestRestart();
                        }
                    }

                    RectangularShadow {
                        anchors.fill: parent
                        anchors.margins: -4
                        spread: 4
                        z: -1
                        opacity: taskRestartAction.isHovered || taskRestartAction.isSelected ? 0.58 : 0.30
                        color: Colors.red
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
                    readonly property bool canAdjust:
                        currentTask
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
                                return "∞";
                            return String(Math.round(mibForPercent(previewPercent)));
                        }
                        if (!processController.hasSoftLimit())
                            return "∞";
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
                        processController.relockDangerAction(
                            taskManagerBody.currentTask,
                            "limit"
                        );
                    }

                    function commitEditorValue() {
                        if (!editingValue)
                            return;

                        const value = Number(editText || 0);
                        if (isFinite(value) && value > 0) {
                            processController.setLimitMiB(value);
                            processController.relockDangerAction(
                                taskManagerBody.currentTask,
                                "limit"
                            );
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
                        layer.enabled: Window.window !== null
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
                                layer.enabled: Window.window !== null
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
                                layer.enabled: Window.window !== null
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
                                processController.relockDangerAction(taskManagerBody.currentTask, "limit");
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
                            processController.relockDangerAction(taskManagerBody.currentTask, "limit");
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

                Rectangle {
                    id: taskFreezeAction

                    width: parent.width - 10
                    height: 34
                    anchors.horizontalCenter: parent.horizontalCenter

                    property bool isHovered:
                        !host.keyboardActive
                        && taskFreezeActionMouse.containsMouse
                    property bool isPressed: taskFreezeActionMouse.pressed
                    property bool isSelected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 1
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

                    color:
                        isPressed ? Colors.magenta
                        : isHovered || isSelected ? Colors.yellow
                        : Colors.black
                    opacity: canFreeze ? 1.0 : 0.34
                    border.width: 1
                    border.color: Colors.cyan

                    Row {
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
                            color: taskFreezeAction.isPressed ? Colors.black
                                   : taskFreezeAction.isHovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: Window.window !== null && (!taskFreezeAction.isPressed)
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.isHovered || taskFreezeAction.isSelected ? 0.62 : 0.40
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
                            color: taskFreezeAction.isPressed ? Colors.black
                                   : taskFreezeAction.isHovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: Window.window !== null && (!taskFreezeAction.isPressed)
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.isHovered || taskFreezeAction.isSelected ? 0.68 : 0.44
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
                            color: taskFreezeAction.isPressed ? Colors.black
                                   : taskFreezeAction.isHovered ? Colors.cyan
                                   : Colors.white
                            layer.enabled: Window.window !== null && (!taskFreezeAction.isPressed)
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity: taskFreezeAction.isHovered || taskFreezeAction.isSelected ? 0.62 : 0.40
                                color: Colors.cyan
                                transparentBorder: true
                            }
                        }
                    }

                    MouseArea {
                        id: taskFreezeActionMouse
                        anchors.fill: parent
                        enabled: taskFreezeAction.canFreeze
                        hoverEnabled: true
                        onEntered: {
                            host.setKeyboardActive(false);
                            host.clearModeRailFocus();
                            host.setDetailFocused(true);
                            host.setDetailActionIndex(1);
                        }
                        onClicked: {
                            host.setDetailActionIndex(1);
                            processController.toggleFreeze();
                        }
                    }

                    
                    RectangularShadow {
                        anchors.fill: parent
                        anchors.margins: -4
                        spread: 4
                        z: -1
                        opacity: taskFreezeAction.isHovered || taskFreezeAction.isSelected ? 0.54 : 0.28
                        color: Colors.cyan
                    }
                }

                Rectangle {
                    id: taskEndAction

                    width: parent.width - 10
                    height: 36
                    anchors.horizontalCenter: parent.horizontalCenter

                    property bool isHovered:
                        !host.keyboardActive
                        && taskEndActionMouse.containsMouse
                    property bool isPressed: taskEndActionMouse.pressed
                    property bool isSelected:
                        host.detailFocused
                        && (processController.currentTask !== null)
                        && host.selectedDetailActionIndex === 2
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

                    color:
                        isPressed ? Colors.red
                        : isHovered || isSelected ? Colors.yellow
                        : Colors.black

                    opacity: canEnd ? 1.0 : 0.34

                    border.width: 1
                    border.color: isPressed ? Colors.black : Colors.red

                    Row {
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
                                taskEndAction.isPressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: Window.window !== null && (!taskEndAction.isPressed)
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
                                taskEndAction.isPressed
                                ? "(=ᗜ=)デ╾━ ๋࣭⭑"
                                : taskEndAction.isHovered || taskEndAction.isSelected
                                ? "ദ്ദി(-_•)デ╾━"
                                : "(-_•)デ╾━"
                            font.pixelSize: 14
                            color:
                                taskEndAction.isPressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: Window.window !== null && (!taskEndAction.isPressed)
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
                                taskEndAction.isPressed
                                ? Colors.black
                                : Colors.red

                            layer.enabled: Window.window !== null && (!taskEndAction.isPressed)
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

                    MouseArea {
                        id: taskEndActionMouse

                        anchors.fill: parent
                        enabled: taskEndAction.canEnd
                        hoverEnabled: true

                        onEntered: {
                            host.setKeyboardActive(false);
                            host.clearModeRailFocus();
                            host.setDetailFocused(true);
                            host.setDetailActionIndex(2);
                        }

                        onClicked: {
                            host.setDetailActionIndex(2);
                            processController.requestTerminate();
                        }
                    }

                    
                    RectangularShadow {
                        anchors.fill: parent
                        anchors.margins: -5
                        spread: 5
                        z: -1
                        opacity:
                            taskEndAction.isPressed ? 0.92
                            : taskEndAction.isHovered || taskEndAction.isSelected
                            ? 0.82 : 0.34
                        color: Colors.red
                    }

                }

                                Rectangle {
                    id: taskProcessScopeInfo
                    width: parent.width - 10
                    height: 112
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    clip: true

                    GohuText {
                        id: taskProcessScopeHeader
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: 7
                        anchors.rightMargin: 7
                        anchors.topMargin: 6

                        text:
                            "PROCESS SCOPE • PID "
                            + String(
                                  taskManagerBody.currentTask
                                  ? taskManagerBody.currentTask.pid : "?"
                              )
                            + " • LIMIT = THIS PROCESS"
                        font.pixelSize: 10
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    Flickable {
                        id: taskProcessScopeFlick
                        anchors.left: parent.left
                        anchors.right: taskProcessScopeScrollTrack.left
                        anchors.top: taskProcessScopeHeader.bottom
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 7
                        anchors.rightMargin: 5
                        anchors.topMargin: 4
                        anchors.bottomMargin: 6

                        clip: true
                        contentWidth: width
                        contentHeight: taskProcessScopeText.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds
                        flickableDirection: Flickable.VerticalFlick

                        GohuText {
                            id: taskProcessScopeText
                            width: taskProcessScopeFlick.width
                            text: processController.scopeProcessText()
                            font.pixelSize: 11
                            color: Colors.white
                            opacity: 0.86
                            wrapMode: Text.Wrap
                            lineHeight: 1.0
                        }
                    }

                    Rectangle {
                        id: taskProcessScopeScrollTrack
                        width: 8
                        anchors.top: taskProcessScopeHeader.bottom
                        anchors.bottom: parent.bottom
                        anchors.right: parent.right
                        anchors.topMargin: 4
                        anchors.bottomMargin: 6
                        anchors.rightMargin: 4

                        color: taskProcessScopeInfo.border.color
                        opacity:
                            taskProcessScopeFlick.contentHeight
                            > taskProcessScopeFlick.height + 1
                            ? 0.90 : 0.0
                        visible: opacity > 0.0
                        z: 20

                        property real maxContentY:
                            Math.max(
                                0,
                                taskProcessScopeFlick.contentHeight
                                - taskProcessScopeFlick.height
                            )
                        property real handleTravel:
                            Math.max(
                                0,
                                height - taskProcessScopeScrollHandle.height
                            )

                        function setScrollFromHandleY(handleY) {
                            if (maxContentY <= 0 || handleTravel <= 0)
                                return;

                            const clampedY = Math.max(
                                0,
                                Math.min(handleTravel, handleY)
                            );

                            taskProcessScopeFlick.contentY =
                                (clampedY / handleTravel) * maxContentY;
                        }

                        Rectangle {
                            id: taskProcessScopeScrollHandle
                            width: 5
                            anchors.horizontalCenter: parent.horizontalCenter

                            height: Math.max(
                                18,
                                parent.height * Math.min(
                                    1.0,
                                    taskProcessScopeFlick.visibleArea.heightRatio
                                )
                            )

                            y: {
                                if (taskProcessScopeScrollTrack.maxContentY <= 0
                                        || taskProcessScopeScrollTrack.handleTravel <= 0)
                                    return 0;

                                const clampedContentY = Math.max(
                                    0,
                                    Math.min(
                                        taskProcessScopeScrollTrack.maxContentY,
                                        taskProcessScopeFlick.contentY
                                    )
                                );

                                return (
                                    clampedContentY
                                    / taskProcessScopeScrollTrack.maxContentY
                                ) * taskProcessScopeScrollTrack.handleTravel;
                            }

                            color: Colors.magenta

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 2
                                z: -1
                                opacity: 0.22
                                color: Colors.magenta
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton
                            property real dragOffset: 0

                            onPressed: function(mouse) {
                                const handleTop = taskProcessScopeScrollHandle.y;
                                const handleBottom =
                                    taskProcessScopeScrollHandle.y
                                    + taskProcessScopeScrollHandle.height;

                                if (mouse.y >= handleTop && mouse.y <= handleBottom)
                                    dragOffset =
                                        mouse.y - taskProcessScopeScrollHandle.y;
                                else {
                                    dragOffset =
                                        taskProcessScopeScrollHandle.height / 2;

                                    taskProcessScopeScrollTrack.setScrollFromHandleY(
                                        mouse.y - dragOffset
                                    );
                                }

                                mouse.accepted = true;
                            }

                            onPositionChanged: function(mouse) {
                                if (pressed)
                                    taskProcessScopeScrollTrack.setScrollFromHandleY(
                                        mouse.y - dragOffset
                                    );
                            }

                            onWheel: function(wheel) {
                                wheel.accepted = false;
                            }
                        }
                    }
                }

            
                // Process metadata and command text stay below KILLING ACTIONS.
                GridLayout {
                    width: parent.width
                    columns: 3
                    columnSpacing: 6
                    rowSpacing: 4

                    GohuText {
                        Layout.preferredWidth: 62
                        text: "USER"
                        font.pixelSize: 11
                        color: Colors.cyan
                    }

                    GohuText {
                        Layout.preferredWidth: 10
                        text: ":"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.fillWidth: true
                        text:
                            taskManagerBody.currentTask
                            ? String(taskManagerBody.currentTask.user || "?")
                            : "?"
                        font.pixelSize: 11
                        color: Colors.white
                        elide: Text.ElideRight
                    }

                    GohuText {
                        Layout.preferredWidth: 62
                        text: "PPID"
                        font.pixelSize: 11
                        color: Colors.cyan
                    }

                    GohuText {
                        Layout.preferredWidth: 10
                        text: ":"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.fillWidth: true
                        text:
                            taskManagerBody.currentTask
                            ? String(taskManagerBody.currentTask.ppid || "?")
                            : "?"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.preferredWidth: 62
                        text: "VIRT"
                        font.pixelSize: 11
                        color: Colors.cyan
                    }

                    GohuText {
                        Layout.preferredWidth: 10
                        text: ":"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.fillWidth: true
                        text:
                            taskManagerBody.currentTask
                            ? processController.formatMemory(
                                  taskManagerBody.currentTask.vsz
                              )
                            : "?"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.preferredWidth: 62
                        text: "STATE"
                        font.pixelSize: 11
                        color: Colors.cyan
                    }

                    GohuText {
                        Layout.preferredWidth: 10
                        text: ":"
                        font.pixelSize: 11
                        color: Colors.white
                    }

                    GohuText {
                        Layout.fillWidth: true
                        text:
                            taskManagerBody.currentTask
                            ? String(taskManagerBody.currentTask.state || "?")
                            : "?"
                        font.pixelSize: 11
                        color: Colors.white
                    }
                }

                GohuText {
                    width: parent.width

                    text:
                        taskManagerBody.currentTask
                        ? String(taskManagerBody.currentTask.args || "")
                        : ""

                    font.pixelSize: 10
                    color: Colors.white
                    opacity: 0.56
                    wrapMode: Text.Wrap
                }

                                }
