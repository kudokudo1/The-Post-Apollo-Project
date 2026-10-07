import QtQuick
import Quickshell

Scope {
    id: root

    property var roundsService: null
    property var registryService: null
    property var assignmentService: null
    property string currentRoomId: ""

    function normalized(value) {
        return String(value || "")
            .trim()
            .toLowerCase();
    }

    function roomScore(roomValue, repositoryValue, branchValue) {
        const room = roomValue || {};
        const repository = root.normalized(repositoryValue);
        const branch = root.normalized(branchValue);
        const roomRepository = root.normalized(room.repository);
        const roomBranch = root.normalized(room.branch);
        const roomTeam = root.normalized(room.team);
        const responsibility = root.normalized(room.responsibility);
        let score = 0;
        const reasons = [];

        if (repository && roomRepository === repository) {
            score += 60;
            reasons.push("REPOSITORY");
        }

        if (branch && roomBranch && roomBranch === branch) {
            score += 40;
            reasons.push("BRANCH");
        } else if (branch && roomTeam && roomTeam === branch) {
            score += 30;
            reasons.push("TEAM");
        } else if (branch
                && responsibility
                && responsibility === branch) {
            score += 20;
            reasons.push("RESPONSIBILITY");
        }

        return {
            score: score,
            reasons: reasons
        };
    }

    function bestRoom(repositoryValue, branchValue) {
        const rows =
            roundsService && Array.isArray(roundsService.rooms)
            ? roundsService.rooms
            : [];
        let best = null;
        let bestScore = 0;
        let bestReasons = [];

        for (let i = 0; i < rows.length; ++i) {
            const room = rows[i] || {};
            const scored = root.roomScore(
                room,
                repositoryValue,
                branchValue
            );

            if (scored.score > bestScore) {
                best = room;
                bestScore = scored.score;
                bestReasons = scored.reasons;
            }
        }

        return {
            room: best,
            score: bestScore,
            reasons: bestReasons
        };
    }

    function specialistMatch(recordValue, roomValue) {
        const record = recordValue || {};
        const room = roomValue || {};
        const assignment = root.normalized(record.assignment);

        if (!assignment || assignment === "unassigned")
            return false;

        const needles = [
            room.team,
            room.responsibility,
            room.branch,
            room.repository
        ].map(function(value) {
            return root.normalized(value);
        }).filter(function(value) {
            return value.length > 0;
        });

        for (let i = 0; i < needles.length; ++i) {
            if (assignment === needles[i]
                    || assignment.indexOf(needles[i]) >= 0
                    || needles[i].indexOf(assignment) >= 0)
                return true;
        }

        return false;
    }

    function specialistsForRoom(roomValue) {
        const rows =
            registryService && Array.isArray(registryService.specialists)
            ? registryService.specialists
            : [];
        const out = [];

        for (let i = 0; i < rows.length; ++i) {
            const record = rows[i] || {};
            if (!root.specialistMatch(record, roomValue))
                continue;

            out.push({
                id: String(record.id || ""),
                name: String(record.name || record.id || "SPECIALIST"),
                role: String(record.role || "SPECIALIST"),
                provider: String(record.provider || ""),
                presence: String(record.presence || "UNKNOWN"),
                assignment: String(record.assignment || "")
            });
        }

        return out;
    }

    function activeAssignmentForRoom(roomValue) {
        const room = roomValue || {};
        const team = String(room.team || "").trim();
        const selected = String(currentRoomId || "").trim();

        if (!assignmentService
                || !team
                || team !== selected)
            return null;

        return assignmentService.activeAssignment || null;
    }

    function confidenceLabel(scoreValue) {
        const score = Number(scoreValue || 0);
        if (score >= 100)
            return "EXACT";
        if (score >= 80)
            return "STRONG";
        if (score >= 60)
            return "REPOSITORY";
        if (score > 0)
            return "PARTIAL";
        return "UNMAPPED";
    }

    function contextFor(repositoryValue, branchValue) {
        const repository = String(repositoryValue || "").trim();
        const branch = String(branchValue || "").trim();
        const matched = root.bestRoom(repository, branch);
        const room = matched.room || null;
        const specialists = room
            ? root.specialistsForRoom(room)
            : [];
        const assignment = room
            ? root.activeAssignmentForRoom(room)
            : null;
        const roomTeam = room ? String(room.team || "") : "";
        const responsibility =
            room ? String(room.responsibility || "") : "";
        const specialistNames = specialists.map(function(row) {
            return String(row.name || row.id || "SPECIALIST");
        });

        let ownerLabel = "UNMAPPED";
        if (specialistNames.length > 0)
            ownerLabel = specialistNames.join(", ");
        else if (roomTeam)
            ownerLabel = roomTeam;
        else if (responsibility)
            ownerLabel = responsibility;

        return {
            repository: repository,
            branch: branch,
            confidence: root.confidenceLabel(matched.score),
            score: matched.score,
            reasons: matched.reasons,
            roomTeam: roomTeam,
            roomResponsibility: responsibility,
            roomBranch: room ? String(room.branch || "") : "",
            roomState: room ? String(room.state || "") : "",
            floorLabel: room ? String(room.floorLabel || "") : "",
            specialists: specialists,
            specialistNames: specialistNames,
            ownerLabel: ownerLabel,
            assignmentId:
                assignment ? String(assignment.id || "") : "",
            assignmentTitle:
                assignment ? String(assignment.title || "") : "",
            assignmentGoal:
                assignment ? String(assignment.goal || "") : "",
            assignmentPhase:
                assignment ? String(assignment.phase || "") : "",
            assignmentPermissions:
                assignment && Array.isArray(assignment.permissions)
                ? assignment.permissions.slice()
                : []
        };
    }
}
