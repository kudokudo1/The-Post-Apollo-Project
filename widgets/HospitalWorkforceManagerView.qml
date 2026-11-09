import QtQuick
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalWorkforceManagerPolicy.js" as ManagementPolicy

// Collapsible content inside SURGERY → SHOW WORKERS, not a new Hospital route.
// All writes require a separate operator REVIEW and CONFIRM. No AI turns.
Column {
    id: root
    property bool active: false
    property var doctorService: null
    property var rooms: []
    property var sessions: []
    property bool roomsLoaded: false
    property bool sessionsLoaded: false
    property string registryError: ""
    property bool registryBusy: false
    property string suggestedRepository: ""
    property string mode: "WORKER"
    property string workerRole: "INT"
    property string workerId: makeId("worker")
    property string roomId: makeId("room")
    property string selectedDoctorId: ""
    property string selectedRoomId: ""
    property int workerPage: 0
    property int roomPage: 0
    property string armedKind: ""
    property string armedKey: ""
    property string outcome: ""
    property string pendingKind: ""
    readonly property int pageSize: 5
    readonly property var doctors: doctorService
        && Array.isArray(doctorService.doctors) ? doctorService.doctors : []
    readonly property var workerPlan: ManagementPolicy.worker({
        id: root.workerId, name: workerNameField.value,
        role: root.workerRole, doctors: root.doctors, rooms: root.rooms,
        sessions: root.sessions, doctorsLoaded: !!root.doctorService && root.doctorService.loaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        registryError: root.registryError
    })
    readonly property var roomPlan: ManagementPolicy.room({
        id: root.roomId, name: roomNameField.value,
        repository: roomRepositoryField.value, doctors: root.doctors,
        rooms: root.rooms, sessions: root.sessions,
        doctorsLoaded: !!root.doctorService && root.doctorService.loaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        registryError: root.registryError
    })
    readonly property var retirePlan: ManagementPolicy.retirement({
        doctorId: root.selectedDoctorId, doctors: root.doctors,
        rooms: root.rooms, sessions: root.sessions,
        doctorsLoaded: !!root.doctorService && root.doctorService.loaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        registryError: root.registryError
    })
    readonly property var jobPlan: ManagementPolicy.assignment({
        roomId: root.selectedRoomId, rooms: root.rooms, sessions: root.sessions,
        doctorsLoaded: !!root.doctorService && root.doctorService.loaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        registryError: root.registryError,
        title: jobTitleField.value, goal: jobGoalField.value,
        permissions: jobPermissionsField.value
    })
    signal rosterRefreshRequested()

    width: parent ? parent.width : 350
    height: visible ? implicitHeight : 0
    spacing: 8
    visible: active

    function makeId(prefix) {
        return prefix + "-" + Date.now().toString(36)
            + "-" + Math.floor(Math.random() * 0x7fffffff).toString(36)
            + "-" + Math.floor(Math.random() * 0x7fffffff).toString(36);
    }
    function disarm() {
        armedKind = "";
        armedKey = "";
    }
    function selectMode(value) {
        if (mode === value) return;
        mode = value;
        disarm();
        outcome = "";
        if (value === "ROOM" && !roomRepositoryField.value)
            roomRepositoryField.value = suggestedRepository;
    }
    function planFor(kind) {
        return kind === "CREATE_WORKER" ? workerPlan
             : kind === "CREATE_ROOM" ? roomPlan
             : kind === "RETIRE" ? retirePlan : jobPlan;
    }
    function signature(kind) {
        const p = planFor(kind);
        return JSON.stringify({
            kind: kind, plan: p,
            name: kind === "CREATE_WORKER" ? workerNameField.value
                : kind === "CREATE_ROOM" ? roomNameField.value : "",
            title: jobTitleField.value,
            goal: jobGoalField.value,
            constraints: jobConstraintsField.value,
            done: jobDoneField.value,
            checklist: jobChecklistField.value
        });
    }
    function review(kind) {
        disarm();
        const p = planFor(kind);
        if (registryBusy || !p.ready) {
            outcome = "HOLD // " + (registryBusy
                ? "Refreshing PX registry"
                : p.blockers.join(" // "));
            return false;
        }
        if (kind === "RETIRE" && root.doctors.some(function(d) {
            return String(d.id || "") === root.selectedDoctorId
                && String(d.status || "").toUpperCase() === "RELEASED";
        })) {
            outcome = "HOLD // Worker already released";
            return false;
        }
        armedKind = kind;
        armedKey = signature(kind);
        outcome = "REVIEW READY // " + kind
            + " // confirm only if these names, target and permissions are correct";
        return true;
    }
    function confirm(kind) {
        const p = planFor(kind);
        if (registryBusy || !p.ready || armedKind !== kind
                || armedKey !== signature(kind)) {
            disarm();
            outcome = "REFUSED // Selection, permissions or registry changed; review again";
            return false;
        }
        disarm(); // one-shot, even when PX refuses
        if (kind === "CREATE_WORKER" || kind === "RETIRE") {
            if (!doctorService || doctorService.saving) {
                outcome = "REFUSED // DOCTOR WRITER BUSY";
                return false;
            }
            pendingKind = kind;
            const chosen = root.doctors.filter(function(d) {
                return String(d.id || "") === root.selectedDoctorId;
            })[0] || {};
            const ok = kind === "CREATE_WORKER"
                ? doctorService.saveDoctor(p.id, p.name, p.role, "ACTIVE")
                : doctorService.releaseDoctor(chosen.id);
            outcome = ok ? "SAVING // " + kind : "REFUSED // PX WORKER WRITER";
            if (!ok) pendingKind = "";
            return ok;
        }
        if (kind === "CREATE_ROOM") {
            const ok = roomCreate.create(p);
            outcome = ok ? "CREATING ROOM RECORD // NO AI SESSION"
                         : roomCreate.lastError;
            return ok;
        }
        if (inlineAssignment.writing) {
            outcome = "REFUSED // ASSIGNMENT WRITER BUSY";
            return false;
        }
        const ok = inlineAssignment.createAssignment(
            jobTitleField.value, jobGoalField.value,
            jobConstraintsField.value, jobDoneField.value,
            p.permissions.join(", "), jobChecklistField.value,
            "", "PLANNING"
        );
        outcome = ok ? "SAVING DRAFT JOB // NOT ACTIVATED"
                     : inlineAssignment.lastError;
        return ok;
    }
    onActiveChanged: {
        disarm();
        if (active && !roomRepositoryField.value)
            roomRepositoryField.value = suggestedRepository;
    }
    onRoomsChanged: disarm()
    onSessionsChanged: disarm()
    onRegistryErrorChanged: disarm()

    Connections {
        target: root.doctorService
        function onDoctorSaved(doctor) {
            root.outcome = "PX SAVED // " + String(doctor.name || doctor.id)
                + " // " + root.pendingKind
                + " // NO AI TURN OR SESSION";
            if (root.pendingKind === "CREATE_WORKER") {
                workerNameField.value = "";
                root.workerId = root.makeId("worker");
            }
            root.pendingKind = "";
            root.rosterRefreshRequested();
        }
    }
    HospitalWorkforceRoomCreateService {
        id: roomCreate
        onCreated: function(room) {
            root.outcome = roomCreate.lastStatus
                + " // " + String((room || {}).id || "");
            root.selectedRoomId = String((room || {}).id || "");
            root.roomId = root.makeId("room");
            roomNameField.value = "";
            root.rosterRefreshRequested();
        }
    }
    HospitalAssignmentService {
        id: inlineAssignment
        roomId: root.selectedRoomId
        onRoomIdChanged: {
            if (roomId) Qt.callLater(refresh);
        }
        onAssignmentSaved: function(assignment) {
            root.outcome = "DRAFT JOB SAVED // #" + String(assignment.id || "")
                + " // NOT ACTIVATED // NO AI TURN";
            jobTitleField.value = "";
            jobGoalField.value = "";
            root.rosterRefreshRequested();
            refresh();
        }
    }

    Rectangle {
        width: parent.width
        height: 40
        color: Colors.black
        border.width: 1
        border.color: Colors.magenta
        GohuText {
            anchors.fill: parent
            anchors.margins: 6
            text: "WORKFORCE // SURGERY CONTROL\nRecords only. Nothing launches an AI. REVIEW then CONFIRM to save."
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.Wrap
        }
    }
    Row {
        width: parent.width
        spacing: 5
        Repeater {
            model: [
                {label:"WORKERS", code:"WORKER"},
                {label:"NEW ROOM", code:"ROOM"},
                {label:"JOB", code:"JOB"}
            ]
            HospitalActionButton {
                required property var modelData
                width: (root.width - 10) / 3
                height: 30
                label: modelData.label
                accent: root.mode === modelData.code ? Colors.magenta : Colors.cyan
                selectedAction: root.mode === modelData.code
                contentGlowEnabled: false
                onTriggered: root.selectMode(modelData.code)
            }
        }
    }

    // WORKERS: Register one ordinary worker or release an unassigned one.
    Column {
        width: parent.width
        spacing: 7
        visible: root.mode === "WORKER"
        GohuText {
            width: parent.width
            text: "REGISTER WORKER // ORGANIZATIONAL ROLE, NOT GIT PERMISSION"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
        ManagerField {
            id: workerNameField
            caption: "NEW WORKER NAME"
        }
        Row {
            width: parent.width
            spacing: 4
            Repeater {
                model: [
                    {code:"INT",name:"INTERN"},
                    {code:"NRS",name:"NURSE"},
                    {code:"DOC",name:"DOCTOR"}
                ]
                HospitalActionButton {
                    required property var modelData
                    width: (root.width - 8) / 3
                    height: 28
                    label: modelData.name
                    accent: root.workerRole === modelData.code
                        ? Colors.magenta : Colors.cyan
                    selectedAction: root.workerRole === modelData.code
                    contentGlowEnabled: false
                    onTriggered: {
                        root.workerRole = modelData.code;
                        root.disarm();
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            text: "ID // " + root.workerId + "\nNo Room, Session, Provider or permission assigned."
            font.pixelSize: 8
            color: Colors.blue
            wrapMode: Text.WrapAnywhere
        }
        ManagerConfirmRow { kind: "CREATE_WORKER" }
        Rectangle {width:parent.width; height:2; color:Colors.magenta}
        GohuText {
            width: parent.width
            text: "EXISTING WORKERS // SELECT TO RETIRE WHEN UNASSIGNED"
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.Wrap
        }
        Repeater {
            model: root.doctors.slice(root.workerPage * root.pageSize,
                                      (root.workerPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 28
                color: Colors.black
                border.width: 1
                border.color: root.selectedDoctorId === String(modelData.id || "")
                    ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    font.pixelSize: 9
                    text: String(modelData.name || modelData.id || "")
                        + " // " + String(modelData.role || "")
                        + " // " + String(modelData.status || "")
                    color: Colors.white
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.selectedDoctorId = String(modelData.id || "");
                        root.disarm();
                    }
                }
            }
        }
        ManagerPageRow {
            currentPage: root.workerPage
            count: root.doctors.length
            onPrevious: root.workerPage--
            onNext: root.workerPage++
        }
        GohuText {
            width: parent.width
            text: root.selectedDoctorId
                ? "SELECTED // " + root.selectedDoctorId
                    + " // " + (root.retirePlan.ready
                        ? "RELEASE ELIGIBLE" : root.retirePlan.blockers.join(" // "))
                : "No worker selected for release"
            font.pixelSize: 9
            color: root.retirePlan.ready ? Colors.cyan : Colors.orange
            wrapMode: Text.WrapAnywhere
        }
        ManagerConfirmRow {kind:"RETIRE"; caution:true}
    }

    // ROOMS: creates a durable EMPTY Room, not a Git worktree or worker.
    Column {
        width: parent.width
        spacing: 7
        visible: root.mode === "ROOM"
        GohuText {
            width: parent.width
            text: "NEW ROOM // SAVED JOB CONTAINER ONLY"
            color: Colors.orange
            font.pixelSize: 9
        }
        ManagerField {id:roomNameField; caption:"ROOM NAME"}
        ManagerField {id:roomRepositoryField; caption:"PATIENT // GITHUB OWNER/REPO"}
        GohuText {
            width: parent.width
            text: "ID // " + root.roomId
                + "\nNo Doctor, Assignment, Provider, branch, Bed or Session will be attached."
            font.pixelSize: 8
            color: Colors.blue
            wrapMode: Text.WrapAnywhere
        }
        ManagerConfirmRow {kind:"CREATE_ROOM"}
        GohuText {
            width: parent.width
            text: roomCreate.creating ? roomCreate.lastStatus
                : roomCreate.lastError || roomCreate.lastStatus
            color: roomCreate.lastError ? Colors.orange : Colors.cyan
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
    }

    // JOB: a draft Assignment is saved INSIDE the selected registered Room.
    Column {
        width: parent.width
        spacing: 7
        visible: root.mode === "JOB"
        GohuText {
            width: parent.width
            text: "NEW JOB // CHOOSE EXACT REGISTERED ROOM"
            color: Colors.orange
            font.pixelSize: 9
        }
        Repeater {
            model: root.rooms.slice(root.roomPage * root.pageSize,
                                    (root.roomPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 30
                color: Colors.black
                border.width: 1
                border.color: root.selectedRoomId
                    === String(modelData.id || modelData.roomId || "")
                    ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: String(modelData.displayName || modelData.team
                                 || modelData.id || "ROOM")
                        + " // " + String(modelData.repository || "NO PATIENT")
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.selectedRoomId = String(modelData.id || modelData.roomId || "");
                        root.disarm();
                    }
                }
            }
        }
        ManagerPageRow {
            currentPage: root.roomPage
            count: root.rooms.length
            onPrevious: root.roomPage--
            onNext: root.roomPage++
        }
        GohuText {
            width: parent.width
            text: "ROOM // " + (root.selectedRoomId || "NOT SELECTED")
                + " // Assignment saved in PLANNING, not activated"
            color: Colors.blue
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }
        ManagerField {id:jobTitleField; caption:"JOB TITLE"}
        ManagerArea {id:jobGoalField; caption:"GOAL"}
        ManagerArea {id:jobConstraintsField; caption:"CONSTRAINTS / FILE OWNERSHIP"}
        ManagerArea {id:jobDoneField; caption:"DEFINITION OF DONE"}
        ManagerArea {id:jobChecklistField; caption:"CHECKLIST"}
        ManagerField {id:jobPermissionsField; caption:"PERMISSIONS"; Component.onCompleted:value="READ"}
        GohuText {
            width: parent.width
            text: "READ only is the default. Permissions are PX command guards, not a filesystem sandbox. COMMIT, PUSH and OPEN_PR need separate approval."
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.Wrap
        }
        ManagerConfirmRow {kind:"CREATE_JOB"}
        GohuText {
            width: parent.width
            visible: inlineAssignment.lastError.length > 0
            text: inlineAssignment.lastError
            font.pixelSize: 9
            color: Colors.red
            wrapMode: Text.Wrap
        }
    }
    Rectangle {
        width: parent.width
        height: Math.max(30, statusText.implicitHeight + 14)
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        GohuText {
            id: statusText
            anchors.fill: parent
            anchors.margins: 6
            text: root.outcome || "Choose an action; REVIEW never writes to PX."
            color: root.outcome.indexOf("HOLD") >= 0
                || root.outcome.indexOf("REFUSED") >= 0 ? Colors.orange : Colors.cyan
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }
    }

    component ManagerConfirmRow: Row {
        property string kind: ""
        property bool caution: false
        width: root.width
        spacing: 6
        HospitalActionButton {
            width: (parent.width - 6) / 2
            height: 30
            label: "REVIEW"
            accent: caution ? Colors.orange : Colors.cyan
            contentGlowEnabled: false
            enabledAction: !root.registryBusy
            onTriggered: root.review(kind)
        }
        HospitalActionButton {
            width: (parent.width - 6) / 2
            height: 30
            label: caution ? "CONFIRM RELEASE" : "CONFIRM SAVE"
            accent: caution ? Colors.red : Colors.green
            destructive: caution
            contentGlowEnabled: false
            enabledAction: root.armedKind === kind && root.armedKey !== ""
            onTriggered: root.confirm(kind)
        }
    }

    component ManagerPageRow: Row {
        property int currentPage: 0
        property int count: 0
        signal previous()
        signal next()
        width: root.width
        spacing: 6
        height: 27
        HospitalActionButton {
            width: 68
            height: parent.height
            label: "PREV"
            compactIcon: "<"
            contentGlowEnabled: false
            enabledAction: currentPage > 0
            onTriggered: previous()
        }
        GohuText {
            width: parent.width - 148
            height: parent.height
            text: "PAGE " + (currentPage + 1)
                + " // " + count + " RECORDS"
            color: Colors.blue
            font.pixelSize: 9
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        HospitalActionButton {
            width: 68
            height: parent.height
            label: "NEXT"
            compactIcon: ">"
            contentGlowEnabled: false
            enabledAction: (currentPage + 1) * root.pageSize < count
            onTriggered: next()
        }
    }

    component ManagerField: Column {
        property string caption: ""
        property alias value: input.text
        width: root.width
        spacing: 3
        height: 43
        GohuText {
            text: caption
            color: Colors.blue
            font.pixelSize: 9
            height: 12
            width: parent.width
        }
        Rectangle {
            width: parent.width
            height: 28
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta
            TextInput {
                id: input
                anchors.fill: parent
                anchors.leftMargin: 7
                anchors.rightMargin: 7
                color: Colors.white
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                selectByMouse: true
                maximumLength: 256
                verticalAlignment: TextInput.AlignVCenter
                clip: true
            }
        }
    }

    component ManagerArea: Column {
        property string caption: ""
        property alias value: edit.text
        width: root.width
        spacing: 3
        height: 94
        GohuText {
            text: caption
            color: Colors.blue
            font.pixelSize: 9
            height: 12
            width: parent.width
        }
        Rectangle {
            width: parent.width
            height: 79
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta
            TextEdit {
                id: edit
                anchors.fill: parent
                anchors.margins: 6
                color: Colors.white
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                clip: true
            }
        }
    }
}
