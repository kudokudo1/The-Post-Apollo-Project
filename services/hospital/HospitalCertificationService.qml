import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: certificationService

    // Hospital certification is deliberately provider-neutral.
    // Git/GitHub supplies evidence; this service decides what that evidence means.
    property string repository: ""
    property string team: ""

    property string state: "IDLE"
    property string lastError: ""
    property string lastReason: ""

    property string candidateHead: ""
    property string candidateBaseHead: ""
    property string verifiedHead: ""
    property string certifiedHead: ""
    property string armedHead: ""
    property string postOpHead: ""

    property bool hydrated: false
    property bool evidenceReady: false

    property var verificationChecks: ({})
    property var verificationRuns: ({})

    property var evidencePacket: ({})
    property var history: []

    readonly property string roomKey:
        repository.length > 0 && team.length > 0
        ? repository + "::" + team
        : ""

    readonly property bool isCandidate: state === "CANDIDATE"
    readonly property bool isVerified: state === "VERIFIED"
    readonly property bool isCertified: state === "CERTIFIED"
    readonly property bool isArmed: state === "ARMED"
    readonly property bool isIntegrating: state === "INTEGRATING"
    readonly property bool isPostOp: state === "POST_OP"
    readonly property bool isInMain: state === "IN_MAIN"
    readonly property bool isBlocked: state === "BLOCKED"
    readonly property bool isReopened: state === "REOPENED"

    readonly property bool canVerify:
        isCandidate
        && candidateHead.length > 0

    readonly property bool canCertify:
        isVerified
        && evidenceReady
        && verifiedHead.length > 0

    readonly property bool canArm:
        isCertified
        && certifiedHead.length > 0

    readonly property bool canIntegrate:
        isArmed
        && armedHead.length > 0

    signal certificationChanged(
        string previousState,
        string nextState,
        string eventType)
    signal evidenceRecorded(var packet)
    signal certificationBlocked(string reason)

    HospitalHistoryService {
        id: hospitalHistory
    }

    FileView {
        id: historyFile

        path: Quickshell.dataPath("hospital-certification.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: historyAdapter

            property int schemaVersion: 1
            property var events: []
        }

        onAdapterUpdated: writeAdapter()

        onLoaded: {
            certificationService.hydrate();
        }

        onLoadFailed: {
            certificationService.hydrate();
        }

        onSaveFailed: function(error) {
            certificationService.lastError =
                "CERTIFICATION SAVE // " + String(error);
        }
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function normalizeList(value) {
        return Array.isArray(value) ? value.slice() : [];
    }

    function normalizeSnapshot(input) {
        const source = input || {};
        const rehearsal = source.rehearsal || {};
        const checks = source.checks || {};
        const runs = source.runs || {};

        return {
            repository: String(source.repository || repository),
            team: String(source.team || team),
            branch: String(source.branch || ""),
            head: String(source.head || ""),
            base: String(source.base || ""),
            baseHead: String(
                source.baseHead
                || source.base_head
                || ""
            ),
            relation: String(source.relation || ""),
            mode: String(
                source.mode
                || source.integrationMode
                || ""
            ).toUpperCase(),

            diffFileCount: Number(
                source.diffFileCount
                || source.diff_files
                || (source.totals || {}).files
                || 0
            ),
            additions: Number(
                source.additions
                || (source.totals || {}).additions
                || 0
            ),
            deletions: Number(
                source.deletions
                || (source.totals || {}).deletions
                || 0
            ),
            changedFiles: normalizeList(
                source.changedFiles || source.changed_files
            ),

            rehearsal: {
                status: String(
                    rehearsal.status
                    || source.rehearsalStatus
                    || ""
                ).toUpperCase(),
                mergeBase: String(
                    rehearsal.mergeBase
                    || source.rehearsalMergeBase
                    || ""
                ),
                resultTree: String(
                    rehearsal.resultTree
                    || source.rehearsalResultTree
                    || ""
                ),
                conflicts: normalizeList(
                    rehearsal.conflicts
                    || source.rehearsalConflicts
                ),
                changedFiles: normalizeList(
                    rehearsal.changedFiles
                    || source.rehearsalChangedFiles
                ),
                fileCount: Number(
                    rehearsal.fileCount
                    || source.rehearsalFileCount
                    || 0
                ),
                additions: Number(
                    rehearsal.additions
                    || source.rehearsalAdditions
                    || 0
                ),
                deletions: Number(
                    rehearsal.deletions
                    || source.rehearsalDeletions
                    || 0
                )
            },

            checks: checks,
            runs: runs,
            postOp: source.postOp || {},
            notes: String(source.notes || "")
        };
    }

    function buildPacket(snapshot, details) {
        const normalized = normalizeSnapshot(snapshot);
        const extra = details || {};

        return {
            schemaVersion: 1,
            recordedAt: nowIso(),
            roomKey: roomKey,
            repository: normalized.repository,
            team: normalized.team,
            branch: normalized.branch,
            state: state,

            head: normalized.head,
            base: normalized.base,
            baseHead: normalized.baseHead,
            relation: normalized.relation,
            mode: normalized.mode,

            candidateHead: candidateHead,
            candidateBaseHead: candidateBaseHead,
            verifiedHead: verifiedHead,
            certifiedHead: certifiedHead,
            armedHead: armedHead,
            postOpHead: postOpHead,

            diff: {
                files: normalized.diffFileCount,
                additions: normalized.additions,
                deletions: normalized.deletions,
                changedFiles: normalized.changedFiles
            },

            rehearsal: normalized.rehearsal,
            checks: verificationChecks,
            runs: verificationRuns,
            postOp: normalized.postOp,

            reason: lastReason,
            details: extra
        };
    }

    function validateSnapshot(snapshot) {
        const normalized = normalizeSnapshot(snapshot);

        if (!normalized.repository || !normalized.team) {
            lastError = "CERTIFICATION REFUSED // ROOM IDENTITY MISSING";
            return null;
        }

        if (!normalized.head) {
            lastError = "CERTIFICATION REFUSED // HEAD MISSING";
            return null;
        }

        if (!normalized.base || !normalized.baseHead) {
            lastError = "CERTIFICATION REFUSED // BASE SNAPSHOT MISSING";
            return null;
        }

        return normalized;
    }

    function checksPassed(checks) {
        if (checks === true)
            return true;

        if (!checks)
            return false;

        if (checks.passed === true)
            return true;

        const status = String(checks.status || "").toUpperCase();

        return status === "PASS"
            || status === "PASSED"
            || status === "SUCCESS"
            || status === "SUCCESSFUL"
            || status === "CLEAN";
    }

    function bindRoom(targetRepository, targetTeam) {
        repository = String(targetRepository || "");
        team = String(targetTeam || "");

        if (hydrated)
            hydrate();
        else
            history = [];
    }

    function resetLiveState() {
        state = "IDLE";
        lastError = "";
        lastReason = "";

        candidateHead = "";
        candidateBaseHead = "";
        verifiedHead = "";
        certifiedHead = "";
        armedHead = "";
        postOpHead = "";

        evidenceReady = false;
        verificationChecks = ({});
        verificationRuns = ({});
        evidencePacket = ({});
        history = [];
    }

    function hydrate() {
        hydrated = true;

        const events = Array.isArray(historyAdapter.events)
                       ? historyAdapter.events.slice()
                       : [];

        history = roomKey
                  ? events.filter(function(event) {
                        return String(event.roomKey || "") === roomKey;
                    })
                  : [];

        if (history.length === 0) {
            resetLiveState();
            hydrated = true;
            return;
        }

        const latest = history[history.length - 1] || {};
        const packet = latest.packet || {};

        state = String(latest.state || "IDLE");
        lastReason = String(latest.reason || "");
        lastError = "";

        candidateHead = String(packet.candidateHead || "");
        candidateBaseHead = String(packet.candidateBaseHead || "");
        verifiedHead = String(packet.verifiedHead || "");
        certifiedHead = String(packet.certifiedHead || "");
        armedHead = String(packet.armedHead || "");
        postOpHead = String(packet.postOpHead || "");

        verificationChecks = packet.checks || ({});
        verificationRuns = packet.runs || ({});
        evidencePacket = packet;
        evidenceReady =
            state === "VERIFIED"
            || state === "CERTIFIED"
            || state === "ARMED"
            || state === "INTEGRATING"
            || state === "POST_OP"
            || state === "IN_MAIN";
    }

    function recordTransition(
            nextState,
            eventType,
            snapshot,
            details) {
        const normalized = normalizeSnapshot(snapshot);
        const previousState = state;

        state = String(nextState || "IDLE").toUpperCase();
        evidencePacket = buildPacket(normalized, details);

        const event = {
            schemaVersion: 1,
            id: nowIso() + "::" + eventType,
            recordedAt: evidencePacket.recordedAt,
            roomKey: roomKey,
            eventType: String(eventType || ""),
            state: state,
            previousState: previousState,
            reason: lastReason,
            packet: evidencePacket
        };

        const nextHistory = history.slice();
        nextHistory.push(event);
        history = nextHistory;

        const allEvents = Array.isArray(historyAdapter.events)
                         ? historyAdapter.events.slice()
                         : [];
        allEvents.push(event);
        historyAdapter.events = allEvents;

        hospitalHistory.record(
            eventType,
            normalized.team,
            state,
            {
                repository: normalized.repository,
                branch: normalized.branch,
                head: normalized.head,
                base: normalized.base,
                baseHead: normalized.baseHead,
                reason: lastReason,
                packet: evidencePacket
            }
        );

        evidenceRecorded(evidencePacket);
        certificationChanged(previousState, state, eventType);
    }

    function beginCandidate(snapshot) {
        if (state !== "IDLE"
                && state !== "REOPENED") {
            lastError =
                "CANDIDATE REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        if (normalized.mode !== "FAST_FORWARD"
                && normalized.mode !== "DIVERGED") {
            lastError =
                "CANDIDATE REFUSED // PREPARE MODE "
                + normalized.mode;
            return false;
        }

        repository = normalized.repository;
        team = normalized.team;

        candidateHead = normalized.head;
        candidateBaseHead = normalized.baseHead;
        verifiedHead = "";
        certifiedHead = "";
        armedHead = "";
        postOpHead = "";
        evidenceReady = false;
        verificationChecks = ({});
        verificationRuns = ({});
        lastReason = "PREPARE SNAPSHOT ACCEPTED";
        lastError = "";

        recordTransition(
            "CANDIDATE",
            "CANDIDATE_CREATED",
            normalized,
            {
                source: "PREPARE",
                acceptance: "SNAPSHOT_VALID"
            }
        );

        return true;
    }

    function verifyCandidate(snapshot, checks, runs) {
        if (!canVerify) {
            lastError =
                "VERIFY REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        verificationChecks = checks || ({});
        verificationRuns = runs || ({});
        normalized.checks = verificationChecks;
        normalized.runs = verificationRuns;

        if (normalized.head !== candidateHead) {
            block(
                "VERIFY DRIFT // CANDIDATE "
                + candidateHead.slice(0, 8)
                + " != CURRENT "
                + normalized.head.slice(0, 8),
                normalized
            );
            return false;
        }

        if (normalized.baseHead !== candidateBaseHead) {
            block(
                "VERIFY DRIFT // BASE MOVED",
                normalized
            );
            return false;
        }

        if (normalized.mode === "DIVERGED") {
            if (normalized.rehearsal.status !== "CLEAN_MERGE"
                    || !normalized.rehearsal.resultTree) {
                block(
                    "VERIFY BLOCKED // MERGE REHEARSAL NOT CLEAN",
                    normalized,
                    {
                        rehearsal: normalized.rehearsal
                    }
                );
                return false;
            }
        }

        if (!checksPassed(checks)) {
            block(
                "VERIFY BLOCKED // CHECKS NOT CLEAN",
                normalized,
                {
                    checks: checks || {},
                    runs: runs || {}
                }
            );
            return false;
        }

        repository = normalized.repository;
        team = normalized.team;
        verifiedHead = normalized.head;
        evidenceReady = true;
        lastReason = "CANDIDATE VERIFIED";
        lastError = "";

        recordTransition(
            "VERIFIED",
            "CANDIDATE_VERIFIED",
            normalized,
            {
                source: "VERIFICATION",
                checksPassed: true
            }
        );

        return true;
    }

    function certifyVerified(snapshot) {
        if (!canCertify) {
            lastError =
                "CERTIFY REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        if (normalized.head !== verifiedHead) {
            block(
                "CERTIFY DRIFT // VERIFIED HEAD MOVED",
                normalized
            );
            return false;
        }

        if (normalized.baseHead !== candidateBaseHead) {
            block(
                "CERTIFY DRIFT // BASE MOVED",
                normalized
            );
            return false;
        }

        repository = normalized.repository;
        team = normalized.team;
        certifiedHead = normalized.head;
        lastReason = "VERIFIED EVIDENCE ACCEPTED";
        lastError = "";

        recordTransition(
            "CERTIFIED",
            "CERTIFICATION_GRANTED",
            normalized,
            {
                source: "HOSPITAL_CERTIFICATION",
                evidenceComplete: true
            }
        );

        return true;
    }

    function armCertified(snapshot) {
        if (!canArm) {
            lastError =
                "ARM REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        if (normalized.head !== certifiedHead) {
            block(
                "ARM DRIFT // CERTIFIED HEAD MOVED",
                normalized
            );
            return false;
        }

        armedHead = normalized.head;
        lastReason = "CERTIFICATION FROZEN";
        lastError = "";

        recordTransition(
            "ARMED",
            "CERTIFICATION_ARMED",
            normalized,
            {
                source: "ARM_GATE"
            }
        );

        return true;
    }

    function beginIntegration(snapshot) {
        if (!canIntegrate) {
            lastError =
                "INTEGRATE REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        if (normalized.head !== armedHead) {
            block(
                "INTEGRATE DRIFT // ARMED HEAD MOVED",
                normalized
            );
            return false;
        }

        lastReason = "ARMED SNAPSHOT ACCEPTED";
        lastError = "";

        recordTransition(
            "INTEGRATING",
            "INTEGRATION_STARTED",
            normalized,
            {
                source: "INTEGRATE_GATE"
            }
        );

        return true;
    }

    function beginPostOp(snapshot) {
        if (state !== "INTEGRATING") {
            lastError =
                "POST-OP REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);

        if (!normalized)
            return false;

        postOpHead = normalized.head;
        lastReason = "INTEGRATION COMPLETED";
        lastError = "";

        recordTransition(
            "POST_OP",
            "POST_OP_STARTED",
            normalized,
            {
                source: "POST_OP_VERIFICATION"
            }
        );

        return true;
    }

    function completePostOp(snapshot) {
        if (state !== "POST_OP") {
            lastError =
                "POST-OP REFUSED // STATE " + state;
            return false;
        }

        const normalized = validateSnapshot(snapshot);
        const postOp = normalized ? normalized.postOp : {};

        if (!normalized)
            return false;

        const status =
            String(postOp.status || "").toUpperCase();

        if (status !== "POST_OP_CLEAN") {
            block(
                "POST-OP BLOCKED // "
                + (status || "NO CLEAN RESULT"),
                normalized
            );
            return false;
        }

        const operatedRoomHead =
            String(
                postOp.expectedRoomHead
                || postOp.expected_room_head
                || normalized.head
            );
        const currentRoomHead =
            String(
                postOp.currentRoomHead
                || postOp.current_room_head
                || operatedRoomHead
            );
        const roomHeadUnchanged =
            postOp.roomBranchUnchanged !== undefined
            ? Boolean(postOp.roomBranchUnchanged)
            : postOp.room_branch_unchanged !== undefined
            ? Boolean(postOp.room_branch_unchanged)
            : currentRoomHead === operatedRoomHead;

        if (armedHead && operatedRoomHead !== armedHead) {
            block(
                "POST-OP DRIFT // OPERATED ROOM HEAD DOES NOT MATCH ARMED",
                normalized,
                {
                    armedHead: armedHead,
                    operatedRoomHead: operatedRoomHead,
                    currentRoomHead: currentRoomHead
                }
            );
            return false;
        }

        postOpHead = operatedRoomHead;
        lastReason = "POST-OP CLEAN";
        lastError = "";

        recordTransition(
            "IN_MAIN",
            "POST_OP_VERIFIED",
            normalized,
            {
                source: "POST_OP",
                operatedRoomHead: operatedRoomHead,
                currentRoomHead: currentRoomHead,
                roomHeadUnchanged: roomHeadUnchanged
            }
        );

        return true;
    }

    function block(reason, snapshot, details) {
        lastReason = String(reason || "CERTIFICATION BLOCKED");
        lastError = lastReason;

        const normalized = normalizeSnapshot(snapshot);

        recordTransition(
            "BLOCKED",
            "CERTIFICATION_BLOCKED",
            normalized,
            details || {}
        );

        certificationBlocked(lastReason);

        return false;
    }

    function reopen(reason, snapshot) {
        lastReason = String(reason || "ROOM REOPENED");
        lastError = "";

        const normalized = normalizeSnapshot(snapshot);

        recordTransition(
            "REOPENED",
            "CERTIFICATION_REOPENED",
            normalized,
            {}
        );

        return true;
    }

    function clearHistory() {
        history = [];

        const allEvents = Array.isArray(historyAdapter.events)
                         ? historyAdapter.events.slice()
                         : [];

        const kept = allEvents.filter(function(event) {
            return String(event.roomKey || "") !== roomKey;
        });

        historyAdapter.events = kept;
        resetLiveState();
        hydrated = true;
    }

    Component.onCompleted: {
        if (historyFile.loaded)
            hydrate();
    }
}
