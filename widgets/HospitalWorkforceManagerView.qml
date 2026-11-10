import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalWorkforceManagerPolicy.js" as ManagementPolicy
import "../services/hospital/HospitalWorkforceJobActivationPolicy.js" as JobActivationPolicy
import "../services/hospital/HospitalWorkforceStaffingPolicy.js" as StaffingPolicy
import "../services/hospital/HospitalFirstBedVerificationPolicy.js" as BedPolicy
import "../services/hospital/HospitalGitHubOwnerPolicy.js" as GitHubOwnerPolicy
import "../services/hospital/HospitalConversationIntakePolicy.js" as ConversationIntakePolicy
import "../services/hospital/HospitalDictationTextPolicy.js" as DictationTextPolicy

// Collapsible content inside SURGERY → SHOW WORKERS, not a new Hospital route.
// All writes require a separate operator REVIEW and CONFIRM. No AI turns.
Column {
    id: root
    property bool active: false
    property var doctorService: null
    property var providerService: null
    property var speechInputService: null
    property bool otherVoiceBusy: false
    // One active microphone for long-form fields; no auto submit or save.
    property string dictationField: ""
    property string dictationMode: ""
    property string dictationOriginalText: ""
    property string dictationFeedbackField: ""
    property string dictationFeedback: ""
    property var rooms: []
    property var sessions: []
    property var knownBeds: []
    property bool bedsDiscovering: false
    property string bedDiscoveryError: ""
    property string selectedBedPath: ""
    property int staffBedPage: 0
    property bool roomsLoaded: false
    property bool sessionsLoaded: false
    property string registryError: ""
    property bool registryBusy: false
    property string suggestedRepository: ""
    property bool roomOwnerManuallyEdited: false
    property bool roomRepositoryManuallyEdited: false
    readonly property string selectedGitHubRepository:
        GitHubOwnerPolicy.compose(roomOwnerField.value, roomRepoField.value)
    readonly property var currentPatientRepository:
        GitHubOwnerPolicy.splitRepository(root.suggestedRepository)
    // Registered Room records supply owner suggestions, not extra credentials.
    readonly property var otherKnownGitHubOwners:
        GitHubOwnerPolicy.ownerOptions(root.rooms, root.suggestedRepository,
            githubOwner.login).filter(function(entry) {
                return entry.label === "USED IN HOSPITAL";
            }).slice(0, 3)
    property string mode: "WORKER"
    // Conversation-style local starter draft; no model or PX invocation.
    property var intakeDraft: ({})
    property string intakeSource: ""
    property string workerRole: "INT"
    property string workerId: makeId("worker")
    property string roomId: makeId("room")
    property string selectedDoctorId: ""
    property string selectedRoomId: ""
    property string selectedStaffDoctorId: ""
    property string selectedStaffProviderId: ""
    property int staffDoctorPage: 0
    property int staffProviderPage: 0
    property int staffRoomPage: 0
    property string staffingReviewKey: ""
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
    readonly property var providers: providerService
        && Array.isArray(providerService.providers) ? providerService.providers : []
    readonly property var selectedStaffingRoom: {
        const rows = root.rooms.filter(function(r) {
            return String((r || {}).id || (r || {}).roomId || "") === root.selectedRoomId;
        });
        return rows.length === 1 ? rows[0] : ({});
    }
    readonly property var bedChoices: BedPolicy.candidateRows({
        room: root.selectedStaffingRoom,
        rooms: root.rooms, roomsLoaded: root.roomsLoaded,
        beds: root.knownBeds
    })
    readonly property var bedPlan: BedPolicy.assess({
        room: root.selectedStaffingRoom,
        rooms: root.rooms, roomsLoaded: root.roomsLoaded,
        sessions: root.sessions, beds: root.knownBeds,
        bedsDiscovering: root.bedsDiscovering,
        selectedPath: root.selectedBedPath,
        evidence: bedProbe.evidence,
        evidenceChecked: bedProbe.verified,
        evidenceBusy: bedProbe.checking
    })
    readonly property var staffingPlan: StaffingPolicy.plan({
        roomId: root.selectedRoomId,
        doctorId: root.selectedStaffDoctorId,
        providerId: root.selectedStaffProviderId,
        rooms: root.rooms, sessions: root.sessions,
        doctors: root.doctors, providers: root.providers,
        assignments: staffingAssignments.assignments,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        doctorsLoaded: !!root.doctorService && root.doctorService.loaded
            && !root.doctorService.refreshing,
        providersLoaded: !!root.providerService && root.providerService.loaded
            && !root.providerService.refreshing,
        assignmentsLoaded: staffingAssignments.loaded
            && staffingAssignments.requestedRoomId === root.selectedRoomId,
        assignmentsLoading: staffingAssignments.loading,
        sourceError: root.registryError
            || (root.doctorService ? root.doctorService.lastError : "")
            || (root.providerService ? root.providerService.lastError : "")
            || staffingAssignments.lastError
    })
    readonly property string staffingSignature: JSON.stringify({
        plan: root.staffingPlan, rooms: root.rooms, sessions: root.sessions,
        assignments: staffingAssignments.assignments,
        doctors: root.doctors, providers: root.providers
    })
    readonly property var workerPlan: ManagementPolicy.worker({
        id: root.workerId, name: workerNameField.value,
        role: root.workerRole, doctors: root.doctors, rooms: root.rooms,
        sessions: root.sessions, doctorsLoaded: !!root.doctorService && root.doctorService.loaded,
        roomsLoaded: root.roomsLoaded, sessionsLoaded: root.sessionsLoaded,
        registryError: root.registryError
    })
    readonly property var roomPlan: ManagementPolicy.room({
        id: root.roomId, name: roomNameField.value,
        repository: root.selectedGitHubRepository, doctors: root.doctors,
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
    signal discoverBedsRequested()
    // Read-only candidate handoff to the existing nested attachment preview.
    // This signal cannot authorize or execute a PX Session mutation.
    signal openRoomRequested(string roomId, var selection)

    width: parent ? parent.width : 350
    height: visible ? implicitHeight : 0
    spacing: 8
    visible: active

    function voiceAreaForKey(key) {
        if (key === "intake") return intakeBriefField;
        if (key === "goal") return jobGoalField;
        if (key === "constraints") return jobConstraintsField;
        if (key === "done") return jobDoneField;
        if (key === "checklist") return jobChecklistField;
        return null;
    }
    function toggleDictation(key) {
        const svc = root.speechInputService;
        const field = root.voiceAreaForKey(key);
        if (!root.active || !svc || !field || !key
                || (root.mode !== "SETUP" && root.mode !== "JOB"))
            return false;
        if (svc.recording) {
            if (root.dictationField !== key)
                return false;
            const stopping = svc.stopRecording(false);
            if (stopping)
                root.dictationFeedback = "STOPPED // TRANSCRIBING LOCALLY // NO SUBMIT";
            return stopping;
        }
        if (svc.busy || root.otherVoiceBusy) {
            root.dictationFeedbackField = key;
            root.dictationFeedback = "MIC BUSY // WAIT FOR THE OTHER RECORDING";
            return false;
        }
        root.dictationField = key;
        root.dictationMode = root.mode;
        // A live mic locks just this editor until STOP; CANCEL restores the
        // exact pre-recording text without losing an unrelated form's values.
        root.dictationOriginalText = field.value;
        root.dictationFeedbackField = key;
        root.dictationFeedback = "STARTING MICROPHONE // LOCAL TRANSCRIPTION";
        const started = svc.startRecording();
        if (!started) {
            root.dictationField = "";
            root.dictationMode = "";
            root.dictationFeedback = "MIC UNAVAILABLE // CHECK LOCAL WHISPER AND PIPEWIRE";
        }
        return started;
    }
    function cancelDictation() {
        const target = root.dictationField;
        const field = root.voiceAreaForKey(target);
        if (root.speechInputService && root.speechInputService.busy)
            root.speechInputService.cancel();
        if (field && root.speechInputService
                && root.speechInputService.liveStreaming === true)
            field.value = root.dictationOriginalText;
        root.dictationField = "";
        root.dictationMode = "";
        root.dictationOriginalText = "";
        if (target) {
            root.dictationFeedbackField = target;
            root.dictationFeedback = "DICTATION CANCELLED // ORIGINAL TEXT PRESERVED";
        }
    }
    function acceptLivePhrase(text) {
        const key = root.dictationField;
        const field = root.voiceAreaForKey(key);
        if (!root.active || !field || root.mode !== root.dictationMode
                || (key === "intake" ? root.mode !== "SETUP" : root.mode !== "JOB"))
            return false;
        const result = DictationTextPolicy.appendTranscription(
            field.value, text, field.voiceMaxLength);
        root.dictationFeedbackField = key;
        if (!result.accepted) {
            if (result.reason.indexOf("TEXT LIMIT") >= 0
                    && root.speechInputService.recording)
                root.speechInputService.stopRecording(false);
            root.dictationFeedback = result.reason;
            return false;
        }
        field.value = result.text;
        root.dictationFeedback = "LIVE TEXT // EDIT AFTER STOP // NEVER AUTO SUBMITTED";
        return true;
    }
    function finishLiveDictation() {
        if (!root.dictationField)
            return;
        const key = root.dictationField;
        const field = root.voiceAreaForKey(key);
        root.dictationField = "";
        root.dictationMode = "";
        root.dictationOriginalText = "";
        root.dictationFeedbackField = key;
        root.dictationFeedback = "LIVE TRANSCRIPT READY // REVIEW BEFORE SUBMIT";
        if (field) field.focusEditorAtEnd();
    }
    function acceptDictation(text) {
        const key = root.dictationField;
        const startedMode = root.dictationMode;
        root.dictationField = "";
        root.dictationMode = "";
        const field = root.voiceAreaForKey(key);
        if (!root.active || !field
                || startedMode !== root.mode
                || (key !== "intake" && startedMode !== "JOB")
                || (key === "intake" && startedMode !== "SETUP"))
            return false;
        const result = DictationTextPolicy.appendTranscription(
            field.value, text, field.voiceMaxLength);
        root.dictationFeedbackField = key;
        root.dictationFeedback = result.reason;
        if (!result.accepted)
            return false;
        // Append to the CURRENT field text. Concurrent user typing is kept.
        // This is not a form submit, job approval or AI request.
        field.value = result.text;
        field.focusEditorAtEnd();
        return true;
    }
    function makeId(prefix) {
        return prefix + "-" + Date.now().toString(36)
            + "-" + Math.floor(Math.random() * 0x7fffffff).toString(36)
            + "-" + Math.floor(Math.random() * 0x7fffffff).toString(36);
    }
    function disarm() {
        armedKind = "";
        armedKey = "";
        activationArmKey = "";
        staffingReviewKey = "";
    }
    function invalidateIntake() {
        intakeDraft = ({});
        intakeSource = "";
        disarm();
    }
    function draftIntake() {
        root.invalidateIntake();
        if (!root.active || root.mode !== "SETUP") {
            root.outcome = "SETUP HOLD // OPEN CHAT SETUP FIRST";
            return false;
        }
        const candidate = ConversationIntakePolicy.proposal(intakeBriefField.value);
        if (!candidate.ready) {
            root.outcome = "SETUP HOLD // " + candidate.blockers.join(" // ");
            return false;
        }
        root.intakeDraft = candidate;
        root.intakeSource = intakeBriefField.value;
        root.outcome = "LOCAL STARTER DRAFT // NOT AI-GENERATED // REVIEW EACH FIELD";
        return true;
    }
    function applyIntake(section) {
        const p = root.intakeDraft || {};
        if (!root.active || root.mode !== "SETUP" || !p.ready
                || !root.intakeSource
                || root.intakeSource !== intakeBriefField.value) {
            root.invalidateIntake();
            root.outcome = "SETUP REFUSED // DESCRIPTION CHANGED; DRAFT AGAIN";
            return false;
        }
        // These only prefill existing, independently reviewed editors.
        // They never invoke a writer or create/activate a Provider Session.
        if (section === "ROOM") {
            roomNameField.value = p.roomName;
            root.selectMode("ROOM");
        } else if (section === "WORKER") {
            workerNameField.value = p.workerName;
            root.workerRole = p.role;
            root.selectMode("WORKER");
        } else if (section === "JOB") {
            jobTitleField.value = p.title;
            jobGoalField.value = p.goal;
            jobConstraintsField.value = p.constraints;
            jobDoneField.value = p.definitionDone;
            jobChecklistField.value = p.checklist;
            jobPermissionsField.value = "READ";
            root.selectMode("JOB");
        } else {
            return false;
        }
        root.disarm();
        root.outcome = "DRAFT PREFILLED // " + section
            + " // EDIT FIELDS; REVIEW + CONFIRM REQUIRED // NO AI TURN";
        return true;
    }
    function applyRoomSuggestions() {
        // The active Floor's GitHub origin takes priority over account login.
        // Keep any explicit manual edits until the user chooses CURRENT REPO
        // or successfully creates a Room and starts a new form.
        const proposed = GitHubOwnerPolicy.suggestion(root.suggestedRepository,
            githubOwner.login);
        if (!root.roomOwnerManuallyEdited)
            roomOwnerField.value = proposed.owner;
        if (!root.roomRepositoryManuallyEdited)
            roomRepoField.value = proposed.repository;
    }
    function useOwnGitHub() {
        if (!githubOwner.loaded || !githubOwner.login) {
            root.outcome = "GITHUB ACCOUNT NOT VERIFIED // USE PATIENT OR TYPE OWNER";
            return;
        }
        roomOwnerField.value = githubOwner.login;
        root.roomOwnerManuallyEdited = true;
        root.disarm();
        root.outcome = "GITHUB OWNER // @" + githubOwner.login
            + " // REVIEW THE REPOSITORY NAME BEFORE SAVING";
    }
    function useKnownGitHubOwner(owner) {
        const chosen = GitHubOwnerPolicy.part(owner);
        if (!chosen) return false;
        roomOwnerField.value = chosen;
        root.roomOwnerManuallyEdited = true;
        root.disarm();
        root.outcome = "GITHUB OWNER // " + chosen
            + " // OWNER KNOWN FROM ANOTHER ROOM, NOT AN AUTHENTICATED ACCOUNT";
        return true;
    }
    function useCurrentPatient() {
        const current = root.currentPatientRepository;
        if (!current.owner || !current.repository) {
            root.outcome = "CURRENT FLOOR REPO UNAVAILABLE // SELECT A GITHUB REPOSITORY";
            return;
        }
        // Re-enter automatic mode explicitly, including when the user was
        // previously editing a repository owned by another GitHub account.
        root.roomOwnerManuallyEdited = false;
        root.roomRepositoryManuallyEdited = false;
        root.applyRoomSuggestions();
        root.disarm();
        root.outcome = "CURRENT FLOOR REPO SELECTED // " + root.selectedGitHubRepository;
    }
    function selectMode(value) {
        if (mode === value) return;
        mode = value;
        disarm();
        outcome = "";
        if (value === "ROOM") {
            root.applyRoomSuggestions();
            if (!githubOwner.loaded && !githubOwner.reading)
                githubOwner.refresh();
        }
    }
    function refreshStaffing() {
        root.staffingReviewKey = "";
        if (!root.active || root.mode !== "STAFFING")
            return false;
        const assignmentsRequested = staffingAssignments.refresh();
        root.rosterRefreshRequested();
        if (root.providerService && !root.providerService.refreshing)
            root.providerService.refresh();
        return assignmentsRequested;
    }
    function verifySelectedBed() {
        root.staffingReviewKey = "";
        if (!root.active || root.mode !== "STAFFING"
                || !root.bedPlan.candidateSelectable || root.bedsDiscovering) {
            root.outcome = "GIT BED HOLD // SELECT A CLEAN MATCHING WORKTREE";
            return false;
        }
        const ok = bedProbe.verify(root.selectedBedPath);
        root.outcome = ok ? "GIT VERIFY // READ-ONLY INSPECTION STARTED"
                          : "GIT VERIFY HOLD // " + bedProbe.lastError;
        return ok;
    }
    function reviewStaffing() {
        root.staffingReviewKey = "";
        const p = root.staffingPlan;
        if (!root.active || root.mode !== "STAFFING" || root.registryBusy
                || !p.readyForReview) {
            root.outcome = "STAFFING HOLD // " +
                (root.registryBusy ? "PX registry refreshing" : p.blockers.join(" // "));
            return false;
        }
        root.staffingReviewKey = root.staffingSignature;
        root.outcome = "STAFFING REVIEW // ROOM " + p.roomId
            + " // ASSIGNMENT #" + p.assignmentId
            + " // DOCTOR " + p.doctorId
            + " // PROVIDER " + p.providerId
            + " // READ ONLY // NO PX WRITE OR AI TURN";
        return true;
    }
    function openStaffingRoom() {
        const id = String(root.selectedRoomId || "").trim();
        if (!root.active || root.mode !== "STAFFING"
                || !id || !root.rooms.some(function(r) {
                    return String(r.id || r.roomId || "") === id;
                })) {
            root.outcome = "OPEN ROOM REFUSED // SELECT A REGISTERED ROOM";
            return false;
        }
        const prepared = root.staffingReviewKey
            && root.staffingReviewKey === root.staffingSignature
            && root.staffingPlan.readyForReview
            ? {
                roomId: root.staffingPlan.roomId,
                assignmentId: root.staffingPlan.assignmentId,
                doctorId: root.staffingPlan.doctorId,
                providerId: root.staffingPlan.providerId
            } : null;
        root.staffingReviewKey = "";
        root.openRoomRequested(id, prepared);
        return true;
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
        selectedStaffDoctorId = "";
        selectedStaffProviderId = "";
        selectedBedPath = "";
        staffBedPage = 0;
        bedProbe.invalidate();
        staffDoctorPage = 0;
        staffProviderPage = 0;
        jobPage = 0;
    }
    onSelectedDraftAssignmentIdChanged: activationArmKey = ""
    onSelectedStaffDoctorIdChanged: staffingReviewKey = ""
    onSelectedStaffProviderIdChanged: staffingReviewKey = ""
    onSelectedBedPathChanged: {
        staffingReviewKey = "";
        bedProbe.invalidate();
    }
    onKnownBedsChanged: bedProbe.invalidate()
    onProvidersChanged: staffingReviewKey = ""
    onDoctorsChanged: staffingReviewKey = ""
    onActiveChanged: {
        disarm();
        if (!active)
            cancelDictation();
        if (!active)
            invalidateIntake();
        if (!active)
            bedProbe.invalidate();
        if (active)
            Qt.callLater(function() {
                if (!root.active) return;
                root.applyRoomSuggestions();
                if (!githubOwner.loaded && !githubOwner.reading)
                    githubOwner.refresh();
            });
    }
    onModeChanged: {
        if (root.dictationField && root.mode !== root.dictationMode)
            cancelDictation();
    }
    onSuggestedRepositoryChanged: {
        if (active && mode === "ROOM")
            applyRoomSuggestions();
    }
    onRoomsChanged: {
        disarm();
        bedProbe.invalidate();
    }
    onSessionsChanged: disarm()
    onRegistryErrorChanged: disarm()
    onStaffingPlanChanged: staffingReviewKey = ""
    onAssignmentListVerifiedChanged: activationArmKey = ""

    Connections {
        target: root.speechInputService
        function onTranscriptionReady(text, submitRequested) {
            // Legacy post-STOP recorder fallback, never a form submission.
            if (!root.speechInputService
                    || root.speechInputService.liveStreaming !== true)
                root.acceptDictation(text);
        }
        function onLiveTextReady(text) {
            root.acceptLivePhrase(text);
        }
        function onLiveFinished() {
            root.finishLiveDictation();
        }
        function onVoiceError(message) {
            if (!root.dictationField)
                return;
            const messageText = String(message || "LOCAL DICTATION FAILED").slice(0,180);
            const fieldKey = root.dictationField;
            root.cancelDictation();
            root.dictationFeedbackField = fieldKey;
            root.dictationFeedback = messageText;
        }
    }

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
    HospitalGitHubOwnerService {
        id: githubOwner
        onRefreshed: {
            // Late account responses only change fields the user has NOT edited.
            root.applyRoomSuggestions();
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
            // Start the NEXT Room in this same Floor with a fresh auto-fill.
            // Only reset after the previous Room is confirmed as created.
            root.roomOwnerManuallyEdited = false;
            root.roomRepositoryManuallyEdited = false;
            root.applyRoomSuggestions();
            root.rosterRefreshRequested();
        }
    }
    HospitalFirstBedProbeService {
        id: bedProbe
    }
    HospitalWorkerAttachmentPreviewService {
        id: staffingAssignments
        roomId: root.active && root.mode === "STAFFING"
            ? root.selectedRoomId : ""
        onAssignmentsChanged: root.staffingReviewKey = ""
        onLoadedChanged: root.staffingReviewKey = ""
        onLastErrorChanged: root.staffingReviewKey = ""
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
    HospitalActionButton {
        width: parent.width
        height: 30
        label: "START HERE // DESCRIBE A NEW AI JOB"
        accent: root.mode === "SETUP" ? Colors.magenta : Colors.cyan
        selectedAction: root.mode === "SETUP"
        contentGlowEnabled: false
        onTriggered: root.selectMode("SETUP")
    }
    Row {
        width: parent.width
        spacing: 5
        Repeater {
            model: [
                {label:"WORKERS", code:"WORKER"},
                {label:"NEW ROOM", code:"ROOM"},
                {label:"JOB", code:"JOB"},
                {label:"STAFFING", code:"STAFFING"}
            ]
            HospitalActionButton {
                required property var modelData
                width: (root.width - 15) / 4
                height: 30
                label: modelData.label
                accent: root.mode === modelData.code ? Colors.magenta : Colors.cyan
                selectedAction: root.mode === modelData.code
                contentGlowEnabled: false
                onTriggered: root.selectMode(modelData.code)
            }
        }
    }

    // SETUP: conversation-style intake that only pre-fills existing editors.
    Column {
        width: parent.width
        spacing: 7
        visible: root.mode === "SETUP"
        GohuText {
            width: parent.width
            text: "NEW AI // TELL HOSPITAL WHAT YOU WANT TO WORK ON"
            color: Colors.magenta
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "Describe the job like a chat message. For now this makes a LOCAL STARTER TEMPLATE, not a model-generated answer. You choose the Room, worker and job records before saving."
            color: Colors.cyan
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
        ManagerArea {
            id: intakeBriefField
            caption: "YOUR INSTRUCTIONS // WHAT IS THIS AI WORKING ON?"
            voiceKey: "intake"
            voiceMaxLength: 4000
            editHeight: 156
            onEdited: root.invalidateIntake()
        }
        HospitalActionButton {
            width: parent.width
            height: 30
            label: "BUILD STARTER DRAFT"
            accent: Colors.magenta
            contentGlowEnabled: false
            enabledAction: root.active
            onTriggered: root.draftIntake()
        }
        GohuText {
            width: parent.width
            text: root.intakeDraft.ready
                ? "LOCAL PROPOSAL // NOT AI-GENERATED"
                    + "\\nROLE // " + root.intakeDraft.role
                    + "\\nROOM // " + root.intakeDraft.roomName
                    + "\\nWORKER // " + root.intakeDraft.workerName
                    + "\\nJOB // " + root.intakeDraft.title
                    + "\\nGOAL // " + root.intakeDraft.goal
                    + "\\nPERMISSIONS // READ ONLY"
                : "NO DRAFT YET // WRITE YOUR INSTRUCTIONS ABOVE"
            font.pixelSize: 9
            color: root.intakeDraft.ready ? Colors.cyan : Colors.orange
            wrapMode: Text.WrapAnywhere
        }
        GohuText {
            width: parent.width
            text: "Choose one editor below. Prefilling never creates records. Save Room, Worker and Job independently using their existing REVIEW / CONFIRM controls. The JOB needs a saved Room."
            font.pixelSize: 9
            color: Colors.blue
            wrapMode: Text.Wrap
        }
        Row {
            width: parent.width
            spacing: 6
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "EDIT ROOM"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.intakeDraft.ready === true
                onTriggered: root.applyIntake("ROOM")
            }
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "EDIT WORKER"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.intakeDraft.ready === true
                onTriggered: root.applyIntake("WORKER")
            }
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "EDIT JOB"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.intakeDraft.ready === true
                onTriggered: root.applyIntake("JOB")
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
        GohuText {
            width: parent.width
            text: "CURRENT FLOOR REPOSITORY // "
                + (root.currentPatientRepository.owner
                    ? root.suggestedRepository
                    : "NOT DETECTED // SELECT OR ENTER MANUALLY")
                + "\nOwner and project auto-fill together when available."
            font.pixelSize: 9
            color: root.currentPatientRepository.owner ? Colors.cyan : Colors.orange
            wrapMode: Text.WrapAnywhere
        }
        GohuText {
            width: parent.width
            text: "GITHUB OWNER = the account or organization hosting the repository. NOT the worker, Doctor or person assigned the job."
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.Wrap
        }
        ManagerField {
            id: roomOwnerField
            caption: "GITHUB OWNER // ACCOUNT OR ORGANIZATION"
            onEdited: {
                root.roomOwnerManuallyEdited = true;
                root.disarm();
            }
        }
        Row {
            width: root.width
            spacing: 6
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 29
                label: "USE MY GITHUB"
                accent: Colors.magenta
                contentGlowEnabled: false
                enabledAction: githubOwner.loaded && !!githubOwner.login
                onTriggered: root.useOwnGitHub()
            }
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 29
                label: "USE CURRENT REPO"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: !!root.currentPatientRepository.owner
                onTriggered: root.useCurrentPatient()
            }
        }
        GohuText {
            width: parent.width
            text: githubOwner.reading ? "MY GITHUB // READING SIGNED-IN ACCOUNT"
                : githubOwner.loaded ? "MY GITHUB // @" + githubOwner.login
                : "MY GITHUB // NOT VERIFIED; CURRENT PATIENT OR MANUAL OWNER STILL WORK"
            font.pixelSize: 8
            color: githubOwner.loaded ? Colors.cyan : Colors.orange
            wrapMode: Text.Wrap
        }
        Repeater {
            model: root.otherKnownGitHubOwners
            HospitalActionButton {
                required property var modelData
                width: root.width
                height: 27
                label: "RECENT GITHUB OWNER // " + modelData.owner
                accent: Colors.blue
                contentGlowEnabled: false
                onTriggered: root.useKnownGitHubOwner(modelData.owner)
            }
        }
        ManagerField {
            id: roomRepoField
            caption: "REPOSITORY // PROJECT NAME ON THAT GITHUB ACCOUNT"
            onEdited: {
                root.roomRepositoryManuallyEdited = true;
                root.disarm();
            }
        }
        GohuText {
            width: parent.width
            text: "PATIENT // GITHUB.COM/" + root.selectedGitHubRepository
                + "\nOWNER = WHOSE GITHUB ACCOUNT // REPOSITORY = WHICH PROJECT"
            font.pixelSize: 9
            color: root.roomPlan.ready ? Colors.cyan : Colors.orange
            wrapMode: Text.WrapAnywhere
        }
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
        ManagerArea {id:jobGoalField; caption:"GOAL"; voiceKey:"goal"; voiceMaxLength:4000}
        ManagerArea {id:jobConstraintsField; caption:"CONSTRAINTS / FILE OWNERSHIP"; voiceKey:"constraints"; voiceMaxLength:4000}
        ManagerArea {id:jobDoneField; caption:"DEFINITION OF DONE"; voiceKey:"done"; voiceMaxLength:4000}
        ManagerArea {id:jobChecklistField; caption:"CHECKLIST"; voiceKey:"checklist"; voiceMaxLength:4000}
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

    // STAFFING: first-worker, read-only preflight using saved PX identities.
    // Handoff to the existing nested Room inspector, NEVER a backend upsert.
    Column {
        id: staffingColumn
        width: root.width
        spacing: 7
        visible: root.mode === "STAFFING"

        GohuText {
            width: parent.width
            text: "STAFFING // ONE ROOM + ACTIVE READ JOB + DOCTOR + PROVIDER"
            font.pixelSize: 10
            color: Colors.magenta
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "Choose records below. REVIEW STAFFING only checks saved identities. It does not attach a Session, edit Git, or give anyone permission."
            font.pixelSize: 9
            color: Colors.blue
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "1 // SELECT ROOM + ACTIVE ASSIGNMENT"
            font.pixelSize: 9
            color: Colors.orange
        }
        Repeater {
            model: root.rooms.slice(root.staffRoomPage * root.pageSize,
                (root.staffRoomPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 31
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
                        + " // JOB #" + String(modelData.assignmentId || "NONE")
                    color: Colors.white
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectedRoomId
                        = String(modelData.id || modelData.roomId || "")
                }
            }
        }
        ManagerPageRow {
            currentPage: root.staffRoomPage
            count: root.rooms.length
            onPrevious: root.staffRoomPage--
            onNext: root.staffRoomPage++
        }
        Rectangle { width: root.width; height: 2; color: Colors.magenta }
        GohuText {
            width: parent.width
            text: "GIT BED // VERIFY EXISTING WORKTREE BEFORE STAFFING"
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "This checks an existing local Git folder. It does not create, switch, clean or register a Bed. Only clean, non-live worktrees for this Room's repository are listed."
            font.pixelSize: 9
            color: Colors.blue
            wrapMode: Text.Wrap
        }
        Repeater {
            model: root.bedChoices.slice(root.staffBedPage * root.pageSize,
                (root.staffBedPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 36
                color: Colors.black
                border.width: 1
                border.color: root.selectedBedPath === String(modelData.path || "")
                    ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: String(modelData.label || "GIT BED")
                        + " // " + String(modelData.branch || "DETACHED")
                        + "\n" + String(modelData.path || "")
                    font.pixelSize: 8
                    color: Colors.white
                    elide: Text.ElideRight
                    wrapMode: Text.Wrap
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectedBedPath = String(modelData.path || "")
                }
            }
        }
        ManagerPageRow {
            currentPage: root.staffBedPage
            count: root.bedChoices.length
            onPrevious: root.staffBedPage--
            onNext: root.staffBedPage++
        }
        Row {
            width: root.width
            spacing: 6
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 30
                label: "FIND BEDS"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.active && !root.bedsDiscovering
                onTriggered: root.discoverBedsRequested()
            }
            HospitalActionButton {
                width: (parent.width - 6) / 2
                height: 30
                label: "VERIFY BED"
                accent: Colors.magenta
                contentGlowEnabled: false
                enabledAction: root.active && root.bedPlan.candidateSelectable
                    && !bedProbe.checking
                onTriggered: root.verifySelectedBed()
            }
        }
        GohuText {
            width: parent.width
            text: root.bedPlan.status
                + " // " + (root.selectedBedPath || "NO SELECTED BED")
                + (bedProbe.checked ? " // CHECKED " + bedProbe.lastCheckedAt : "")
                + (bedProbe.lastError ? "\nERROR // " + bedProbe.lastError : "")
                + (root.bedDiscoveryError ? "\nDISCOVERY // " + root.bedDiscoveryError : "")
            font.pixelSize: 9
            color: root.bedPlan.verifiedForReview ? Colors.cyan : Colors.orange
            wrapMode: Text.WrapAnywhere
        }
        GohuText {
            width: parent.width
            visible: root.bedPlan.verifiedForReview
            text: "GIT VERIFIED // " + root.bedPlan.repository
                + " // " + root.bedPlan.branch
                + " // HEAD " + root.bedPlan.head.slice(0,12)
                + "\nPX BED REGISTRATION STILL REQUIRES AUTHENTICATED APPROVAL."
            font.pixelSize: 9
            color: Colors.cyan
            wrapMode: Text.WrapAnywhere
        }
        Repeater {
            model: root.bedPlan.blockers.slice(0, 8)
            GohuText {
                required property string modelData
                width: root.width
                text: "BED HOLD // " + modelData
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.Wrap
            }
        }
        GohuText {
            width: parent.width
            text: "2 // SELECT REGISTERED DOCTOR (INTERN / NURSE / DOCTOR)"
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.Wrap
        }
        Repeater {
            model: root.doctors.slice(root.staffDoctorPage * root.pageSize,
                (root.staffDoctorPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 31
                color: Colors.black
                border.width: 1
                border.color: root.selectedStaffDoctorId
                    === String(modelData.id || "") ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: String(modelData.name || modelData.id || "WORKER")
                        + " // " + String(modelData.role || "NO ROLE")
                        + " // " + String(modelData.status || "UNKNOWN")
                    color: Colors.white
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectedStaffDoctorId
                        = String(modelData.id || "")
                }
            }
        }
        ManagerPageRow {
            currentPage: root.staffDoctorPage
            count: root.doctors.length
            onPrevious: root.staffDoctorPage--
            onNext: root.staffDoctorPage++
        }
        GohuText {
            width: parent.width
            text: "3 // SELECT AVAILABLE AI PROVIDER"
            font.pixelSize: 9
            color: Colors.orange
        }
        Repeater {
            model: root.providers.slice(root.staffProviderPage * root.pageSize,
                (root.staffProviderPage + 1) * root.pageSize)
            Rectangle {
                required property var modelData
                width: root.width
                height: 31
                color: Colors.black
                border.width: 1
                border.color: root.selectedStaffProviderId
                    === String(modelData.id || "") ? Colors.magenta : Colors.blue
                GohuText {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: String(modelData.name || modelData.id || "PROVIDER")
                        + " // " + (modelData.available === true
                            ? "AVAILABLE" : "UNAVAILABLE")
                    color: modelData.available === true ? Colors.white : Colors.orange
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.selectedStaffProviderId
                        = String(modelData.id || "")
                }
            }
        }
        ManagerPageRow {
            currentPage: root.staffProviderPage
            count: root.providers.length
            onPrevious: root.staffProviderPage--
            onNext: root.staffProviderPage++
        }
        Rectangle {width:parent.width; height:2; color:Colors.magenta}
        GohuText {
            width: parent.width
            text: "SOURCE // " + (staffingAssignments.loading ? "LOADING"
                : staffingAssignments.loaded ? "PX ASSIGNMENTS READ"
                : "NOT VERIFIED")
                + " // " + root.staffingPlan.headline
            color: root.staffingPlan.readyForReview ? Colors.cyan : Colors.orange
            font.pixelSize: 9
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "ROOM " + (root.staffingPlan.roomId || "NONE")
                + " // JOB #" + (root.staffingPlan.assignmentId || "NONE")
                + " // " + (root.staffingPlan.assignmentTitle || "NO ACTIVE JOB")
                + "\nPATIENT " + (root.staffingPlan.repository || "MISSING")
                + " // BRANCH " + (root.staffingPlan.branch || "MISSING")
                + " // BED " + (root.staffingPlan.bedPath || "MISSING")
            color: Colors.blue
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }
        Repeater {
            model: root.staffingPlan.blockers.slice(0, 12)
            GohuText {
                required property string modelData
                width: staffingColumn.width
                text: "HOLD // " + modelData
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.Wrap
            }
        }
        Repeater {
            model: root.staffingPlan.notes
            GohuText {
                required property string modelData
                width: staffingColumn.width
                text: "NOTE // " + modelData
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.Wrap
            }
        }
        Row {
            width: parent.width
            spacing: 6
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "REFRESH"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.active && !root.registryBusy
                onTriggered: root.refreshStaffing()
            }
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "REVIEW STAFF"
                accent: Colors.magenta
                contentGlowEnabled: false
                enabledAction: root.active && root.staffingPlan.readyForReview
                    && !root.registryBusy
                onTriggered: root.reviewStaffing()
            }
            HospitalActionButton {
                width: (parent.width - 12) / 3
                height: 30
                label: "OPEN ROOM"
                accent: Colors.cyan
                contentGlowEnabled: false
                enabledAction: root.active && root.selectedRoomId !== ""
                onTriggered: root.openStaffingRoom()
            }
        }
        GohuText {
            width: parent.width
            text: root.staffingReviewKey
                && root.staffingReviewKey === root.staffingSignature
                ? "REVIEWED // OPEN ROOM WILL PRESELECT IDS IN EXISTING ATTACHMENT PREVIEW; CONFIRM STILL SEPARATE"
                : "NO STAFFING WRITER // Backend authority and atomic ownership check still required"
            color: root.staffingReviewKey ? Colors.cyan : Colors.orange
            font.pixelSize: 9
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
        signal edited()
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
            border.color: Colors.orange
            TextInput {
                id: input
                anchors.fill: parent
                anchors.leftMargin: 7
                anchors.rightMargin: 7
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                cursorDelegate: Rectangle {
                    width: 2
                    color: Colors.orange
                }
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                selectByMouse: true
                maximumLength: 256
                onTextEdited: managerField.edited()
                verticalAlignment: TextInput.AlignVCenter
                clip: true
            }
        }
    }

    // Shared multi-line editor. Uses Hospital's existing local Whisper input,
    // not a network recognizer. The same controls apply to every long prompt.
    component ManagerArea: Column {
        id: managerArea
        property string caption: ""
        property alias value: edit.text
        property int editHeight: 79
        property string voiceKey: ""
        property int voiceMaxLength: 4000
        readonly property bool voiceActive:
            !!voiceKey && root.dictationField === voiceKey
        readonly property bool showVoiceLine:
            !!voiceKey && (voiceActive
                || root.dictationFeedbackField === voiceKey)
        signal edited()
        width: root.width
        spacing: 3
        height: editHeight + 33 + (showVoiceLine ? 15 : 0)

        function focusEditorAtEnd() {
            edit.cursorPosition = edit.text.length;
            edit.forceActiveFocus();
        }

        Row {
            width: managerArea.width
            height: 30
            spacing: 5
            GohuText {
                width: Math.max(50, parent.width - micAction.width
                    - cancelAction.width - parent.spacing * 2)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: managerArea.caption
                color: Colors.blue
                font.pixelSize: 9
                elide: Text.ElideRight
            }
            // Reception's talking-person microphone, scaled for the Manage
            // editor header. Green Omnitrix at rest/recording, orange hover.
            Rectangle {
                id: micAction
                readonly property bool canAct:
                    root.active && !!root.speechInputService
                    && (managerArea.voiceActive
                        && root.speechInputService.recording
                        || (!root.speechInputService.busy && !root.otherVoiceBusy))
                width: managerArea.voiceKey ? 36 : 0
                height: parent.height
                visible: !!managerArea.voiceKey
                color: micMouse.pressed ? Colors.black : Colors.dark
                border.width: (managerArea.voiceActive || micMouse.containsMouse)
                    ? 2 : 1
                border.color: managerArea.voiceActive && root.speechInputService
                    && root.speechInputService.recording
                    ? Colors.omnitrix
                    : managerArea.voiceActive && root.speechInputService
                        && root.speechInputService.busy
                    ? Colors.orange
                    : micMouse.containsMouse && canAct
                    ? Colors.orange : Colors.omnitrix
                opacity: canAct ? 1.0 : 0.48

                RectangularShadow {
                    anchors.fill: parent
                    spread: 4
                    z: -1
                    opacity: micMouse.containsMouse && micAction.canAct
                        ? 0.48 : 0.34
                    color: micMouse.containsMouse && micAction.canAct
                        ? Colors.orange : Colors.omnitrix
                }

                GohuText {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: 1
                    text: "🗣︎"
                    font.pixelSize: 22
                    color: micMouse.containsMouse && micAction.canAct
                        ? Colors.orange : Colors.omnitrix
                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 7
                        samples: 9
                        opacity: 0.54
                        color: micMouse.containsMouse && micAction.canAct
                            ? Colors.orange : Colors.omnitrix
                        transparentBorder: true
                    }
                }
                MouseArea {
                    id: micMouse
                    anchors.fill: parent
                    enabled: micAction.canAct
                    hoverEnabled: true
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.toggleDictation(managerArea.voiceKey)
                }
            }
            HospitalActionButton {
                id: cancelAction
                visible: managerArea.voiceActive && !!root.speechInputService
                    && root.speechInputService.busy
                width: visible ? 62 : 0
                height: 30
                label: "CANCEL"
                accent: Colors.red
                contentGlowEnabled: false
                onTriggered: root.cancelDictation()
            }
        }
        Rectangle {
            width: parent.width
            height: managerArea.editHeight
            color: Colors.black
            border.width: 1
            border.color: Colors.orange
            TextEdit {
                id: edit
                anchors.fill: parent
                anchors.margins: 6
                color: Colors.magenta
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                cursorDelegate: Rectangle {
                    width: 2
                    color: Colors.orange
                }
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                selectByMouse: true
                onTextChanged: managerArea.edited()
                clip: true
            }
        }
        GohuText {
            width: parent.width
            height: managerArea.showVoiceLine ? 12 : 0
            visible: managerArea.showVoiceLine
            text: managerArea.voiceActive && root.speechInputService
                && root.speechInputService.recording
                ? "LISTENING " + root.speechInputService.recordingElapsedLabel
                    + " // STOP TO INSERT TEXT, CANCEL TO DISCARD"
                : managerArea.voiceActive && root.speechInputService
                    && (root.speechInputService.stopping
                        || root.speechInputService.transcribing)
                ? "LOCAL WHISPER // TRANSCRIBING // NO FORM SUBMISSION"
                : root.dictationFeedback
            color: managerArea.voiceActive ? Colors.magenta : Colors.orange
            font.pixelSize: 8
            elide: Text.ElideRight
        }
    }
}