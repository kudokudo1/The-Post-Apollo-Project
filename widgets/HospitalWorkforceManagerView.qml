import QtQuick
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalWorkforceManagerPolicy.js" as ManagementPolicy
import "../services/hospital/HospitalWorkforceJobActivationPolicy.js" as JobActivationPolicy

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
    property string selectedDraftAssignmentId: ""
    property bool assignmentListVerified: false
    property string activationArmKey: ""
    property int jobPage: 0
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
    readonly property var activationPlan: JobActivationPolicy.review({
        roomId: root.selectedRoomId,
        assignmentId: root.selectedDraftAssignmentId,
        rooms: root.rooms,
        sessions: root.sessions,
        assignments: inlineAssignment.assignments,
        roomsLoaded: root.roomsLoaded,
        sessionsLoaded: root.sessionsLoaded,
        assignmentsLoaded: root.assignmentListVerified,
        assignmentsLoading: inlineAssignment.loading || inlineAssignment.writing,
        registryError: root.registryError,
        assignmentError: inlineAssignment.lastError
    })
    readonly property string activationSignature: JSON.stringify({
        plan: root.activationPlan,
        rooms: root.rooms,
        sessions: root.sessions,
        assignments: inlineAssignment.assignments
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
        activationArmKey = "";
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
        const detail = kind === "CREATE_WORKER"
            ? p.name + " // ROLE " + p.role + " // ID " + p.id
            : kind === "CREATE_ROOM"
            ? p.name + " // PATIENT " + p.repository + " // ID " + p.id
            : kind === "RETIRE"
            ? "WORKER " + p.id + " // PRESERVE ALL ROOM/SESSION HISTORY"
            : "ROOM " + p.roomId + " // " + jobTitleField.value
                + " // AUTH " + p.permissions.join(", ");
        outcome = "REVIEW READY // " + detail
            + " // CONFIRM SAVES ONLY THIS RECORD";
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
    function reviewActivation() {
        activationArmKey = "";
        if (!root.active || root.registryBusy || !root.activationPlan.ready) {
            outcome = "ACTIVATION HOLD // " + (root.registryBusy
                ? "PX registry refreshing"
                : root.activationPlan.blockers.join(" // "));
            return false;
        }
        activationArmKey = activationSignature;
        outcome = "REVIEW // ACTIVATE DRAFT #" + root.activationPlan.assignmentId
            + " // " + root.activationPlan.title
            + " // ROOM " + root.activationPlan.roomId
            + " // READ ONLY // NO AI START";
        return true;
    }
    function confirmActivation() {
        if (!root.active || root.registryBusy
                || !root.activationPlan.ready
                || !activationArmKey
                || activationArmKey !== activationSignature
                || inlineAssignment.writing || inlineAssignment.loading) {
            activationArmKey = "";
            outcome = "ACTIVATION REFUSED // Reload and review the selected Room / job";
            return false;
        }
        const id = root.activationPlan.assignmentId;
        activationArmKey = "";
        const ok = inlineAssignment.activateAssignment(id);
        outcome = ok ? "PX ACTIVATING DRAFT #" + id + " // NO AI LAUNCH"
            : "ACTIVATION REFUSED // " + inlineAssignment.lastError;
        return ok;
    }

    onSelectedRoomIdChanged: {
        disarm();
        assignmentListVerified = false;
        selectedDraftAssignmentId = "";
        jobPage = 0;
    }
    onSelectedDraftAssignmentIdChanged: activationArmKey = ""
    onActiveChanged: {
        disarm();
        if (active)
            Qt.callLater(function() {
                if (root.active && !roomRepositoryField.value)
                    roomRepositoryField.value = root.suggestedRepository;
            });
    }
    onRoomsChanged: disarm()
    onSessionsChanged: disarm()
    onRegistryErrorChanged: disarm()
    onAssignmentListVerifiedChanged: activationArmKey = ""

    Connections {
        target: root.doctorService
        function onSavingChanged() {
            if (root.doctorService && !root.doctorService.saving
                    && root.doctorService.lastError && root.pendingKind) {
                root.outcome = "PX WORKER REFUSED // " + root.doctorService.lastError;
                root.pendingKind = "";
            }
        }
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
            root.assignmentListVerified = false;
            root.activationArmKey = "";
            if (roomId) Qt.callLater(refresh);
        }
        onAssignmentsRefreshed: {
            root.assignmentListVerified = !loading && !lastError
                && roomId === root.selectedRoomId;
            root.activationArmKey = "";
        }
        onAssignmentActivated: function(result) {
            const assignment = (result || {}).assignment || {};
            const room = (result || {}).room || {};
            if (String(assignment.id || "") !== root.selectedDraftAssignmentId
                    || String(assignment.roomId || "") !== root.selectedRoomId
                    || String(room.id || "") !== root.selectedRoomId
                    || String(assignment.status || "") !== "ACTIVE"
                    || String(room.assignmentId || "")
                        !== root.selectedDraftAssignmentId) {
                root.outcome = "ACTIVATION RESPONSE MISMATCH // REFRESH ROOM";
            } else {
                root.outcome = "JOB ACTIVE // #" + assignment.id
                    + " // ROOM " + root.selectedRoomId
                    + " // NO AI LAUNCHED";
            }
            root.rosterRefreshRequested();
            root.assignmentListVerified = false;
        }
        onAssignmentSaved: function(assignment) {
            root.outcome = "DRAFT JOB SAVED // #" + String(assignment.id || "")
                + " // NOT ACTIVATED // NO AI TURN";
            jobTitleField.value = "";
            jobGoalField.value = "";
            root.selectedDraftAssignmentId = String(assignment.id || "");
            root.assignmentListVerified = false;
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
        GohuText {
            width: parent.width
            visible: !!root.doctorService && !!root.doctorService.lastError
            text: root.doctorService ? root.doctorService.lastError : ""
            font.pixelSize: 9
            color: Colors.red
            wrapMode: Text.Wrap
        }
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
        Rectangle {width:root.width; height:2; color:Colors.magenta}
        GohuText {
            width: parent.width
            text: "SAVED JOBS // CHOOSE READ-ONLY DRAFT TO ACTIVATE"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "ACTIVATE marks a job ACTIVE and links it to this Room. It does NOT start an AI. Existing active jobs and occupied Rooms are held for ORDERS."
            color: Colors.blue
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
        Repeater {
            model: inlineAssignment.assignments.slice(
                root.jobPage * root.pageSize,
                (root.jobPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 34
                color: Colors.black
                border.width: 1
                border.color: root.selectedDraftAssignmentId
                    === String(modelData.id || "") ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: "#" + String(modelData.id || "")
                        + " // " + String(modelData.status || "UNKNOWN")
                        + " // " + String(modelData.title || "UNTITLED")
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectedDraftAssignmentId
                        = String(modelData.id || "")
                }
            }
        }
        ManagerPageRow {
            currentPage: root.jobPage
            count: inlineAssignment.assignments.length
            onPrevious: root.jobPage--
            onNext: root.jobPage++
        }
        GohuText {
            width: parent.width
            text: root.activationPlan.ready
                ? "READY FOR REVIEW // #" + root.activationPlan.assignmentId
                    + " // " + root.activationPlan.title
                    + " // AUTH READ"
                : "ACTIVATION HOLD // " + root.activationPlan.blockers.join(" // ")
            color: root.activationPlan.ready ? Colors.cyan : Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }
        Row {
            width: parent.width
            spacing: 6
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 30
                label: "REVIEW ACTIVE"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.active && !inlineAssignment.loading
                onTriggered: root.reviewActivation()
            }
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 30
                label: "CONFIRM ACTIVE"
                accent: Colors.green
                contentGlowEnabled: false
                enabledAction: root.active && root.activationArmKey !== ""
                onTriggered: root.confirmActivation()
            }
        }
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
        id: confirmRow
        property string kind: ""
        property bool caution: false
        width: root.width
        spacing: 6
        HospitalActionButton {
            width: (parent.width - 6) / 2
            height: 30
            label: "REVIEW"
            accent: confirmRow.caution ? Colors.orange : Colors.cyan
            contentGlowEnabled: false
            enabledAction: !root.registryBusy
            onTriggered: root.review(confirmRow.kind)
        }
        HospitalActionButton {
            width: (parent.width - 6) / 2
            height: 30
            label: confirmRow.caution ? "CONFIRM RELEASE" : "CONFIRM SAVE"
            accent: confirmRow.caution ? Colors.red : Colors.green
            destructive: confirmRow.caution
            contentGlowEnabled: false
            enabledAction: root.armedKind === confirmRow.kind && root.armedKey !== ""
            onTriggered: root.confirm(confirmRow.kind)
        }
    }

    component ManagerPageRow: Row {
        id: pageRow
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
            enabledAction: pageRow.currentPage > 0
            onTriggered: pageRow.previous()
        }
        GohuText {
            width: parent.width - 148
            height: parent.height
            text: "PAGE " + (pageRow.currentPage + 1)
                + " // " + pageRow.count + " RECORDS"
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
            enabledAction: (pageRow.currentPage + 1) * root.pageSize < pageRow.count
            onTriggered: pageRow.next()
        }
    }

    component ManagerField: Column {
        id: managerField
        property string caption: ""
        property alias value: input.text
        width: root.width
        spacing: 3
        height: 43
        GohuText {
            text: managerField.caption
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
        id: managerArea
        property string caption: ""
        property alias value: edit.text
        width: root.width
        spacing: 3
        height: 94
        GohuText {
            text: managerArea.caption
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
