import QtQuick
import Quickshell

Scope {
    id: coordinator

    property var roomService: null
    property var evidenceProvider: null

    property bool verificationPending: false
    property string verificationRunId: ""
    property string pendingDriftGate: ""
    property string bridgeError: ""
    property var lastGitEvidence: ({})
    property var lastVerificationChecks: ({})
    property var pendingVerificationRuns: ({})

    HospitalOperatingAuthorityService {
        id: authority
    }

    HospitalCertificationDriftService {
        id: driftProbe
    }

    property string hostLeaseId: ""

    Connections {
        target: authority

        function onHydratedChanged() {
            if (authority.hydrated)
                coordinator.recoverHostLease();
        }
    }

    readonly property bool hostSlotOwned:
        roomService
        && hostLeaseId.length > 0
        && authority.isOwner(
            roomService.team,
            hostLeaseId
        )

    HospitalCertificationService {
        id: certification

        onCertificationChanged: function(previousState, nextState, eventType) {
            coordinator.certificationChanged(
                previousState,
                nextState,
                eventType
            );
        }

        onCertificationBlocked: function(reason) {
            coordinator.certificationBlocked(reason);
        }
    }

    readonly property string state: certification.state
    readonly property string lastError:
        bridgeError
        || certification.lastError
        || authority.lastError
    readonly property string lastReason: certification.lastReason

    readonly property bool canVerify: certification.canVerify
    readonly property bool canRequestVerification:
        certification.canVerify
        && evidenceProvider
        && !verificationPending
        && !driftProbe.busy
    readonly property bool canCertify:
        certification.canCertify
        && !driftProbe.busy
    readonly property bool canArm:
        certification.canArm
        && !driftProbe.busy
    readonly property bool canIntegrate: certification.canIntegrate

    readonly property var evidencePacket:
        certification.evidencePacket

    signal certificationChanged(
        string previousState,
        string nextState,
        string eventType)
    signal certificationBlocked(string reason)
    signal verificationEvidenceReady(var checks, var evidence)

    Connections {
        target: coordinator.roomService

        function onBranchChanged() {
            coordinator.recoverHostLease();
        }

        function onHeadChanged() {
            coordinator.recoverHostLease();
        }

        function onInspected() {
            if (!coordinator.roomService)
                return;

            coordinator.recoverHostLease();

            if (String(coordinator.roomService.action || "") !== "PREPARE")
                return;

            coordinator.refreshBinding();
            certification.beginCandidate(
                coordinator.roomService.certificationSnapshot()
            );
        }

        function onIntegrationFailed(reason, uncertain) {
            if (!coordinator.roomService)
                return;

            if (certification.state !== "INTEGRATING")
                return;

            certification.block(
                (uncertain
                 ? "INTEGRATION UNCERTAIN // "
                 : "INTEGRATION REFUSED // ")
                + String(reason || "UNKNOWN FAILURE"),
                coordinator.roomSnapshot(),
                {
                    source: "ROOM_SERVICE",
                    uncertain: Boolean(uncertain),
                    hostSlotRetained:
                        coordinator.hostSlotOwned
                }
            );

            coordinator.bridgeError =
                certification.lastError;
        }

        function onPostOpStarted() {
            if (!coordinator.roomService)
                return;

            certification.beginPostOp(
                coordinator.roomService.postOpSnapshot()
            );
        }

        function onPostOpFinished() {
            if (!coordinator.roomService)
                return;

            certification.completePostOp(
                coordinator.roomService.postOpSnapshot()
            );

            if (certification.state === "IN_MAIN"
                    && coordinator.hostSlotOwned) {
                authority.releaseSlot(
                    coordinator.roomService.team,
                    coordinator.hostLeaseId,
                    "POST-OP COMPLETE"
                );
                coordinator.hostLeaseId = "";
            }
        }
    }

    Connections {
        target: coordinator.evidenceProvider
        ignoreUnknownSignals: true

        function onRequestFinished(packet) {
            if (!coordinator.verificationPending)
                return;

            coordinator.verificationPending = false;
            coordinator.verifyEvidencePacket(packet);
        }
    }

    Connections {
        target: driftProbe

        function onChecked(result) {
            const gate = coordinator.pendingDriftGate;
            coordinator.pendingDriftGate = "";

            const outcome =
                String((result || {}).status || "").toUpperCase();

            if (outcome === "ERROR") {
                coordinator.bridgeError =
                    String((result || {}).error || "")
                    || "REMOTE DRIFT CHECK FAILED";
                return;
            }

            if (outcome === "DRIFT") {
                const differences =
                    Array.isArray((result || {}).differences)
                    ? result.differences
                    : [];

                certification.block(
                    "REMOTE DRIFT // "
                    + (
                        differences.length > 0
                        ? differences.join(" + ")
                        : "SNAPSHOT CHANGED"
                    ),
                    coordinator.roomSnapshot(),
                    {
                        source: "REMOTE_DRIFT_PROBE",
                        drift: result || {}
                    }
                );

                coordinator.bridgeError =
                    certification.lastError;
                return;
            }

            if (outcome !== "MATCH") {
                coordinator.bridgeError =
                    "REMOTE DRIFT CHECK // UNKNOWN RESULT";
                return;
            }

            coordinator.bridgeError = "";

            if (gate === "VERIFY")
                coordinator.startEvidenceRequest();
            else if (gate === "VERIFY_FINAL")
                coordinator.completeEvidenceVerification();
            else if (gate === "CERTIFY")
                coordinator.certifyAfterDrift();
            else if (gate === "ARM")
                coordinator.armAfterDrift();
        }
    }

    function roomSnapshot() {
        if (!roomService
                || typeof roomService.certificationSnapshot
                    !== "function")
            return ({});

        return roomService.certificationSnapshot();
    }

    function expectedSnapshotForGate(gate) {
        const current = roomSnapshot();
        let expectedHead = "";

        if (gate === "VERIFY"
                || gate === "VERIFY_FINAL")
            expectedHead = String(certification.candidateHead || "");
        else if (gate === "CERTIFY")
            expectedHead = String(certification.verifiedHead || "");
        else if (gate === "ARM")
            expectedHead = String(certification.certifiedHead || "");

        return {
            repository: String(current.repository || ""),
            team: String(current.team || ""),
            branch: String(current.branch || ""),
            head: expectedHead,
            base: String(current.base || ""),
            baseHead: String(certification.candidateBaseHead || "")
        };
    }

    function beginRemoteDriftGate(gate) {
        if (!roomService) {
            bridgeError = String(gate || "")
                          + " // ROOM SERVICE MISSING";
            return false;
        }

        if (driftProbe.busy) {
            bridgeError = "REMOTE DRIFT CHECK // BUSY";
            return false;
        }

        const expected =
            expectedSnapshotForGate(String(gate || ""));

        pendingDriftGate = String(gate || "");
        bridgeError = "";

        const started = driftProbe.check(
            expected.repository,
            expected.team,
            expected
        );

        if (!started) {
            pendingDriftGate = "";
            bridgeError =
                driftProbe.lastError
                || "REMOTE DRIFT CHECK REFUSED";
            return false;
        }

        return true;
    }

    function recoverHostLease() {
        if (!roomService || !authority.hydrated) {
            hostLeaseId = "";
            return false;
        }

        const roomBranch = String(roomService.branch || "");
        const roomHead = String(roomService.head || "");

        if ((authority.ownerBranch && !roomBranch)
                || (authority.ownerHead && !roomHead)) {
            hostLeaseId = "";
            return false;
        }

        const recovered = authority.recoverLease(
            roomService.team,
            roomBranch,
            roomHead
        );

        hostLeaseId = String(recovered || "");

        if (!hostLeaseId
                && authority.ownerTeam === String(roomService.team || "")) {
            bridgeError =
                "HOST SLOT RECOVERY BLOCKED // SNAPSHOT MISMATCH";
            return false;
        }

        if (hostLeaseId
                && bridgeError.indexOf("HOST SLOT RECOVERY") === 0)
            bridgeError = "";

        return hostLeaseId.length > 0;
    }

    function bindRoom(service) {
        roomService = service;
        verificationPending = false;
        verificationRunId = "";
        pendingDriftGate = "";
        bridgeError = "";
        lastGitEvidence = ({});
        lastVerificationChecks = ({});
        pendingVerificationRuns = ({});

        if (!roomService) {
            certification.bindRoom("", "");
            return false;
        }

        certification.bindRoom(
            roomService.repository,
            roomService.team
        );

        recoverHostLease();
        return true;
    }

    function refreshBinding() {
        if (!roomService)
            return false;

        certification.bindRoom(
            roomService.repository,
            roomService.team
        );

        return true;
    }

    function prepare() {
        if (!roomService)
            return false;

        bridgeError = "";

        if (certification.state === "BLOCKED") {
            if (!certification.reopen(
                    "NEW PREPARE REQUEST",
                    roomService.certificationSnapshot()
                )) {
                bridgeError =
                    certification.lastError
                    || "PREPARE // REOPEN FAILED";
                return false;
            }
        } else if (certification.state !== "IDLE"
                && certification.state !== "REOPENED") {
            bridgeError =
                "PREPARE REFUSED // STATE "
                + certification.state;
            return false;
        }

        roomService.runInspection("prepare");
        return true;
    }

    function rehearse() {
        if (!roomService)
            return false;

        roomService.rehearsePrepared();
        return true;
    }

    function beginCandidate() {
        if (!roomService)
            return false;

        refreshBinding();
        return certification.beginCandidate(
            roomService.certificationSnapshot()
        );
    }

    function verify(checks, runs) {
        bridgeError =
            "VERIFY // DIRECT CHECK INJECTION DISABLED";
        return false;
    }

    function checksFromEvidence(packet) {
        const data = packet || {};
        const target = data.target || {};
        const github = data.github || {};
        const facts = data.facts || {};
        const completeness = data.completeness || {};
        const summary = facts.runSummary || {};
        const staleness = facts.staleness || {};
        const snapshot = roomService
                         ? roomService.certificationSnapshot()
                         : {};

        const schemaMatches =
            Number(data.schemaVersion || 0) === 1;
        const providerMatches =
            String(data.provider || "")
            === "post-apollo.git-evidence";

        const repositoryMatches =
            String(target.repository || "")
            === String(snapshot.repository || "");
        const shaMatches =
            String(target.sha || "")
            === String(snapshot.head || "");

        const total = Number(summary.total || 0);
        const success = Number(summary.success || 0);
        const active =
            Number(summary.queued || 0)
            + Number(summary.inProgress || 0);
        const failed =
            Number(summary.failure || 0)
            + Number(summary.cancelled || 0)
            + Number(summary.timedOut || 0)
            + Number(summary.otherConclusion || 0);

        let status = "PASS";
        let reason = "EXACT-SHA RUNS CLEAN";

        if (!schemaMatches || !providerMatches) {
            status = "ERROR";
            reason = "UNSUPPORTED GIT EVIDENCE CONTRACT";
        } else if (!repositoryMatches || !shaMatches) {
            status = "FAIL";
            reason = "EVIDENCE TARGET DOES NOT MATCH CANDIDATE";
        } else if (staleness.exactQueryTargetsRequestedSha === false) {
            status = "FAIL";
            reason = "EXACT-SHA QUERY TARGET DRIFT";
        } else if (staleness.inspectedRunTargetsRequestedSha === false) {
            status = "FAIL";
            reason = "INSPECTED RUN SHA DOES NOT MATCH CANDIDATE";
        } else if (String(completeness.requestError || "")) {
            status = "ERROR";
            reason = String(completeness.requestError);
        } else if (String(github.lastError || "")) {
            status = "ERROR";
            reason = String(github.lastError);
        } else if (!Boolean(completeness.githubAvailable)) {
            status = "ERROR";
            reason = "GITHUB EVIDENCE UNAVAILABLE";
        } else if (!Boolean(completeness.exactRunQuery)) {
            status = "WAITING";
            reason = "EXACT-SHA RUN QUERY NOT COMPLETE";
        } else if (String(completeness.inspectorError || "")) {
            status = "ERROR";
            reason = String(completeness.inspectorError);
        } else if (total <= 0) {
            status = "FAIL";
            reason = "NO EXACT-SHA WORKFLOW RUNS";
        } else if (active > 0) {
            status = "WAITING";
            reason = "WORKFLOW RUNS STILL ACTIVE";
        } else if (failed > 0) {
            status = "FAIL";
            reason = "WORKFLOW RUN FAILED";
        } else if (success !== total) {
            status = "FAIL";
            reason = "NOT ALL EXACT-SHA RUNS SUCCEEDED";
        }

        return {
            passed: status === "PASS",
            status: status,
            reason: reason,
            repositoryMatches: repositoryMatches,
            shaMatches: shaMatches,
            exactRunQuery: Boolean(completeness.exactRunQuery),
            totalRuns: total,
            successfulRuns: success,
            activeRuns: active,
            failedRuns: failed,
            schemaMatches: schemaMatches,
            providerMatches: providerMatches,
            provider: String(data.provider || ""),
            capturedAt: String(data.capturedAt || "")
        };
    }

    function runsFromEvidence(packet) {
        const data = packet || {};
        const github = data.github || {};
        const facts = data.facts || {};

        return {
            provider: String(data.provider || ""),
            capturedAt: String(data.capturedAt || ""),
            summary: facts.runSummary || {},
            matchingRuns:
                Array.isArray(github.matchingRuns)
                ? github.matchingRuns.slice()
                : [],
            inspectedRun: github.inspectedRun || null,
            completeness: data.completeness || {}
        };
    }

    function requestVerification(runId) {
        if (!roomService) {
            bridgeError = "VERIFY // ROOM SERVICE MISSING";
            return false;
        }

        if (!certification.canVerify) {
            bridgeError =
                certification.lastError
                || "VERIFY // CANDIDATE REQUIRED";
            return false;
        }

        if (!evidenceProvider
                || typeof evidenceProvider.requestEvidence
                    !== "function") {
            bridgeError = "VERIFY // GIT EVIDENCE PROVIDER MISSING";
            return false;
        }

        verificationRunId = String(runId || "");
        return beginRemoteDriftGate("VERIFY");
    }

    function startEvidenceRequest() {
        if (!evidenceProvider
                || typeof evidenceProvider.requestEvidence
                    !== "function") {
            bridgeError = "VERIFY // GIT EVIDENCE PROVIDER MISSING";
            return false;
        }

        verificationPending = true;
        bridgeError = "";

        const started = evidenceProvider.requestEvidence(
            certification.candidateHead,
            verificationRunId
        );

        if (!started) {
            verificationPending = false;
            bridgeError =
                String(evidenceProvider.requestError || "")
                || "VERIFY // EVIDENCE REQUEST REFUSED";
            return false;
        }

        return true;
    }

    function verifyEvidencePacket(packet) {
        if (!roomService || !certification.canVerify) {
            bridgeError = "VERIFY // CANDIDATE NOT READY";
            return false;
        }

        const checks = checksFromEvidence(packet);
        const runs = runsFromEvidence(packet);

        lastGitEvidence =
            JSON.parse(JSON.stringify(packet || {}));
        lastVerificationChecks =
            JSON.parse(JSON.stringify(checks));
        pendingVerificationRuns =
            JSON.parse(JSON.stringify(runs));

        verificationEvidenceReady(
            lastVerificationChecks,
            lastGitEvidence
        );

        if (checks.status === "WAITING") {
            bridgeError = checks.reason;
            return false;
        }

        if (checks.status !== "PASS") {
            const rejected = certification.verifyCandidate(
                roomService.certificationSnapshot(),
                checks,
                runs
            );

            bridgeError = rejected
                          ? ""
                          : certification.lastError;
            return rejected;
        }

        return beginRemoteDriftGate("VERIFY_FINAL");
    }

    function completeEvidenceVerification() {
        if (!roomService || !certification.canVerify) {
            bridgeError = "VERIFY // CANDIDATE NOT READY";
            return false;
        }

        if (String(lastVerificationChecks.status || "")
                !== "PASS") {
            bridgeError =
                "VERIFY // PASSING EVIDENCE REQUIRED";
            return false;
        }

        const accepted = certification.verifyCandidate(
            roomSnapshot(),
            lastVerificationChecks,
            pendingVerificationRuns
        );

        bridgeError = accepted
                      ? ""
                      : certification.lastError;

        return accepted;
    }

    function certify() {
        if (!roomService)
            return false;

        if (!certification.canCertify) {
            bridgeError =
                certification.lastError
                || "CERTIFY // VERIFIED STATE REQUIRED";
            return false;
        }

        return beginRemoteDriftGate("CERTIFY");
    }

    function certifyAfterDrift() {
        const accepted = certification.certifyVerified(
            roomSnapshot()
        );

        bridgeError = accepted
                      ? ""
                      : certification.lastError;
        return accepted;
    }

    function arm() {
        if (!roomService)
            return false;

        if (!certification.canArm) {
            bridgeError =
                certification.lastError
                || "ARM // CERTIFICATION REQUIRED";
            return false;
        }

        return beginRemoteDriftGate("ARM");
    }

    function armAfterDrift() {
        if (!roomService)
            return false;

        if (!hostSlotOwned) {
            if (!authority.acquireSlot(
                    roomService.team,
                    roomService.branch,
                    roomService.head,
                    "CERTIFICATION ARMED"
                )) {
                bridgeError = authority.lastError;
                return false;
            }

            hostLeaseId = authority.ownerLeaseId;
        }

        if (!certification.armCertified(
                roomService.certificationSnapshot()
            )) {
            if (hostSlotOwned) {
                authority.releaseSlot(
                    roomService.team,
                    hostLeaseId,
                    "CERTIFICATION ARM FAILED"
                );
                hostLeaseId = "";
            }

            bridgeError = certification.lastError;
            return false;
        }

        const armed = roomService.armPrepared();

        if (!armed) {
            if (hostSlotOwned) {
                authority.releaseSlot(
                    roomService.team,
                    hostLeaseId,
                    "ROOM ARM FAILED"
                );
                hostLeaseId = "";
            }

            certification.reopen(
                "ROOM ARM FAILED",
                roomService.certificationSnapshot()
            );

            bridgeError =
                String(roomService.lastError || roomService.summary || "")
                || certification.lastError;
            return false;
        }

        bridgeError = "";
        return true;
    }

    function integrate() {
        if (!roomService)
            return false;

        if (!hostSlotOwned) {
            certification.lastError =
                "INTEGRATE REFUSED // HOST SLOT NOT OWNED";
            return false;
        }

        if (!certification.beginIntegration(
                roomService.certificationSnapshot()
            ))
            return false;

        roomService.integrateArmed();
        return true;
    }

    function beginPostOp() {
        if (!roomService)
            return false;

        return certification.beginPostOp(
            roomService.postOpSnapshot()
        );
    }

    function completePostOp() {
        if (!roomService)
            return false;

        return certification.completePostOp(
            roomService.postOpSnapshot()
        );
    }

    function reopen(reason) {
        if (!roomService)
            return false;

        const reopened = certification.reopen(
            reason || "ROOM REOPENED",
            roomService.certificationSnapshot()
        );

        if (reopened && hostSlotOwned) {
            authority.releaseSlot(
                roomService.team,
                hostLeaseId,
                "ROOM REOPENED"
            );
            hostLeaseId = "";
        }

        return reopened;
    }
}
