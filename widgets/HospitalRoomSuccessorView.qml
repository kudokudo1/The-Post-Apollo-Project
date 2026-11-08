import QtQuick
import qs.components
import "../services/hospital/HospitalRoomSuccessorPreviewPolicy.js" as SuccessorPolicy

// Guided Doctor succession, PREVIEW ONLY.
// Does not bind staffing, release a Session, launch a Provider or send a turn.
Item {
    id: root
    property bool active: false
    property string roomId: ""
    property var overview: ({})
    property var snapshot: ({})
    property var roomData: ({})
    property var doctors: []
    property var providers: []
    property var rooms: []
    property var sessions: []
    property bool doctorsLoaded: false
    property bool providersLoaded: false
    property bool roomsLoaded: false
    property bool sessionsLoaded: false
    property string sourceError: ""
    property string successorDoctorId: ""
    property string successorProviderId: ""
    property int doctorPage: 0
    property int providerPage: 0
    readonly property int pageSize: 8
    property bool prepared: false
    readonly property var plan: SuccessorPolicy.preview({
        roomId: root.roomId,
        overview: root.overview,
        snapshot: root.snapshot,
        roomData: root.roomData,
        rooms: root.rooms, sessions: root.sessions,
        doctors: root.doctors, providers: root.providers,
        doctorsLoaded: root.doctorsLoaded, providersLoaded: root.providersLoaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        sourceError: root.sourceError,
        doctorId: root.successorDoctorId, providerId: root.successorProviderId
    })
    readonly property string briefing: prepared
        ? SuccessorPolicy.briefing({
            roomId: root.roomId, overview: root.overview,
            snapshot: root.snapshot, roomData: root.roomData,
            rooms: root.rooms, sessions: root.sessions,
            doctors: root.doctors, providers: root.providers,
            doctorsLoaded: root.doctorsLoaded,
            providersLoaded: root.providersLoaded,
            roomsLoaded: root.roomsLoaded,
            sessionsLoaded: root.sessionsLoaded,
            sourceError: root.sourceError,
            doctorId: root.successorDoctorId,
            providerId: root.successorProviderId
        }) : ""

    signal returnRequested()
    signal refreshRequested()

    onRoomIdChanged: {
        successorDoctorId = "";
        successorProviderId = "";
        doctorPage = 0;
        providerPage = 0;
        prepared = false;
    }
    onSuccessorDoctorIdChanged: prepared = false
    onSuccessorProviderIdChanged: prepared = false
    onOverviewChanged: prepared = false
    onSnapshotChanged: prepared = false
    onSessionsChanged: prepared = false

    Flickable {
        id: recoveryScroll
        anchors.fill: parent
        visible: root.active
        clip: true
        contentWidth: width
        contentHeight: recoveryRows.implicitHeight + 10
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: recoveryRows
            width: recoveryScroll.width
            spacing: 8

            Row {
                width: parent.width
                height: 29
                spacing: 7
                GohuText {
                    width: parent.width - 172
                    height: parent.height
                    text: "RECOVER ROOM // DOCTOR SUCCESSION"
                    font.pixelSize: 12
                    color: Colors.magenta
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                HospitalActionButton {
                    width: 77
                    height: 27
                    label: "REFRESH"
                    compactIcon: "↻"
                    accent: Colors.cyan
                    onTriggered: root.refreshRequested()
                }
                HospitalActionButton {
                    width: 88
                    height: 27
                    label: "BACK"
                    compactIcon: "X"
                    accent: Colors.orange
                    onTriggered: root.returnRequested()
                }
            }
            GohuText {
                width: parent.width
                text: root.plan.status
                font.pixelSize: 11
                color: root.plan.blockers.length ? Colors.orange : Colors.green
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "ROOM // " + root.roomId
                    + "  //  PERSISTENT JOB, REPLACEABLE DOCTOR"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideMiddle
            }
            GohuText {
                width: parent.width
                text: "All selections are local to this preview. No PX transfer, Session mutation, Doctor release, launch or browser-chat attachment occurs here."
                font.pixelSize: 9
                color: Colors.blue
                wrapMode: Text.Wrap
            }
            Repeater {
                model: root.plan.evidence
                GohuText {
                    required property var modelData
                    width: recoveryRows.width
                    text: String(modelData.label || "")
                        + " // " + String(modelData.value || "")
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideMiddle
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "SELECT SUCCESSOR // REGISTERED DOCTORS"
                font.pixelSize: 11
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                visible: root.doctors.length === 0
                text: "NO DOCTORS AVAILABLE IN THE LOADED DIRECTORY"
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.Wrap
            }
            Repeater {
                model: root.doctors.slice(root.doctorPage * root.pageSize,
                    (root.doctorPage + 1) * root.pageSize)
                Rectangle {
                    required property var modelData
                    width: recoveryRows.width
                    height: 30
                    color: Colors.black
                    border.width: 1
                    border.color: root.successorDoctorId === String(modelData.id || "")
                        ? Colors.orange : Colors.magenta
                    GohuText {
                        anchors.fill: parent
                        anchors.margins: 6
                        text: String(modelData.name || modelData.id || "")
                            + " // " + String(modelData.status || "UNKNOWN")
                            + " // " + String(modelData.id || "")
                        color: Colors.white
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.successorDoctorId = String(modelData.id || "")
                    }
                }
            }
            Row {
                width: parent.width
                height: 28
                spacing: 8
                HospitalActionButton {
                    width: 69
                    height: 27
                    label: "PREV"
                    compactIcon: "<"
                    accent: Colors.cyan
                    enabledAction: root.doctorPage > 0
                    onTriggered: root.doctorPage--
                }
                GohuText {
                    width: parent.width - 154
                    height: parent.height
                    text: "DOCTORS // " + root.doctors.length
                        + " // PAGE " + (root.doctorPage + 1)
                    font.pixelSize: 8
                    color: Colors.blue
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                HospitalActionButton {
                    width: 69
                    height: 27
                    label: "NEXT"
                    compactIcon: ">"
                    accent: Colors.cyan
                    enabledAction: (root.doctorPage + 1) * root.pageSize
                        < root.doctors.length
                    onTriggered: root.doctorPage++
                }
            }
            GohuText {
                width: parent.width
                text: "SELECT PROVIDER // REGISTERED RUNTIMES"
                font.pixelSize: 11
                color: Colors.orange
            }
            Repeater {
                model: root.providers.slice(root.providerPage * root.pageSize,
                    (root.providerPage + 1) * root.pageSize)
                Rectangle {
                    required property var modelData
                    width: recoveryRows.width
                    height: 30
                    color: Colors.black
                    border.width: 1
                    border.color: root.successorProviderId === String(modelData.id || "")
                        ? Colors.orange : Colors.magenta
                    GohuText {
                        anchors.fill: parent
                        anchors.margins: 6
                        text: String(modelData.name || modelData.id || "")
                            + " // " + (modelData.available
                                ? "LISTED AVAILABLE" : "UNAVAILABLE")
                            + " // " + String(modelData.id || "")
                        color: Colors.white
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.successorProviderId = String(modelData.id || "")
                    }
                }
            }
            Row {
                width: parent.width
                height: 28
                spacing: 8
                HospitalActionButton {
                    width: 69
                    height: 27
                    label: "PREV"
                    compactIcon: "<"
                    accent: Colors.cyan
                    enabledAction: root.providerPage > 0
                    onTriggered: root.providerPage--
                }
                GohuText {
                    width: parent.width - 154
                    height: parent.height
                    text: "PROVIDERS // " + root.providers.length
                        + " // PAGE " + (root.providerPage + 1)
                    font.pixelSize: 8
                    color: Colors.blue
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                HospitalActionButton {
                    width: 69
                    height: 27
                    label: "NEXT"
                    compactIcon: ">"
                    accent: Colors.cyan
                    enabledAction: (root.providerPage + 1) * root.pageSize
                        < root.providers.length
                    onTriggered: root.providerPage++
                }
            }
            Rectangle {
                width: parent.width
                height: 2
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "REPLACEMENT BLOCKERS // " + root.plan.blockers.length
                font.pixelSize: 11
                color: root.plan.blockers.length ? Colors.orange : Colors.cyan
            }
            Repeater {
                model: root.plan.blockers.slice(0, 12)
                GohuText {
                    required property string modelData
                    width: recoveryRows.width
                    text: "! " + modelData
                    font.pixelSize: 9
                    color: Colors.orange
                    wrapMode: Text.Wrap
                }
            }
            Repeater {
                model: root.plan.warnings.slice(0, 8)
                GohuText {
                    required property string modelData
                    width: recoveryRows.width
                    text: "NOTE // " + modelData
                    font.pixelSize: 9
                    color: Colors.blue
                    wrapMode: Text.Wrap
                }
            }
            GohuText {
                width: parent.width
                text: "REQUIRED TRANSFER STEPS"
                font.pixelSize: 11
                color: Colors.orange
            }
            Repeater {
                model: root.plan.actions
                GohuText {
                    required property string modelData
                    width: recoveryRows.width
                    text: "• " + modelData
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.Wrap
                }
            }
            HospitalActionButton {
                width: parent.width
                height: 33
                label: "PREPARE HANDOFF BRIEF // NO WRITES"
                compactIcon: "ROOM"
                accent: Colors.magenta
                enabledAction: root.plan.contextAvailable
                onTriggered: root.prepared = true
            }
            GohuText {
                width: parent.width
                visible: root.prepared
                text: "READ-ONLY SUCCESSOR BRIEF // REBUILT FROM ROOM EVIDENCE"
                color: Colors.cyan
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                visible: root.prepared
                text: root.briefing
                color: Colors.white
                font.pixelSize: 9
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "TRANSFER NOT AUTHORIZED // This summary is not an execution packet. PX must independently rebuild current context and recheck Session, Bed and staffing authority at final admission."
                font.pixelSize: 9
                color: Colors.blue
                wrapMode: Text.Wrap
            }
        }
    }

    NeonScrollBar {
        flickable: recoveryScroll
        handleStyle: "star"
        visible: root.active && scrollable
    }
}
