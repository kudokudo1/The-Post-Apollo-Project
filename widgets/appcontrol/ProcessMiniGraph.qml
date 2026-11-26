import QtQuick
import "../../components"

// AppControl's existing mini-history scene graph, shared by both Kill hosts.
// Host owns sampling, identity resolution and metric ranges; this owns only
// isolated display snapshots, animation, grid, fill and line geometry.
Item {
    id: root
    required property var geometry
    required property var readHistory
    required property var readMetricHistory
    required property var metricRange
    property bool showingTask: true
    property string taskIdentity: ""
    property int historyRevision: -1
    property string metricKey: "normal"
    property bool combiView: false
    property real graphRange: 5
    property int historyLimit: 48
    property int scrollDuration: 1080
    property color accent: Colors.magenta
    property bool graphReady: false
    property real graphScrollOffset: 0
    readonly property var emptyCombiHistories: ({cpu: [], mem: [], io: [], age: []})
    property var historyFrame: ({values: [], combi: emptyCombiHistories})
    readonly property var historyValues: historyFrame.values
    readonly property var combiHistories: historyFrame.combi
    readonly property var combiSeries: [
        {metric:"cpu",label:"CPU",accent:Colors.orange},
        {metric:"mem",label:"MEM",accent:Colors.magenta},
        {metric:"io",label:"I/O",accent:Colors.cyan},
        {metric:"age",label:"AGE",accent:Colors.white}
    ]
    clip: true
    NumberAnimation {
        id: motion
        target: root
        property: "graphScrollOffset"
        to: 0
        duration: root.scrollDuration
        easing.type: Easing.Linear
    }
    function refreshHistory(animate) {
        if (!graphReady) return
        if (!showingTask) {
            motion.stop()
            graphScrollOffset = 0
            historyFrame = {values: [], combi: emptyCombiHistories}
            return
        }
        const next = readHistory()
        let combi = emptyCombiHistories
        if (combiView) {
            const cpu=readMetricHistory("cpu"), mem=readMetricHistory("mem")
            const io=readMetricHistory("io"), age=readMetricHistory("age")
            const n=Math.min(cpu.length,mem.length,io.length,age.length)
            if (n>0) combi={cpu:cpu.slice(-n),mem:mem.slice(-n),io:io.slice(-n),age:age.slice(-n)}
        }
        motion.stop()
        graphScrollOffset = animate && historyValues.length >= 1
            ? width / Math.max(1, historyLimit - 1) : 0
        if (graphScrollOffset>0) motion.restart()
        historyFrame = {values:Array.isArray(next)?next.slice():[],combi:combi}
    }
    onHistoryRevisionChanged: refreshHistory(true)
    onShowingTaskChanged: refreshHistory(false)
    onTaskIdentityChanged: refreshHistory(false)
    onMetricKeyChanged: refreshHistory(false)
    onCombiViewChanged: refreshHistory(false)
    Component.onCompleted: { graphReady=true; refreshHistory(false) }
    // Keep the same three-quarter grid used by MEMORY HISTORY
    // so every mini graph has a stable visual scale reference.
    Repeater {
        model: 3
        delegate: Rectangle {
            x: 0
            y: root.height * (index + 1) / 4
            width: root.width
            height: 1
            color: root.accent
            opacity: 0.13
            z: 0
        }
    }

    readonly property var graphPoints: {
        const values = historyValues;

        // Always render against the final 48-sample timeline.
        // Startup samples stay at the right side instead of being
        // stretched across the whole box and then reflowing every
        // refresh. That reflow was the source of the early fill
        // overhang. Background preloading fills this timeline before
        // the user normally reaches KILL/FAVORITES.
        const slots = root.historyLimit;

        return root.geometry.linePoints(
            values,
            width,
            height,
            root.graphRange,
            slots,
            2,
            3
        );
    }

    readonly property bool fillReady:
        graphPoints.length >= 2

    // Move all trace geometry as one scene-graph layer.
    // Keep the grid stationary and the original outer clip.
    Item {
        id: miniTraceLayer
        anchors.fill: parent
        transform: Translate {
            x: root.graphScrollOffset
        }
        // COMBI overlays the four real histories in the same
        // mini graph. Each metric keeps its own vertical scale, but
        // every series is trimmed to the same common history length
        // so CPU/MEM/I-O/AGE begin at the same x/time origin.
        Repeater {
            model:
                root.combiView
                ? root.combiSeries : []

            delegate: Item {
                id: miniCombiTrace
                required property var modelData
                required property int index
                anchors.fill: parent
                z: 5

                readonly property var metricHistory: {
                    // The controller has already aligned and
                    // isolated all four local series.
                    const values = root.combiHistories[modelData.metric];
                    return Array.isArray(values) ? values : [];
                }
                readonly property var metricPoints:
                    root.geometry.linePoints(
                        metricHistory,
                        width,
                        height,
                        root.metricRange(modelData.metric),
                        root.historyLimit,
                        2,
                        3
                    )

                // Very light per-series area fill. The four fills
                // intentionally overlap, matching the overlaid lines.
                Repeater {
                    model: miniCombiTrace.metricPoints.length

                    delegate: Rectangle {
                        readonly property point graphPoint:
                            miniCombiTrace.metricPoints[index]
                        x:
                            graphPoint.x
                            - width / 2
                        y: graphPoint.y
                        width: Math.max(
                            1.5,
                            miniCombiTrace.width
                            / Math.max(
                                2,
                                root.historyLimit - 1
                            )
                            + 0.8
                        )
                        height: Math.max(
                            0,
                            miniCombiTrace.height - graphPoint.y - 1
                        )
                        color: miniCombiTrace.modelData.accent
                        opacity: 0.055
                        antialiasing: true
                        z: 1
                    }
                }

                Repeater {
                    model: Math.max(
                        0,
                        miniCombiTrace.metricPoints.length - 1
                    )

                    delegate: Item {
                        anchors.fill: parent
                        z: 3
                        readonly property point p1:
                            miniCombiTrace.metricPoints[index]
                        readonly property point p2:
                            miniCombiTrace.metricPoints[index + 1]
                        readonly property real dx: p2.x - p1.x
                        readonly property real dy: p2.y - p1.y
                        readonly property real segmentLength:
                            Math.sqrt(dx * dx + dy * dy)
                        readonly property real segmentAngle:
                            Math.atan2(dy, dx) * 180 / Math.PI

                        Rectangle {
                            x:
                                parent.p1.x
                            y: parent.p1.y - height / 2
                            width: parent.segmentLength
                            height: 4
                            radius: 2
                            rotation: parent.segmentAngle
                            transformOrigin: Item.Left
                            color: miniCombiTrace.modelData.accent
                            opacity: 0.18
                            antialiasing: true
                        }

                        Rectangle {
                            x:
                                parent.p1.x
                            y: parent.p1.y - height / 2
                            width: parent.segmentLength
                            height: 1.5
                            radius: 0.75
                            rotation: parent.segmentAngle
                            transformOrigin: Item.Left
                            color: miniCombiTrace.modelData.accent
                            opacity: 1.0
                            antialiasing: true
                        }
                    }
                }
            }
        }

        // Fixed timeline geometry means the fill can be enabled as
        // soon as one real segment exists. There is no delayed six-
        // sample transition anymore, so the graph does not visibly
        // "pop" into a malformed filled state after several seconds.
        // Match the large TASK MANAGER graphs with a
        // translucent filled area beneath the mini trace. This is
        // ordinary QML geometry, so it keeps the same hide/show
        // stability as the segment renderer.
        // Fill only underneath segments that already have
        // two valid endpoints. The older point-cell fill could
        // briefly paint ahead of the trace while a delegate was
        // initializing, which produced the startup overhang.
        Repeater {
            model: !root.combiView
                   && root.fillReady
                   ? Math.max(
                         0,
                         root.graphPoints.length - 1
                     )
                   : 0

            delegate: Rectangle {
                readonly property point p1:
                    root.graphPoints[index]
                readonly property point p2:
                    root.graphPoints[index + 1]
                readonly property real leftX:
                    Math.max(0, Math.min(p1.x, p2.x))
                readonly property real rightX:
                    Math.min(
                        root.width,
                        Math.max(p1.x, p2.x)
                    )
                readonly property real topY:
                    Math.max(
                        0,
                        Math.min(
                            root.height - 1,
                            Math.min(p1.y, p2.y)
                        )
                    )

                x:
                    leftX
                y: topY
                width: Math.max(0, rightX - leftX + 0.8)
                height: Math.max(
                    0,
                    root.height - topY - 1
                )
                visible:
                    Number.isFinite(p1.x)
                    && Number.isFinite(p1.y)
                    && Number.isFinite(p2.x)
                    && Number.isFinite(p2.y)
                    && width > 0
                    && height > 0
                color: root.accent
                opacity: 0.20
                antialiasing: true
            }
        }

        Repeater {
            model: root.combiView
                   ? 0
                   : Math.max(0, root.graphPoints.length - 1)

            delegate: Item {
                anchors.fill: parent

                // Fresh graphPoints also notify existing
                // segments when the point count is unchanged.
                readonly property point p1:
                    root.graphPoints[index]
                readonly property point p2:
                    root.graphPoints[index + 1]
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
                    color: root.accent
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
                    color: root.accent
                    opacity: 1.0
                    antialiasing: true
                }
            }
        }
    }
}
