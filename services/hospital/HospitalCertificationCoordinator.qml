import QtQuick
import Quickshell

Scope {
    id: coordinator

    property var roomService: null

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

        if (!certification.armCertified(
                roomService.certificationSnapshot()
            ))
            return false;

        return roomService.armPrepared();
    }

    function integrate() {
        if (!roomService)
            return false;

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

        return certification.reopen(
            reason || "ROOM REOPENED",
            roomService.certificationSnapshot()
        );
    }
}
