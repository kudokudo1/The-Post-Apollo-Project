import QtQuick

QtObject {
    id: processPresentationState

    // Reusable live-process presentation state shared by task-manager views.
    // Telemetry acquisition remains in ProcessTelemetry; this object owns only
    // the rolling histories and presentation revisions derived from samples.

    property int taskHistoryPid: 0
    property bool taskRestoringSelection: false

    property var taskCpuHistory: []
    property var taskMemHistory: []

    readonly property int taskHistoryLimit: 132
    readonly property int taskGraphScrollDuration: 920
    readonly property int taskMiniGraphScrollDuration: 1080
    readonly property int taskCombiRenderPointLimit: taskHistoryLimit

    property var taskMiniCpuHistories: ({})
    property var taskMiniHunterMetricHistories: ({})

    property var taskHunterDetailHistories: ({
        cpu: [],
        mem: [],
        io: [],
        age: [],
        combined: []
    })
    property int taskHunterDetailHistoryRevision: 0

    // Favorites survive PID turnover, so their mini CPU histories also keep a
    // persistent-identity keyed form alongside the exact-PID histories.
    property var taskMiniCpuIdentityHistories: ({})

    // Explicit revisions are part of the presentation contract. QML does not
    // reliably invalidate every nested JS-array binding when an object-held
    // history is replaced.
    property int taskMiniHistoryRevision: 0
    property int taskMiniDisplayRevision: 0

    readonly property int taskMiniHistoryLimit: 48
    property int taskMiniPreloadSnapshots: 0
    readonly property int taskMiniPreloadTarget: taskMiniHistoryLimit

    function resetDetailHistories() {
        taskHistoryPid = 0;
        taskCpuHistory = [];
        taskMemHistory = [];
        taskHunterDetailHistories = ({
            cpu: [],
            mem: [],
            io: [],
            age: [],
            combined: []
        });
        taskHunterDetailHistoryRevision += 1;
    }
}
