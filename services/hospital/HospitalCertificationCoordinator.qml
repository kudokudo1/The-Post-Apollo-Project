import QtQuick
import Quickshell

Scope {
    id: coordinator

    property var roomService: null

    HospitalOperatingAuthorityService {
        id: authority
    }

    property string hostLeaseId: ""

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
    readonly property string lastError: certification.lastError
    readonly property string lastReason: certification.lastReason

    readonly property bool canVerify: certification.canVerify
    readonly property bool canCertify: certification.canCertify
    readonly property bool canArm: certification.canArm
    readonly property bool canIntegrate: certification.canIntegrate

    readonly property var evidencePacket:
        certification.evidencePacket

    signal certificationChanged(
        string previousState,
        string nextState,
        string eventType)
    signal certificationBlocked(string reason)

    Connections {
        target: coordinator.roomService

        function onInspected() {
            if (!coordinator.roomService)
                return;

            if (String(coordinator.roomService.action || "") !== "PREPARE")
                return;

            coordinator.refreshBinding();
            coordinator.certification.beginCandidate(
                coordinator.roomService.certificationSnapshot()
            );
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

    function bindRoom(service) {
        roomService = service;

        if (!roomService) {
            certification.bindRoom("", "");
            return false;
        }

        certification.bindRoom(
            roomService.repository,
            roomService.team
        );

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
        if (!roomService)
            return false;

        return certification.verifyCandidate(
            roomService.certificationSnapshot(),
            checks || {},
            runs || {}
        );
    }

    function certify() {
        if (!roomService)
            return false;

        return certification.certifyVerified(
            roomService.certificationSnapshot()
        );
    }

    function arm() {
        if (!roomService)
            return false;

        if (hostSlotOwned)
            return roomService.armPrepared();

        if (!authority.acquireSlot(
                roomService.team,
                roomService.branch,
                roomService.head,
                "CERTIFICATION ARMED"
            )) {
            return false;
        }

        hostLeaseId = authority.ownerLeaseId;

        if (!certification.armCertified(
                roomService.certificationSnapshot()
            )) {
            authority.releaseSlot(
                roomService.team,
                hostLeaseId,
                "CERTIFICATION ARM FAILED"
            );
            hostLeaseId = "";
            return false;
        }

        const armed = roomService.armPrepared();

        if (!armed) {
            authority.releaseSlot(
                roomService.team,
                hostLeaseId,
                "ROOM ARM FAILED"
            );
            hostLeaseId = "";

            certification.reopen(
                "ROOM ARM FAILED",
                roomService.certificationSnapshot()
            );

            return false;
        }

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
